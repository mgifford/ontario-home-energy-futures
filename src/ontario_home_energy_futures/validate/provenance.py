"""Validation for the provenance record schema used by every imported
observation (see the ``id``/``period``/``source_url``/... schema documented
in the project brief and README).

Validation fails loudly and specifically rather than silently coercing bad
data, so a malformed source cannot produce a malformed automated update.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_ALLOWED_STATUS = {"observed", "estimated", "projected", "user_supplied", "scenario"}
_REQUIRED_FIELDS = (
    "id",
    "period",
    "geography",
    "measure",
    "value",
    "unit",
    "nominal",
    "status",
    "source_url",
    "source_title",
    "published_at",
    "retrieved_at",
    "licence",
)


class ProvenanceError(ValueError):
    """Raised when an observation or manifest entry fails validation."""


@dataclass
class ObservationRecord:
    """A single provenance-stamped data observation."""

    id: str
    period: str
    geography: str
    measure: str
    value: float
    unit: str
    nominal: bool
    status: str
    source_url: str
    source_title: str
    published_at: str
    retrieved_at: str
    licence: str
    utility: str | None = None
    rate_plan: str | None = None
    period_name: str | None = None
    source_sha256: str | None = None
    notes: str = ""
    extra: dict = field(default_factory=dict)


def validate_observation(record: dict) -> ObservationRecord:
    """Validate a raw dict against the provenance schema.

    Raises ``ProvenanceError`` on any missing field, wrong type, malformed
    date/period, invalid unit, or unrecognized status.
    """
    missing = [f for f in _REQUIRED_FIELDS if f not in record or record[f] in (None, "")]
    if missing:
        raise ProvenanceError(f"observation missing required fields: {missing}")

    if not _PERIOD_RE.match(str(record["period"])):
        raise ProvenanceError(
            f"observation {record['id']!r} has malformed period "
            f"{record['period']!r}; expected YYYY-MM"
        )

    for date_field in ("published_at", "retrieved_at"):
        value = str(record[date_field])
        if not _DATE_RE.match(value):
            raise ProvenanceError(
                f"observation {record['id']!r} has malformed {date_field} "
                f"{value!r}; expected YYYY-MM-DD"
            )
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ProvenanceError(
                f"observation {record['id']!r} has invalid {date_field} {value!r}"
            ) from exc

    if record["status"] not in _ALLOWED_STATUS:
        raise ProvenanceError(
            f"observation {record['id']!r} has unrecognized status "
            f"{record['status']!r}; expected one of {sorted(_ALLOWED_STATUS)}"
        )

    if not isinstance(record["nominal"], bool):
        raise ProvenanceError(
            f"observation {record['id']!r} field 'nominal' must be a boolean"
        )

    try:
        value = float(record["value"])
    except (TypeError, ValueError) as exc:
        raise ProvenanceError(
            f"observation {record['id']!r} has non-numeric value {record['value']!r}"
        ) from exc

    unit = str(record["unit"])
    if not unit:
        raise ProvenanceError(f"observation {record['id']!r} has empty unit")

    sha256 = record.get("source_sha256")
    if sha256 is not None and not _SHA256_RE.match(str(sha256)):
        raise ProvenanceError(
            f"observation {record['id']!r} has malformed source_sha256 {sha256!r}"
        )

    known = set(_REQUIRED_FIELDS) | {
        "utility",
        "rate_plan",
        "period_name",
        "source_sha256",
        "notes",
    }
    extra = {k: v for k, v in record.items() if k not in known}

    return ObservationRecord(
        id=str(record["id"]),
        period=str(record["period"]),
        geography=str(record["geography"]),
        measure=str(record["measure"]),
        value=value,
        unit=unit,
        nominal=bool(record["nominal"]),
        status=str(record["status"]),
        source_url=str(record["source_url"]),
        source_title=str(record["source_title"]),
        published_at=str(record["published_at"]),
        retrieved_at=str(record["retrieved_at"]),
        licence=str(record["licence"]),
        utility=record.get("utility"),
        rate_plan=record.get("rate_plan"),
        period_name=record.get("period_name"),
        source_sha256=sha256,
        notes=str(record.get("notes", "")),
        extra=extra,
    )


def sha256_of_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file's contents."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest_entry(entry: dict, *, repo_root: Path) -> None:
    """Validate a ``data/source-manifest.yaml`` entry, including that its
    recorded SHA-256 matches the actual committed file on disk.

    Raises ``ProvenanceError`` if the file is missing or the hash does not
    match — this is the mechanism that prevents a raw source file from being
    silently replaced without the manifest being updated to match.
    """
    required = ("source_id", "file_path", "sha256", "publisher", "source_url", "licence", "retrieved_at")
    missing = [f for f in required if f not in entry or entry[f] in (None, "")]
    if missing:
        raise ProvenanceError(f"manifest entry missing required fields: {missing}")

    sha256 = str(entry["sha256"])
    if not _SHA256_RE.match(sha256):
        raise ProvenanceError(
            f"manifest entry {entry['source_id']!r} has malformed sha256 {sha256!r}"
        )

    file_path = repo_root / str(entry["file_path"])
    if not file_path.is_file():
        raise ProvenanceError(
            f"manifest entry {entry['source_id']!r} references missing file "
            f"{file_path}"
        )

    actual = sha256_of_file(file_path)
    if actual != sha256:
        raise ProvenanceError(
            f"manifest entry {entry['source_id']!r} sha256 mismatch: "
            f"manifest says {sha256}, file on disk hashes to {actual}. "
            "A raw source file must never be silently replaced; add a new "
            "manifest entry for the new file instead of editing this one."
        )
