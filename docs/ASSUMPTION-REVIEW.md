# Assumption Review Process

This document describes how and when the entries in
[data/governance/assumptions.yaml](../data/governance/assumptions.yaml)
and [data/governance/claims.yaml](../data/governance/claims.yaml) are
reviewed, and what triggers a review outside the normal schedule.

## Who reviews

Any project maintainer may perform a scheduled or triggered review. A
review that changes a claim's `status` to `approved` should, where
practical, be performed or checked by someone who was not the original
author of that claim — matching the spirit of
[GOVERNANCE.md](../GOVERNANCE.md)'s independent-review commitment. This is
a process goal for this open-source project, not a hard organizational
requirement given current maintainer capacity.

## Review cadence

- **Claims** (`data/governance/claims.yaml`): each entry has its own
  `review_due` date, generally 3–6 months out for anything tied to a
  regulatory rule or rate (things that can change on a predictable OEB
  cycle), and up to 12 months for stable structural facts (e.g., "net
  metering is not a cash payment," which is unlikely to change quickly).
- **Assumptions** (`data/governance/assumptions.yaml`): reviewed
  opportunistically whenever the underlying `assumptions/*.yaml` file
  they reference is edited, and at minimum once every 12 months even if
  unchanged, to confirm the recorded `range` and `confidence` still look
  reasonable.
- **Scenario files** (`scenarios/*.yaml`): reviewed whenever a new
  version is published (see [GOVERNANCE.md](../GOVERNANCE.md) "Historical
  scenario retention") — a new version is itself a review event, since it
  requires deciding whether prior assumptions still hold.

## What triggers an out-of-cycle review

- A source publisher (OEB, IESO, Hydro Ottawa, Statistics Canada, or
  Natural Resources Canada) issues a material update to a document this
  project cites.
- A user or reviewer reports a suspected error via
  [docs/CORRECTIONS.md](CORRECTIONS.md).
- A `status: needs_review` claim is discovered during unrelated work —
  this should not be left until its scheduled `review_due` date if it is
  encountered sooner.
- A red-team or external review (see
  [review/REVIEW-GUIDE.md](../review/REVIEW-GUIDE.md)) identifies a
  concern.

## How a review is conducted

1. Re-fetch or re-read the claim's `source_url` (where one exists) and
   confirm the claim text still accurately reflects it.
2. Re-assess the three confidence dimensions independently — do not let a
   high `source_quality` score compensate for a stale
   `temporal_stability` assessment, or vice versa.
3. Update `verified_at` and `review_due` regardless of outcome.
4. If the claim or assumption changed, follow the correction process in
   [docs/CORRECTIONS.md](CORRECTIONS.md) rather than silently editing the
   value in place if it has already been published/displayed — see
   [GOVERNANCE.md](../GOVERNANCE.md).
5. If a claim cannot be re-verified (source unavailable, ambiguous, or
   contradictory), its `status` must move to `needs_review`, never remain
   at `approved` by default.

## Relationship to the red-team review

[docs/RED-TEAM-REVIEW.md](RED-TEAM-REVIEW.md) is a broader, periodic
adversarial audit; this document governs the narrower, ongoing
per-entry review of the claims and assumptions registers specifically.
A red-team review finding that names a specific claim or assumption
should result in that entry's `review_due` being brought forward, not
just a note in the red-team document alone.
