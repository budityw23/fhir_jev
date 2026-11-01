/** Standalone, mock-only continuous demo recorder. */
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: "*.video.ts",
  timeout: 180_000,
  workers: 1,
  retries: 0,
  outputDir: "../test-results/video-recording",
  use: {
    baseURL: "http://127.0.0.1:18760/demo/",
    browserName: "chromium",
    viewport: { width: 1920, height: 1080 },
    video: { mode: "on", size: { width: 1920, height: 1080 } },
    colorScheme: "light",
  },
  webServer: {
    command: "cd ../.. && DEMO_ENABLED=true MOCK_JEV=true .venv/bin/python -m " +
      "uvicorn jev_fhir.main:app --host 127.0.0.1 --port 18760",
    url: "http://127.0.0.1:18760/demo/",
    reuseExistingServer: true,
  },
});
