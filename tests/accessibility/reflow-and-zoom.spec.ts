import { test, expect } from "@playwright/test";

// Reflow at 320 CSS pixels wide (WCAG 1.4.10). See ACCESSIBILITY.md manual
// checklist item for the 200% browser-zoom equivalent, which needs a real
// browser zoom API and is verified manually rather than here.

test("page reflows at 320px width without horizontal scrolling on body", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto("/index.html");
  const hasHorizontalScroll = await page.evaluate(() => {
    return document.documentElement.scrollWidth > document.documentElement.clientWidth + 1;
  });
  expect(hasHorizontalScroll).toBe(false);
});

test("wide tables scroll within their own container, not the page", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto("/compare-timing.html");
  const scrollContainer = page.locator(".table-scroll").first();
  await expect(scrollContainer).toBeVisible();
  const pageHasHorizontalScroll = await page.evaluate(() => {
    return document.documentElement.scrollWidth > document.documentElement.clientWidth + 1;
  });
  expect(pageHasHorizontalScroll).toBe(false);
});
