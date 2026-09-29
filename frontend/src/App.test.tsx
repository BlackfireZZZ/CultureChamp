import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { afterEach, expect, test, vi } from "vitest"

import { App } from "./App"
import * as demo from "./api/demo"

function renderApp() {
  render(<QueryClientProvider client={new QueryClient()}><App /></QueryClientProvider>)
}

afterEach(() => { cleanup(); vi.restoreAllMocks() })

test("each starter fills an editable composer without sending", () => {
  renderApp()
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
  renderApp()
  fireEvent.click(screen.getByRole("button", { name: "Что можно сделать?" }))
  expect(screen.getByRole("dialog", { name: "Что можно сделать?" })).toBeInTheDocument()
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: /UC-06/ }))
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Отправить" }))
  await waitFor(() => expect(screen.getByText("Демонстрационный ответ. Серверная генерация и проверенные ссылки пока не подключены.")).toBeInTheDocument())
  expect(screen.getByRole("status", { name: "" }).textContent).toContain("чаты не сохраняются")
})

test("materials show no unapproved candidates", async () => {
  renderApp()
  fireEvent.click(screen.getByRole("button", { name: "Материалы" }))
  expect(await screen.findByText("Одобренных материалов пока нет")).toBeInTheDocument()
  expect(screen.queryByText(/PDF-02/)).not.toBeInTheDocument()
})

test("a failed demo send keeps the editable brief", async () => {
  vi.spyOn(demo, "createDemoReply").mockRejectedValueOnce(new Error("provider secret must stay hidden"))
  renderApp()
  fireEvent.change(screen.getByRole("textbox", { name: "Ваш творческий бриф" }), { target: { value: "Мой бриф" } })
  fireEvent.click(screen.getByRole("button", { name: "Отправить" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("Текст сохранён")
  expect(screen.getByRole<HTMLTextAreaElement>("textbox", { name: "Ваш творческий бриф" }).value).toBe("Мой бриф")
  expect(screen.queryByText("provider secret must stay hidden")).not.toBeInTheDocument()
})
