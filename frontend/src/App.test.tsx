import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { afterEach, expect, test, vi } from "vitest"

import { App } from "./App"

function renderApp() {
  render(<QueryClientProvider client={new QueryClient()}><App /></QueryClientProvider>)
}

function mockSession(role: "user" | "admin" = "user", failSend = false) {
  let chat: { id: string; title: string; turns: unknown[] } | null = null
  vi.stubGlobal("fetch", vi.fn((input: string, options?: RequestInit) => {
    if (input === "/api/v1/auth/me") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ user: { id: "test-user", username: "tester", role }, csrf_token: "test-csrf" }) })
    if (input === "/api/v1/materials") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([]) })
    if (input === "/api/v1/chats" && !options?.method) return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(chat ? [{ id: chat.id, title: chat.title, updated_at: "2026-09-30T00:00:00Z" }] : []) })
    if (input === "/api/v1/chats" && options?.method === "POST") {
      chat = { id: "chat-1", title: "Новый чат", turns: [] }
      return Promise.resolve({ ok: true, status: 201, json: () => Promise.resolve({ id: chat!.id, title: chat!.title, updated_at: "2026-09-30T00:00:00Z" }) })
    }
    if (input === "/api/v1/chats/chat-1" && !options?.method) return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ ...chat, updated_at: "2026-09-30T00:00:00Z" }) })
    if (input === "/api/v1/chats/chat-1/messages" && options?.method === "POST") {
      if (failSend) return Promise.resolve({ ok: false, status: 503 })
      const payload = JSON.parse(options.body as string) as { text: string; request_id: string }
      const turn = { request_id: payload.request_id, ordinal: 0, user_text: payload.text, assistant_text: "Нет одобренных источников для культурного утверждения.", evidence_status: "insufficient", status: "complete", citations: [] }
      chat!.turns.push(turn)
      chat!.title = payload.text.slice(0, 38)
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(turn) })
    }
    throw new Error("Unexpected request")
  }))
}

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })

test("each starter fills an editable composer without sending", async () => {
  mockSession()
  renderApp()
  await screen.findByRole("heading", { name: "Идея с культурным контекстом" })
  for (let index = 1; index <= 6; index += 1) {
    const id = `UC-0${index}`
    fireEvent.click(screen.getByRole("button", { name: new RegExp(id) }))
    const composer = screen.getByRole<HTMLTextAreaElement>("textbox", { name: "Ваш творческий бриф" })
    expect(composer.value.length).toBeGreaterThan(20)
    fireEvent.change(composer, { target: { value: "Мой изменённый бриф" } })
    expect(composer.value).toBe("Мой изменённый бриф")
  }
  expect(screen.queryByText("Демонстрационный ответ. Серверная генерация и проверенные ссылки пока не подключены.")).not.toBeInTheDocument()
})

test("guide sends a persisted brief and shows an honest no-evidence answer", async () => {
  mockSession()
  renderApp()
  await screen.findByRole("heading", { name: "Идея с культурным контекстом" })
  fireEvent.click(screen.getByRole("button", { name: "Что можно сделать?" }))
  expect(screen.getByRole("dialog", { name: "Что можно сделать?" })).toBeInTheDocument()
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: /UC-06/ }))
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Отправить" }))
  await waitFor(() => expect(screen.getByText("Нет одобренных источников для культурного утверждения.")).toBeInTheDocument())
  expect(screen.getByRole("status", { name: "" }).textContent).toContain("Пилотный чат")
})

test("materials show no unapproved candidates", async () => {
  mockSession()
  renderApp()
  await screen.findByRole("heading", { name: "Идея с культурным контекстом" })
  fireEvent.click(screen.getByRole("button", { name: "Материалы" }))
  expect(await screen.findByText("Одобренных материалов пока нет")).toBeInTheDocument()
  expect(screen.queryByText(/PDF-02/)).not.toBeInTheDocument()
})

