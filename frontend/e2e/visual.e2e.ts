import { expect, test } from "@playwright/test"

const revisionId = "00000000-0000-4000-8000-000000000002"
const segmentId = "00000000-0000-4000-8000-000000000003"
const material = {
  revision_id: revisionId, title: "Синтетический проверочный источник", description: "Самостоятельно составленный тестовый материал.",
  creator: "Тестовый автор", origin_url: "https://example.invalid/source.pdf", rights_usage_note: "Синтетический тестовый материал",
  media_type: "application/pdf", tags: [{ kind: "region", value: "Тестовый регион" }],
}
const citation = { revision_id: revisionId, segment_id: segmentId, page: 2, section: null, sheet: null, table: null, row_start: null, row_end: null, column_start: null, column_end: null, available: true }

test("canonical user and admin screens in both themes", async ({ page }) => {
  let role: "user" | "admin" = "user"
  await page.clock.install({ time: new Date("2026-10-02T12:00:00Z") })
  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === "/api/v1/auth/me") return route.fulfill({ json: { user: { id: "visual-user", username: "tester", role }, csrf_token: "visual-csrf" } })
    if (path === "/api/v1/chats") return route.fulfill({ json: [{ id: "chat-visual", title: "Синтетический бриф", updated_at: "2026-10-02T12:00:00Z" }] })
    if (path === "/api/v1/chats/chat-visual") return route.fulfill({ json: { id: "chat-visual", title: "Синтетический бриф", updated_at: "2026-10-02T12:00:00Z", turns: [{ request_id: "turn-visual", ordinal: 0, user_text: "Создайте тестовый творческий бриф", assistant_text: "Source-supported: Тестовый фрагмент.\n\nInterpretation: Возможная тестовая трактовка.\n\nNew creative proposal: Новый синтетический вариант.", evidence_status: "grounded", status: "complete", citations: [citation] }] } })
    if (path === "/api/v1/materials") return route.fulfill({ json: [material] })
    if (path === `/api/v1/materials/${revisionId}`) return route.fulfill({ json: { ...material, original_available: true, segments: [{ segment_id: segmentId, locator: { kind: "page", page: 2 }, text: "Тестовый фрагмент." }] } })
    if (path === "/api/v1/admin/sources") return route.fulfill({ json: [{ revision_id: revisionId, source_id: "00000000-0000-4000-8000-000000000001", title: "Синтетический кандидат", origin_url: "https://example.invalid/source.pdf", status: "review_pending", decision: null }] })
    return route.fulfill({ status: 404 })
  })

  for (const theme of ["light", "dark"] as const) {
    for (const width of [360, 768, 1280, 1440]) {
      const key = `${theme}-${width}`
      await page.setViewportSize({ width, height: 900 })
      await page.addInitScript((selectedTheme) => localStorage.setItem("culturechamp-theme", selectedTheme), theme)
      role = "user"
      await page.goto("/")
      await page.evaluate(() => document.fonts.ready)
      await expect(page.getByRole("heading", { name: "Идея с культурным контекстом" })).toBeVisible()
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
      await expect(page).toHaveScreenshot(`chat-empty-${key}.png`, { animations: "disabled" })

      if (width === 360) await page.getByRole("button", { name: "Чаты", exact: true }).last().click()
      await page.getByRole("button", { name: "Синтетический бриф" }).click()
      await expect(page.getByRole("heading", { name: "Подтверждено источником" })).toBeVisible()
      await expect(page.getByRole("textbox", { name: "Ваш творческий бриф" })).toBeInViewport()
      await expect(page).toHaveScreenshot(`chat-answer-${key}.png`, { animations: "disabled" })

      await page.getByRole("button", { name: "Материалы" }).click()
      await page.getByRole("button", { name: /Синтетический проверочный источник/ }).click()
      await expect(page.getByRole("heading", { name: "Синтетический проверочный источник" })).toBeVisible()
      await expect(page).toHaveScreenshot(`materials-${key}.png`, { animations: "disabled" })

      role = "admin"
      await page.reload()
      await expect(page.getByRole("heading", { name: "Кандидаты и ревизии" })).toBeVisible()
      await expect(page.getByRole("button", { name: /Синтетический кандидат/ })).toBeVisible()
      await page.evaluate(() => window.scrollTo(0, 0))
      await expect(page).toHaveScreenshot(`admin-inventory-${key}.png`, { animations: "disabled" })
      await page.getByRole("button", { name: "Статистика" }).click()
      await expect(page.getByRole("heading", { name: "Статистика недоступна" })).toBeVisible()
      await expect(page).toHaveScreenshot(`admin-statistics-${key}.png`, { animations: "disabled" })
    }
  }
})
