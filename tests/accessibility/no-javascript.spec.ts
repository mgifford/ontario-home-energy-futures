import { test, expect } from "@playwright/test";

// Confirms the site's no-JavaScript baseline: methodology, data-source, and
// standard-scenario content must remain fully usable with JavaScript
// disabled. See ACCESSIBILITY.md "Supported input methods".

test.use({ javaScriptEnabled: false });

test("standard scenario table is present without JavaScript", async ({ page }) => {
  await page.goto("/index.html");
  const table = page.locator("table").first();
  await expect(table).toBeVisible();
  await expect(page.locator("text=500 kWh")).toBeVisible();
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
  await expect(page.locator("noscript")).toContainText("JavaScript is off");
});
