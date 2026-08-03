"""Build the Jinja2 context data for each page from the assumption/scenario
YAML files and the calculation model. Presentation-only formatting (currency
strings, percentages) happens here, not in the model.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ..model import bill as bill_mod
from ..model import decline as decline_mod
from ..model import net_metering as nm_mod
from ..model import solar as solar_mod
from .. import __version__

STANDARD_PROFILES_KWH = [500, 700, 1000, 1500]
DATA_CUTOFF = "2026-08-02"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def cad(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def pct(value: float, decimals: int = 1) -> str:
    return f"{value * 100:.{decimals}f}%"


class SiteData:
    """Loads all assumptions/scenarios once and exposes computed page
    contexts.
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.hydro_ottawa = _load_yaml(repo_root / "assumptions" / "utilities" / "hydro-ottawa.yaml")
        self.ontario = _load_yaml(repo_root / "assumptions" / "ontario.yaml")
        self.household_loads = _load_yaml(repo_root / "assumptions" / "household-loads.yaml")
        self.solar = _load_yaml(repo_root / "assumptions" / "solar.yaml")
        self.financing = _load_yaml(repo_root / "assumptions" / "financing.yaml")
        self.batteries = _load_yaml(repo_root / "assumptions" / "batteries.yaml")
        self.generators = _load_yaml(repo_root / "assumptions" / "generators.yaml")

        self.price_scenarios = [
            _load_yaml(repo_root / "scenarios" / f"{name}.yaml")
            for name in ("low", "reference", "high", "stress")
        ]
        self.decline_scenarios = [
            _load_yaml(repo_root / "scenarios" / "solar-cost-decline" / f"{name}.yaml")
            for name in ("flat", "moderate", "faster")
        ]

        self.rate_structure = bill_mod.rate_structure_from_dict(self.hydro_ottawa)

    def base_context(self, asset_prefix: str = "") -> dict:
        return {
            "asset_prefix": asset_prefix,
            "model_version": __version__,
            "data_cutoff": DATA_CUTOFF,
        }

    def standard_profile_rows(self) -> list[dict]:
        rows = []
        for kwh in STANDARD_PROFILES_KWH:
            b = bill_mod.calculate_tou_bill(
                period="2026-08",
                consumption_kwh=kwh,
                hourly_shares=bill_mod.DEFAULT_TOU_HOURLY_SHARES,
                rates=self.rate_structure,
            )
            rows.append(
                {
                    "kwh": kwh,
                    "monthly_bill_formatted": cad(b.total_cad),
                    "energy_charge_formatted": cad(b.electricity_energy_charge_cad),
                    "fixed_delivery_formatted": cad(b.fixed_delivery_charge_cad),
                    "variable_delivery_formatted": cad(b.variable_delivery_charge_cad),
                    "regulatory_formatted": cad(b.regulatory_charge_cad),
                    "rebate_formatted": cad(b.rebate_cad),
                    "tax_formatted": cad(b.tax_cad),
                    "total_formatted": cad(b.total_cad),
                    "effective_cents_formatted": f"{b.effective_cents_per_kwh:.2f}¢",
                }
            )
        return rows

    def tiered_profile_rows(self) -> list[dict]:
        rows = []
        for kwh in STANDARD_PROFILES_KWH:
            b = bill_mod.calculate_tiered_bill(period="2026-08", consumption_kwh=kwh, month=8, rates=self.rate_structure)
            rows.append(
                {
                    "kwh": kwh,
                    "energy_charge_formatted": cad(b.electricity_energy_charge_cad),
                    "fixed_delivery_formatted": cad(b.fixed_delivery_charge_cad),
                    "total_formatted": cad(b.total_cad),
                    "effective_cents_formatted": f"{b.effective_cents_per_kwh:.2f}¢",
                }
            )
        return rows

    def price_scenario_summaries(self) -> list[dict]:
        return [
            {
                "id": s["id"].split("-")[-3] if False else s["label"].lower(),
                "label": s["label"],
                "electricity_energy_real_pct": pct(s["annual_changes"]["electricity_energy_real"]),
                "fixed_delivery_real_pct": pct(s["annual_changes"]["fixed_delivery_real"]),
                "variable_delivery_real_pct": pct(s["annual_changes"]["variable_delivery_real"]),
                "general_inflation_pct": pct(s["annual_changes"]["general_inflation"]),
            }
            for s in self.price_scenarios
        ]

    def decline_scenario_summaries(self) -> list[dict]:
        return [
            {
                "id": s["label"].lower().replace(" ", "-"),
                "label": s["label"],
                "real_annual_change_pct": pct(s["real_annual_installed_cost_change"]),
            }
            for s in self.decline_scenarios
        ]

    def net_metering_ledger_example(self) -> dict:
        system_kw = 7.2
        orientation_factors = self.solar["production"]["orientation_factors"]
        shading_factors = self.solar["production"]["shading_estimate_factors"]
        regional_yield = {int(k): float(v) for k, v in self.solar["production"]["regional_monthly_yield_kwh_per_kw"]["ottawa"].items()}

        inputs = solar_mod.SolarSystemInputs(
            capacity_kw_dc=system_kw,
            orientation="south",
            shading="none",
            degradation_annual=self.solar["production"]["degradation_annual_default"],
            inverter_efficiency=self.solar["production"]["inverter_efficiency_default"],
            other_system_losses=self.solar["production"]["other_system_losses_default"],
        )
        production = solar_mod.calculate_annual_monthly_production_kwh(
            inputs,
            regional_monthly_yield_kwh_per_kw=regional_yield,
            orientation_factors=orientation_factors,
            shading_factors=shading_factors,
            system_age_years=0,
        )

        monthly_demand = 700.0
        eligible_rate = self.rate_structure.tou_rates_cad_per_kwh["off_peak"]
        export_credit_rate = eligible_rate

        ledger = nm_mod.NetMeteringLedger(export_credit_rate_cad_per_kwh=export_credit_rate)
        rows = []
        for month in range(1, 13):
            period = f"2026-{month:02d}"
            solar_kwh = production[month]
            direct = min(solar_kwh, monthly_demand) * 0.35  # simple daytime-overlap approximation
            result = ledger.process_month(
                period=period,
                solar_generation_kwh=solar_kwh,
                household_demand_kwh=monthly_demand,
                direct_self_consumption_kwh=direct,
                eligible_energy_rate_cad_per_kwh=eligible_rate,
                ineligible_charges_cad=45.0,
            )
            rows.append(
                {
                    "period": result.period,
                    "generation_kwh": f"{result.solar_generation_kwh:.0f}",
                    "self_consumption_kwh": f"{result.direct_self_consumption_kwh:.0f}",
                    "exported_kwh": f"{result.exported_kwh:.0f}",
                    "grid_import_kwh": f"{result.grid_import_kwh:.0f}",
                    "credit_created": cad(result.credit_created_cad),
                    "credit_used": cad(result.credit_used_cad),
                    "credit_expired": cad(result.credit_expired_cad),
                    "closing_balance": cad(result.credit_closing_balance_cad),
                }
            )

        return {
            "rows": rows,
            "effective_value_per_kwh": ledger.effective_value_per_generated_kwh(),
            "retail_rate": eligible_rate,
            "system_kw": system_kw,
        }
