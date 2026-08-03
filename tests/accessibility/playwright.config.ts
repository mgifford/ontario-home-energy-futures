import { defineConfig } from "@playwright/test";

// Requires `npm install` in this directory and `npx playwright install`
// before it can run. See README.md and ACCESSIBILITY.md for setup; this
// build environment does not have Playwright's browser binaries installed,
// so these specs are written but not executed here.
export default defineConfig({
  testDir: ".",
  webServer: {
    command: "python3 -m http.server 8765 -d ../../dist",
    port: 8765,
    reuseExistingServer: true,
    timeout: 30_000,
  },
  use: {
    baseURL: "http://localhost:8765",
  },
});
