"""Collective-purchasing cost-reduction model.

Independent of technology-cost decline (``technology_decline.py``): this
module represents savings from acting collectively (shared customer
acquisition, standard designs, bulk hardware, shared permitting), applied
as a ONE-TIME reduction to eligible installation cost components, capped by
an overall discount ceiling. Never applied to taxes, government fees,
utility charges, or interest rates. See METHODOLOGY.md section 18 and
``assumptions/collective_purchasing.yaml``.

Mirrors ``model/financing.py::apply_group_discount``'s "eligible components
only" pattern but keyed by household-count tier, with per-component
reduction percentages and an overall cap.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

NEVER_DISCOUNTABLE = frozenset({"taxes", "government_fees", "utility_charges", "interest_rate"})


@dataclass(frozen=True)
class CollectiveTier:
    id: str
    label: str
    households: int
    reductions: dict[str, float]  # component_id -> percent
    overall_discount_cap_percent: float


def load_collective_tiers(path: Path) -> dict[str, CollectiveTier]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    tiers: dict[str, CollectiveTier] = {}
    for entry in raw["tiers"]:
        tiers[entry["id"]] = CollectiveTier(
            id=entry["id"],
            label=entry["label"],
            households=int(entry["households"]),
            reductions={k.replace("_percent", ""): float(v) for k, v in entry["reductions"].items()},
            overall_discount_cap_percent=float(entry["overall_discount_cap_percent"]),
        )
    return tiers


@dataclass(frozen=True)
class ComponentReductionResult:
    component_id: str
    base_cost: float
    reduced_cost: float
    reduction_cad: float


@dataclass(frozen=True)
class CollectivePurchaseResult:
    tier_id: str
    total_base_cost: float
    total_reduced_cost: float
    total_reduction_cad: float
    effective_discount_percent: float
    capped: bool
    by_component: list[ComponentReductionResult]


def apply_collective_purchase(
    *, tier: CollectiveTier, base_costs_by_component: dict[str, float]
) -> CollectivePurchaseResult:
    """Apply a collective-purchasing tier's per-component reductions,
    enforcing that taxes/government fees/utility charges/interest rates are
    never discounted, and that the overall discount never exceeds the
    tier's cap (a proportional scale-back is applied to every component's
    reduction if the uncapped total would exceed the cap, keeping each
    component's *relative* reduction consistent rather than zeroing some
    components out arbitrarily).
    """
    total_base = sum(base_costs_by_component.values())
    if total_base <= 0:
        return CollectivePurchaseResult(
            tier_id=tier.id, total_base_cost=0.0, total_reduced_cost=0.0,
            total_reduction_cad=0.0, effective_discount_percent=0.0, capped=False, by_component=[],
        )

    uncapped_reductions: dict[str, float] = {}
    for component_id, base_cost in base_costs_by_component.items():
        if component_id in NEVER_DISCOUNTABLE:
            uncapped_reductions[component_id] = 0.0
            continue
        pct = tier.reductions.get(component_id, 0.0)
        uncapped_reductions[component_id] = base_cost * (pct / 100.0)

    uncapped_total_reduction = sum(uncapped_reductions.values())
    uncapped_discount_percent = (uncapped_total_reduction / total_base) * 100.0

    capped = uncapped_discount_percent > tier.overall_discount_cap_percent
    if capped and uncapped_total_reduction > 0:
        scale = (tier.overall_discount_cap_percent / 100.0 * total_base) / uncapped_total_reduction
    else:
        scale = 1.0

    by_component: list[ComponentReductionResult] = []
    total_reduction = 0.0
    for component_id, base_cost in base_costs_by_component.items():
        reduction = uncapped_reductions[component_id] * scale
        reduced_cost = base_cost - reduction
        total_reduction += reduction
        by_component.append(
            ComponentReductionResult(
                component_id=component_id,
                base_cost=round(base_cost, 2),
                reduced_cost=round(reduced_cost, 2),
                reduction_cad=round(reduction, 2),
            )
        )

    total_reduced = total_base - total_reduction
    effective_discount_percent = (total_reduction / total_base) * 100.0 if total_base else 0.0

    return CollectivePurchaseResult(
        tier_id=tier.id,
        total_base_cost=round(total_base, 2),
        total_reduced_cost=round(total_reduced, 2),
        total_reduction_cad=round(total_reduction, 2),
        effective_discount_percent=round(effective_discount_percent, 4),
        capped=capped,
        by_component=by_component,
    )
