import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures";

const sizes = [
  { width: 1280, height: 720 },
  { width: 1920, height: 1080 },
];

test("D4 polish keeps every main page within both projector widths", async ({ page }) => {
  for (const size of sizes) {
    await page.setViewportSize(size);
    for (const path of [
      "/demo/",
      "/demo/studio/quality",
      "/demo/studio/router",
      "/demo/studio/notifiable",
      "/demo/playground",
      "/demo/benchmarks",
    ]) {
      await page.goto(path);
      await expect(page.locator("main")).toBeVisible();
      await expect(noHorizontalScroll(page)).resolves.toBe(true);
    }
    await page.goto("/demo/pipeline");
    await page.getByLabel("Source").selectOption("unit");
    await page.getByLabel("Pace").selectOption("max");
    await page.getByRole("button", { name: "Start" }).click();
    await expect(page.getByTestId("run-status")).toHaveText("Status: finished");
    await expect(noHorizontalScroll(page)).resolves.toBe(true);
    await page.getByLabel("Observability").click();
    await expect(page.getByLabel("Observability drawer")).toBeVisible();
    await expect(noHorizontalScroll(page)).resolves.toBe(true);
  }
});

test("900px Overview and Studio have no horizontal scroll", async ({ page }) => {
  await page.setViewportSize({ width: 900, height: 800 });
  for (const path of ["/demo/", "/demo/studio/quality"]) {
    await page.goto(path);
    await expect(noHorizontalScroll(page)).resolves.toBe(true);
  }
});

async function noHorizontalScroll(page: Page): Promise<boolean> {
  return page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
}

test("Studio columns stack below 1024 pixels", async ({ page }) => {
  await page.setViewportSize({ width: 900, height: 800 });
  await page.goto("/demo/studio/quality");
  const columns = page.locator(".studio-grid > div");
  const boxes = await Promise.all([0, 1, 2].map((index) => columns.nth(index).boundingBox()));
  expect(boxes.every((box) => box !== null)).toBe(true);
  expect(boxes.map((box) => box!.x)).toEqual([boxes[0]!.x, boxes[0]!.x, boxes[0]!.x]);
});

test("reduced motion stops the architecture edge animation", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/demo/");
  await expect(page.locator(".architecture-edge").first()).toHaveCSS("animation-name", "none");
});
