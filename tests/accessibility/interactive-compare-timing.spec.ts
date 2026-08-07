import { test, expect } from "@playwright/test";

// Verifies the client-side interactive calculator on compare-timing.html:
// JS-rendered results must match the no-JS server-rendered baseline on
// first load, recalculation must happen without a network request, and
// the live region must announce changes without moving focus. See the
// interactive-dashboard plan and ACCESSIBILITY.md's decision record on
// dynamic results.

test("JS-rendered table matches the no-JS server-rendered table on default load", async ({ page }) => {
  // First capture the no-JS baseline.
  const noJsContext = await page.context().browser()!.newContext({ javaScriptEnabled: false });
  const noJsPage = await noJsContext.newPage();
  await noJsPage.goto("/compare-timing.html");
  const noJsFirstRow = (await noJsPage.locator("#compare-timing-tbody tr").first().textContent())!
    .replace(/\s+/g, " ")
    .trim();
  await noJsContext.close();

  // Then load with JS enabled and let it recalculate on page load isn't
  // automatic (only on user input) - the initial server-rendered content
  // must already match what the JS *would* compute for the same defaults,
  // so no recalculation is required to see a consistent first paint.
  await page.goto("/compare-timing.html");
  const jsFirstRow = (await page.locator("#compare-timing-tbody tr").first().textContent())!
    .replace(/\s+/g, " ")
    .trim();

  expect(jsFirstRow).toBe(noJsFirstRow);
});

test("changing household consumption recalculates the table without a network request", async ({ page }) => {
  await page.goto("/compare-timing.html");

  const networkRequests: string[] = [];
  page.on("request", (req) => {
    if (!req.url().endsWith(".html")) {
      networkRequests.push(req.url());
    }
  });

  const beforeRange = await page.locator("#compare-timing-range").textContent();

  await page.locator("#calc-monthly-kwh").fill("1500");
  await page.locator("#calc-monthly-kwh").dispatchEvent("input");
  await page.waitForTimeout(400); // allow the debounce + recalculation

  const afterRange = await page.locator("#compare-timing-range").textContent();
  expect(afterRange).not.toBe(beforeRange);

  // The only non-.html network requests should be the one-time data JSON
  // fetches on initial page load (rates.json, scenarios-full.json,
  // assumption-defaults.json, calculator.js, styles.css) - none of these
  // should repeat as a result of the recalculation itself, and nothing
  // should be a household-data-carrying request.
  const recalculationRequests = networkRequests.filter((url) => !url.includes("/data/") && !url.includes("calculator.js") && !url.includes("styles.css"));
  expect(recalculationRequests).toEqual([]);
});

test("recalculation announces via the live region without moving focus", async ({ page }) => {
  await page.goto("/compare-timing.html");

  const monthlyKwhInput = page.locator("#calc-monthly-kwh");
  await monthlyKwhInput.focus();
  await monthlyKwhInput.fill("1000");
  await monthlyKwhInput.dispatchEvent("input");
  await page.waitForTimeout(400);

  const liveRegionText = await page.locator("#results-status").textContent();
  expect(liveRegionText).toContain("Recalculated");
  expect(liveRegionText).toContain("modelled estimate");

  const focusedId = await page.evaluate(() => document.activeElement?.id);
  expect(focusedId).toBe("calc-monthly-kwh");
});

test("range and number inputs for group discount stay in sync", async ({ page }) => {
  await page.goto("/compare-timing.html");
  const range = page.locator("#discount-range");
  const number = page.locator("#discount-number");

  await range.fill("10");
  await range.dispatchEvent("input");
  await expect(number).toHaveValue("10");

  await number.fill("15");
  await number.dispatchEvent("input");
  await expect(range).toHaveValue("15");
});

test("changing an input recalculates the collective-purchasing and cost-of-inaction tables live", async ({ page }) => {
  await page.goto("/compare-timing.html");

  const collectiveBefore = await page.locator("#collective-purchasing-tbody").innerHTML();
  const inactionBefore = await page.locator("#cost-of-inaction-tbody").innerHTML();

  await page.locator("#calc-monthly-kwh").fill("1500");
  await page.locator("#calc-monthly-kwh").dispatchEvent("input");
  await page.waitForTimeout(400);

  const collectiveAfter = await page.locator("#collective-purchasing-tbody").innerHTML();
  const inactionAfter = await page.locator("#cost-of-inaction-tbody").innerHTML();

  expect(collectiveAfter).not.toBe(collectiveBefore);
  expect(inactionAfter).not.toBe(inactionBefore);

  // Both tables must still have their expected row counts after
  // recalculation (4 collective-purchasing tiers, 3 cost-of-inaction
  // decisions) - a recalculation bug could plausibly clear or duplicate
  // rows without changing enough content to fail the above inequality
  // checks alone.
  expect(await page.locator("#collective-purchasing-tbody tr").count()).toBe(4);
  expect(await page.locator("#cost-of-inaction-tbody tr").count()).toBe(3);
});