test("materials search uses approved-only server filters and can be reset", async () => {
  const material = { revision_id: "rev-filter", title: "Synthetic table", creator: "Author", origin_url: "https://example.invalid/table", rights_usage_note: "Self-authored", region: "Test region", people: null, period: null, media_type: "text/csv", tags: [{ kind: "region", value: "Test region" }] }
  const requests: string[] = []
  vi.stubGlobal("fetch", vi.fn((input: string) => {
    if (input === "/api/v1/auth/me") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ user: { id: "test-user", username: "tester", role: "user" }, csrf_token: "test-csrf" }) })
    if (input.startsWith("/api/v1/materials")) {
      requests.push(input)
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(input === "/api/v1/materials" ? [material] : []) })
    }
    throw new Error("Unexpected request")
  }))
  renderApp()
  fireEvent.click(await screen.findByRole("button", { name: "Материалы" }))
  expect(await screen.findByRole("button", { name: /Synthetic table/ })).toBeInTheDocument()
  const form = screen.getByRole("form", { name: "Поиск материалов" })
  fireEvent.change(within(form).getByRole("textbox", { name: "Регион" }), { target: { value: "Other" } })
  fireEvent.click(within(form).getByRole("button", { name: "Найти" }))
  expect(await screen.findByRole("heading", { name: "Материалов по запросу не найдено" })).toBeInTheDocument()
  expect(requests).toContain("/api/v1/materials?region=Other")
  fireEvent.click(within(form).getByRole("button", { name: "Сбросить" }))
  expect(await screen.findByRole("button", { name: /Synthetic table/ })).toBeInTheDocument()
})

test("approved material opens its exact revision and page", async () => {
  const material = { revision_id: "rev-2", title: "Источник Приморья", creator: "Автор", origin_url: "https://example.org/source.pdf", rights_usage_note: "Review approved", region: "Приморье", people: null, period: null, media_type: "application/pdf", tags: [{ kind: "region", value: "Приморье" }] }
  vi.stubGlobal("fetch", vi.fn((input: string) => {
    if (input === "/api/v1/auth/me") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ user: { id: "test-user", username: "tester", role: "user" }, csrf_token: "test-csrf" }) })
    if (input === "/api/v1/materials") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([material]) })
    if (input === "/api/v1/materials/rev-2") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ ...material, original_available: true, segments: [{ segment_id: "seg-1", locator: { kind: "page", page: 7 }, text: "Проверяемый фрагмент." }] }) })
    throw new Error("Unexpected request")
  }))
  renderApp()
  await screen.findByRole("heading", { name: "Идея с культурным контекстом" })
  fireEvent.click(screen.getByRole("button", { name: "Материалы" }))
  fireEvent.click(await screen.findByRole("button", { name: /Источник Приморья/ }))
  expect(await screen.findByText("Проверяемый фрагмент.")).toBeInTheDocument()
  expect(screen.getByRole("link", { name: "Открыть страницу 7 в источнике" })).toHaveAttribute("href", "/api/v1/materials/rev-2/original#page=7")
})

test("a chat citation opens the exact approved segment and returns to chat", async () => {
  const revisionId = "rev-cited"
  const segmentId = "segment-cited"
  const material = { revision_id: revisionId, title: "Учебный синтетический источник", creator: null, origin_url: "https://example.invalid/synthetic", rights_usage_note: "Synthetic", media_type: "application/pdf", tags: [] }
  vi.stubGlobal("fetch", vi.fn((input: string) => {
    if (input === "/api/v1/auth/me") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ user: { id: "test-user", username: "tester", role: "user" }, csrf_token: "test-csrf" }) })
    if (input === "/api/v1/chats") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([{ id: "chat-cited", title: "Синтетический бриф", updated_at: "2026-09-30T00:00:00Z" }]) })
    if (input === "/api/v1/chats/chat-cited") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ id: "chat-cited", title: "Синтетический бриф", updated_at: "2026-09-30T00:00:00Z", turns: [{ request_id: "turn-1", ordinal: 0, user_text: "Бриф", assistant_text: "Source-supported: Synthetic fact", evidence_status: "grounded", status: "complete", citations: [{ revision_id: revisionId, segment_id: segmentId, page: 7, section: null, sheet: null, table: null, row_start: null, row_end: null, column_start: null, column_end: null, available: true }] }] }) })
    if (input === "/api/v1/materials") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([material]) })
    if (input === `/api/v1/materials/${revisionId}`) return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ ...material, original_available: false, segments: [{ segment_id: segmentId, locator: { kind: "page", page: 7 }, text: "Точный синтетический фрагмент." }] }) })
    throw new Error("Unexpected request")
  }))
  renderApp()
  fireEvent.click(await screen.findByRole("button", { name: "Синтетический бриф" }))
  fireEvent.click(await screen.findByRole("button", { name: "Источник · страница 7" }))
  const excerpt = await screen.findByText("Точный синтетический фрагмент.")
  expect(excerpt.closest("li")).toHaveFocus()
  fireEvent.click(screen.getByRole("button", { name: "Вернуться к чату" }))
  expect(await screen.findByText("Source-supported: Synthetic fact")).toBeInTheDocument()
})

