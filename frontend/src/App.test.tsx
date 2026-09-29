import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { afterEach, expect, test, vi } from "vitest"

import { App } from "./App"

afterEach(() => vi.unstubAllGlobals())

test("shows the API status", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve({ status: "alive" }),
  }))
  render(
    <QueryClientProvider client={new QueryClient()}>
      <App />
    </QueryClientProvider>,
  )
  expect(await screen.findByText("API работает")).toBeInTheDocument()
})