test("cumulative-cost chart and table are present on default load with no JS interaction", async ({ page }) => {
  await page.goto("/compare-timing.html");
  const svg = page.locator("#cumulative-cost-chart-container svg");
  await expect(svg).toBeVisible();
  await expect(page.locator("#cumulative-cost-chart-container polyline")).toHaveCount(4);

  const table = page.locator("#cumulative-cost-table");
  await expect(table).toBeVisible();
  const rowCount = await page.locator("#cumulative-cost-tbody tr").count();
  expect(rowCount).toBeGreaterThan(0);
});

test("cumulative-cost chart updates live when an input changes", async ({ page }) => {
  await page.goto("/compare-timing.html");

  const svgBefore = await page.locator("#cumulative-cost-chart-container").innerHTML();
  const tableBefore = await page.locator("#cumulative-cost-tbody").innerHTML();

  await page.locator("#calc-monthly-kwh").fill("1500");
  await page.locator("#calc-monthly-kwh").dispatchEvent("input");
  await page.waitForTimeout(400);

  const svgAfter = await page.locator("#cumulative-cost-chart-container").innerHTML();
  const tableAfter = await page.locator("#cumulative-cost-tbody").innerHTML();

  expect(svgAfter).not.toBe(svgBefore);
  expect(tableAfter).not.toBe(tableBefore);
  await expect(page.locator("#cumulative-cost-chart-container polyline")).toHaveCount(4);
});

test("cumulative-cost chart's last row matches the main comparison table's 20-year totals", async ({ page }) => {
  await page.goto("/compare-timing.html");

  const lastChartRow = page.locator("#cumulative-cost-tbody tr").last();
  const gridOnlyChartValue = await lastChartRow.locator("td").nth(0).textContent();

  const gridOnlyTableRow = page.locator("#compare-timing-tbody tr").first(); // "Grid only" is first row
  const gridOnlyTableValue = await gridOnlyTableRow.locator("td").nth(3).textContent(); // 20-year cost column

  const parseCad = (s: string) => Number(s.replace(/[$,]/g, ""));
  expect(parseCad(gridOnlyChartValue!)).toBeCloseTo(parseCad(gridOnlyTableValue!), 0);
});

test("collective-purchasing initial cost decreases monotonically by group size after recalculation", async ({ page }) => {
  await page.goto("/compare-timing.html");
  await page.locator("#calc-quote-total").fill("25000");
  await page.locator("#calc-quote-total").dispatchEvent("input");
  await page.waitForTimeout(400);

  const rows = page.locator("#collective-purchasing-tbody tr");
  const count = await rows.count();
  const costs: number[] = [];
  for (let i = 0; i < count; i++) {
    const cellText = await rows.nth(i).locator("td").nth(1).textContent();
    costs.push(Number(cellText!.replace(/[$,]/g, "")));
  }
  for (let i = 1; i < costs.length; i++) {
    expect(costs[i]).toBeLessThanOrEqual(costs[i - 1]);
  }
});

test("no household data appears in any request URL or query string", async ({ page }) => {
  const requestUrls: string[] = [];
  page.on("request", (req) => requestUrls.push(req.url()));

  await page.goto("/compare-timing.html");
  await page.locator("#calc-monthly-kwh").fill("1234");
  await page.locator("#calc-monthly-kwh").dispatchEvent("input");
  await page.locator("#calc-quote-total").fill("27500");
  await page.locator("#calc-quote-total").dispatchEvent("input");
  await page.waitForTimeout(400);

  for (const url of requestUrls) {
    expect(url).not.toContain("1234");
    expect(url).not.toContain("27500");
  }
});

test("entered values persist to localStorage and are restored on reload", async ({ page }) => {
  await page.goto("/compare-timing.html");

  await page.locator("#calc-monthly-kwh").fill("1234");
  await page.locator("#calc-monthly-kwh").dispatchEvent("input");
  await page.waitForTimeout(400);

  const stored = await page.evaluate(() =>
    localStorage.getItem("ontario-home-energy-futures:compare-timing-inputs:v1")
  );
  expect(stored).toContain("1234");

  await page.reload();
  await page.waitForTimeout(400);

  await expect(page.locator("#calc-monthly-kwh")).toHaveValue("1234");
});

test("reset to defaults clears localStorage and restores default values", async ({ page }) => {
  await page.goto("/compare-timing.html");

  await page.locator("#calc-monthly-kwh").fill("1234");
  await page.locator("#calc-monthly-kwh").dispatchEvent("input");
  await page.waitForTimeout(400);

  await page.locator("#reset-to-defaults").click();
  await page.waitForTimeout(300);

  await expect(page.locator("#calc-monthly-kwh")).toHaveValue("700");
  const stored = await page.evaluate(() =>
    localStorage.getItem("ontario-home-energy-futures:compare-timing-inputs:v1")
  );
  expect(stored).toBeNull();
});

test("nothing is stored in localStorage before the user changes anything", async ({ page }) => {
  await page.goto("/compare-timing.html");
  await page.waitForTimeout(300);
  const stored = await page.evaluate(() =>
    localStorage.getItem("ontario-home-energy-futures:compare-timing-inputs:v1")
  );
  expect(stored).toBeNull();
});
