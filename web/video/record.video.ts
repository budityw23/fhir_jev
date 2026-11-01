/** Record one continuous take with browser-drawn captions and real presenter controls. */
import { expect, test } from "@playwright/test";
import { writeFile } from "node:fs/promises";

test("record the Jev × FHIR demo", async ({ page }) => {
  const started = Date.now();
  const timings: Array<{ row: number; start: number; end: number; caption: string }> = [];
  await page.addInitScript(() => {
    const install = () => {
      const overlay = document.createElement("div");
      overlay.id = "video-caption";
      overlay.style.cssText = [
        "position:fixed;z-index:2147483647;pointer-events:none",
        "color:white;font:500 32px/1.4 Inter,Arial,sans-serif;text-align:center",
        "white-space:pre-line;box-sizing:border-box",
      ].join(";");
      document.body.appendChild(overlay);
    };
    if (document.body) install();
    else document.addEventListener("DOMContentLoaded", install, { once: true });
  });
  async function caption(row: number, text: string, seconds: number, title = false) {
    await page.evaluate(({ text, title }) => {
      const element = document.getElementById("video-caption")!;
      Object.assign(element.style, title ? {
        inset: "0", width: "100%", height: "100%", padding: "0 100px",
        display: "flex", alignItems: "center", justifyContent: "center",
        background: "#101c30", fontSize: "54px", borderRadius: "0",
      } : {
        inset: "auto 90px 20px", width: "auto", height: "112px", padding: "10px 30px",
        display: "flex", alignItems: "center", justifyContent: "center",
        background: "rgba(10,20,36,.94)", fontSize: "32px", borderRadius: "12px",
      });
      element.textContent = text;
    }, { text, title });
    const start = (Date.now() - started) / 1000;
    await page.waitForTimeout(seconds * 1000);
    timings.push({ row, start, end: (Date.now() - started) / 1000, caption: text });
  }
  async function clear() {
    await page.evaluate(() => { document.getElementById("video-caption")!.textContent = "";
      document.getElementById("video-caption")!.style.background = "transparent"; });
  }
  async function key(value: string, url: RegExp) {
    await clear();
    await page.keyboard.press(value);
    await expect(page).toHaveURL(url);
    await expect(page.getByTestId("lane")).toBeVisible();
  }
  await page.goto("/demo/");
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  await expect(page.getByText("● MOCK", { exact: true })).toBeVisible();
  await caption(1, "Jev × FHIR\nA decision layer for FHIR data", 7, true);
  await caption(2, "FHIR conformance asks: is this resource valid?\n" +
    "This project asks: what should we do with it?", 6, true);
  await caption(3, "FHIR is flattened into typed state. Jev returns a decision and a confidence," +
    "\nnot generated text.", 9);
  await key("1", /quality.*complete_patient/);
  await expect(page.getByTestId("quality-action")).toContainText("auto_accept");
  await caption(4, "A complete Patient is scored and auto-accepted. " +
    "This panel shows exactly what Jev sees.", 7);
  await key("ArrowRight", /quality.*invalid_nik/);
  await expect(page.getByTestId("quality-action")).toContainText("review_needed");
  await caption(5, "Also valid FHIR. But the NIK has 15 digits, not 16, " +
    "so it goes to human review.", 8);
  await key("ArrowRight", /quality.*nik_dotted/);
  await page.waitForTimeout(700);
  await key("ArrowRight", /quality.*minimal_patient/);
  await page.waitForTimeout(700);
  await key("ArrowRight", /quality.*quality_threshold=85/);
  await expect(page.getByTestId("quality-action")).toContainText("review_needed");
  await caption(6, "The threshold is the control: raise it, and more records go to a person.", 4);
  await key("2", /router.*lab_bundle/);
  await expect(page.getByRole("heading", { name: "Router decision" })).toBeVisible();
  await caption(7, "Which pipeline should get this Bundle? " +
    "Routing shows probabilities, not only a category.", 6);
  await key("ArrowRight", /router.*immunization_bundle/);
  await key("ArrowRight", /router.*mixed_bundle/);
  await key("ArrowRight", /router.*route_confidence_minimum=0.99/);
  await expect(page.getByText("overridden: confidence 0.92 < 0.99")).toBeVisible();
  await caption(8, "Below the confidence floor, the answer is unknown, and a person decides.", 7);
  await key("3", /notifiable.*japanese_encephalitis_a83/);
  await page.getByRole("button", { name: "Flag", exact: true }).click();
  await caption(9, "A notifiable disease produces a FHIR Flag " +
    "for the health office and an AuditEvent.", 8);
  await key("ArrowRight", /notifiable.*common_cold/);
  await key("ArrowRight", /notifiable.*dbd_text_only/);
  await expect(page.locator(".noul-answer")).toContainText("not_notifiable");
  await caption(10, "The mock can't read free text, so it misses this. " +
    "After a fix, the live model catches it.", 7);
  await clear();
  await page.keyboard.press("4");
  await expect(page.getByTestId("run-status")).toContainText(/running|finished/);
  await expect(page.getByTestId("lane-count-auto_accepted")).not.toHaveText("0");
  await caption(11, "In a stream, each resource lands in a lane: " +
    "auto_accepted, routed, flagged, or review.", 10);
  await clear();
  await page.keyboard.press("5");
  await page.getByLabel("Benchmark report").selectOption("bench_20261101T001036Z");
  await expect(page.locator(".report-details")).toContainText("LIVE");
  await expect(page.locator(".benchmark-card").first()).toContainText("65%");
  // Scroll within the existing viewport: retain the persistent MOCK header and both tables.
  await page.mouse.wheel(0, 1);
  await caption(12, "Live results on 204 synthetic fixtures. " +
    "Jev beats rules on quality and notifiable disease. Rules win routing.", 11);
  await caption(13, "Live latency misses the target: about 235–470 ms at p50 " +
    "against a 30 ms goal. Labels are still provisional.", 7);
  await caption(14, "A proof of concept on synthetic data.\n" +
    "Conformance first, decisions on top.", 6, true);
  await writeFile("test-results/video-timings.json", JSON.stringify(timings, null, 2));
  const video = page.video()!;
  await page.close();
  await video.saveAs("../docs/demo-video/jev-fhir-demo.webm");
});
