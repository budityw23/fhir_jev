import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures";

const sizes = [
  { width: 1280, height: 720 },
  { width: 1920, height: 1080 },
];

test("captures all D2 pages at projector and desktop sizes", async ({ page }) => {
  for (const size of sizes) {
    await page.setViewportSize(size);
    await capture(page, "overview", async () => {
      await page.goto("/demo/");
      await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
    });
    await capture(page, "studio-quality", async () => {
      await page.goto("/demo/studio/quality");
      await page.getByLabel("complete_patient", { exact: true }).check();
      await expect(page.getByTestId("quality-action")).toBeVisible();
    });
    await capture(page, "studio-router", async () => {
      await page.goto("/demo/studio/router");
      await page.getByLabel("mixed_bundle", { exact: true }).check();
      await page.getByLabel("Route confidence minimum").fill("0.99");
      await expect(page.getByText("overridden: confidence 0.92 < 0.99")).toBeVisible();
    });
    await capture(page, "studio-notifiable", async () => {
      await page.goto("/demo/studio/notifiable");
      await page.getByLabel("japanese_encephalitis_a83", { exact: true }).check();
      await expect(page.getByRole("button", { name: "Flag" })).toBeVisible();
    });
    await capture(page, "playground", async () => {
      await page.goto("/demo/playground");
      await page.getByLabel("complete_patient", { exact: true }).check();
      await page.getByRole("button", { name: "Load fixture as starting point" }).click();
      await page.getByRole("button", { name: "Run" }).click();
      await expect(page.getByTestId("lane")).toBeVisible();
    });
    await capture(page, "pipeline", async () => {
      await page.goto("/demo/pipeline");
      await page.getByLabel("Source").selectOption("unit");
      await page.getByLabel("Pace").selectOption("max");
      await page.getByRole("button", { name: "Start" }).click();
      await expect(page.getByTestId("run-status")).toHaveText("Status: finished");
    });
  }
});

async function capture(
  page: Page,
  name: string,
  prepare: () => Promise<void>,
): Promise<void> {
  await prepare();
  const viewport = page.viewportSize();
  if (viewport === null) throw new Error("Screenshot viewport is unavailable");
  await page.screenshot({
    fullPage: true,
    path: `e2e/screenshots/${name}-${viewport.width}x${viewport.height}.png`,
  });
}
