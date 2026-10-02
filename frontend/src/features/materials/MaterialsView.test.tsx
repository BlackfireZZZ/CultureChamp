import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, expect, test, vi } from "vitest"

import type { ChatCitation } from "../../api/chats"
import { MaterialsView } from "./MaterialsView"

const revisionId = "rev-reading"
const citation = (segmentId: string): ChatCitation => ({
  revision_id: revisionId, segment_id: segmentId, page: null, section: null, sheet: null,
  table: null, row_start: null, row_end: null, column_start: null, column_end: null, available: true,
})

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView })

test("reads the whole source, highlights chat evidence, and smoothly scrolls between relevant passages", async () => {
  const scroll = vi.fn()
  Object.defineProperty(Element.prototype, "scrollIntoView", { configurable: true, value: scroll })
  const source = { revision_id: revisionId, title: "Костюм", creator: "Музей", origin_url: "https://example.org/source", rights_usage_note: "Approved", media_type: "text/plain", tags: [] }
  vi.stubGlobal("fetch", vi.fn((input: string) => {
    if (input === "/api/v1/materials") return Promise.resolve({ ok: true, json: () => Promise.resolve([source, { ...source, revision_id: "rev-other", title: "Другой источник" }]) })
    if (input === `/api/v1/materials/${revisionId}`) return Promise.resolve({ ok: true, json: () => Promise.resolve({ ...source, original_available: true, segments: [
      { segment_id: "one", locator: { kind: "section", page: null, section: "Line 1" }, text: "Первый абзац." },
      { segment_id: "middle", locator: { kind: "section", page: null, section: "Line 2" }, text: "Контекст между упоминаниями." },
      { segment_id: "three", locator: { kind: "section", page: null, section: "Line 3" }, text: "Третий абзац." },
    ] }) })
    throw new Error(`Unexpected request: ${input}`)
  }))
  render(<QueryClientProvider client={new QueryClient()}><MaterialsView onBack={vi.fn()} citationTarget={citation("one")} citations={[citation("one"), citation("three")]} /></QueryClientProvider>)
  expect(await screen.findByText("Контекст между упоминаниями.")).toBeInTheDocument()
  expect(screen.queryByRole("button", { name: /Другой источник/ })).not.toBeInTheDocument()
  expect(screen.getAllByRole("mark")).toHaveLength(2)
  expect(screen.queryByText("Line 1")).not.toBeInTheDocument()
  await waitFor(() => expect(document.getElementById("segment-one")).toHaveFocus())
  fireEvent.click(screen.getByRole("button", { name: "Следующее отмеченное место" }))
  expect(document.getElementById("segment-three")).toHaveFocus()
  expect(screen.getByText(/2 из 2/)).toBeInTheDocument()
  expect(scroll).toHaveBeenLastCalledWith({ behavior: "smooth", block: "center" })
  fireEvent.click(screen.getByRole("button", { name: "Предыдущее отмеченное место" }))
  expect(document.getElementById("segment-one")).toHaveFocus()
})
