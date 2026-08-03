# OEB raw data

`billdata-fixture.xml` is a manually constructed, clearly labelled illustrative
fixture approximating the structure and rate levels of the OEB's live
`BillData.xml` (<https://www.oeb.ca/_html/calculator/data/BillData.xml>), captured
2026-08-02.

This project's build environment does not have scheduled network access to
retrieve the live file, so this fixture stands in for it in Phase 1. **Verify
this fixture against the live `BillData.xml` before treating derived figures as
current.** See [DATA_SOURCES.md](../../../DATA_SOURCES.md).

Do not overwrite this file in place when a new snapshot is captured — add a new
dated file (e.g. `billdata-2026-11.xml`) and update
`data/source-manifest.yaml` with its hash and retrieval date instead.
