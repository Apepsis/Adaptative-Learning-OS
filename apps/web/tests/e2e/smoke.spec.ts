import { expect, test } from "@playwright/test";

// Requires the full stack running (`make dev`): web, api, and its
// dependencies. Deeper flows (upload -> status transition) belong here once
// Phase 2 gives sources something real to transition through.

test("home page loads and links to the library", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await page.getByRole("link", { name: "Library" }).first().click();
  await expect(page).toHaveURL(/\/library$/);
});
