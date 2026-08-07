import { test, expect } from "@playwright/test";

// Confirms the site's no-JavaScript baseline: methodology, data-source, and
// standard-scenario content must remain fully usable with JavaScript
// disabled. See ACCESSIBILITY.md "Supported input methods".

test.use({ javaScriptEnabled: false });

test("standard scenario table is present without JavaScript", async ({ page }) => {
  await page.goto("/index.html");
  const table = page.locator("table").first();
  await expect(table).toBeVisible();
  await expect(page.locator("text=500 kWh").first()).toBeVisible();
});

test("methodology page is fully readable without JavaScript", async ({ page }) => {
  await page.goto("/methodology.html");
  await expect(page.locator("h1")).toHaveText("Methodology");
  const headingCount = await page.locator("h2").count();
  expect(headingCount).toBeGreaterThan(5);
});

test("current-costs standardized bill table renders without JavaScript", async ({ page }) => {
  await page.goto("/current-costs.html");
  await expect(page.locator("table").first()).toBeVisible();
});

test("noscript warning appears on the household page without JavaScript", async ({ page }) => {
  await page.goto("/household.html");
  // Playwright's javaScriptEnabled:false context renders <noscript>
  // content into the accessibility tree (innerText) but not into the raw
  // DOM textContent, so innerText() is used here rather than
  // toContainText/textContent - this reflects an actual real browser with
  // JS disabled, which does render this content visibly.
  const noscriptText = await page.locator("noscript").innerText();
  expect(noscriptText).toContain("JavaScript is off");
});

test("compare-timing table and noscript warning render without JavaScript", async ({ page }) => {
  await page.goto("/compare-timing.html");
  const noscriptText = await page.locator("noscript").innerText();
  expect(noscriptText).toContain("JavaScript is off");
  const table = page.locator("#compare-timing-tbody");
  await expect(table).toBeVisible();
  const rowCount = await table.locator("tr").count();
  expect(rowCount).toBeGreaterThan(0);
  // The interactive form must not be shown/usable without JS (CSS-hidden
  // via .js-only until .js-enabled is set by calculator.js).
  await expect(page.locator("#compare-timing-form")).toBeHidden();
});
