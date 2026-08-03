# Equity Review Questions

See [docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md](../docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md)
and [docs/RED-TEAM-REVIEW.md §6](../docs/RED-TEAM-REVIEW.md).

## Access

- [ ] Try to complete the household-input flow as a renter. What happens?
      Is there any acknowledgment that renters cannot use the core
      purchase-decision comparison? (As of this version: no — this is a
      named, unmitigated gap.)
- [ ] Try it as a condominium resident without individual roof access.
      Same question.
- [ ] Is there any mention of community solar, shared solar, or
      non-ownership alternatives anywhere in the live site? (Currently:
      no live-site mention; only named as a gap in
      `docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md`.)

## Who pays, who benefits

- [ ] Does the tool anywhere distinguish private household savings from
      the cost of that saving to other ratepayers (via net-metering
      cross-subsidy) or to government (via incentive funding)? Check
      `docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md`'s "Who pays" section —
      does its honesty about not quantifying this satisfy you, or do you
      believe quantification is achievable and should be prioritized?
- [ ] Does the group-purchase/collective-discount framing anywhere
      acknowledge that organizing a group purchase requires social capital
      and existing homeownership? Compare the live site's framing
      (`web/templates/net_metering.html`) against
      `docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md`'s "Collective purchasing
      and wealth bias" section — is the live site's framing consistent
      with the documented risk, or does it inadvertently oversell
      accessibility?

## Financial safety for lower-income households

- [ ] Does the tool warn a low-income household about financing risk
      differently than a high-income household, or does it apply the same
      generic financing assumptions to everyone regardless of ability to
      absorb a bad outcome? (Currently: same generic assumptions for
      everyone; no income-sensitivity exists.)

## Disability and specific needs

- [ ] Is there a labelled way to describe a disability-related critical
      load (e.g., medical refrigeration, powered mobility equipment)
      distinct from general household backup convenience? (Currently: no
      — `battery_generator.html` only has generic "critical load in
      watts.")

## Geographic and community scope

- [ ] Does the tool make any claim about rural, remote, or Indigenous
      community energy reliability or programme eligibility? (It
      shouldn't — its stated scope is Ottawa/Hydro Ottawa only. Confirm
      this boundary is respected everywhere, including in the IESO
      provincial-context sections.)

## Language and access

- [ ] Is the site usable in French, or any language other than English?
      (Currently: English only.) Is this an acceptable limitation given
      the project's stated Phase 1 scope, or does it need earlier
      remediation than currently planned?

## Report what you find

Open a GitHub issue describing the equity gap. If it's a factual
inaccuracy in `docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md` itself (e.g., a
distributional claim stated as fact that should be marked unknown), treat
it as a correction — see [docs/CORRECTIONS.md](../docs/CORRECTIONS.md).
