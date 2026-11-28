import { defineConfig, devices } from "@playwright/test";

// The tests serve the built page and answer /api with fake data. No backend and no Paperclip is read.
const PORT = Number(process.env.SAFEBOARD_TEST_PORT || 4179);

// Width order follows the mobile-first acceptance order. Firefox is left out on purpose.
const SIZES = [
  ["320", { width: 320, height: 640 }],
  ["360", { width: 360, height: 740 }],
  ["375", { width: 375, height: 812 }],
  ["390", { width: 390, height: 844 }],
  ["tablet", { width: 768, height: 1024 }],
  ["desktop", { width: 1280, height: 800 }],
];
const ENGINES = [
  ["chromium", devices["Desktop Chrome"]],
  ["webkit", devices["Desktop Safari"]],
];

export default defineConfig({
  testDir: "tests",
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: process.env.CI ? [["list"], ["github"]] : "list",
  use: { baseURL: `http://127.0.0.1:${PORT}`, trace: "retain-on-failure" },
  // Local quick run: npm run test:quick (one project, 320 px). CI runs every project.
  projects: ENGINES.flatMap(([engine, device]) => SIZES.map(([name, viewport]) => ({ name: `${engine}-${name}`, use: { ...device, viewport } }))),
  webServer: {
    command: `npm run build && npx vite preview --host 127.0.0.1 --port ${PORT} --strictPort`,
    url: `http://127.0.0.1:${PORT}/`,
    reuseExistingServer: false,
    timeout: 120000,
  },
});
