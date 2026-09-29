import { expect, test } from "@playwright/test"

test("shows the concept placeholder", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" })
  await page.route("**/api/v1/health/live", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: '{"status":"alive"}' }),
  )
  await page.goto("/")
  await expect(page.getByRole("heading", { name: "Новая концепция в работе" })).toBeVisible()
  await expect(page.getByRole("status")).toHaveText("API работает")
  for (const width of [360, 768, 1280, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
  }
  await page.getByRole("button", { name: "Тёмная тема" }).click()
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark")
  await page.reload()
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark")
})
