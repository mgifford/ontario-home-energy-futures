# Accessibility

## Target

Ontario Home Energy Futures targets **WCAG 2.2 Level AA** as a minimum across all
pages, including the interactive calculator.

## Supported input methods

- Full keyboard operation, including all form controls, the results table, and
  any progressive-disclosure ("show advanced options") controls.
- Screen readers (tested with the browser accessibility tree and at least one
  manual screen-reader pass; see "Manual test process" below).
- Browser zoom up to 200% and reflow at 320 CSS pixels wide.
- Touch, with minimum target sizes per WCAG 2.2 (2.5.8).
- Reduced-motion and high-contrast operating-system settings.
- No JavaScript: every essential methodology page, source-documentation page,
  and a set of standard precomputed scenarios (500/700/1,000/1,500 kWh at the
  reference electricity-price and solar-cost scenarios) render as static HTML
  with no dependency on JavaScript. Instant recalculation with custom inputs
  requires JavaScript; the equivalent inputs can still be explored by selecting
  from the precomputed standard scenarios without it.

## Design commitments

- Semantic HTML first; ARIA only where no native element suffices.
- Correct `lang` attribute; a skip-to-content link on every page.
- Logical, single heading hierarchy per page (no skipped levels).
- Native form controls (`<input>`, `<select>`, `<fieldset>`/`<legend>`) for every
  input, with explicit `<label>` elements and instructions placed before the
  control they describe.
- Any range/slider control has an equivalent numeric text input; no
  drag-only or slider-only interaction exists anywhere in the site.
- Validation errors are associated programmatically with their field
  (`aria-describedby`) and summarized in an error summary linked to each
  invalid field.
- Visible focus indicators on every interactive element; no keyboard traps.
- Colour is never the only way information is conveyed (e.g., scenario ranges
  use pattern/label in addition to colour in any chart).
- **Planned, not yet implemented:** charts are intended to be inline, accessibly
  named SVG, each with an equivalent HTML data table adjacent to it — the table
  as the source of truth, the chart as a supplement. No chart currently exists
  in the application (see "Known limitations" below and
  [docs/RED-TEAM-REVIEW.md](docs/RED-TEAM-REVIEW.md) section 8.3).
- Dynamic result updates (client-side recalculation) are announced via an
  appropriately scoped live region, and focus is not moved unexpectedly after
  recalculation.
- `prefers-reduced-motion` disables any non-essential transition or animation.
- Currency, percentages, and units are written in full plain language on first
  use per page, with a glossary of technical terms linked from every page
  footer.

## Testing tools

- **axe-core**, run automatically against every built page
  (`tests/accessibility/`).
- **Playwright**, driving keyboard-only navigation, focus-order, and form
  submission/error-handling specs (`tests/accessibility/`,
  `tests/integration/`).
- Browser DevTools accessibility tree inspection.
- Browser zoom and reflow testing at 320px width / 200% zoom.
- Operating-system high-contrast and reduced-motion simulation.

Automated tests (axe-core rule violations, keyboard-navigation specs) are
necessary but **not sufficient** on their own — see the manual checklist below.

## Manual test process

Before each release, complete this checklist against the built site:

- [ ] Navigate every page using only the keyboard (Tab, Shift+Tab, Enter,
      Space, arrow keys where applicable). Confirm a visible focus indicator at
      every stop and no keyboard trap.
- [ ] Complete the full "explore your household" → "compare solar purchase
      timing" flow using only the keyboard.
- [ ] Trigger a validation error (e.g. a non-numeric consumption value) and
      confirm the error is announced, linked to its field, and listed in an
      error summary.
- [ ] Zoom the browser to 200% and confirm no content or functionality is lost,
      and no horizontal scrolling is required for body text.
- [ ] Resize the viewport to 320 CSS pixels wide and confirm the layout
      reflows without loss of content or function.
- [ ] Enable a high-contrast OS/browser setting and confirm all text and
      controls remain legible and operable.
- [ ] Enable "reduce motion" and confirm no non-essential animation plays.
- [ ] Run at least one full manual pass with a screen reader (e.g. VoiceOver,
      NVDA, or JAWS) through the home page, the household input flow, and the
      results comparison table, confirming table headers and dynamic-update
      announcements all make sense read aloud. (No chart currently exists to
      verify chart accessible names against — see "Known limitations.")
- [ ] Disable JavaScript and confirm the methodology, data-source, and standard
      precomputed scenario pages remain fully readable and usable.
- [ ] Run `axe-core` against the built `dist/` output and confirm zero
      violations at the `serious` or `critical` impact level.

## Known limitations

- The client-side calculator's live-region announcement wording has not yet
  been validated with a screen-reader user outside the project maintainers; see
  the open accessibility issues for the current status.
- Playwright/axe-core automated specs are included in `tests/accessibility/` but
  require a local `npm install` and Playwright browser-binary install to
  execute; they have not been run inside this build environment (see the
  project's implementation report for details).
- A full manual screen-reader pass against a live deployment has not yet been
  logged for this Phase 1 prototype; it is listed above as a required
  pre-release step.
- **No chart exists in the application yet.** `src/ontario_home_energy_futures/charts/`
  is currently empty. The "Accessibility decision record" below describes the
  intended design for when charts are built, not delivered functionality — see
  [docs/RED-TEAM-REVIEW.md](docs/RED-TEAM-REVIEW.md) section 8.3 and
  [docs/CORRECTIONS.md](docs/CORRECTIONS.md) for how this documentation
  overstatement was found and corrected.

## Accessibility decision record: charts and dynamic results

**Status: planned design, not yet implemented.** The decisions below describe
how charts must be built when that work happens, so the design is settled in
advance and reviewable now — not a description of current behaviour.

- **Decision:** Every chart will be inline SVG (not a client-side charting library),
  paired with a visible or accessibly-linked HTML `<table>` containing the same
  data. Rationale: this avoids a third-party charting dependency, keeps the data
  available to assistive technology without relying on ARIA graphics roles
  working correctly in every browser/AT combination, and keeps the page-weight
  budget low.
- **Decision:** Dynamic recalculation results update within a labelled
  `aria-live="polite"` region, and keyboard focus stays on the control the user
  just used rather than jumping to the results. Rationale: prevents disorienting
  focus jumps while still surfacing the update to screen-reader users.
- **Decision:** No slider-only inputs. Every range control has a paired numeric
  `<input type="number">` kept in sync. Rationale: sliders are difficult to
  operate precisely with a keyboard or with some assistive technologies;
  requiring a numeric alternative is explicit in this project's accessibility
  requirements.

## How to report a problem

Open a GitHub issue using the "Accessibility" label, including: the page URL,
the assistive technology and browser/OS combination (if applicable), the
expected behaviour, and the actual behaviour. If you are not comfortable
opening a public issue, note that in the issue and a maintainer will follow up
about a private channel.
