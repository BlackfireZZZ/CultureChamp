import { useEffect, useRef, useState } from "react"
import type { ChatSummary } from "../../api/chats"

export function ChatRailItem({ chat, active, onSelect, onRename, onDelete, renaming, deleting }: {
  chat: ChatSummary
  active: boolean
  onSelect: () => void
  onRename: (title: string) => Promise<void>
  onDelete: () => Promise<void>
  renaming: boolean
  deleting: boolean
}) {
  const [mode, setMode] = useState<"normal" | "rename" | "delete">("normal")
  const [title, setTitle] = useState(chat.title)
  const [error, setError] = useState(false)
  const renameTrigger = useRef<HTMLButtonElement>(null)
  const deleteTrigger = useRef<HTMLButtonElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const cancel = useRef<HTMLButtonElement>(null)
  useEffect(() => { if (mode === "rename") input.current?.focus(); if (mode === "delete") cancel.current?.focus() }, [mode])

  function close(focus: "rename" | "delete") {
    setMode("normal")
    setError(false)
    window.setTimeout(() => (focus === "rename" ? renameTrigger : deleteTrigger).current?.focus(), 0)
  }

  async function save() {
    const next = title.trim()
    if (!next) { setError(true); input.current?.focus(); return }
    if (next === chat.title) { close("rename"); return }
    try { await onRename(next); close("rename") }
    catch { setError(true); input.current?.focus() }
  }

  async function remove() {
    try { await onDelete() }
    catch { setError(true); cancel.current?.focus() }
  }

  return <li className={`chat-rail-item ${active ? "is-active" : ""}`}>
    {mode === "rename" ? <form className="rail-rename" onSubmit={(event) => { event.preventDefault(); void save() }} onKeyDown={(event) => { if (event.key === "Escape") { event.preventDefault(); close("rename") } }}>
      <label className="visually-hidden" htmlFor={`rename-${chat.id}`}>Название чата</label>
      <input ref={input} id={`rename-${chat.id}`} value={title} maxLength={120} onChange={(event) => setTitle(event.target.value)} />
      <div className="rail-confirm-actions"><button type="submit" disabled={renaming || !title.trim()}>Сохранить</button><button type="button" disabled={renaming} onClick={() => close("rename")}>Отмена</button></div>
    </form> : <div className="rail-chat-row">
      <button className="rail-chat-select" type="button" title={chat.title} aria-current={active ? "page" : undefined} onClick={onSelect}>{chat.title}</button>
      <div className="rail-chat-actions">
        <button ref={renameTrigger} className="rail-chat-icon" type="button" aria-label={`Переименовать чат «${chat.title}»`} title="Переименовать чат" disabled={renaming || deleting} onClick={() => { setTitle(chat.title); setError(false); setMode("rename") }}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M4 20h4l11-11a2 2 0 0 0-4-4L4 16v4Z"/><path d="m13.5 6.5 4 4"/></svg></button>
        <button ref={deleteTrigger} className="rail-chat-icon is-danger" type="button" aria-label={`Удалить чат «${chat.title}»`} title="Удалить чат" aria-expanded={mode === "delete"} disabled={renaming || deleting} onClick={() => { setError(false); setMode("delete") }}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6m4-6v6"/></svg></button>
      </div>
    </div>}
    {mode === "delete" && <div className="rail-delete-confirm" role="group" aria-label={`Подтверждение удаления чата «${chat.title}»`} onKeyDown={(event) => { if (event.key === "Escape") close("delete") }}><p>Удалить чат и сообщения?</p><div className="rail-confirm-actions"><button ref={cancel} type="button" onClick={() => close("delete")}>Отмена</button><button className="is-danger" type="button" disabled={deleting} onClick={() => { void remove() }}>{deleting ? "Удаляем…" : "Удалить"}</button></div></div>}
    {error && <p className="rail-action-error" role="alert">Не удалось выполнить действие. Повторите попытку.</p>}
  </li>
}
