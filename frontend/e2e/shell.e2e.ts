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
    if (path === "/api/v1/chats/chat-test/messages/stream" && request.method() === "POST") {
      const body = request.postDataJSON() as { text: string; request_id: string }
      const turn = { request_id: body.request_id, ordinal: 0, user_text: body.text, assistant_text: "Нет одобренных источников для культурного утверждения.", evidence_status: "insufficient", status: "complete", citations: [], rating: null, feedback_comment: null }
      chat!.turns.push(turn)
      chat!.title = body.text
      return route.fulfill({ contentType: "text/event-stream", body: `event: delta\ndata: ${JSON.stringify({ text: turn.assistant_text })}\n\nevent: complete\ndata: ${JSON.stringify({ turn })}\n\n` })
    }
    if (path.endsWith("/feedback") && request.method() === "PUT") {
      const body = request.postDataJSON() as { rating: "up" | "down" | null; comment: string | null }
      chat!.turns[0] = { ...(chat!.turns[0] as object), rating: body.rating, feedback_comment: body.comment }
      return route.fulfill({ json: chat!.turns[0] })
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
  await expect(page.getByText(/^UC-0[1-6]$/)).toHaveCount(0)
  const composer = page.getByRole("textbox", { name: "Ваша задача" })
  const initialHeight = await composer.evaluate((input) => input.clientHeight)
  await composer.fill("Первая строка\nВторая строка\nТретья строка\nЧетвёртая строка")
  expect(await composer.evaluate((input) => input.clientHeight)).toBeGreaterThan(initialHeight)
  await expect(page.getByRole("region", { name: "Идеи для начала" })).toHaveCount(0)
  await composer.fill("")
  await page.getByRole("button", { name: "Идея подарка" }).focus()
  await page.keyboard.press("Enter")
  await expect(composer).toContainText("подарка")
  await expect(page.getByRole("region", { name: "Идеи для начала" })).toHaveCount(0)
  await composer.fill("Пробная задача")
  await page.keyboard.press("Enter")
  await expect(page.getByText("Нет одобренных источников для культурного утверждения.")).toBeVisible()
  await page.getByRole("button", { name: "Не нравится ответ" }).focus()
  await page.keyboard.press("Enter")
  await expect(page.getByRole("button", { name: "Не нравится ответ" })).toHaveAttribute("aria-pressed", "true")
  await page.getByRole("button", { name: "Комментарий" }).click()
  await page.getByRole("textbox", { name: "Что стоит улучшить или сохранить?" }).fill("Синтетический отзыв")
  await page.getByRole("button", { name: "Сохранить комментарий" }).click()
  await expect(page.getByText("Ваш комментарий: Синтетический отзыв")).toBeVisible()
  await page.getByRole("button", { name: "Материалы" }).click()
  await expect(page.getByText("Материалов пока нет")).toBeVisible()
  await page.getByRole("button", { name: "Тёмная тема" }).click()
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark")
  await page.reload()
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark")
  await page.getByRole("button", { name: "Чат", exact: true }).click()
  await page.getByRole("button", { name: "Чаты", exact: true }).last().click()
  await page.getByRole("complementary", { name: "Список чатов" }).getByRole("button", { name: "Пробная задача", exact: true }).click()
  await expect(page.getByRole("button", { name: "Не нравится ответ" })).toHaveAttribute("aria-pressed", "true")
})