test("a material without original-file rights keeps the locator but offers no PDF link", async () => {
  const material = { revision_id: "rev-4", title: "Только текст", creator: null, origin_url: "https://example.org/source.pdf", rights_usage_note: "Text only", media_type: "application/pdf", tags: [] }
  vi.stubGlobal("fetch", vi.fn((input: string) => {
    if (input === "/api/v1/auth/me") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ user: { id: "test-user", username: "tester", role: "user" }, csrf_token: "test-csrf" }) })
    if (input === "/api/v1/materials") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([material]) })
    if (input === "/api/v1/materials/rev-4") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ ...material, original_available: false, segments: [{ segment_id: "seg-4", locator: { kind: "page", page: 4 }, text: "Одобренный текст." }] }) })
    throw new Error("Unexpected request")
  }))
  renderApp()
  fireEvent.click(await screen.findByRole("button", { name: "Материалы" }))
  fireEvent.click(await screen.findByRole("button", { name: /Только текст/ }))
  expect(await screen.findByText("Одобренный текст.")).toBeInTheDocument()
  expect(screen.getByText(/Оригинальный файл недоступен/)).toBeInTheDocument()
  expect(screen.queryByRole("link", { name: /Открыть страницу/ })).not.toBeInTheDocument()
})

test("a table cell keeps its sheet locator without inventing a PDF page", async () => {
  const material = { revision_id: "rev-table", title: "Synthetic table", creator: null, origin_url: "https://example.invalid/table", rights_usage_note: "Synthetic", media_type: "text/csv", tags: [] }
  vi.stubGlobal("fetch", vi.fn((input: string) => {
    if (input === "/api/v1/auth/me") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ user: { id: "test-user", username: "tester", role: "user" }, csrf_token: "test-csrf" }) })
    if (input === "/api/v1/materials") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([material]) })
    if (input === "/api/v1/materials/rev-table") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ ...material, original_available: true, segments: [{ segment_id: "cell-1", locator: { kind: "table", page: null, sheet: "Synthetic", table: null, row_start: 3, row_end: 3, column_start: 2, column_end: 2 }, text: "Row 3, column 2: seven" }] }) })
    throw new Error("Unexpected request")
  }))
  renderApp()
  fireEvent.click(await screen.findByRole("button", { name: "Материалы" }))
  fireEvent.click(await screen.findByRole("button", { name: /Synthetic table/ }))
  expect(await screen.findByRole("heading", { name: "Таблица Synthetic, строка 3, столбец 2" })).toBeInTheDocument()
  expect(screen.getByRole("link", { name: "Скачать исходную таблицу CSV" })).toHaveAttribute("href", "/api/v1/materials/rev-table/original")
  expect(screen.queryByRole("link", { name: /Открыть страницу/ })).not.toBeInTheDocument()
})

