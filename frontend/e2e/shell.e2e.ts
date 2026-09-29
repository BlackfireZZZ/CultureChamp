import { expect, test } from "@playwright/test"

test("responsive preview, starter keyboard path and theme", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" })
  await page.goto("/")
  await expect(page.getByRole("heading", { name: "Идея с культурным контекстом" })).toBeVisible()
  for (const width of [360, 768, 1280, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
  }
  await page.setViewportSize({ width: 360, height: 800 })
  await page.getByRole("button", { name: "Чаты", exact: true }).last().click()
  await expect(page.getByRole("button", { name: "Чаты", exact: true }).last()).toHaveAttribute("aria-expanded", "true")
  await page.keyboard.press("Escape")
  await expect(page.getByRole("button", { name: "Чаты", exact: true }).last()).toBeFocused()
  await page.getByRole("button", { name: /UC-01/ }).focus()
  await page.keyboard.press("Enter")
  await expect(page.getByRole("textbox", { name: "Ваш творческий бриф" })).toContainText("подарка")
  await page.getByRole("textbox", { name: "Ваш творческий бриф" }).fill("Пробный бриф")
  await page.keyboard.press("Enter")
  await expect(page.getByText("Демонстрационный ответ. Серверная генерация и проверенные ссылки пока не подключены.")).toBeVisible()
  await page.getByRole("button", { name: "Материалы" }).click()
  await expect(page.getByText("Одобренных материалов пока нет")).toBeVisible()
  await page.getByRole("button", { name: "Тёмная тема" }).click()
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark")
  await page.reload()
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark")
})
