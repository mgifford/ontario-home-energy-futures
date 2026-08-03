import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// Automated axe-core sweep of every built page. Run `python build.py`
// first so dist/ exists. See ACCESSIBILITY.md: automated tests are
// necessary but not sufficient - pair with the manual checklist there.
const PAGES = [
  "index.html",
  "current-costs.html",
  "household.html",
  "compare-timing.html",
  "net-metering.html",
  "battery-generator.html",
  "assumptions.html",
  "data-sources.html",
  "methodology.html",
  "download.html",
  "accessibility.html",
  "about.html",
];

for (const page of PAGES) {
  test(`axe-core: ${page} has no serious or critical violations`, async ({ page: browserPage }) => {
    await browserPage.goto(`/${page}`);
    const results = await new AxeBuilder({ page: browserPage })
      .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
      .analyze();

    const seriousOrCritical = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical"
    );
    expect(seriousOrCritical, JSON.stringify(seriousOrCritical, null, 2)).toEqual([]);
  });
}
