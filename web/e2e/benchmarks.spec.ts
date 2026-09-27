import { expect, test } from "./fixtures";

const latestTitle = [
  "The benchmarks page shows the latest report; ",
  "the mock report shows the disclaimer and router FAIL.",
].join("");
test(latestTitle, async ({ page }) => {
  await page.goto("/demo/benchmarks");
  await expect(
    page.getByText(
      "Mock decisions mirror rule logic; this report validates the harness, not Jev.",
    ),
  ).toBeVisible();
  await expect(page.getByText("FAIL · Routing accuracy ≥ 90%")).toBeVisible();
  await page
    .getByLabel("Benchmark report")
    .selectOption("bench_20260924T151507Z");
  const router = page
    .locator(".benchmark-card")
    .filter({ hasText: "Accuracy" })
    .getByRole("row", { name: /Router/ });
  await expect(router).toContainText("73%");
  await expect(router).toContainText("FAIL · Routing accuracy ≥ 90%");
});

test("A disagreement row click opens Studio with that fixture.", async ({
  page,
}) => {
  await page.goto("/demo/benchmarks");
  const row = page
    .locator(".disagreement-list a")
    .filter({ hasText: "Router:" })
    .first();
  const href = await row.getAttribute("href");
  const fixture = new URL(`http://localhost${href}`).searchParams.get(
    "fixture",
  );
  await row.click();
  await expect(page).toHaveURL(
    new RegExp(href?.replace(/[?]/g, "\\?") ?? "studio"),
  );
  expect(new URL(page.url()).searchParams.get("fixture")).toBe(fixture);
  await expect(page.locator("input[type=radio]:checked")).toHaveCount(1);
});

test("Benchmarks guards old labels without horizontal scroll or console errors.", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto("/demo/benchmarks");
  await page
    .getByLabel("Benchmark report")
    .selectOption("bench_20260924T083443Z");
  await expect(
    page.getByText("labels not suitable for live scoring").first(),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});
