import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, expect, test, vi } from "vitest"

import type { ChatDetail, ChatSummary } from "../../api/chats"
import { ChatDialogue } from "./ChatDialogue"

const summary = { id: "chat-test", title: "Synthetic task", updated_at: "2026-10-02T00:00:00Z" } as ChatSummary
const detail = { ...summary, turns: [{ request_id: "turn-test", ordinal: 0, user_text: "Test task", assistant_text: "Source-supported: Synthetic excerpt.\n\nInterpretation: A possible reading.\n\nNew creative proposal: An original draft.", evidence_status: "grounded", status: "complete", citations: [], rating: null, feedback_comment: null }] } as ChatDetail

afterEach(cleanup)

test("separates source support, interpretation, and new work", () => {
  render(<ChatDialogue summary={summary} detail={detail} pending={false} error={false} onRetry={vi.fn()} onCitation={vi.fn()} onRate={vi.fn()} />)
  for (const title of ["Подтверждено источником", "Интерпретация", "Новая творческая идея"]) expect(screen.getByRole("heading", { name: title })).toBeInTheDocument()
  expect(screen.getByText("Synthetic excerpt.")).toBeInTheDocument()
})

test("image request shows a copyable prompt and optional external example", () => {
  const imageDetail = { ...detail, turns: [{ ...detail.turns[0], user_text: "Сгенерируй фото", assistant_text: "Source-supported: Synthetic blue lid.\n\nInterpretation: Contemporary studio setting.\n\nImage prompt: Фотореалистичная предметная фотография коробки с синей крышкой, мягкий боковой свет." }] } as ChatDetail
  render(<ChatDialogue summary={summary} detail={imageDetail} pending={false} error={false} onRetry={vi.fn()} onCitation={vi.fn()} onRate={vi.fn()} />)
  expect(screen.getByRole("heading", { name: "Промпт для изображения" })).toBeInTheDocument()
  expect(screen.getByText(/Фотореалистичная предметная фотография/)).toBeInTheDocument()
  expect(screen.getByRole("link", { name: "GigaChat" })).toHaveAttribute("href", "https://giga.chat/")
  expect(screen.getByRole("link", { name: "GigaChat" })).toHaveAttribute("rel", "noopener noreferrer")
})

test("rates an answer, submits a comment, and can clear the rating", async () => {
  const onRate = vi.fn().mockResolvedValue(undefined)
  const props = { summary, pending: false, error: false, onRetry: vi.fn(), onCitation: vi.fn(), onRate }
  const view = render(<ChatDialogue {...props} detail={detail} />)
  fireEvent.click(screen.getByRole("button", { name: "Нравится ответ" }))
  await waitFor(() => expect(onRate).toHaveBeenCalledWith("turn-test", "up", null))
  const rated = { ...detail, turns: [{ ...detail.turns[0], rating: "up" as const, feedback_comment: null }] }
  view.rerender(<ChatDialogue {...props} detail={rated} />)
  expect(screen.getByRole("button", { name: "Нравится ответ" })).toHaveAttribute("aria-pressed", "true")
  fireEvent.click(screen.getByRole("button", { name: "Комментарий" }))
  fireEvent.change(screen.getByRole("textbox", { name: "Что стоит улучшить или сохранить?" }), { target: { value: "Helpful source" } })
  fireEvent.click(screen.getByRole("button", { name: "Сохранить комментарий" }))
  await waitFor(() => expect(onRate).toHaveBeenCalledWith("turn-test", "up", "Helpful source"))
  view.rerender(<ChatDialogue {...props} detail={{ ...rated, turns: [{ ...rated.turns[0], feedback_comment: "Helpful source" }] }} />)
  fireEvent.click(screen.getByRole("button", { name: "Не нравится ответ" }))
  await waitFor(() => expect(onRate).toHaveBeenCalledWith("turn-test", "down", null))
  view.rerender(<ChatDialogue {...props} detail={{ ...rated, turns: [{ ...rated.turns[0], rating: "down", feedback_comment: null }] }} />)
  fireEvent.click(screen.getByRole("button", { name: "Комментарий" }))
  expect(screen.getByRole("textbox", { name: "Что стоит улучшить или сохранить?" })).toHaveValue("")
  fireEvent.click(screen.getByRole("button", { name: "Не нравится ответ" }))
  await waitFor(() => expect(onRate).toHaveBeenCalledWith("turn-test", null, null))
})

test("shows incoming answer before the completed turn and its citations arrive", () => {
  render(<ChatDialogue summary={summary} detail={{ ...detail, turns: [] }} pending={false} error={false} onRetry={vi.fn()} onCitation={vi.fn()} onRate={vi.fn()} isGenerating streamingText="Начало ответа модели" />)
  expect(screen.getByRole("article", { name: "Ответ формируется" })).toHaveTextContent("Начало ответа модели")
})