test("materials error can be retried without showing candidates", async () => {
  let attempts = 0
  vi.stubGlobal("fetch", vi.fn((input: string) => {
    if (input === "/api/v1/auth/me") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ user: { id: "test-user", username: "tester", role: "user" }, csrf_token: "test-csrf" }) })
    if (input === "/api/v1/materials") {
      attempts += 1
      if (attempts === 1) return Promise.resolve({ ok: false, status: 503 })
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([]) })
    }
    throw new Error("Unexpected request")
  }))
  renderApp()
  await screen.findByRole("heading", { name: "Идея с культурным контекстом" })
  fireEvent.click(screen.getByRole("button", { name: "Материалы" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("Не удалось загрузить материалы")
  fireEvent.click(within(screen.getByRole("alert")).getByRole("button", { name: "Повторить" }))
  expect(await screen.findByText("Одобренных материалов пока нет")).toBeInTheDocument()
  expect(attempts).toBe(2)
})

test("a failed API send keeps the editable brief", async () => {
  mockSession("user", true)
  renderApp()
  await screen.findByRole("heading", { name: "Идея с культурным контекстом" })
  fireEvent.change(screen.getByRole("textbox", { name: "Ваш творческий бриф" }), { target: { value: "Мой бриф" } })
  fireEvent.click(screen.getByRole("button", { name: "Отправить" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("Текст сохранён")
  expect(screen.getByRole<HTMLTextAreaElement>("textbox", { name: "Ваш творческий бриф" }).value).toBe("Мой бриф")
})

test("unauthenticated visitors see login and no protected navigation", async () => {
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: false, status: 401 })))
  renderApp()
  expect(await screen.findByRole("heading", { name: "Войти в мастерскую" })).toBeInTheDocument()
  expect(screen.queryByRole("button", { name: "Материалы" })).not.toBeInTheDocument()
})

test("session failure has a retry path and never reveals protected content", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: false, status: 503 })
    .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve({ user: { id: "test-user", username: "tester", role: "user" }, csrf_token: "test-csrf" }) })
    .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve([]) })
  vi.stubGlobal("fetch", fetchMock)
  renderApp()
  expect(await screen.findByRole("alert")).toHaveTextContent("Не удалось проверить сессию")
  expect(screen.queryByRole("button", { name: "Материалы" })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Повторить" }))
  expect(await screen.findByRole("heading", { name: "Идея с культурным контекстом" })).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledTimes(3)
})

test("admin navigation is visible only for an admin session", async () => {
  mockSession("admin")
  renderApp()
  expect(await screen.findByRole("button", { name: "Админка" })).toBeInTheDocument()
})

test("admin inventory and exact revision come from admin API", async () => {
  const source = { revision_id: "rev-3", source_id: "source-3", title: "Кандидат", origin_url: "https://example.org", status: "ready", decision: null }
  vi.stubGlobal("fetch", vi.fn((input: string) => {
    if (input === "/api/v1/auth/me") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ user: { id: "admin", username: "admin", role: "admin" }, csrf_token: "csrf" }) })
    if (input === "/api/v1/admin/sources?limit=100") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([source]) })
    if (input === "/api/v1/admin/sources?status=failed&decision=none&limit=100") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([]) })
    if (input.startsWith("/api/v1/admin/sources?")) return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([source]) })
    if (input === "/api/v1/admin/revisions/rev-3") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ ...source, sha256: "test-hash", creator: null, rights_usage_note: null, media_type: "application/pdf", tags: [{ kind: "region", value: "Приморье" }], segments: [] }) })
    throw new Error("Unexpected request")
  }))
  renderApp()
  fireEvent.click(await screen.findByRole("button", { name: "Админка" }))
  fireEvent.click(await screen.findByRole("button", { name: /Кандидат/ }))
  expect(await screen.findByText("test-hash")).toBeInTheDocument()
  expect(screen.getByText("Не подтверждены")).toBeInTheDocument()
  expect(screen.getByText("region: Приморье")).toBeInTheDocument()
  fireEvent.change(screen.getByRole("combobox", { name: "Обработка" }), { target: { value: "failed" } })
  fireEvent.change(screen.getByRole("combobox", { name: "Решение" }), { target: { value: "none" } })
  expect(await screen.findByText("Ревизий не найдено")).toBeInTheDocument()
})

