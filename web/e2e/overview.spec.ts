import { expect, test } from "./fixtures";

test("1. Overview loads, and the mode badge says MOCK.", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await expect(
    page.getByTitle(
      "Deterministic offline client — decisions are rule-derived, latency is simulated.",
    ),
  ).toHaveText(/MOCK/);
});

test.fail(
  "network guard catches and records an external request",
  async ({ page }) => {
    const result = await page.evaluate(async () => {
      try {
        await fetch("http://example.com/");
        return "allowed";
      } catch {
        return "blocked";
      }
    });

    expect(result).toBe("blocked");
  },
);
