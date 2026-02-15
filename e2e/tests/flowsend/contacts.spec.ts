import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin, createContactAPI } from "../service-helpers";

test.describe("FlowSend Contacts", () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("flowsend");
    token = user.token;
    await serviceLogin(page, user.email, user.password);
  });

  test("can add contact via dialog", async ({ page }) => {
    await page.goto("/contacts");
    await page.getByRole("button", { name: /add contact/i }).first().click();
    
    await page.fill("#contact-email", "test@example.com");
    await page.fill("#contact-first", "Test");
    await page.fill("#contact-last", "User");
    await page.getByRole("button", { name: /add/i }).last().click();
    
    await expect(page.getByText(/test@example\.com/i)).toBeVisible({ timeout: 10000 });
  });
});
