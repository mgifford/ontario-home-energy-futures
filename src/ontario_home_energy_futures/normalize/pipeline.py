"""Offline-buildable normalization pipeline: raw fixtures -> validated
observation records -> data/observations.csv.

Fails safely: if any source fails validation, the pipeline raises rather than
writing a partial or corrupted observations.csv, so a bad update never
overwrites previously normalized data (see METHODOLOGY.md and DATA_SOURCES.md
on "do not publish a malformed automated update").
"""

from __future__ import annotations

import csv
from pathlib import Path

import yaml

from ..validate.provenance import (
    ProvenanceError,
    validate_manifest_entry,
    validate_observation,
)
from .oeb import parse_oeb_billdata

_CSV_FIELDS = [
    "id",
    "period",
    "geography",
    "utility",
    "measure",
    "rate_plan",
    "period_name",
    "value",
    "unit",
    "nominal",
    "status",
    "source_url",
    "source_title",
    "published_at",
    "retrieved_at",
    "source_sha256",
    "licence",
    "notes",
]


def build_observations_csv(repo_root: Path, output_path: Path | None = None) -> Path:
    """Validate the source manifest, parse each raw source, validate every
    resulting observation, and write ``data/observations.csv``.

    Returns the path written. Raises ``ProvenanceError`` /
    ``MalformedSourceError`` without writing anything if any step fails.
    """
    manifest_path = repo_root / "data" / "source-manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    sources = manifest.get("sources", [])
    if not sources:
        raise ProvenanceError(f"{manifest_path} has no sources listed")

    all_observations: list[dict] = []

    for entry in sources:
        validate_manifest_entry(entry, repo_root=repo_root)

        file_path = repo_root / str(entry["file_path"])
        if entry["source_id"].startswith("oeb-"):
            raw_records = parse_oeb_billdata(
                file_path,
                source_url=str(entry["source_url"]),
                source_sha256=str(entry["sha256"]),
                retrieved_at=str(entry["retrieved_at"]),
            )
        else:
            raise ProvenanceError(
                f"no normalizer registered for source_id {entry['source_id']!r}"
            )

        for raw in raw_records:
            record = validate_observation(raw)
            all_observations.append(record.__dict__)

    output_path = output_path or (repo_root / "data" / "observations.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for obs in all_observations:
            writer.writerow(obs)

    return output_path
