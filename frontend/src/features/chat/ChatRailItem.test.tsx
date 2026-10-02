import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { afterEach, expect, test, vi } from "vitest"
import type { ChatSummary } from "../../api/chats"
import { ChatRailItem } from "./ChatRailItem"

afterEach(cleanup)

const chat = { id: "chat-test", title: "Русский костюм", updated_at: "2026-10-02T00:00:00Z" } as ChatSummary

test("chat actions sit beside their history item and rename it", async () => {
  const onRename = vi.fn().mockResolvedValue(undefined)
  render(<ul><ChatRailItem chat={chat} active onSelect={vi.fn()} onRename={onRename} onDelete={vi.fn()} renaming={false} deleting={false} /></ul>)
  const row = screen.getByRole("listitem")
  expect(within(row).getByRole("button", { name: chat.title })).toHaveAttribute("aria-current", "page")
  const trigger = within(row).getByRole("button", { name: `Переименовать чат «${chat.title}»` })
  fireEvent.click(trigger)
  const input = within(row).getByRole("textbox", { name: "Название чата" })
  expect(input).toHaveFocus()
  fireEvent.change(input, { target: { value: "  Новый заголовок  " } })
  fireEvent.click(within(row).getByRole("button", { name: "Сохранить" }))
  await waitFor(() => expect(onRename).toHaveBeenCalledWith("Новый заголовок"))
})

test("deletion requires confirmation and Escape returns focus", async () => {
  const onDelete = vi.fn().mockResolvedValue(undefined)
  render(<ul><ChatRailItem chat={chat} active={false} onSelect={vi.fn()} onRename={vi.fn()} onDelete={onDelete} renaming={false} deleting={false} /></ul>)
  const trigger = screen.getByRole("button", { name: `Удалить чат «${chat.title}»` })
  fireEvent.click(trigger)
  const confirm = screen.getByRole("group", { name: `Подтверждение удаления чата «${chat.title}»` })
  expect(within(confirm).getByRole("button", { name: "Отмена" })).toHaveFocus()
  fireEvent.keyDown(confirm, { key: "Escape" })
  await waitFor(() => expect(trigger).toHaveFocus())
  expect(onDelete).not.toHaveBeenCalled()
  fireEvent.click(trigger)
  fireEvent.click(within(screen.getByRole("group", { name: `Подтверждение удаления чата «${chat.title}»` })).getByRole("button", { name: "Удалить" }))
  await waitFor(() => expect(onDelete).toHaveBeenCalledOnce())
})
