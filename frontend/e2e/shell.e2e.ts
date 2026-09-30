import { expect, test } from "@playwright/test"

test("responsive persisted chat, starter keyboard path and theme", async ({ page }) => {
  let chat: { id: string; title: string; turns: unknown[] } | null = null
  await page.route("**/api/v1/chats**", (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    if (path === "/api/v1/chats" && request.method() === "GET") return route.fulfill({ json: chat ? [{ id: chat.id, title: chat.title, updated_at: "2026-09-30T00:00:00Z" }] : [] })
    if (path === "/api/v1/chats" && request.method() === "POST") {
      chat = { id: "chat-test", title: "Новый чат", turns: [] }
      return route.fulfill({ status: 201, json: { id: chat.id, title: chat.title, updated_at: "2026-09-30T00:00:00Z" } })
    }
    if (path === "/api/v1/chats/chat-test" && request.method() === "GET") return route.fulfill({ json: { ...chat, updated_at: "2026-09-30T00:00:00Z" } })
    if (path === "/api/v1/chats/chat-test/messages" && request.method() === "POST") {
      const body = request.postDataJSON() as { text: string; request_id: string }
      const turn = { request_id: body.request_id, ordinal: 0, user_text: body.text, assistant_text: "Нет одобренных источников для культурного утверждения.", evidence_status: "insufficient", status: "complete", citations: [] }
      chat!.turns.push(turn)
      chat!.title = body.text
      return route.fulfill({ json: turn })
    }
    return route.fulfill({ status: 404 })
  })
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
  await expect(page.getByText("Нет одобренных источников для культурного утверждения.")).toBeVisible()
  await page.getByRole("button", { name: "Материалы" }).click()
  await expect(page.getByText("Одобренных материалов пока нет")).toBeVisible()
  await page.getByRole("button", { name: "Тёмная тема" }).click()
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark")
  await page.reload()
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark")
})

test("login is keyboard accessible and does not show protected views before authentication", async ({ page }) => {
  await page.route("**/api/v1/chats", (route) => route.fulfill({ json: [] }))
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
  await page.route("**/api/v1/chats", (route) => route.fulfill({ json: [] }))
  const material = { revision_id: "00000000-0000-4000-8000-000000000002", title: "Одобренный источник", creator: "Автор", origin_url: "https://example.org/source.pdf", rights_usage_note: "Approved", media_type: "application/pdf", tags: [{ kind: "region", value: "Приморье" }] }
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

test("admin can filter inventory with keyboard without exposing it to user navigation", async ({ page }) => {
  const source = { revision_id: "00000000-0000-4000-8000-000000000004", source_id: "00000000-0000-4000-8000-000000000005", title: "Кандидат", origin_url: "https://example.org", status: "review_pending", decision: null }
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ json: { user: { id: "admin", username: "admin", role: "admin" }, csrf_token: "csrf" } }))
  await page.route("**/api/v1/admin/sources?*", (route) => {
    const url = new URL(route.request().url())
    return route.fulfill({ json: url.searchParams.get("status") === "failed" ? [] : [source] })
  })
  await page.goto("/")
  await page.getByRole("button", { name: "Админка" }).click()
  await expect(page.getByRole("button", { name: /Кандидат/ })).toBeVisible()
  const status = page.getByRole("combobox", { name: "Обработка" })
  await status.focus()
  await status.selectOption("failed")
  await expect(page.getByText("Ревизий не найдено")).toBeVisible()
  await page.setViewportSize({ width: 360, height: 800 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(360)
})
