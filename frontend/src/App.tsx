import { useQuery } from "@tanstack/react-query"
import { useEffect, useRef, useState } from "react"
import type { FormEvent, KeyboardEvent } from "react"

import { createDemoReply, getApprovedMaterialsPreview, getDemoChats } from "./api/demo"
import type { DemoChat } from "./api/demo"
import { ApiError } from "./api/auth"
import { LoginScreen } from "./features/auth/LoginScreen"
import { useAuth } from "./features/auth/useAuth"
import { StarterGuide } from "./features/onboarding/StarterGuide"
import { starters } from "./features/onboarding/starters"

type View = "chat" | "materials" | "admin"

export function App() {
  const auth = useAuth()
  const chats = useQuery({ queryKey: ["demo-chats"], queryFn: getDemoChats, staleTime: Infinity })
  const materials = useQuery({ queryKey: ["demo-materials"], queryFn: getApprovedMaterialsPreview, staleTime: Infinity })
  const [view, setView] = useState<View>("chat")
  const [theme, setTheme] = useState<"light" | "dark">(document.documentElement.dataset.theme === "dark" ? "dark" : "light")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [localChats, setLocalChats] = useState<DemoChat[]>([])
  const [draft, setDraft] = useState("")
  const [guideOpen, setGuideOpen] = useState(false)
  const [listOpen, setListOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const [sendError, setSendError] = useState(false)
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const guideTriggerRef = useRef<HTMLButtonElement>(null)
  const listTriggerRef = useRef<HTMLButtonElement>(null)
  const listRef = useRef<HTMLElement>(null)
  const allChats = [...(chats.data ?? []), ...localChats]
  const selected = allChats.find((chat) => chat.id === selectedId)

  useEffect(() => {
    if (listOpen) listRef.current?.querySelector("button")?.focus()
  }, [listOpen])

  function closeList() {
    setListOpen(false)
    listTriggerRef.current?.focus()
  }

  function onListKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === "Escape") { closeList(); return }
    if (event.key !== "Tab" || !listRef.current) return
    const buttons = Array.from(listRef.current.querySelectorAll("button"))
    const first = buttons[0]
    const last = buttons.at(-1)
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
    if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
  }

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark"
    document.documentElement.dataset.theme = next
    try { localStorage.setItem("culturechamp-theme", next) } catch { /* Storage may be disabled. */ }
    setTheme(next)
  }

  function chooseStarter(prompt: string) {
    setView("chat")
    setDraft(prompt)
    setGuideOpen(false)
    window.setTimeout(() => composerRef.current?.focus(), 0)
  }

  async function send(event?: FormEvent) {
    event?.preventDefault()
    const text = draft.trim()
    if (!text || pending) return
    setPending(true)
    setSendError(false)
    try {
      const reply = await createDemoReply(text)
      const id = `local-${Date.now()}`
      setLocalChats((previous) => [...previous, { id, title: text.slice(0, 38), messages: [
        { role: "user", text },
        { role: "assistant", text: reply },
      ] }])
      setSelectedId(id)
      setDraft("")
    } catch {
      setSendError(true)
    } finally {
      setPending(false)
    }
  }

  function onComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      void send()
    }
  }

  if (auth.session.isPending) return <div className="app-shell"><main className="login-page"><p role="status">Проверяем сессию…</p></main></div>
  if (auth.session.isError && !(auth.session.error instanceof ApiError && auth.session.error.status === 401)) {
    return <div className="app-shell"><main className="login-page"><p role="alert">Не удалось проверить сессию.</p><button type="button" onClick={() => void auth.session.refetch()}>Повторить</button></main></div>
  }
  if (!auth.session.data) {
    return <div className="app-shell"><header className="site-header"><span className="wordmark">CultureChamp</span><button className="theme-toggle" type="button" onClick={toggleTheme}>{theme === "dark" ? "Светлая тема" : "Тёмная тема"}</button></header><LoginScreen onSubmit={(username, password) => auth.signIn.mutate({ username, password })} pending={auth.signIn.isPending} error={auth.signIn.error} /></div>
  }
  const activeSession = auth.session.data

  return <div className="app-shell">
    <header className="site-header">
      <span className="wordmark">CultureChamp</span>
      <nav aria-label="Основная навигация">
        <button aria-current={view === "chat" ? "page" : undefined} type="button" onClick={() => setView("chat")}>Чат</button>
        <button aria-current={view === "materials" ? "page" : undefined} type="button" onClick={() => setView("materials")}>Материалы</button>
        {activeSession.user.role === "admin" && <button aria-current={view === "admin" ? "page" : undefined} type="button" onClick={() => setView("admin")}>Админка</button>}
      </nav>
      <button className="theme-toggle" type="button" onClick={toggleTheme}>{theme === "dark" ? "Светлая тема" : "Тёмная тема"}</button>
      <button className="signout" type="button" onClick={() => auth.signOut.mutate(activeSession.csrf_token)} disabled={auth.signOut.isPending}>Выйти</button>
    </header>
    {auth.signOut.isError && <p className="auth-error" role="alert">Не удалось выйти. Повторите попытку.</p>}
    <div className="preview-banner" role="status">Предпросмотр интерфейса · чаты не сохраняются · источники ещё не одобрены</div>
    {view === "chat" && <main className="workspace">
      <aside ref={listRef} className={`chat-rail ${listOpen ? "open" : ""}`} aria-label="Список чатов" onKeyDown={onListKeyDown}>
        <div className="rail-heading"><h2>Чаты</h2><button type="button" onClick={() => { setSelectedId(null); setListOpen(false); composerRef.current?.focus() }}>Новый чат</button></div>
        {chats.isPending && <p role="status">Загружаем чаты…</p>}
        {chats.isError && <p role="alert">Не удалось загрузить чаты. <button type="button" onClick={() => void chats.refetch()}>Повторить</button></p>}
        {chats.isSuccess && allChats.length === 0 && <p>Пока нет чатов. Начните с задачи.</p>}
        <ul>{allChats.map((chat) => <li key={chat.id}><button aria-current={selectedId === chat.id ? "page" : undefined} type="button" onClick={() => { setSelectedId(chat.id); setListOpen(false) }}>{chat.title}</button></li>)}</ul>
      </aside>
      <div className="chat-main">
        <div className="chat-topline"><button ref={listTriggerRef} className="mobile-list" type="button" aria-expanded={listOpen} onClick={() => setListOpen(!listOpen)}>Чаты</button><span>Текстовый творческий бриф</span><button ref={guideTriggerRef} type="button" onClick={() => setGuideOpen(true)}>Что можно сделать?</button></div>
        {selected ? <section className="dialogue" aria-label="Диалог"><h1>{selected.title}</h1>{selected.messages.map((message, index) => <article className={`message ${message.role}`} key={`${selected.id}-${index}`}><span className="eyebrow">{message.role === "user" ? "Ваш бриф" : "Демо-ответ"}</span><p>{message.text}</p></article>)}</section> : <section className="chat-empty"><svg className="stitch-trim" viewBox="0 0 112 16" aria-hidden="true" focusable="false"><path d="M4 4l8 8m0-8l-8 8m16-8l8 8m0-8l-8 8m16-8l8 8m0-8l-8 8m16-8l8 8m0-8l-8 8m16-8l8 8m0-8l-8 8m16-8l8 8m0-8l-8 8" /></svg><p className="eyebrow">Начните с задачи</p><h1>Идея с культурным контекстом</h1><p>Опишите, что хотите создать. Источники будут доступны после проверки прав и одобрения материалов.</p><div className="starter-grid">{starters.map((item) => <button key={item.id} type="button" onClick={() => chooseStarter(item.prompt)}><span>{item.id}</span><strong>{item.label}</strong></button>)}</div></section>}
        <form className="composer" onSubmit={(event) => { void send(event) }}><label htmlFor="brief">Ваш творческий бриф</label><textarea id="brief" ref={composerRef} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={onComposerKeyDown} placeholder="Например: подготовить текст для музейной вводной панели…" rows={3} /><div className="composer-actions"><span>Enter — отправить · Shift+Enter — новая строка</span><button type="submit" disabled={!draft.trim() || pending}>{pending ? "Готовим демо…" : "Отправить"}</button></div>{pending && <p role="status">Создаём демонстрационный ответ…</p>}{sendError && <p role="alert">Не удалось создать демо-ответ. Текст сохранён; повторите отправку.</p>}</form>
      </div>
    </main>}
    {view === "materials" && <main className="simple-page"><p className="eyebrow">Материалы</p><h1>Проверенные источники</h1>{materials.isPending && <p role="status">Загружаем материалы…</p>}{materials.isError && <p role="alert">Не удалось загрузить материалы. <button type="button" onClick={() => void materials.refetch()}>Повторить</button></p>}{materials.isSuccess && <div className="empty-panel"><h2>Одобренных материалов пока нет</h2><p>Кандидатные PDF не показываются до проверки прав, контекста и точной ревизии.</p><button type="button" onClick={() => setView("chat")}>Вернуться к чату</button></div>}</main>}
    {view === "admin" && <main className="simple-page"><p className="eyebrow">Администрация · макет</p><h1>Документы</h1><div className="empty-panel"><h2>Инвентарь ожидает серверный API</h2><p>В предпросмотре нет доступа к неопубликованным ревизиям, действиям одобрения или статусам обработки.</p><button type="button" onClick={() => setView("chat")}>Вернуться к чату</button></div></main>}
    {guideOpen && <StarterGuide onChoose={chooseStarter} onClose={() => { setGuideOpen(false); guideTriggerRef.current?.focus() }} />}
  </div>
}
