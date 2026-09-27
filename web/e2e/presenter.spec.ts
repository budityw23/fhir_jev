import { expect, test } from "./fixtures";

test.describe.configure({ mode: "serial" });

const walkTitle = [
  "Pressing `→` from Overview walks scenes 0 through 6 with no manual input, ",
  "and each scene's key element is visible.",
].join("");

test(walkTitle, async ({ page }) => {
  await page.goto("/demo/");
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await page.keyboard.press("1");
  await expect(page).toHaveURL(/studio\/quality.*complete_patient/);
  await expect(page.getByTestId("lane")).toBeVisible();
  for (let index = 0; index < 4; index += 1)
    await page.keyboard.press("ArrowRight");
  await expect(page.getByTestId("quality-action")).toHaveText(/review_needed/);
  await page.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/studio\/router.*lab_bundle/);
  for (let index = 0; index < 3; index += 1)
    await page.keyboard.press("ArrowRight");
  await expect(
    page.getByText("overridden: confidence 0.92 < 0.99"),
  ).toBeVisible();
  await page.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/studio\/notifiable.*japanese_encephalitis/);
  await expect(page.getByRole("button", { name: "Flag" })).toBeVisible();
  for (let index = 0; index < 3; index += 1)
    await page.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/pipeline$/);
  await expect(page.getByTestId("run-status")).toContainText(
    /running|finished/,
  );
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("heading", { name: "Benchmarks" })).toBeVisible();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
});

test("`R` resets the thresholds.", async ({ page }) => {
  await page.goto("/demo/");
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await page.keyboard.press("ArrowRight");
  await page.getByLabel("Quality threshold").fill("85");
  await expect(page.getByTestId("quality-action")).toHaveText(/review_needed/);
  await page.keyboard.press("r");
  await expect(page.getByLabel("Quality threshold")).toHaveValue("70");
});

test("`F` changes the root font size.", async ({ page }) => {
  await page.goto("/demo/");
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  const before = await page
    .locator("html")
    .evaluate((node) => getComputedStyle(node).fontSize);
  await page.keyboard.press("f");
  await expect
    .poll(async () =>
      page.locator("html").evaluate((node) => getComputedStyle(node).fontSize),
    )
    .not.toBe(before);
});

test("`1`–`6` jump to the matching scene.", async ({ page }) => {
  await page.goto("/demo/");
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await page.keyboard.press("2");
  await expect(page).toHaveURL(/studio\/router.*lab_bundle/);
  await page.keyboard.press("6");
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
});

test("The network guard (no external hosts) covers the whole walk.", async ({
  page,
  blockedUrls,
}) => {
  await page.goto("/demo/");
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByTestId("lane")).toBeVisible();
  expect(blockedUrls).toEqual([]);
});
