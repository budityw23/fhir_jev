import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: { baseURL: "http://127.0.0.1:8010/demo/", browserName: "chromium" },
  webServer: {
    command: [
      "cd .. && make web-build &&",
      "DEMO_ENABLED=true MOCK_JEV=true .venv/bin/python -m uvicorn",
      "jev_fhir.main:app --host 127.0.0.1 --port 8010",
    ].join(" "),
    url: "http://127.0.0.1:8010/demo/",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
