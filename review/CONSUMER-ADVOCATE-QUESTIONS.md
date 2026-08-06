# Consumer Advocate Review Questions

Use this checklist against the live site and the source code. See
[docs/RED-TEAM-REVIEW.md §1](../docs/RED-TEAM-REVIEW.md) for this
project's own self-assessment against these questions — check whether you
agree with it.

## Debt and affordability

- [ ] Could a household take on debt they cannot afford because of a
      result this tool showed them? Check `assumptions/financing.yaml`'s
      default loan rate/term and whether any warning appears when a
      modelled payment is high relative to the modelled bill savings.
      (As of this version, no such warning exists — see
      [docs/RED-TEAM-REVIEW.md](../docs/RED-TEAM-REVIEW.md) "Deferred to
      next phase.")
- [ ] Are loan payments ever compared against a *conservative* (not
      optimistic) bill-savings estimate? Check `model/financing.py` and
      `model/scenario.py`/`model/scenario_v2.py`.
- [ ] Does the tool warn if a loan term exceeds a typical equipment
      warranty period? (Check `assumptions/solar.yaml`,
      `assumptions/batteries.yaml` warranty fields against
      `assumptions/financing.yaml` term options.)

## Contract and quote practices

- [ ] Are cancellation fees, liens, warranties, or equipment agreements
      ever mentioned? (As of this version: no — see
      [docs/RED-TEAM-REVIEW.md §1.2](../docs/RED-TEAM-REVIEW.md).)
- [ ] Are users encouraged to obtain independent, itemized quotes before
      purchasing? Check every template that references a "quote" or
      "installed price."
- [ ] Is the pre-filled $21,000/7.2kW reference quote in
      `web/templates/net_metering.html` clearly distinguishable from a
      real quote, or could a user submit the form without noticing it's
      a placeholder? Try it yourself.

## Claims and guarantees

- [ ] Search the live site and templates for "guarantee," "guaranteed,"
      "will save," or similar absolute language. Does anything promise a
      specific outcome? (Compare against `MODEL_CARD.md` "Prohibited
      use" and the language standard in
      [data/governance/claims.yaml](../data/governance/claims.yaml).)
- [ ] Does any number on the page look computed but is actually static?
      (This project found and partially corrected one instance —
      `compare-timing.html`'s sensitivity table — see
      [docs/CORRECTIONS.md](../docs/CORRECTIONS.md) 2026-08-03 entry.
      Check whether other static-but-computed-looking content remains.)

## Deceptive use by a third party

- [ ] Could a salesperson screenshot this tool's output and present it as
      an official quote, endorsement, or guarantee? What text or design
      element would make that misuse obvious versus easy?
- [ ] Does the tool's branding or framing anywhere imply OEB, IESO, or
      government endorsement of a specific financial outcome? (This
      project's self-review found none — see
      [docs/RED-TEAM-REVIEW.md §2.3](../docs/RED-TEAM-REVIEW.md). Verify.)

## Report what you find

See [docs/CORRECTIONS.md](../docs/CORRECTIONS.md) for factual errors, or
open a general GitHub issue for a consumer-protection concern that isn't
a factual error but a design or disclosure gap.