test("admin review sends explicit rights scopes and can revoke the exact revision", async () => {
  const revisionId = "00000000-0000-4000-8000-000000000009"
  const source = { revision_id: revisionId, source_id: "source-9", title: "Синтетический кандидат", origin_url: "https://example.invalid/synthetic", status: "review_pending", decision: null }
  let decision: string | null = null
  const requests: { path: string; body: unknown; csrf: string | undefined }[] = []
  vi.stubGlobal("fetch", vi.fn((input: string, options?: RequestInit) => {
    if (input === "/api/v1/auth/me") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ user: { id: "admin", username: "admin", role: "admin" }, csrf_token: "review-csrf" }) })
    if (input === "/api/v1/admin/sources?limit=100") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([{ ...source, decision }]) })
    if (input === `/api/v1/admin/revisions/${revisionId}`) return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ ...source, decision, sha256: "hash", creator: null, rights_usage_note: null, media_type: "application/pdf", tags: [], segments: [], error_code: null }) })
    if (input.endsWith("/approve") || input.endsWith("/revoke")) {
      requests.push({ path: input, body: JSON.parse(options?.body as string) as unknown, csrf: (options?.headers as Record<string, string>)["x-csrf-token"] })
      decision = input.endsWith("/approve") ? "approve" : "revoke"
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ ...source, decision }) })
    }
    throw new Error("Unexpected request")
  }))
  renderApp()
  fireEvent.click(await screen.findByRole("button", { name: /Синтетический кандидат/ }))
  const approval = await screen.findByRole("form", { name: "Одобрение ревизии" })
  fireEvent.change(within(approval).getByRole("textbox", { name: "Основание и ограничения" }), { target: { value: "Self-authored synthetic fixture" } })
  fireEvent.change(within(approval).getByRole("textbox", { name: "HTTPS-ссылка на доказательство прав" }), { target: { value: "https://example.invalid/synthetic/rights" } })
  fireEvent.click(within(approval).getByRole("checkbox", { name: "Показ текстовых фрагментов пользователям разрешён" }))
  fireEvent.click(within(approval).getByRole("checkbox", { name: "Чувствительность материала проверена" }))
  fireEvent.click(within(approval).getByRole("button", { name: "Одобрить эту ревизию" }))
  await screen.findByRole("form", { name: "Отзыв ревизии" })
  expect(requests[0]).toEqual({ path: `/api/v1/admin/revisions/${revisionId}/approve`, csrf: "review-csrf", body: { reason: "Self-authored synthetic fixture", evidence_url: "https://example.invalid/synthetic/rights", user_text: true, original_file: false, provider_transfer: false, sensitivity_cleared: true } })
  const revocation = screen.getByRole("form", { name: "Отзыв ревизии" })
  fireEvent.change(within(revocation).getByRole("textbox", { name: "Причина отзыва" }), { target: { value: "Synthetic review withdrawn" } })
  fireEvent.click(within(revocation).getByRole("button", { name: "Отозвать эту ревизию" }))
  await waitFor(() => expect(requests).toHaveLength(2))
  expect(requests[1]).toEqual({ path: `/api/v1/admin/revisions/${revisionId}/revoke`, csrf: "review-csrf", body: { reason: "Synthetic review withdrawn" } })
})

test("logout sends CSRF and clears local chat before another login", async () => {
  const fetchMock = vi.fn((input: string, options?: RequestInit) => {
    if (input === "/api/v1/auth/me") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ user: { id: "first", username: "first", role: "user" }, csrf_token: "test-csrf" }) })
    if (input === "/api/v1/auth/logout") {
      expect(options?.headers).toEqual({ "x-csrf-token": "test-csrf" })
      expect(options?.credentials).toBe("same-origin")
      return Promise.resolve({ ok: true, status: 204 })
    }
    if (input === "/api/v1/auth/login") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ user: { id: "second", username: "second", role: "user" }, csrf_token: "other-csrf" }) })
    throw new Error("Unexpected request")
  })
  vi.stubGlobal("fetch", fetchMock)
  renderApp()
  await screen.findByRole("heading", { name: "Идея с культурным контекстом" })
  fireEvent.change(screen.getByRole("textbox", { name: "Ваш творческий бриф" }), { target: { value: "Локальный секретный черновик" } })
  fireEvent.click(screen.getByRole("button", { name: "Отправить" }))
  expect(await screen.findByText("Локальный секретный черновик")).toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Выйти" }))
  await screen.findByRole("heading", { name: "Войти в мастерскую" })
  fireEvent.change(screen.getByRole("textbox", { name: "Имя пользователя" }), { target: { value: "second" } })
  fireEvent.change(screen.getByLabelText("Пароль"), { target: { value: "password" } })
  fireEvent.click(screen.getByRole("button", { name: "Войти" }))
  await screen.findByRole("heading", { name: "Идея с культурным контекстом" })
  expect(screen.queryByText("Локальный секретный черновик")).not.toBeInTheDocument()
  expect(screen.getByRole<HTMLTextAreaElement>("textbox", { name: "Ваш творческий бриф" }).value).toBe("")
})
