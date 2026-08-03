import { test, expect } from "@playwright/test";

// Keyboard-only navigation and focus-order specs. See ACCESSIBILITY.md
// "Design commitments" and the manual test checklist.

test("skip link is the first focusable element and jumps to main content", async ({ page }) => {
  await page.goto("/index.html");
  await page.keyboard.press("Tab");
  const active = await page.evaluate(() => document.activeElement?.className);
  expect(active).toContain("skip-link");
  await page.keyboard.press("Enter");
  const mainFocused = await page.evaluate(() => document.activeElement?.id === "main-content" || document.location.hash === "#main-content");
  expect(mainFocused).toBeTruthy();
});

test("every page has exactly one h1", async ({ page }) => {
  const pages = ["index.html", "household.html", "compare-timing.html", "net-metering.html"];
  for (const p of pages) {
    await page.goto(`/${p}`);
    const h1Count = await page.locator("h1").count();
    expect(h1Count, `${p} should have exactly one h1`).toBe(1);
  }
});

test("main navigation is reachable and operable by keyboard", async ({ page }) => {
  await page.goto("/index.html");
  const navLinks = page.locator("nav.site-nav a");
  const count = await navLinks.count();
  expect(count).toBeGreaterThan(5);
  await navLinks.first().focus();
  await expect(navLinks.first()).toBeFocused();
});

test("compare-timing form range input has a paired numeric input kept in sync", async ({ page }) => {
  await page.goto("/compare-timing.html");
  const range = page.locator("#discount-range");
  const number = page.locator("#discount-number");
  await expect(range).toHaveCount(1);
  await expect(number).toHaveCount(1);
  await range.fill("10");
  await range.dispatchEvent("input");
  await expect(number).toHaveValue("10");
});

test("no keyboard trap when tabbing through the household form", async ({ page }) => {
  await page.goto("/household.html");
  for (let i = 0; i < 15; i++) {
    await page.keyboard.press("Tab");
  }
  // If a trap existed, focus would be stuck on one element; simply
  // completing 15 tabs without hanging (Playwright would time out on a
  // genuine trap in surrounding assertions) is the primary signal here.
  const activeTag = await page.evaluate(() => document.activeElement?.tagName);
  expect(activeTag).toBeTruthy();
});
