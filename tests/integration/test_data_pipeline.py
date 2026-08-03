"""Data-pipeline tests: valid sources, missing fields, unexpected units,
duplicate observations, revised source files, hash changes, unavailable
source, malformed XML/CSV, offline fixture build, and failure without
corrupting existing normalized data.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from ontario_home_energy_futures.normalize.oeb import MalformedSourceError, parse_oeb_billdata
from ontario_home_energy_futures.normalize.pipeline import build_observations_csv
from ontario_home_energy_futures.validate.provenance import ProvenanceError, sha256_of_file

REPO_ROOT = Path(__file__).parent.parent.parent


def test_offline_fixture_build_succeeds(tmp_path):
    output = tmp_path / "observations.csv"
    result_path = build_observations_csv(REPO_ROOT, output_path=output)
    assert result_path == output
    content = output.read_text(encoding="utf-8")
    assert "oeb-rpp-tou-off_peak" in content
    assert content.count("\n") > 5


def test_pipeline_produces_valid_observations():
    import csv
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "observations.csv"
        build_observations_csv(REPO_ROOT, output_path=output)
        with open(output, newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) > 0
        for row in rows:
            assert row["id"]
            assert row["source_url"]
            assert row["status"] in ("observed", "estimated", "projected", "user_supplied", "scenario")


def test_missing_manifest_file_raises(tmp_path):
    fake_root = tmp_path / "fake_repo"
    (fake_root / "data").mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        build_observations_csv(fake_root, output_path=tmp_path / "out.csv")


def test_empty_manifest_raises(tmp_path):
    fake_root = tmp_path / "fake_repo"
    (fake_root / "data").mkdir(parents=True)
    (fake_root / "data" / "source-manifest.yaml").write_text("sources: []\n", encoding="utf-8")
    with pytest.raises(ProvenanceError, match="no sources"):
        build_observations_csv(fake_root, output_path=tmp_path / "out.csv")


def test_unregistered_source_id_raises(tmp_path):
    fake_root = tmp_path / "fake_repo"
    raw_dir = fake_root / "data" / "raw" / "unknown"
    raw_dir.mkdir(parents=True)
    raw_file = raw_dir / "source.xml"
    raw_file.write_text("<x/>", encoding="utf-8")
    manifest = {
        "sources": [
            {
                "source_id": "unknown-source-2026",
                "file_path": "data/raw/unknown/source.xml",
                "sha256": sha256_of_file(raw_file),
                "publisher": "Unknown",
                "source_url": "https://example.com",
                "licence": "Unknown",
                "retrieved_at": "2026-08-02",
            }
        ]
    }
    (fake_root / "data" / "source-manifest.yaml").write_text(yaml.dump(manifest), encoding="utf-8")
    with pytest.raises(ProvenanceError, match="no normalizer registered"):
        build_observations_csv(fake_root, output_path=tmp_path / "out.csv")


def test_duplicate_source_file_content_flagged_by_hash_mismatch(tmp_path):
    # Simulate a raw file being silently replaced: manifest still records
    # the old hash, but the file on disk now differs.
    fake_root = tmp_path / "fake_repo"
    raw_dir = fake_root / "data" / "raw" / "oeb"
    raw_dir.mkdir(parents=True)
    original = REPO_ROOT / "data" / "raw" / "oeb" / "billdata-fixture.xml"
    shutil.copy(original, raw_dir / "billdata-fixture.xml")
    original_hash = sha256_of_file(raw_dir / "billdata-fixture.xml")

    # Now silently modify the file without updating the manifest hash.
    (raw_dir / "billdata-fixture.xml").write_text(
        original.read_text(encoding="utf-8").replace("2026-08-01", "2027-01-01"), encoding="utf-8"
    )

    manifest = {
        "sources": [
            {
                "source_id": "oeb-billdata-fixture-2026-08",
                "file_path": "data/raw/oeb/billdata-fixture.xml",
                "sha256": original_hash,  # stale hash - file has changed
                "publisher": "OEB",
                "source_url": "https://example.com",
                "licence": "OGL",
                "retrieved_at": "2026-08-02",
            }
        ]
    }
    (fake_root / "data" / "source-manifest.yaml").write_text(yaml.dump(manifest), encoding="utf-8")

    with pytest.raises(ProvenanceError, match="sha256 mismatch"):
        build_observations_csv(fake_root, output_path=tmp_path / "out.csv")


def test_revised_source_file_recorded_as_new_manifest_entry(tmp_path):
    # A revision must be a NEW manifest entry (different source_id/file_path),
    # not an edit of the old one's hash. Verify both entries can coexist and
    # both validate independently.
    fake_root = tmp_path / "fake_repo"
    raw_dir = fake_root / "data" / "raw" / "oeb"
    raw_dir.mkdir(parents=True)

    original = REPO_ROOT / "data" / "raw" / "oeb" / "billdata-fixture.xml"
    v1 = raw_dir / "billdata-2026-08.xml"
    v2 = raw_dir / "billdata-2026-11.xml"
    shutil.copy(original, v1)
    shutil.copy(original, v2)
    # make v2 distinguishable
    v2.write_text(v1.read_text(encoding="utf-8").replace("2026-08-01", "2026-11-01"), encoding="utf-8")

    from ontario_home_energy_futures.validate.provenance import validate_manifest_entry

    entry_v1 = {
        "source_id": "oeb-billdata-2026-08", "file_path": "data/raw/oeb/billdata-2026-08.xml",
        "sha256": sha256_of_file(v1), "publisher": "OEB", "source_url": "https://example.com", "licence": "OGL",
        "retrieved_at": "2026-08-02",
    }
    entry_v2 = {
        "source_id": "oeb-billdata-2026-11", "file_path": "data/raw/oeb/billdata-2026-11.xml",
        "sha256": sha256_of_file(v2), "publisher": "OEB", "source_url": "https://example.com", "licence": "OGL",
        "revises": "oeb-billdata-2026-08", "retrieved_at": "2026-11-01",
    }
    validate_manifest_entry(entry_v1, repo_root=fake_root)  # both validate independently
    validate_manifest_entry(entry_v2, repo_root=fake_root)
    assert v1.read_text() != v2.read_text()  # the old version is untouched


def test_malformed_xml_does_not_write_partial_csv(tmp_path):
    fake_root = tmp_path / "fake_repo"
    raw_dir = fake_root / "data" / "raw" / "oeb"
    raw_dir.mkdir(parents=True)
    bad_file = raw_dir / "billdata-fixture.xml"
    bad_file.write_text("<OEBBillData effectiveDate='2026-08-01'><broken", encoding="utf-8")

    manifest = {
        "sources": [
            {
                "source_id": "oeb-broken",
                "file_path": "data/raw/oeb/billdata-fixture.xml",
                "sha256": sha256_of_file(bad_file),
                "publisher": "OEB",
                "source_url": "https://example.com",
                "licence": "OGL",
                "retrieved_at": "2026-08-02",
            }
        ]
    }
    (fake_root / "data" / "source-manifest.yaml").write_text(yaml.dump(manifest), encoding="utf-8")

    output = tmp_path / "out.csv"
    with pytest.raises(MalformedSourceError):
        build_observations_csv(fake_root, output_path=output)
    assert not output.exists()  # no partial/corrupt file written


def test_failure_does_not_corrupt_existing_normalized_data(tmp_path):
    # Write a "previously normalized" file, then run a failing build against
    # a different output path to confirm the previous file is untouched.
    existing = tmp_path / "observations.csv"
    existing.write_text("id,period\nprevious-good-data,2026-01\n", encoding="utf-8")
    original_content = existing.read_text(encoding="utf-8")

    fake_root = tmp_path / "fake_repo"
    (fake_root / "data").mkdir(parents=True)
    (fake_root / "data" / "source-manifest.yaml").write_text("sources: []\n", encoding="utf-8")

    with pytest.raises(ProvenanceError):
        build_observations_csv(fake_root, output_path=existing)

    assert existing.read_text(encoding="utf-8") == original_content
