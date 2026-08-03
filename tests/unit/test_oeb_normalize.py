from pathlib import Path

import pytest

from ontario_home_energy_futures.normalize.oeb import MalformedSourceError, parse_oeb_billdata

FIXTURE = Path(__file__).parent.parent.parent / "data" / "raw" / "oeb" / "billdata-fixture.xml"


def test_parses_committed_fixture():
    records = parse_oeb_billdata(
        FIXTURE, source_url="https://example.ca/BillData.xml", source_sha256="a" * 64, retrieved_at="2026-08-02"
    )
    assert len(records) > 0
    tou_records = [r for r in records if r["rate_plan"] == "time_of_use"]
    assert {r["period_name"] for r in tou_records} == {"off_peak", "mid_peak", "on_peak"}


def test_rejects_malformed_xml(tmp_path):
    bad = tmp_path / "bad.xml"
    bad.write_text("<not><valid</not>")
    with pytest.raises(MalformedSourceError):
        parse_oeb_billdata(bad, source_url="x", source_sha256="a" * 64, retrieved_at="2026-08-02")


def test_rejects_wrong_root_element(tmp_path):
    bad = tmp_path / "bad.xml"
    bad.write_text("<SomethingElse></SomethingElse>")
    with pytest.raises(MalformedSourceError):
        parse_oeb_billdata(bad, source_url="x", source_sha256="a" * 64, retrieved_at="2026-08-02")


def test_rejects_missing_effective_date(tmp_path):
    bad = tmp_path / "bad.xml"
    bad.write_text("<OEBBillData></OEBBillData>")
    with pytest.raises(MalformedSourceError):
        parse_oeb_billdata(bad, source_url="x", source_sha256="a" * 64, retrieved_at="2026-08-02")


def test_rejects_missing_time_of_use(tmp_path):
    bad = tmp_path / "bad.xml"
    bad.write_text(
        '<OEBBillData effectiveDate="2026-08-01">'
        "<RegulatedPriceplan></RegulatedPriceplan>"
        "</OEBBillData>"
    )
    with pytest.raises(MalformedSourceError):
        parse_oeb_billdata(bad, source_url="x", source_sha256="a" * 64, retrieved_at="2026-08-02")


def test_rejects_missing_distributor(tmp_path):
    bad = tmp_path / "bad.xml"
    bad.write_text(
        '<OEBBillData effectiveDate="2026-08-01">'
        '<RegulatedPriceplan><TimeOfUse>'
        '<Period name="off_peak" rateCadPerKwh="0.076"/>'
        '<Period name="mid_peak" rateCadPerKwh="0.122"/>'
        '<Period name="on_peak" rateCadPerKwh="0.158"/>'
        "</TimeOfUse></RegulatedPriceplan>"
        "</OEBBillData>"
    )
    with pytest.raises(MalformedSourceError):
        parse_oeb_billdata(bad, source_url="x", source_sha256="a" * 64, retrieved_at="2026-08-02")