test("chat rail resizes, persists its width, and reveals row actions when needed", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ json: { user: { id: "test-user", username: "tester", role: "user" }, csrf_token: "test-csrf" } }))
  await page.route("**/api/v1/chats", (route) => route.fulfill({ json: [{ id: "chat-test", title: "Тестовый чат", updated_at: "2026-10-02T12:00:00Z" }] }))
  await page.goto("/")
  const rail = page.getByRole("complementary", { name: "Список чатов" })
  const handle = page.getByRole("separator", { name: "Ширина панели чатов" })
  const row = rail.getByRole("listitem")
  const rename = row.getByRole("button", { name: "Переименовать чат «Тестовый чат»" })
  await expect(rename).toBeHidden()
  await row.hover()
  await expect(rename).toBeVisible()
  await page.mouse.move(700, 400)
  await expect(rename).toBeHidden()
  await row.getByRole("button", { name: "Тестовый чат", exact: true }).focus()
  await expect(rename).toBeVisible()

  const before = (await rail.boundingBox())!.width
  const grip = (await handle.boundingBox())!
  await page.mouse.move(grip.x + grip.width / 2, grip.y + 130)
  await page.mouse.down()
  await page.mouse.move(grip.x + grip.width / 2 + 95, grip.y + 130, { steps: 5 })
  await page.mouse.up()
  const resized = (await rail.boundingBox())!.width
  expect(resized).toBeGreaterThan(before + 80)
  await page.reload()
  await expect.poll(async () => (await rail.boundingBox())!.width).toBe(resized)
  await handle.focus()
  await page.keyboard.press("ArrowLeft")
  await expect.poll(async () => (await rail.boundingBox())!.width).toBe(resized - 24)
  await page.keyboard.press("Home")
  await expect(handle).toHaveAttribute("aria-valuenow", "220")
  await handle.dblclick()
  await expect(handle).toHaveAttribute("aria-valuenow", "250")
  await page.setViewportSize({ width: 768, height: 900 })
  await expect(handle).toBeHidden()
})

test("composer clears immediately after send and restores text on failure", async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ json: { user: { id: "test-user", username: "tester", role: "user" }, csrf_token: "test-csrf" } }))
  await page.route("**/api/v1/chats**", async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === "/api/v1/chats" && route.request().method() === "GET") return route.fulfill({ json: [] })
    if (path === "/api/v1/chats" && route.request().method() === "POST") return route.fulfill({ status: 201, json: { id: "chat-test", title: "Новый чат", updated_at: "2026-10-02T12:00:00Z" } })
    if (path === "/api/v1/chats/chat-test" && route.request().method() === "GET") return route.fulfill({ json: { id: "chat-test", title: "Новый чат", updated_at: "2026-10-02T12:00:00Z", turns: [] } })
    if (path.endsWith("/messages/stream")) {
      await new Promise((resolve) => setTimeout(resolve, 500))
      return route.fulfill({ status: 503, json: { detail: "Unavailable" } })
    }
    return route.fulfill({ status: 404 })
  })
  await page.goto("/")
  const composer = page.getByRole("textbox", { name: "Ваша задача" })
  await composer.fill("Пробная задача")
  await page.getByRole("button", { name: "Отправить" }).click()
  await expect(composer).toHaveValue("")
  await expect(composer).toHaveValue("Пробная задача", { timeout: 5_000 })
  await expect(page.getByRole("alert")).toContainText("Текст сохранён")
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
    const geometry = await page.evaluate(() => ({
      scrollRight: document.querySelector(".materials-page")!.getBoundingClientRect().right,
      signoutRight: document.querySelector(".site-header .signout")!.getBoundingClientRect().right,
      viewportRight: window.innerWidth,
    }))
    expect(geometry.scrollRight).toBeCloseTo(geometry.viewportRight, 0)
    expect(geometry.signoutRight).toBeLessThanOrEqual(geometry.viewportRight)
  }
})

