import { cleanup, fireEvent, render, screen, within } from "@testing-library/react"
import { afterEach, expect, test, vi } from "vitest"

import type { ChatDetail, ChatSummary } from "../../api/chats"
import { ChatDialogue } from "./ChatDialogue"

const summary = { id: "chat-test", title: "Synthetic task", updated_at: "2026-10-02T00:00:00Z" } as ChatSummary
const detail = { ...summary, turns: [{ request_id: "turn-test", ordinal: 0, user_text: "Test task", assistant_text: "Source-supported: Synthetic excerpt.\n\nInterpretation: A possible reading.\n\nNew creative proposal: An original draft.", evidence_status: "grounded", status: "complete", citations: [] }] } as ChatDetail

afterEach(cleanup)

test("separates source support, interpretation, and new work", () => {
  render(<ChatDialogue summary={summary} detail={detail} pending={false} error={false} onRetry={vi.fn()} onCitation={vi.fn()} onDelete={vi.fn()} deleting={false} />)
  for (const title of ["Подтверждено источником", "Интерпретация", "Новая творческая идея"]) expect(screen.getByRole("heading", { name: title })).toBeInTheDocument()
  expect(screen.getByText("Synthetic excerpt.")).toBeInTheDocument()
})

test("image request shows a copyable prompt and optional external example", () => {
  const imageDetail = { ...detail, turns: [{ ...detail.turns[0], user_text: "Сгенерируй фото", assistant_text: "Source-supported: Synthetic blue lid.\n\nInterpretation: Contemporary studio setting.\n\nImage prompt: Фотореалистичная предметная фотография коробки с синей крышкой, мягкий боковой свет." }] } as ChatDetail
  render(<ChatDialogue summary={summary} detail={imageDetail} pending={false} error={false} onRetry={vi.fn()} onCitation={vi.fn()} onDelete={vi.fn()} deleting={false} />)
  expect(screen.getByRole("heading", { name: "Промпт для изображения" })).toBeInTheDocument()
  expect(screen.getByText(/Фотореалистичная предметная фотография/)).toBeInTheDocument()
  expect(screen.getByRole("link", { name: "GigaChat" })).toHaveAttribute("href", "https://giga.chat/")
  expect(screen.getByRole("link", { name: "GigaChat" })).toHaveAttribute("rel", "noopener noreferrer")
})

test("requires explicit deletion and restores focus after cancellation", () => {
  const onDelete = vi.fn()
  render(<ChatDialogue summary={summary} detail={detail} pending={false} error={false} onRetry={vi.fn()} onCitation={vi.fn()} onDelete={onDelete} deleting={false} />)
  const trigger = screen.getByRole("button", { name: "Удалить чат" })
  fireEvent.click(trigger)
  const confirmation = screen.getByRole("group", { name: "Подтверждение удаления чата" })
  expect(within(confirmation).getByRole("button", { name: "Отмена" })).toHaveFocus()
  fireEvent.keyDown(confirmation, { key: "Escape" })
  expect(trigger).toHaveFocus()
  expect(onDelete).not.toHaveBeenCalled()
  fireEvent.click(trigger)
  fireEvent.click(within(screen.getByRole("group", { name: "Подтверждение удаления чата" })).getByRole("button", { name: "Подтвердить удаление" }))
  expect(onDelete).toHaveBeenCalledOnce()
})
