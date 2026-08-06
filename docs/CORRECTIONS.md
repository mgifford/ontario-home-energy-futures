# Corrections

This is the public errata log and correction process for Ontario Home
Energy Futures, distinct from the accessibility-specific reporting
channel in [ACCESSIBILITY.md](../ACCESSIBILITY.md) and from routine
feature development tracked in [CHANGELOG.md](../CHANGELOG.md).

## What belongs here

A factual, data, or methodological error that affected — or could affect
— a result a household saw. Examples: a wrong rate figure, an outdated
regulatory citation, an incorrectly labelled assumption `status`, a
calculation bug, or (as found and fixed in this hardening phase) content
that reads as computed but is actually static.

## What does not belong here

New features, enhancements, or planned-but-not-yet-built functionality —
those belong in [CHANGELOG.md](../CHANGELOG.md) and the
[docs/RED-TEAM-REVIEW.md](RED-TEAM-REVIEW.md) "Deferred to next phase"
table, not this log.

## How to report an error

Open a GitHub issue with the label `correction`, including:

- The page or file where the error appears.
- What the content currently says.
- What you believe it should say, with a source if you have one.
- Whether you believe this affected a result you or someone else relied
  on.

**Do not include unredacted bills, exact addresses, or account numbers**
in a correction report — see [MODEL_CARD.md](../MODEL_CARD.md) "Privacy."

## How a correction is handled

1. A maintainer verifies the claimed error against the cited source (or
   the actual source, if none was provided) — the same standard used for
   every entry in [data/governance/claims.yaml](../data/governance/claims.yaml).
2. If confirmed, the fix is made following this project's normal
   conventions: assumption/scenario files are corrected with a new
   version (never silently edited in place if previously published — see
   [GOVERNANCE.md](../GOVERNANCE.md) "Historical scenario retention"),
   code bugs are fixed with a test that would have caught the error.
3. The correction is logged below, dated, with a plain-language
   description of what was wrong and what changed.
4. [CHANGELOG.md](../CHANGELOG.md) is updated to reference the correction.
5. If the error was significant enough that a household may have relied
   on an incorrect result, the correction entry says so explicitly.

## Log

### 2026-08-03 — Sensitivity table presented as computed when it was static

**What was wrong:** `compare-timing.html`'s "What drives this result"
section stated it showed "the five assumptions with the largest effect on
this result, for the current inputs" — implying the table was computed
from the user's actual inputs. The underlying data
(`sensitivity_rows` in `src/ontario_home_energy_futures/site/build_site.py`)
was five hardcoded rows, identical for every user regardless of input.

**Who might have been affected:** Any user who read the "for the current
inputs" claim as meaning the table reflected their specific scenario.

**What changed:** The page copy was corrected to describe the table as a
static, illustrative example of the kind of assumption that typically
matters most, not a computation. See
[docs/RED-TEAM-REVIEW.md §8.4](RED-TEAM-REVIEW.md) for the full finding.
A real computed sensitivity ranking remains future work
(`model/sensitivity.py`, not yet built).

**Test added:**
`tests/unit/test_build_site_honesty.py::test_sensitivity_section_does_not_claim_to_be_computed_from_current_inputs`.

### 2026-08-03 — Documentation described SVG charts as delivered; none existed

**What was wrong:** `README.md`, `CHANGELOG.md`, and `ACCESSIBILITY.md`
described accessible inline SVG charts, paired with data tables, as
already implemented functionality. `src/ontario_home_energy_futures/charts/`
contained zero files.

**Who might have been affected:** Anyone evaluating the project's actual
capabilities from its documentation, including a contributor trying to
locate the chart code, or an accessibility reviewer trying to audit chart
behaviour that did not exist to audit.

**What changed:** All three documents corrected to describe chart support
as planned, not delivered. See
[docs/RED-TEAM-REVIEW.md §8.3](RED-TEAM-REVIEW.md).

**Test added:** None practical for a documentation-accuracy claim;
manually verified via `find src/ontario_home_energy_futures/charts -type f`
returning empty, cross-checked against the corrected text.

### 2026-08-03 — Claims register created to track known status/label mismatches

Not a code correction, but recorded here for transparency: this same
hardening phase identified (but did not yet fix at the source) that
`assumptions/ontario.yaml` labels the IESO provincial demand-growth
figures `status: observed` while its own notes admit they are pending
verification. This is tracked in
[data/governance/claims.yaml](../data/governance/claims.yaml)
(`claim-ieso-demand-growth-2050`, `status: needs_review`) and in
[docs/RED-TEAM-REVIEW.md §2.1](RED-TEAM-REVIEW.md) as an open item for a
future correction, not yet applied to the source YAML file.
