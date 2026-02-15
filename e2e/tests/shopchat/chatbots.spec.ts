/**
 * ShopChat chatbot management e2e tests.
 */

import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin, createChatbotAPI } from "../service-helpers";

test.describe("ShopChat Chatbots", () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("shopchat");
    token = user.token;
    await serviceLogin(page, user.email, user.password);
  });

  test("shows empty state", async ({ page }) => {
    await page.goto("/chatbots");
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("heading", { name: /no chatbots yet/i })).toBeVisible({ timeout: 10000 });
  });

  test("displays chatbots from API", async ({ page }) => {
    await createChatbotAPI(token, { name: "Support Bot" });
    await page.goto("/chatbots");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/support bot/i)).toBeVisible({ timeout: 10000 });
  });
});
