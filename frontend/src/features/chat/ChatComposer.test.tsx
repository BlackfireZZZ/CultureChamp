import { createRef, useState } from "react"
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, expect, test, vi } from "vitest"

import { ChatComposer } from "./ChatComposer"

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

test("voice input appends final Russian speech and can be stopped", () => {
  const recognitions: Array<{
    lang: string; continuous: boolean; interimResults: boolean
    onresult: ((event: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void) | null
    onend: (() => void) | null
    start: ReturnType<typeof vi.fn>; stop: ReturnType<typeof vi.fn>; abort: ReturnType<typeof vi.fn>
  }> = []
  class Recognition {
    lang = ""
    continuous = false
    interimResults = false
    onresult = null
    onerror = null
    onend = null
    start = vi.fn()
    stop = vi.fn()
    abort = vi.fn()
    constructor() { recognitions.push(this) }
  }
  vi.stubGlobal("SpeechRecognition", Recognition)

  function Harness() {
    const [value, setValue] = useState("Создай")
    return <ChatComposer value={value} onChange={setValue} onSubmit={(event) => event.preventDefault()} pending={false} error={false} placeholder="Задача" inputRef={createRef()} onKeyDown={() => {}} />
  }
  render(<Harness />)
  fireEvent.click(screen.getByRole("button", { name: "Голосовой ввод" }))
  const recognition = recognitions[0]
  expect(recognition.lang).toBe("ru-RU")
  expect(recognition.start).toHaveBeenCalledOnce()
  act(() => recognition.onresult?.({ resultIndex: 0, results: [{ isFinal: true, 0: { transcript: "плакат о костюме" } }] }))
  expect(screen.getByRole("textbox", { name: "Ваша задача" })).toHaveValue("Создай плакат о костюме")
  fireEvent.click(screen.getByRole("button", { name: "Остановить голосовой ввод" }))
  expect(recognition.stop).toHaveBeenCalledOnce()
  act(() => recognition.onend?.())
  expect(screen.getByRole("button", { name: "Голосовой ввод" })).toBeInTheDocument()
})
