import { expect, test } from "./fixtures";

test.describe.configure({ mode: "serial" });

async function start(
  page: import("@playwright/test").Page,
  source = "unit",
  pace = "max",
) {
  if (!page.url().includes("/demo/pipeline")) await page.goto("/demo/pipeline");
  await page.getByLabel("Source").selectOption(source);
  await page.getByLabel("Pace").selectOption(pace);
  const response = page.waitForResponse(
    (item) =>
      item.url().includes("/pipeline/run") &&
      item.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Start" }).click();
  return response;
}

const startTitle = [
  'Start with source unit and pace max; wait for "finished"; ',
  "the four lane counters sum to `total` from the start response.",
].join("");
test(startTitle, async ({
  page,
}) => {
  const response = await start(page);
  const body = (await response.json()) as { total: number };
  await expect(page.getByTestId("run-status")).toHaveText("Status: finished");
  const counts = await Promise.all(
    ["auto_accepted", "routed", "flagged", "review"].map((lane) =>
      page.getByTestId(`lane-count-${lane}`).textContent(),
    ),
  );
  expect(counts.reduce((sum, value) => sum + Number(value), 0)).toBe(
    body.total,
  );
  await expect(page.getByTestId("stats-strip")).toContainText(
    `Processed ${body.total}/${body.total}`,
  );
});

test('Stop mid-run at pace 1/s → status "stopped", and processed < total.', async ({
  page,
}) => {
  const response = await start(page, "unit", "1");
  const body = (await response.json()) as { total: number };
  await page.getByRole("button", { name: "Stop" }).click();
  await expect(page.getByTestId("run-status")).toHaveText("Status: stopped");
  const match = (await page.getByTestId("stats-strip").textContent())?.match(
    /Processed (\d+)\//,
  );
  expect(Number(match?.[1])).toBeLessThan(body.total);
});

test("Re-run with quality threshold 95 → the RerunDelta review count increases.", async ({
  page,
}) => {
  await start(page);
  await expect(page.getByTestId("run-status")).toHaveText("Status: finished");
  await page.getByLabel("Quality threshold").fill("95");
  await start(page);
  await expect(page.getByTestId("run-status")).toHaveText("Status: finished");
  const values = (await page.getByTestId("rerun-delta").textContent())?.match(
    /Review queue: (\d+) → (\d+)/,
  );
  expect(Number(values?.[2])).toBeGreaterThan(Number(values?.[1]));
});

test("Clicking a review item shows its `lane_reason`.", async ({ page }) => {
  await start(page);
  await expect(page.getByTestId("run-status")).toHaveText("Status: finished");
  await page.locator(".review-toggle").first().click();
  await expect(page.getByTestId("review-reason")).toHaveText(
    /^(score \d+ < threshold \d+|NIK gate failed: P\(valid\) \d\.\d\d|model chose unknown)/,
  );
});

test("No console errors during a full run.", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  await start(page);
  await expect(page.getByTestId("run-status")).toHaveText("Status: finished");
  expect(errors).toEqual([]);
});

test("a full all-source run renders exactly 100 feed rows", async ({
  page,
}) => {
  await start(page, "all");
  await expect(page.getByTestId("run-status")).toHaveText("Status: finished");
  expect(await page.getByTestId("live-feed").locator("tbody tr").count()).toBe(
    100,
  );
});

test("The drawer opens and shows a request id and a parsed metrics table.", async ({ page }) => {
  const responses: import("@playwright/test").Response[] = [];
  page.on("response", (response) => {
    if (response.url().includes("/api/")) responses.push(response);
  });
  await page.goto("/demo/studio/quality");
  const metricsResponse = page.waitForResponse((response) => (
    response.url().includes("/api/v1/metrics") && response.status() === 200
  ));
  await page.getByLabel("Observability").click();
  await metricsResponse;
  await expect(page.getByLabel("Observability drawer")).toBeVisible();
  await expect(page.getByRole("table", { name: "HTTP requests metrics" }))
    .toContainText("GET");
  const shown = await page.getByTestId("last-request-id").textContent();
  const requestId = shown?.replace("Request id: ", "") ?? "";
  expect(requestId).toMatch(/^[0-9a-f]{8}-[0-9a-f-]{27}$/i);
  expect(responses.some((response) => (
    response.headers()["x-request-id"] === requestId
  ))).toBe(true);
});

test("two pipeline tabs receive the same finished unit run", async ({ page: first }) => {
  const second = await first.context().newPage();
  await Promise.all([first.goto("/demo/pipeline"), second.goto("/demo/pipeline")]);
  await first.getByLabel("Pace").selectOption("max");
  await first.getByRole("button", { name: "Start" }).click();
  await Promise.all([
    expect(first.getByTestId("run-status")).toHaveText("Status: finished"),
    expect(second.getByTestId("run-status")).toHaveText("Status: finished"),
  ]);
  expect(await first.getByTestId("stats-strip").textContent()).toEqual(
    await second.getByTestId("stats-strip").textContent(),
  );
  await second.close();
});
