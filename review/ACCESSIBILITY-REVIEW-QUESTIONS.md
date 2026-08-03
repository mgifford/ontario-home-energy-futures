# Accessibility, Privacy, and Security Review Questions

See [ACCESSIBILITY.md](../ACCESSIBILITY.md) and
[docs/RED-TEAM-REVIEW.md §7](../docs/RED-TEAM-REVIEW.md).

## Operability

- [ ] Can you complete the household-input flow using only a keyboard?
      Check every form on `web/templates/household.html` and
      `web/templates/net_metering.html`.
- [ ] Are all range/slider inputs paired with a numeric text input you can
      type into directly? (Check `web/static/styles.css`
      `.range-with-number` and the corresponding HTML.)
- [ ] Does anything rely on hover, drag, or fine motor precision with no
      keyboard/focus equivalent?
- [ ] Run this site through a screen reader yourself. Does the reading
      order make sense? Are table headers announced correctly? Note:
      [ACCESSIBILITY.md](../ACCESSIBILITY.md) already discloses that a
      full manual screen-reader pass has not yet been logged by the
      project's own maintainers — your pass may be the first thorough
      one.
- [ ] Does the site work with JavaScript disabled? Check that standard
      scenario tables and methodology content remain fully readable (see
      [ACCESSIBILITY.md](../ACCESSIBILITY.md) "Supported input methods").

## Evidence status for assistive technology users

- [ ] Are `status` labels (observed/estimate/scenario) conveyed to a
      screen-reader user, or only visually (e.g., via colour or a small
      badge)? Check `web/templates/partials/assumption_tag.html` and
      whether it's used consistently across all relevant pages.
- [ ] Are charts (once built — none exist yet, see
      [docs/RED-TEAM-REVIEW.md §8.3](../docs/RED-TEAM-REVIEW.md)) backed
      by an equivalent data table from day one, or added as an
      afterthought? Hold future chart work to this standard before it
      ships.

## Automated testing status

- [ ] Run the Playwright/axe-core specs yourself
      (`tests/accessibility/`, per the setup in
      [ACCESSIBILITY.md](../ACCESSIBILITY.md)). As of this version, these
      specs are written but have not been executed in the project's own
      build environment — you may be able to run them where the
      maintainers could not.

## Privacy

- [ ] Confirm no household bill or account data is transmitted anywhere —
      inspect network requests while using the site (there should be
      none beyond loading the static assets themselves).
- [ ] Confirm no exact address or account number can end up in a
      shareable URL or downloaded scenario file.
- [ ] If a future critical-load/resilience feature ships, confirm it does
      not end up in a URL query string — see
      [MODEL_CARD.md](../MODEL_CARD.md) "Privacy" for the explicit rule
      this project has committed to.

## Security (forward-looking)

- [ ] If VPP/aggregator or bidirectional-EV remote-dispatch features are
      ever built, does the project's documentation (
      [MODEL_CARD.md](../MODEL_CARD.md) "Privacy") correctly anticipate
      that such participation implies third-party remote access to
      household equipment, distinct from this tool's own
      no-server-retention design?

## Report what you find

See [ACCESSIBILITY.md §How to report a problem](../ACCESSIBILITY.md) for
accessibility findings specifically; use a general GitHub issue for
privacy/security findings not covered there.
