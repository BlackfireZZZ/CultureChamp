import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { afterEach, expect, test, vi } from "vitest"

import { App } from "./App"
import * as demo from "./api/demo"

function renderApp() {
  render(<QueryClientProvider client={new QueryClient()}><App /></QueryClientProvider>)
}

function mockSession(role: "user" | "admin" = "user") {
  vi.stubGlobal("fetch", vi.fn((input: string) => {
    if (input === "/api/v1/auth/me") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ user: { id: "test-user", username: "tester", role }, csrf_token: "test-csrf" }) })
    if (input === "/api/v1/materials") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([]) })
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

test("guide is reachable before a chat; demo send is labelled and not persisted", async () => {
  mockSession()
  renderApp()
  await screen.findByRole("heading", { name: "Идея с культурным контекстом" })
  fireEvent.click(screen.getByRole("button", { name: "Что можно сделать?" }))
  expect(screen.getByRole("dialog", { name: "Что можно сделать?" })).toBeInTheDocument()
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: /UC-06/ }))
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Отправить" }))
  await waitFor(() => expect(screen.getByText("Демонстрационный ответ. Серверная генерация и проверенные ссылки пока не подключены.")).toBeInTheDocument())
  expect(screen.getByRole("status", { name: "" }).textContent).toContain("чаты не сохраняются")
})

test("materials show no unapproved candidates", async () => {
  mockSession()
  renderApp()
  await screen.findByRole("heading", { name: "Идея с культурным контекстом" })
  fireEvent.click(screen.getByRole("button", { name: "Материалы" }))
  expect(await screen.findByText("Одобренных материалов пока нет")).toBeInTheDocument()
  expect(screen.queryByText(/PDF-02/)).not.toBeInTheDocument()
})

test("approved material opens its exact revision and page", async () => {
  const material = { revision_id: "rev-2", title: "Источник Приморья", creator: "Автор", origin_url: "https://example.org/source.pdf", rights_usage_note: "Review approved", region: null, people: null, period: null, media_type: "application/pdf" }
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

test("a material without original-file rights keeps the locator but offers no PDF link", async () => {
  const material = { revision_id: "rev-4", title: "Только текст", creator: null, origin_url: "https://example.org/source.pdf", rights_usage_note: "Text only", media_type: "application/pdf" }
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

test("a failed demo send keeps the editable brief", async () => {
  mockSession()
  vi.spyOn(demo, "createDemoReply").mockRejectedValueOnce(new Error("provider secret must stay hidden"))
  renderApp()
  await screen.findByRole("heading", { name: "Идея с культурным контекстом" })
  fireEvent.change(screen.getByRole("textbox", { name: "Ваш творческий бриф" }), { target: { value: "Мой бриф" } })
  fireEvent.click(screen.getByRole("button", { name: "Отправить" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("Текст сохранён")
  expect(screen.getByRole<HTMLTextAreaElement>("textbox", { name: "Ваш творческий бриф" }).value).toBe("Мой бриф")
  expect(screen.queryByText("provider secret must stay hidden")).not.toBeInTheDocument()
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
  vi.stubGlobal("fetch", fetchMock)
  renderApp()
  expect(await screen.findByRole("alert")).toHaveTextContent("Не удалось проверить сессию")
  expect(screen.queryByRole("button", { name: "Материалы" })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Повторить" }))
  expect(await screen.findByRole("heading", { name: "Идея с культурным контекстом" })).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledTimes(2)
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
    if (input === "/api/v1/admin/sources") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([source]) })
    if (input === "/api/v1/admin/revisions/rev-3") return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ ...source, sha256: "test-hash", creator: null, rights_usage_note: null, media_type: "application/pdf", tags: [{ kind: "region", value: "Приморье" }], segments: [] }) })
    throw new Error("Unexpected request")
  }))
  renderApp()
  fireEvent.click(await screen.findByRole("button", { name: "Админка" }))
  fireEvent.click(await screen.findByRole("button", { name: /Кандидат/ }))
  expect(await screen.findByText("test-hash")).toBeInTheDocument()
  expect(screen.getByText("Не подтверждены")).toBeInTheDocument()
  expect(screen.getByText("region: Приморье")).toBeInTheDocument()
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
