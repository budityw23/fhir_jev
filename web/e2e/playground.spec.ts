import { expect, test } from "./fixtures";

test("5. Playground: an invalid Condition shows the ErrorCard with a request id.", async (
  { page },
) => {
  await page.goto("/demo/playground");
  const editor = page.locator(".cm-content");
  await editor.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.type(JSON.stringify({ resourceType: "Condition", code: 7 }));
  await page.getByRole("button", { name: "Run" }).click();
  const error = page.getByRole("alert");
  await expect(error).toBeVisible();
  await expect(error).toContainText("request_id:");
  await expect(error.locator("code")).toHaveText(
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
  );
});
