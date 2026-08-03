"""Per-component technology-cost-decline model.

    C_k,y = C_k,0 * (1 - r_k)^y * (1 + i_k)^y

Mirrors ``model/decline.py::installed_cost_after_years``'s formula exactly,
applied per cost component (module, inverter, battery, labour, permitting,
etc.) instead of to one blended quote total - because a global solar-module
price decline does not apply uniformly to Ontario installation labour or
permitting costs. See METHODOLOGY.md section 17 and
``assumptions/technology_components.yaml``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from . import decline as decline_mod

DeclineTier = str  # "low_decline_real" | "reference_decline_real" | "faster_decline_real"


@dataclass(frozen=True)
class ComponentDeclineRates:
    id: str
    label: str
    low_decline_real: float
    reference_decline_real: float
    faster_decline_real: float

    def rate_for_tier(self, tier: str) -> float:
        rates = {
            "low": self.low_decline_real,
            "reference": self.reference_decline_real,
            "faster": self.faster_decline_real,
        }
        if tier not in rates:
            raise ValueError(f"unknown decline tier {tier!r}; expected one of {sorted(rates)}")
        return rates[tier]


def load_technology_components(path: Path) -> dict[str, ComponentDeclineRates]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    components: dict[str, ComponentDeclineRates] = {}
    for entry in raw["components"]:
        components[entry["id"]] = ComponentDeclineRates(
            id=entry["id"],
            label=entry["label"],
            low_decline_real=float(entry["low_decline_real"]),
            reference_decline_real=float(entry["reference_decline_real"]),
            faster_decline_real=float(entry["faster_decline_real"]),
        )
    return components


@dataclass(frozen=True)
class ComponentCostProjection:
    component_id: str
    real_cost: float
    nominal_cost: float


def project_component_cost(
    *,
    component: ComponentDeclineRates,
    base_cost: float,
    tier: str,
    years: int,
    general_inflation: float = 0.0,
) -> ComponentCostProjection:
    """Project one cost component's price ``years`` from now under the
    given decline tier, using the same real/nominal formula as
    ``model/decline.py`` but with a component-specific rate.
    """
    rate = component.rate_for_tier(tier)
    real_cost, nominal_cost = decline_mod.installed_cost_after_years(
        base_cost=base_cost, annual_real_decline=rate, years=years, general_inflation=general_inflation
    )
    return ComponentCostProjection(component_id=component.id, real_cost=real_cost, nominal_cost=nominal_cost)


def project_quote_by_component(
    *,
    components: dict[str, ComponentDeclineRates],
    base_costs_by_component: dict[str, float],
    tier: str,
    years: int,
    general_inflation: float = 0.0,
) -> dict[str, ComponentCostProjection]:
    """Project every component in ``base_costs_by_component`` independently.
    Components not present in ``components`` (e.g. taxes) are returned
    unprojected (zero decline) rather than raising, since not every quote
    line item is a "technology" component with its own decline scenario.
    """
    results: dict[str, ComponentCostProjection] = {}
    for component_id, base_cost in base_costs_by_component.items():
        if component_id in components:
            results[component_id] = project_component_cost(
                component=components[component_id],
                base_cost=base_cost,
                tier=tier,
                years=years,
                general_inflation=general_inflation,
            )
        else:
            nominal = base_cost * (1.0 + general_inflation) ** years
            results[component_id] = ComponentCostProjection(
                component_id=component_id, real_cost=round(base_cost, 2), nominal_cost=round(nominal, 2)
            )
    return results
