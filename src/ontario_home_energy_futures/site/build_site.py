"""Render all 12 pages to static HTML using Jinja2, plus copy static assets
and generate downloadable JSON/CSV scenario results.

Builds entirely offline from committed fixtures (see README "Building the
static site").
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..model.collective_purchasing import apply_collective_purchase
from ..model.cost_of_inaction import DecisionCostInputs, calculate_cost_of_inaction
from ..model.financing import QuoteComponents, amortize_loan
from ..model.scenario import DeclineScenario, PriceScenario, evaluate_grid_only, evaluate_solar_purchase
from ..model.value_streams import ValueStreamStatus, filter_by_status
from ..model.waiting import find_breakeven_decline_rate, format_breakeven_statement
from .context import SiteData, cad, pct


def _make_env(templates_dir: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _price_scenario_obj(raw: dict) -> PriceScenario:
    return PriceScenario(
        id=raw["id"],
        label=raw["label"],
        electricity_energy_real=raw["annual_changes"]["electricity_energy_real"],
        fixed_delivery_real=raw["annual_changes"]["fixed_delivery_real"],
        variable_delivery_real=raw["annual_changes"]["variable_delivery_real"],
        general_inflation=raw["annual_changes"]["general_inflation"],
    )


def _decline_scenario_obj(raw: dict) -> DeclineScenario:
    return DeclineScenario(
        id=raw["label"].lower().replace(" ", "-"),
        label=raw["label"],
        real_annual_installed_cost_change=raw["real_annual_installed_cost_change"],
    )


def _build_comparison_rows(data: SiteData, *, household_kwh: int = 700, horizon_years: int = 20) -> dict:
    reference = next(s for s in data.price_scenarios if s["label"] == "Reference")
    flat_decline = next(s for s in data.decline_scenarios if s["label"] == "Flat")
    price_scenario = _price_scenario_obj(reference)
    decline_scenario = _decline_scenario_obj(flat_decline)

    monthly_bill = data.rate_structure.fixed_delivery_charge_cad_per_day * 30.4 + household_kwh * 0.10
    annual_bill = monthly_bill * 12

    quote_shares = data.solar["cost_components"]
    reference_quote_total = data.solar["illustrative_reference_quote"]["installed_price_before_tax_cad"]
    from ..model.financing import quote_from_total

    base_quote = quote_from_total(reference_quote_total, quote_shares)

    common_kwargs = dict(
        base_annual_bill_cad=annual_bill,
        price_scenario=price_scenario,
        decline_scenario=decline_scenario,
        base_quote=base_quote,
        tax_rate=data.ontario["hst_rate"],
        down_payment_fraction=data.financing["loan"]["default_down_payment_fraction"],
        annual_interest_rate=data.financing["loan"]["default_annual_interest_rate"],
        loan_term_years=data.financing["loan"]["default_term_years"],
        horizon_years=horizon_years,
        discount_rate=data.ontario["discount_rate_default"],
        fixed_share=0.30,
        variable_share=0.15,
        energy_share=0.55,
        annual_grid_bill_after_solar_cad=annual_bill * 0.35,
        annual_maintenance_cad=data.solar["maintenance"]["annual_maintenance_cad_default"],
        inverter_replacement_year=data.solar["maintenance"]["inverter_replacement_year_default"],
        inverter_replacement_cost_cad=data.solar["maintenance"]["inverter_replacement_cost_cad_default"],
        annual_credits_used_cad=annual_bill * 0.30,
        total_credits_expired_cad=0.0,
        total_solar_generation_kwh=9000.0,
        total_grid_imports_kwh=household_kwh * 12 * 0.4,
    )

    grid_only = evaluate_grid_only(
        base_annual_bill_cad=annual_bill,
        price_scenario=price_scenario,
        horizon_years=horizon_years,
        discount_rate=data.ontario["discount_rate_default"],
        fixed_share=0.30,
        variable_share=0.15,
        energy_share=0.55,
    )
    buy_now = evaluate_solar_purchase(label="Buy solar now", purchase_year_offset=0, group_discount_fraction=0.0, is_cash=True, **common_kwargs)
    buy_now_5pct = evaluate_solar_purchase(label="Buy now, 5% group discount", purchase_year_offset=0, group_discount_fraction=0.05, is_cash=True, **common_kwargs)
    buy_now_10pct = evaluate_solar_purchase(label="Buy now, 10% group discount", purchase_year_offset=0, group_discount_fraction=0.10, is_cash=True, **common_kwargs)
    wait_3yr = evaluate_solar_purchase(label="Wait 3 years", purchase_year_offset=3, group_discount_fraction=0.0, is_cash=True, **common_kwargs)
    financed_now = evaluate_solar_purchase(label="Buy now, financed", purchase_year_offset=0, group_discount_fraction=0.0, is_cash=False, **common_kwargs)

    decisions = [grid_only, buy_now, buy_now_5pct, buy_now_10pct, wait_3yr, financed_now]

    rows = []
    for d in decisions:
        cost_10yr = sum(f.total_nominal_cad for f in d.annual_cash_flows[:10])
        rows.append(
            {
                "label": d.label,
                "initial_cost": cad(d.initial_cost_cad),
                "financing_interest": cad(d.financing_interest_cad),
                "cost_10yr": cad(cost_10yr),
                "cost_20yr": cad(d.total_nominal_cad),
                "grid_imports_kwh": f"{d.total_grid_imports_kwh:,.0f}",
                "uncertainty_range": "See sensitivity table below",
            }
        )

    totals = [d.total_nominal_cad for d in decisions if d.label != "Grid only"]
    range_low = min(totals)
    range_high = max(totals)

    def npv_cost_for_rate(rate: float) -> float:
        ds = DeclineScenario(id="sweep", label="sweep", real_annual_installed_cost_change=rate)
        result = evaluate_solar_purchase(
            label="sweep", purchase_year_offset=3, group_discount_fraction=0.0, is_cash=True,
            **{**common_kwargs, "decline_scenario": ds},
        )
        return result.total_present_value_cad

    breakeven = find_breakeven_decline_rate(
        npv_cost_for_decline_rate=npv_cost_for_rate, npv_cost_buy_now=buy_now.total_present_value_cad
    )
    waiting_statement = format_breakeven_statement(
        breakeven_rate=breakeven, wait_years=3, wait_until_year=2029, buy_now_year=2026
    )

    cost_of_inaction_rows = _build_cost_of_inaction_rows([grid_only, buy_now, wait_3yr])
    collective_purchasing_rows = _build_collective_purchasing_rows(data, base_quote=base_quote, tax_rate=data.ontario["hst_rate"])

    return {
        "rows": rows,
        "caption": f"20-year comparison, {household_kwh} kWh/month household, reference price scenario, flat solar-cost-decline scenario",
        "range_low_formatted": cad(range_low),
        "range_high_formatted": cad(range_high),
        "waiting_statement": waiting_statement,
        "horizon_years": horizon_years,
        "household_profile_kwh": household_kwh,
        "price_scenario_label": "Reference",
        "decline_scenario_label": "Flat",
        "cost_of_inaction_rows": cost_of_inaction_rows,
        "collective_purchasing_rows": collective_purchasing_rows,
    }


def _build_cost_of_inaction_rows(decisions: list) -> list[dict]:
    """Itemized cost-of-inaction breakdown for grid-only / buy-now / wait-N,
    using model/cost_of_inaction.py against the SAME DecisionResult objects
    already computed above - no new cash-flow math, and never assumes "buy
    now" is the cheapest (the underlying calculate_cost_of_inaction finds
    the minimum empirically; see that module's docstring and
    tests/unit/test_cost_of_inaction.py).

    Phase 1's DecisionResult does not track incentives, grid-service
    revenue, or residual value (those are Phase 2 concepts - see
    model/scenario_v2.py), so those inputs are 0.0 here, which accurately
    reflects what Phase 1 computes rather than standing in as a
    placeholder for a number that exists elsewhere.
    """
    inputs = [
        DecisionCostInputs(
            label=d.label,
            total_nominal_cad=d.total_nominal_cad,
            total_present_value_cad=d.total_present_value_cad,
            grid_imports_kwh=d.total_grid_imports_kwh,
            solar_generation_kwh=d.total_solar_generation_kwh,
            incentives_received_cad=0.0,
            grid_service_revenue_cad=0.0,
            residual_value_cad=0.0,
        )
        for d in decisions
    ]
    breakdowns = calculate_cost_of_inaction(inputs)

    rows = []
    for d in decisions:
        b = breakdowns[d.label]
        rows.append(
            {
                "label": b.decision_label,
                "additional_nominal_cost": cad(b.additional_nominal_cost_cad),
                "additional_present_value": cad(b.additional_present_value_cad),
                "grid_purchased_while_waiting_kwh": f"{b.grid_electricity_purchased_while_waiting_kwh:,.0f}",
                "solar_forgone_kwh": f"{b.solar_generation_forgone_kwh:,.0f}",
                "incentives_forgone": cad(b.current_incentives_forgone_cad),
                "revenue_forgone": cad(b.currently_available_revenue_forgone_cad),
                "residual_value_difference": cad(b.residual_value_difference_cad),
                "emissions_note": b.emissions_consequence_note,
            }
        )
    return rows


def _build_collective_purchasing_rows(data: SiteData, *, base_quote: QuoteComponents, tax_rate: float) -> list[dict]:
    """Real household-count-tier collective-purchasing comparison using
    model/collective_purchasing.py, replacing the arbitrary 0-20%
    discount slider with the actual tiered model
    (assumptions/collective_purchasing.yaml): individual / 5 / 10 / 20
    households, each with its own per-component reduction percentages and
    an overall discount cap.
    """
    base_costs_by_component = {
        "hardware": base_quote.panels + base_quote.inverter + base_quote.racking + base_quote.electrical_equipment,
        "labour": base_quote.labour,
        "design": base_quote.design_and_engineering,
        "permitting": base_quote.permitting,
        "customer_acquisition": base_quote.installer_overhead,
        "financing_fees": 0.0,
    }

    rows = []
    for tier_id in ("individual", "group_5", "group_10", "group_20"):
        tier = data.collective_tiers[tier_id]
        result = apply_collective_purchase(tier=tier, base_costs_by_component=base_costs_by_component)
        total_with_tax = result.total_reduced_cost * (1 + tax_rate)
        rows.append(
            {
                "label": tier.label,
                "households": tier.households,
                "initial_cost": cad(total_with_tax),
                "one_time_savings": cad(result.total_reduction_cad),
                "effective_discount_pct": f"{result.effective_discount_percent:.1f}%",
                "capped": result.capped,
            }
        )
    return rows


_CURRENT_STATUSES = {ValueStreamStatus.CURRENT}
_NOT_CURRENTLY_AVAILABLE_STATUSES = {
    ValueStreamStatus.PILOT,
    ValueStreamStatus.PROPOSED,
    ValueStreamStatus.DEMONSTRATED_ELSEWHERE,
    ValueStreamStatus.ILLUSTRATIVE_SCENARIO,
    ValueStreamStatus.CLOSED,
}

_STATUS_LABELS = {
    ValueStreamStatus.CURRENT: "Current",
    ValueStreamStatus.CLOSED: "Closed to new participants",
    ValueStreamStatus.PILOT: "Pilot",
    ValueStreamStatus.PROPOSED: "Proposed",
    ValueStreamStatus.DEMONSTRATED_ELSEWHERE: "Demonstrated elsewhere",
    ValueStreamStatus.ILLUSTRATIVE_SCENARIO: "Illustrative scenario",
}


_SOURCE_TYPE_FALLBACK = {
    "model": "Calculated by this tool's model, not an external published rate",
    "illustrative": "Illustrative example value, not a published rate",
}


def _value_stream_row(stream) -> dict:
    return {
        "id": stream.id,
        "name": stream.name,
        "category": stream.category.replace("_", " "),
        "status_label": _STATUS_LABELS.get(stream.status, stream.status.value),
        "verified_at": stream.verified_at,
        "eligibility_summary": (
            ("aggregator required, " if stream.eligibility.aggregator_required else "")
            + ("solar required, " if stream.eligibility.solar_required else "")
            + ("battery required, " if stream.eligibility.battery_required else "")
            + ("bidirectional EV allowed" if stream.eligibility.bidirectional_ev_allowed else "")
        ).strip(", ") or "no special equipment required",
        "combinable": "Yes" if stream.combinable_with_other_streams else "No",
        "source_type": stream.source.type,
        "source_url": stream.source.url,
        "source_title": stream.source.title or stream.source.url or _SOURCE_TYPE_FALLBACK.get(
            stream.source.type, "See methodology"
        ),
    }


def _build_value_streams_context(data: SiteData) -> dict:
    """Context for value-streams.html: every value stream from
    assumptions/value_streams/*.yaml, grouped by availability status so
    the project's own governance commitment (only `current`-status
    streams appear in a default result - see MODEL_CARD.md) is visible
    and checkable on the site itself, not just true in code. Streams with
    status `unsupported` are excluded entirely, per
    model/value_streams.py::ValueStreamStatus semantics - none currently
    exist in the fixture set (see tests/unit/test_value_streams.py), but
    this filter is applied explicitly rather than relied upon by omission.
    """
    all_streams = list(data.value_streams.values())
    current_streams = [s for s in all_streams if s.status in _CURRENT_STATUSES]
    not_available_streams = [s for s in all_streams if s.status in _NOT_CURRENTLY_AVAILABLE_STATUSES]

    return {
        "current_value_stream_rows": [_value_stream_row(s) for s in sorted(current_streams, key=lambda s: s.name)],
        "not_available_value_stream_rows": [
            _value_stream_row(s) for s in sorted(not_available_streams, key=lambda s: s.name)
        ],
        "total_stream_count": len(all_streams),
        "current_stream_count": len(current_streams),
    }


def build_site(repo_root: Path, output_dir: Path) -> Path:
    """Build the full static site into ``output_dir``. Offline, deterministic."""
    templates_dir = repo_root / "web" / "templates"
    static_dir = repo_root / "web" / "static"

    output_dir.mkdir(parents=True, exist_ok=True)
    env = _make_env(templates_dir)
    data = SiteData(repo_root)

    static_out = output_dir / "static"
    if static_out.exists():
        shutil.rmtree(static_out)
    shutil.copytree(static_dir, static_out)

    data_out = output_dir / "data"
    data_out.mkdir(parents=True, exist_ok=True)
    observations_csv = repo_root / "data" / "observations.csv"
    if observations_csv.exists():
        shutil.copy(observations_csv, data_out / "observations.csv")

    base_ctx = data.base_context(asset_prefix="")
    standard_profiles = data.standard_profile_rows()
    tiered_profiles = data.tiered_profile_rows()
    price_scenarios = data.price_scenario_summaries()
    decline_scenarios = data.decline_scenario_summaries()
    comparison = _build_comparison_rows(data)

    ledger_example = data.net_metering_ledger_example()

    pages: dict[str, dict] = {
        "index.html": {
            **base_ctx,
            "standard_profiles": standard_profiles,
        },
        "current-costs.html": {
            **base_ctx,
            "standard_profiles": standard_profiles,
            "tiered_profiles": tiered_profiles,
            "bill_period": "August 2026",
        },
        "household.html": {
            **base_ctx,
            "standard_profiles": standard_profiles,
            "ev_default_annual_km": data.household_loads["electric_vehicle"]["default_annual_km"],
            "ev_default_efficiency": data.household_loads["electric_vehicle"]["default_efficiency_kwh_per_100km"],
            "ev_default_home_share_pct": int(data.household_loads["electric_vehicle"]["default_home_charging_share"] * 100),
            "hp_default_heating_kwh": data.household_loads["heat_pump"]["climate_regions"][0]["default_annual_heating_kwh_equivalent"],
            "hp_default_cop": data.household_loads["heat_pump"]["default_seasonal_cop"],
        },
        "compare-timing.html": {
            **base_ctx,
            **comparison,
            "price_scenarios": price_scenarios,
            "decline_scenarios": decline_scenarios,
            "planning_horizons": data.ontario["planning_horizons_years"],
            # NOT computed from the user's current inputs - see
            # docs/RED-TEAM-REVIEW.md section 8.4 and
            # docs/CORRECTIONS.md. This is a static, illustrative example
            # of the kind of assumption that typically has the largest
            # effect on a 20-year total, pending the real computed
            # sensitivity module (model/sensitivity.py, not yet built).
            # The template must present this as illustrative, never as
            # "for the current inputs" - see
            # tests/unit/test_build_site_honesty.py.
            "sensitivity_rows": [
                {"assumption": "Electricity-price scenario", "low": "Low", "high": "Stress", "effect": "Largest"},
                {"assumption": "Solar installed cost", "low": "-10%", "high": "+10%", "effect": "Large"},
                {"assumption": "Group discount", "low": "0%", "high": "10%", "effect": "Moderate"},
                {"assumption": "Financing rate", "low": "3%", "high": "10%", "effect": "Moderate"},
                {"assumption": "Discount rate", "low": "2%", "high": "6%", "effect": "Small-moderate"},
            ],
            "sensitivity_rows_are_illustrative": True,
            "print_url": "compare-timing.html",
        },
        "net-metering.html": {
            **base_ctx,
            "illustrative_quote": {
                "system_kw_dc": data.solar["illustrative_reference_quote"]["system_kw_dc"],
                "installed_price_before_tax": data.solar["illustrative_reference_quote"]["installed_price_before_tax_cad"],
            },
            "ledger_example_intro": (
                "A 7.2 kW system against a 700 kWh/month household, illustrating "
                "how exports become non-cash credit, and how that credit can "
                "expire unused."
            ),
            "example_system_kw": ledger_example["system_kw"],
            "ledger_rows": ledger_example["rows"],
            "effective_value_per_kwh_formatted": f"{ledger_example['effective_value_per_kwh'] * 100:.2f}¢/kWh",
            "retail_rate_formatted": f"{ledger_example['retail_rate'] * 100:.2f}¢/kWh",
        },
        "battery-generator.html": {
            **base_ctx,
            "battery": {
                "usable_capacity_kwh": data.batteries["illustrative_reference_battery"]["usable_capacity_kwh"],
                "max_continuous_output_kw": data.batteries["illustrative_reference_battery"]["max_continuous_output_kw"],
                "round_trip_efficiency_pct": pct(data.batteries["illustrative_reference_battery"]["round_trip_efficiency"]),
                "purchase_and_installation_formatted": cad(data.batteries["illustrative_reference_battery"]["purchase_and_installation_cad"]),
                "warranty_years": data.batteries["illustrative_reference_battery"]["warranty_years"],
            },
            "generator": {
                "fuel_type": data.generators["illustrative_reference_generator"]["fuel_type"].replace("_", " "),
                "purchase_formatted": cad(data.generators["illustrative_reference_generator"]["purchase_cad"]),
                "installation_formatted": cad(
                    data.generators["illustrative_reference_generator"]["installation_cad"]
                    + data.generators["illustrative_reference_generator"]["transfer_switch_cad"]
                ),
                "maintenance_formatted": cad(data.generators["illustrative_reference_generator"]["exercise_and_maintenance_annual_cad"]),
                "automatic_or_manual": data.generators["illustrative_reference_generator"]["automatic_or_manual"],
            },
        },
        "assumptions.html": {
            **base_ctx,
            "price_scenarios": price_scenarios,
            "decline_scenarios": decline_scenarios,
            "demand_low_pct": pct(data.ontario["provincial_demand_scenarios"]["growth_to_2050"]["low"]),
            "demand_reference_pct": pct(data.ontario["provincial_demand_scenarios"]["growth_to_2050"]["reference"]),
            "demand_high_pct": pct(data.ontario["provincial_demand_scenarios"]["growth_to_2050"]["high"]),
            "net_metering_expiry_months": data.ontario["net_metering"]["credit_expiry_months"],
            "net_metering_eligible_categories": ", ".join(data.ontario["net_metering"]["eligible_charge_categories"]),
            "net_metering_ineligible_categories": ", ".join(data.ontario["net_metering"]["ineligible_charge_categories"]),
            "ev_default_efficiency": data.household_loads["electric_vehicle"]["default_efficiency_kwh_per_100km"],
            "ev_default_annual_km": data.household_loads["electric_vehicle"]["default_annual_km"],
            "hp_default_cop": data.household_loads["heat_pump"]["default_seasonal_cop"],
            "hp_default_heating_kwh": data.household_loads["heat_pump"]["climate_regions"][0]["default_annual_heating_kwh_equivalent"],
            "solar_degradation_pct": pct(data.solar["production"]["degradation_annual_default"]),
            "loan_rate_pct": pct(data.financing["loan"]["default_annual_interest_rate"]),
            "loan_term_years": data.financing["loan"]["default_term_years"],
            "discount_rate_pct": pct(data.ontario["discount_rate_default"]),
        },
        "data-sources.html": {
            **base_ctx,
            "sources": [
                {"title": "OEB BillData.xml (fixture)", "publisher": "Ontario Energy Board", "status": "Illustrative fixture", "retrieved_at": "2026-08-02", "url": "https://www.oeb.ca/_html/calculator/data/BillData.xml"},
                {"title": "Historical RPP rates", "publisher": "Ontario Energy Board", "status": "Not yet integrated", "retrieved_at": "N/A", "url": "https://www.oeb.ca/open-data/historical-regulated-price-plan-electricity-rates"},
                {"title": "Net metering rules", "publisher": "Ontario Energy Board / Government of Ontario", "status": "Observed", "retrieved_at": "2026-08-02", "url": "https://www.oeb.ca/consumer-information-and-protection/net-metering"},
                {"title": "Hydro Ottawa net metering bill sample", "publisher": "Hydro Ottawa", "status": "Observed", "retrieved_at": "2026-08-02", "url": "https://hydroottawa.com/en/residential/rates-billing/your-bill-and-rates-explained/net-metering-bill-sample"},
                {"title": "Electric Power Selling Price Index", "publisher": "Statistics Canada", "status": "Not yet integrated", "retrieved_at": "N/A", "url": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810020401"},
                {"title": "2026 Annual Planning Outlook", "publisher": "IESO", "status": "Recorded, pending verification", "retrieved_at": "2026-08-02", "url": "https://www.ieso.ca/-/media/Files/IESO/Document-Library/planning-forecasts/apo/2026/2026-Annual-Planning-Outlook.pdf"},
            ],
        },
        "methodology.html": {**base_ctx},
        "download.html": {
            **base_ctx,
            "downloadable_scenarios": [
                {"label": "Low", "slug": "low"},
                {"label": "Reference", "slug": "reference"},
                {"label": "High", "slug": "high"},
                {"label": "Stress", "slug": "stress"},
            ],
        },
        "accessibility.html": {**base_ctx},
        "about.html": {**base_ctx},
        "value-streams.html": {
            **base_ctx,
            **_build_value_streams_context(data),
        },
    }

    template_name_map = {
        "index.html": "index.html",
        "current-costs.html": "current_costs.html",
        "household.html": "household.html",
        "compare-timing.html": "compare_timing.html",
        "net-metering.html": "net_metering.html",
        "battery-generator.html": "battery_generator.html",
        "assumptions.html": "assumptions.html",
        "data-sources.html": "data_sources.html",
        "methodology.html": "methodology.html",
        "download.html": "download.html",
        "accessibility.html": "accessibility.html",
        "about.html": "about.html",
        "value-streams.html": "value_streams.html",
    }

    for output_name, ctx in pages.items():
        template = env.get_template(template_name_map[output_name])
        rendered = template.render(**ctx)
        (output_dir / output_name).write_text(rendered, encoding="utf-8")

    _write_scenario_downloads(data, data_out)
    _write_calculator_data(data, data_out)

    return output_dir


def _write_calculator_data(data: SiteData, data_out: Path) -> None:
    """Emit the assumption values the client-side calculator
    (web/static/calculator.js) needs, generated from the SAME YAML-loading
    code (SiteData) the server-rendered pages use - one place these
    numbers are read from disk, avoiding a second hardcoded copy drifting
    from assumptions/*.yaml. See docs/RED-TEAM-REVIEW.md and the
    interactive-dashboard plan for why this exists.
    """
    rates = {
        "fixedDeliveryPerDay": data.rate_structure.fixed_delivery_charge_cad_per_day,
        "variableDeliveryPerKwh": data.rate_structure.variable_delivery_charge_cad_per_kwh,
        "regulatoryPerKwh": data.rate_structure.regulatory_charge_cad_per_kwh,
        "rebatePerKwh": data.rate_structure.rebate_cad_per_kwh,
        "hstRate": data.rate_structure.hst_rate,
        "tou": dict(data.rate_structure.tou_rates_cad_per_kwh),
    }
    (data_out / "rates.json").write_text(json.dumps(rates, indent=2), encoding="utf-8")

    scenarios_full = {
        "price": {
            s["label"].lower(): {
                "id": s["id"],
                "label": s["label"],
                "electricityEnergyReal": s["annual_changes"]["electricity_energy_real"],
                "fixedDeliveryReal": s["annual_changes"]["fixed_delivery_real"],
                "variableDeliveryReal": s["annual_changes"]["variable_delivery_real"],
                "generalInflation": s["annual_changes"]["general_inflation"],
            }
            for s in data.price_scenarios
        },
        "decline": {
            s["label"].lower().replace(" ", "-"): {
                "id": s["label"].lower().replace(" ", "-"),
                "label": s["label"],
                "realAnnualInstalledCostChange": s["real_annual_installed_cost_change"],
            }
            for s in data.decline_scenarios
        },
    }
    (data_out / "scenarios-full.json").write_text(json.dumps(scenarios_full, indent=2), encoding="utf-8")

    quote_shares = {
        k: v for k, v in data.solar["cost_components"].items()
        if k not in ("status",)
    }
    defaults = {
        "solar": {
            "referenceQuoteCad": data.solar["illustrative_reference_quote"]["installed_price_before_tax_cad"],
            "referenceSystemKwDc": data.solar["illustrative_reference_quote"]["system_kw_dc"],
            "costComponentShares": quote_shares,
            "degradationAnnual": data.solar["production"]["degradation_annual_default"],
            "annualMaintenanceCad": data.solar["maintenance"]["annual_maintenance_cad_default"],
            "inverterReplacementYear": data.solar["maintenance"]["inverter_replacement_year_default"],
            "inverterReplacementCostCad": data.solar["maintenance"]["inverter_replacement_cost_cad_default"],
        },
        "financing": {
            "defaultDownPaymentFraction": data.financing["loan"]["default_down_payment_fraction"],
            "defaultAnnualInterestRate": data.financing["loan"]["default_annual_interest_rate"],
            "defaultTermYears": data.financing["loan"]["default_term_years"],
        },
        "ontario": {
            "hstRate": data.ontario["hst_rate"],
            "discountRateDefault": data.ontario["discount_rate_default"],
            "planningHorizonsYears": data.ontario["planning_horizons_years"],
            "defaultPlanningHorizonYears": data.ontario["default_planning_horizon_years"],
        },
        "billShares": {
            # Matches the fixed/variable/energy split used in
            # build_site.py's _build_comparison_rows server-side, kept
            # here so the JS port uses the same split rather than a
            # second guessed value.
            "fixedShare": 0.30,
            "variableShare": 0.15,
            "energyShare": 0.55,
        },
        "collectiveTiers": [
            {
                "id": tier.id,
                "label": tier.label,
                "households": tier.households,
                "reductions": dict(tier.reductions),
                "overallDiscountCapPercent": tier.overall_discount_cap_percent,
            }
            for tier in (
                data.collective_tiers["individual"],
                data.collective_tiers["group_5"],
                data.collective_tiers["group_10"],
                data.collective_tiers["group_20"],
            )
        ],
    }
    (data_out / "assumption-defaults.json").write_text(json.dumps(defaults, indent=2), encoding="utf-8")


def _write_scenario_downloads(data: SiteData, data_out: Path) -> None:
    scenarios_dir = data_out / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)

    for raw in data.price_scenarios:
        slug = raw["label"].lower()
        payload = {
            "schema_version": "1.0",
            "model_version": "0.1.0",
            "data_cutoff": "2026-08-01",
            "region": "Ottawa",
            "utility": "Hydro Ottawa",
            "scenario_ids": [raw["id"]],
            "annual_changes": raw["annual_changes"],
        }
        (scenarios_dir / f"{slug}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

        with open(scenarios_dir / f"{slug}.csv", "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["component", "annual_real_change"])
            for key, value in raw["annual_changes"].items():
                writer.writerow([key, value])
