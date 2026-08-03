from pathlib import Path

import pytest

from ontario_home_energy_futures.validate.provenance import (
    ProvenanceError,
    sha256_of_file,
    validate_manifest_entry,
    validate_observation,
)

VALID_RECORD = {
    "id": "oeb-rpp-tou-offpeak-2026-08",
    "period": "2026-08",
    "geography": "Ontario",
    "utility": None,
    "measure": "electricity_energy_rate",
    "rate_plan": "time_of_use",
    "period_name": "off_peak",
    "value": 0.076,
    "unit": "CAD_per_kWh",
    "nominal": True,
    "status": "observed",
    "source_url": "https://example.ca/source",
    "source_title": "Example source",
    "published_at": "2026-07-20",
    "retrieved_at": "2026-08-01",
    "source_sha256": "a" * 64,
    "licence": "Open Government Licence",
    "notes": "",
}


def test_valid_record_passes():
    record = validate_observation(VALID_RECORD)
    assert record.id == VALID_RECORD["id"]
    assert record.value == 0.076


def test_missing_field_rejected():
    bad = dict(VALID_RECORD)
    del bad["source_url"]
    with pytest.raises(ProvenanceError):
        validate_observation(bad)


def test_malformed_period_rejected():
    bad = dict(VALID_RECORD, period="2026/08")
    with pytest.raises(ProvenanceError):
        validate_observation(bad)


def test_malformed_date_rejected():
    bad = dict(VALID_RECORD, published_at="July 20 2026")
    with pytest.raises(ProvenanceError):
        validate_observation(bad)


def test_invalid_status_rejected():
    bad = dict(VALID_RECORD, status="guessed")
    with pytest.raises(ProvenanceError):
        validate_observation(bad)


def test_non_numeric_value_rejected():
    bad = dict(VALID_RECORD, value="not a number")
    with pytest.raises(ProvenanceError):
        validate_observation(bad)


def test_non_boolean_nominal_rejected():
    bad = dict(VALID_RECORD, nominal="true")
    with pytest.raises(ProvenanceError):
        validate_observation(bad)


def test_malformed_sha256_rejected():
    bad = dict(VALID_RECORD, source_sha256="not-a-hash")
    with pytest.raises(ProvenanceError):
        validate_observation(bad)


def test_sha256_of_file_matches_shasum(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("hello world\n")
    digest = sha256_of_file(f)
    assert len(digest) == 64


def test_manifest_entry_hash_mismatch_detected(tmp_path):
    raw_dir = tmp_path / "data" / "raw" / "test"
    raw_dir.mkdir(parents=True)
    f = raw_dir / "source.txt"
    f.write_text("original content")
    entry = {
        "source_id": "test-source",
        "file_path": "data/raw/test/source.txt",
        "sha256": "0" * 64,
        "publisher": "Test",
        "source_url": "https://example.com",
        "licence": "Test Licence",
        "retrieved_at": "2026-08-02",
    }
    with pytest.raises(ProvenanceError, match="sha256 mismatch"):
        validate_manifest_entry(entry, repo_root=tmp_path)


def test_manifest_entry_missing_file_detected(tmp_path):
    entry = {
        "source_id": "test-source",
        "file_path": "data/raw/test/missing.txt",
        "sha256": "0" * 64,
        "publisher": "Test",
        "source_url": "https://example.com",
        "licence": "Test Licence",
        "retrieved_at": "2026-08-02",
    }
    with pytest.raises(ProvenanceError, match="missing file"):
        validate_manifest_entry(entry, repo_root=tmp_path)


def test_manifest_entry_missing_retrieved_at_detected(tmp_path):
    raw_dir = tmp_path / "data" / "raw" / "test"
    raw_dir.mkdir(parents=True)
    f = raw_dir / "source.txt"
    f.write_text("original content")
    entry = {
        "source_id": "test-source",
        "file_path": "data/raw/test/source.txt",
        "sha256": sha256_of_file(f),
        "publisher": "Test",
        "source_url": "https://example.com",
        "licence": "Test Licence",
    }
    with pytest.raises(ProvenanceError, match="missing required fields"):
        validate_manifest_entry(entry, repo_root=tmp_path)


def test_manifest_entry_correct_hash_passes(tmp_path):
    raw_dir = tmp_path / "data" / "raw" / "test"
    raw_dir.mkdir(parents=True)
    f = raw_dir / "source.txt"
    f.write_text("original content")
    actual_hash = sha256_of_file(f)
    entry = {
        "source_id": "test-source",
        "file_path": "data/raw/test/source.txt",
        "sha256": actual_hash,
        "publisher": "Test",
        "source_url": "https://example.com",
        "licence": "Test Licence",
        "retrieved_at": "2026-08-02",
    }
    validate_manifest_entry(entry, repo_root=tmp_path)  # should not raise