test("admin can filter inventory with keyboard without exposing it to user navigation", async ({ page }) => {
  const source = { revision_id: "00000000-0000-4000-8000-000000000004", source_id: "00000000-0000-4000-8000-000000000005", title: "Кандидат", origin_url: "https://example.org", status: "review_pending", decision: null }
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ json: { user: { id: "admin", username: "admin", role: "admin" }, csrf_token: "csrf" } }))
  await page.route("**/api/v1/admin/sources?*", (route) => {
    const url = new URL(route.request().url())
    return route.fulfill({ json: url.searchParams.get("status") === "failed" ? [] : [source] })
  })
  await page.route("**/api/v1/admin/revisions/00000000-0000-4000-8000-000000000004", (route) => route.fulfill({ json: {
    ...source, creator: "Self-authored fixture", media_type: "text/csv", description: "Synthetic review data",
    rights_usage_note: null, tags: [], segments: [], sha256: "synthetic-hash", error_code: null,
    original_available: false,
  } }))
  await page.route("**/api/v1/admin/revisions/00000000-0000-4000-8000-000000000004/metadata-history", (route) => route.fulfill({ json: [] }))
  await page.goto("/")
  await page.getByRole("button", { name: "Админка" }).click()
  const candidate = page.getByRole("button", { name: /Кандидат/ })
  await candidate.focus()
  await page.keyboard.press("Enter")
  await expect(page.getByRole("link", { name: "Открыть оригинал для проверки" })).toHaveAttribute("href", "/api/v1/admin/revisions/00000000-0000-4000-8000-000000000004/original")
  await expect(page.getByText("Self-authored fixture")).toBeVisible()
  const inventorySearch = page.getByRole("form", { name: "Поиск в инвентаре" })
  await inventorySearch.getByRole("textbox", { name: "Источник или название" }).fill("Кандидат")
  await inventorySearch.getByRole("combobox", { name: "Формат" }).selectOption("text/csv")
  await inventorySearch.getByRole("combobox", { name: "Тип метки" }).selectOption("region")
  await inventorySearch.getByRole("textbox", { name: "Значение метки" }).fill("Тест")
  const filteredRequest = page.waitForRequest((request) => request.url().includes("/api/v1/admin/sources?") && new URL(request.url()).searchParams.get("tag_value") === "Тест")
  await inventorySearch.getByRole("textbox", { name: "Значение метки" }).press("Enter")
  const query = new URL((await filteredRequest).url()).searchParams
  expect([query.get("q"), query.get("media_type"), query.get("tag_kind")]).toEqual(["Кандидат", "text/csv", "region"])
  await inventorySearch.getByRole("button", { name: "Сбросить" }).click()
  const status = page.getByRole("combobox", { name: "Обработка" })
  await status.focus()
  await status.selectOption("failed")
  await expect(page.getByText("Материалы не найдены")).toBeVisible()
  await page.setViewportSize({ width: 360, height: 800 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(360)
})

test("admin statistics show only aggregate API values and recover from an error", async ({ page }) => {
  let requests = 0
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ json: { user: { id: "admin", username: "admin", role: "admin" }, csrf_token: "csrf" } }))
  await page.route("**/api/v1/admin/sources?*", (route) => route.fulfill({ json: [] }))
  await page.route("**/api/v1/admin/request-statistics?*", (route) => {
    requests += 1
    return requests === 1 ? route.fulfill({ status: 503 }) : route.fulfill({ json: {
      period_start: "2026-10-01", period_end: "2026-10-02",
      daily_requests: [{ date: "2026-10-02", count: 7 }],
      starter_requests: [{ starter_id: "UC-01", count: 3 }],
      rated_up: 2, rated_down: 1,
      feedback: [{ request_id: "synthetic-turn", rated_at: "2026-10-02T12:00:00Z", rating: "down", comment: "Synthetic feedback", evidence_status: "grounded", starter_id: "UC-01" }],
    } })
  })
  await page.goto("/")
  await page.getByRole("button", { name: "Статистика" }).click()
  await expect(page.getByRole("heading", { name: "Не удалось загрузить статистику" })).toBeVisible()
  await page.getByRole("button", { name: "Повторить" }).click()
  await expect(page.getByRole("heading", { name: "Запросы по дням" })).toBeVisible()
  await expect(page.getByRole("listitem").filter({ hasText: "2026-10-02" })).toContainText("7")
  await expect(page.locator(".statistics-list").getByRole("listitem").filter({ hasText: "Идея подарка" })).toContainText("3")
  await expect(page.getByText("UC-01")).toHaveCount(0)
  await expect(page.getByText("prompt text secret")).toHaveCount(0)
  await expect(page.getByRole("heading", { name: "Оценки ответов" })).toBeVisible()
  await expect(page.getByText("Synthetic feedback")).toBeVisible()
  await page.getByRole("combobox", { name: "Показать" }).selectOption("up")
  await expect(page.getByText("Synthetic feedback")).toHaveCount(0)
  const periodRequest = page.waitForRequest((request) => request.url().includes("/api/v1/admin/request-statistics?days=7"))
  await page.getByRole("combobox", { name: "Период" }).selectOption("7")
  await periodRequest
})
