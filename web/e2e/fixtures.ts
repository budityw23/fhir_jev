import { expect, test as base } from "@playwright/test";

type GuardFixtures = {
  requests: string[];
  blockedUrls: string[];
  networkGuard: void;
};

/** Shared test fixture that records and blocks every non-local network request. */
export const test = base.extend<GuardFixtures>({
  requests: [
    // Playwright requires a destructured fixture argument even when it is not needed.
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    async ({ page: _page }, use) => {
      await use([]);
    },
    { auto: true },
  ],
  blockedUrls: [
    // Playwright requires a destructured fixture argument even when it is not needed.
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    async ({ page: _page }, use) => {
      await use([]);
    },
    { auto: true },
  ],
  networkGuard: [
    async ({ page, requests, blockedUrls }, use) => {
      await page.context().route("**/*", async (route) => {
        const url = new URL(route.request().url());
        requests.push(url.href);
        if (url.hostname !== "127.0.0.1" && url.hostname !== "localhost") {
          blockedUrls.push(url.href);
          await route.abort();
          return;
        }
        await route.continue();
      });

      await use();

      if (blockedUrls.length > 0) {
        throw new Error(`Network guard blocked: ${blockedUrls.join(", ")}`);
      }
    },
    { auto: true },
  ],
});

export { expect };
