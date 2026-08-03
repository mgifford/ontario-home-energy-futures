"""Parse the OEB BillData.xml (or its fixture) into observation records.

Parsing fails safely: if the expected structure is not found, a
``MalformedSourceError`` is raised rather than silently producing a partial
or wrong result. This is what lets the data-update pipeline avoid publishing
a malformed automated update when a source changes format.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET


class MalformedSourceError(ValueError):
    """Raised when a raw source file does not match the expected structure."""


def parse_oeb_billdata(
    xml_path: Path,
    *,
    source_url: str,
    source_sha256: str,
    retrieved_at: str,
    geography: str = "Ontario",
) -> list[dict]:
    """Parse an OEB BillData.xml-shaped file into a list of raw observation
    dicts (not yet validated — pass each through
    ``validate.validate_observation`` before use).
    """
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError as exc:
        raise MalformedSourceError(f"{xml_path} is not well-formed XML: {exc}") from exc

    root = tree.getroot()
    if root.tag != "OEBBillData":
        raise MalformedSourceError(
            f"{xml_path} root element is {root.tag!r}, expected 'OEBBillData'"
        )

    effective_date = root.get("effectiveDate")
    if not effective_date:
        raise MalformedSourceError(f"{xml_path} missing effectiveDate attribute")
    try:
        published = date.fromisoformat(effective_date)
    except ValueError as exc:
        raise MalformedSourceError(
            f"{xml_path} effectiveDate {effective_date!r} is not a valid date"
        ) from exc
    period = f"{published.year:04d}-{published.month:02d}"

    observations: list[dict] = []

    rpp = root.find("RegulatedPriceplan")
    if rpp is None:
        raise MalformedSourceError(f"{xml_path} missing RegulatedPriceplan element")

    tou = rpp.find("TimeOfUse")
    if tou is None:
        raise MalformedSourceError(f"{xml_path} missing TimeOfUse element")
    for period_el in tou.findall("Period"):
        name = period_el.get("name")
        rate = period_el.get("rateCadPerKwh")
        if not name or rate is None:
            raise MalformedSourceError(
                f"{xml_path} TimeOfUse Period missing name or rateCadPerKwh"
            )
        observations.append(
            _base_record(
                id_=f"oeb-rpp-tou-{name}-{period}",
                period=period,
                geography=geography,
                measure="electricity_energy_rate",
                value=float(rate),
                unit="CAD_per_kWh",
                rate_plan="time_of_use",
                period_name=name,
                source_url=source_url,
                source_sha256=source_sha256,
                published_at=effective_date,
                retrieved_at=retrieved_at,
            )
        )

    for tier_el in rpp.findall("Tier"):
        tier_name = tier_el.findtext("Name")
        rate_text = tier_el.findtext("RateCadPerKwh")
        if not tier_name or rate_text is None:
            raise MalformedSourceError(
                f"{xml_path} Tier element missing Name or RateCadPerKwh"
            )
        observations.append(
            _base_record(
                id_=f"oeb-rpp-tiered-{tier_name.lower()}-{period}",
                period=period,
                geography=geography,
                measure="electricity_energy_rate",
                value=float(rate_text),
                unit="CAD_per_kWh",
                rate_plan="tiered",
                period_name=tier_name.lower(),
                source_url=source_url,
                source_sha256=source_sha256,
                published_at=effective_date,
                retrieved_at=retrieved_at,
            )
        )

    distributor = root.find("Distributor")
    if distributor is None:
        raise MalformedSourceError(f"{xml_path} missing Distributor element")
    utility_id = distributor.get("id")
    if not utility_id:
        raise MalformedSourceError(f"{xml_path} Distributor missing id attribute")

    field_map = {
        "FixedDeliveryChargeCadPerDay": ("fixed_delivery_charge", "CAD_per_day"),
        "VariableDeliveryChargeCadPerKwh": ("variable_delivery_charge", "CAD_per_kWh"),
        "RegulatoryChargeCadPerKwh": ("regulatory_charge", "CAD_per_kWh"),
        "OntarioElectricityRebateCadPerKwh": ("electricity_rebate", "CAD_per_kWh"),
    }
    for xml_field, (measure, unit) in field_map.items():
        text = distributor.findtext(xml_field)
        if text is None:
            raise MalformedSourceError(f"{xml_path} Distributor missing {xml_field}")
        observations.append(
            _base_record(
                id_=f"oeb-{utility_id}-{measure}-{period}",
                period=period,
                geography=geography,
                measure=measure,
                value=float(text),
                unit=unit,
                rate_plan=None,
                period_name=None,
                source_url=source_url,
                source_sha256=source_sha256,
                published_at=effective_date,
                retrieved_at=retrieved_at,
                utility=utility_id,
            )
        )

    return observations


def _base_record(
    *,
    id_: str,
    period: str,
    geography: str,
    measure: str,
    value: float,
    unit: str,
    rate_plan: str | None,
    period_name: str | None,
    source_url: str,
    source_sha256: str,
    published_at: str,
    retrieved_at: str,
    utility: str | None = None,
) -> dict:
    return {
        "id": id_,
        "period": period,
        "geography": geography,
        "utility": utility,
        "measure": measure,
        "rate_plan": rate_plan,
        "period_name": period_name,
        "value": value,
        "unit": unit,
        "nominal": True,
        "status": "estimated",
        "source_url": source_url,
        "source_title": "OEB BillData.xml",
        "published_at": published_at,
        "retrieved_at": retrieved_at,
        "source_sha256": source_sha256,
        "licence": "Open Government Licence - Ontario",
        "notes": "",
    }
