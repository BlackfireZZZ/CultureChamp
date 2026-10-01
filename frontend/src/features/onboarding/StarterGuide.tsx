import { useEffect, useRef } from "react"
import type { KeyboardEvent } from "react"

import { starters } from "./starters"

export function StarterGuide({ onChoose, onClose }: { onChoose: (prompt: string) => void; onClose: () => void }) {
  const panelRef = useRef<HTMLElement>(null)
  useEffect(() => { panelRef.current?.querySelector("button")?.focus() }, [])

  function handleKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === "Escape") { onClose(); return }
    if (event.key !== "Tab" || !panelRef.current) return
    const buttons = Array.from(panelRef.current.querySelectorAll("button"))
    const first = buttons[0]
    const last = buttons.at(-1)
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
    if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
  }

  return (
    <div className="guide-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <section ref={panelRef} aria-labelledby="guide-title" aria-modal="true" className="guide-panel" role="dialog" onKeyDown={handleKeyDown}>
        <div className="guide-heading"><h2 id="guide-title">Что можно сделать?</h2><button type="button" onClick={onClose} aria-label="Закрыть подсказки">✕</button></div>
        <p>Выберите задачу: текст появится в поле ввода, и его можно будет изменить. Примеры не подтверждают наличие источников по выбранной теме.</p>
        <div className="guide-grid">{starters.map((item) => <button key={item.id} type="button" onClick={() => onChoose(item.prompt)}>{item.label}</button>)}</div>
      </section>
    </div>
  )
}
