import { expect, test } from "./fixtures";

const qualityTitle = [
  "2. Studio quality: pick `complete_patient`, see `auto_accept`, ",
  "drag the threshold to 85, see `review_needed`.",
].join("");
const notifiableTitle = [
  "4. Studio notifiable: the JE fixture shows the Flag tab and the Dinkes card; ",
  "common cold shows neither.",
].join("");

test(qualityTitle, async ({ page }) => {
  await page.goto("/demo/studio/quality");
  await page.getByLabel("complete_patient", { exact: true }).check();
  await expect(page.getByTestId("quality-action")).toHaveText(/auto_accept/);
  await page.getByLabel("Quality threshold").fill("85");
  await expect(page.getByTestId("quality-action")).toHaveText(/review_needed/);
  await expect(page.getByTestId("lane-reason")).toHaveText("score 80 < threshold 85");
});

test("3. Studio router: `mixed_bundle`, floor 0.99, see the override note.", async ({ page }) => {
  await page.goto("/demo/studio/router");
  await page.getByLabel("mixed_bundle", { exact: true }).check();
  await page.getByLabel("Route confidence minimum").fill("0.99");
  await expect(page.getByText("overridden: confidence 0.92 < 0.99")).toBeVisible();
});

test(notifiableTitle, async ({ page }) => {
  await page.goto("/demo/studio/notifiable");
  await page.getByLabel("japanese_encephalitis_a83", { exact: true }).check();
  await expect(page.getByText(/Report to Dinkes/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Flag" })).toBeVisible();
  await page.getByLabel("common_cold_j06", { exact: true }).check();
  await expect(page.getByText(/Report to Dinkes/)).not.toBeVisible();
  await expect(page.getByRole("button", { name: "Flag" })).not.toBeVisible();
});

test("6. A deep link reload of `/demo/studio/router?fixture=…` works.", async ({ page }) => {
  await page.goto("/demo/studio/router?fixture=tests/fixtures/bundles/mixed_bundle.json");
  await page.reload();
  await expect(page.getByLabel("mixed_bundle", { exact: true })).toBeChecked();
});
