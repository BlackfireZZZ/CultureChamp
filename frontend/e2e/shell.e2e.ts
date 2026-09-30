import { expect, test } from "@playwright/test"

test("responsive preview, starter keyboard path and theme", async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ json: { user: { id: "test-user", username: "tester", role: "user" }, csrf_token: "test-csrf" } }))
  await page.route("**/api/v1/materials", (route) => route.fulfill({ json: [] }))
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

test("login is keyboard accessible and does not show protected views before authentication", async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 401 }))
  await page.route("**/api/v1/auth/login", (route) => route.fulfill({ json: { user: { id: "test-user", username: "tester", role: "user" }, csrf_token: "test-csrf" } }))
  await page.goto("/")
  await expect(page.getByRole("heading", { name: "Войти в мастерскую" })).toBeVisible()
  await expect(page.getByRole("button", { name: "Материалы" })).toHaveCount(0)
  await page.getByRole("textbox", { name: "Имя пользователя" }).fill("tester")
  await page.getByLabel("Пароль").fill("example")
  await page.getByLabel("Пароль").press("Enter")
  await expect(page.getByRole("heading", { name: "Идея с культурным контекстом" })).toBeVisible()
  await expect(page.getByRole("button", { name: "Админка" })).toHaveCount(0)
})

test("material selection exposes a precise page with keyboard focus at narrow and wide widths", async ({ page }) => {
  const material = { revision_id: "00000000-0000-4000-8000-000000000002", title: "Одобренный источник", creator: "Автор", origin_url: "https://example.org/source.pdf", rights_usage_note: "Approved", media_type: "application/pdf" }
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ json: { user: { id: "test-user", username: "tester", role: "user" }, csrf_token: "test-csrf" } }))
  await page.route("**/api/v1/materials", (route) => route.fulfill({ json: [material] }))
  await page.route("**/api/v1/materials/*", (route) => route.fulfill({ json: { ...material, original_available: true, segments: [{ segment_id: "00000000-0000-4000-8000-000000000003", locator: { kind: "page", page: 7 }, text: "Точный текст страницы." }] } }))
  await page.goto("/")
  await page.getByRole("button", { name: "Материалы" }).click()
  const select = page.getByRole("button", { name: /Одобренный источник/ })
  await select.focus()
  await page.keyboard.press("Enter")
  await expect(page.getByRole("heading", { name: "Одобренный источник" })).toBeFocused()
  await expect(page.getByRole("link", { name: "Открыть страницу 7 в источнике" })).toHaveAttribute("href", "/api/v1/materials/00000000-0000-4000-8000-000000000002/original#page=7")
  for (const width of [360, 768, 1280, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
  }
})
