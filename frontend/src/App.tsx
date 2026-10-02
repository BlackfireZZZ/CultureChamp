import { useEffect, useRef, useState } from "react"
import type { FormEvent, KeyboardEvent } from "react"

import { ApiError } from "./api/auth"
import type { ChatCitation } from "./api/chats"
import { Embroidery } from "./components/ui/Embroidery"
import { TreeOrnament } from "./components/ui/TreeOrnament"
import { AdminView } from "./features/admin/AdminView"
import { LoginScreen } from "./features/auth/LoginScreen"
import { useAuth } from "./features/auth/useAuth"
import { useChat, useChatActions, useChats } from "./features/chat/useChats"
import { ChatDialogue } from "./features/chat/ChatDialogue"
import { ChatComposer } from "./features/chat/ChatComposer"
import { MaterialsView } from "./features/materials/MaterialsView"
import { StarterGuide } from "./features/onboarding/StarterGuide"
import { starters } from "./features/onboarding/starters"

type View = "chat" | "materials" | "admin"

export function App() {
  const auth = useAuth()
  const isUser = auth.session.data?.user.role === "user"
  const chats = useChats(isUser)
  const [view, setView] = useState<View>("chat")
  const [theme, setTheme] = useState<"light" | "dark">(document.documentElement.dataset.theme === "dark" ? "dark" : "light")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const detail = useChat(selectedId, isUser)
  const actions = useChatActions(auth.session.data?.csrf_token ?? "")
  const [citationTarget, setCitationTarget] = useState<ChatCitation | null>(null)
  const [draft, setDraft] = useState("")
  const [starterId, setStarterId] = useState<string | null>(null)
  const [guideOpen, setGuideOpen] = useState(false)
  const [listOpen, setListOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const [sendError, setSendError] = useState(false)
  const [pendingRequest, setPendingRequest] = useState<{ text: string; id: string; chatId: string | null; starterId: string | null } | null>(null)
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const guideTriggerRef = useRef<HTMLButtonElement>(null)
  const listTriggerRef = useRef<HTMLButtonElement>(null)
  const listRef = useRef<HTMLElement>(null)
  const allChats = chats.data ?? []
  const selected = allChats.find((chat) => chat.id === selectedId)
  const effectiveView = isUser ? view : "admin"

  useEffect(() => {
    const input = composerRef.current
    if (!input) return
    input.style.height = "auto"
    input.style.height = `${Math.min(input.scrollHeight, 180)}px`
  }, [draft, selectedId, effectiveView])

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
    setStarterId(starters.find((item) => item.prompt === prompt)?.id ?? null)
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
      const request = pendingRequest?.text === text && pendingRequest.chatId === selectedId
        ? pendingRequest : { text, id: crypto.randomUUID(), chatId: selectedId, starterId }
      setPendingRequest(request)
      const chatId = request.chatId ?? (await actions.create.mutateAsync()).id
      setSelectedId(chatId)
      setPendingRequest({ ...request, chatId })
      await actions.send.mutateAsync({ chatId, text, requestId: request.id, starterId: request.starterId ?? undefined })
      setDraft("")
      setStarterId(null)
      setPendingRequest(null)
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
    return <div className="app-shell"><header className="site-header"><span className="wordmark">Лад</span><button className="theme-toggle" type="button" onClick={toggleTheme}>{theme === "dark" ? "Светлая тема" : "Тёмная тема"}</button></header><LoginScreen onSubmit={(username, password) => auth.signIn.mutate({ username, password })} pending={auth.signIn.isPending} error={auth.signIn.error} /></div>
  }
  const activeSession = auth.session.data

  return <div className="app-shell">
    <header className="site-header">
      <span className="wordmark">Лад</span>
      <div className="header-controls"><nav aria-label="Основная навигация">
        {isUser && <button aria-current={effectiveView === "chat" ? "page" : undefined} type="button" onClick={() => setView("chat")}>Чат</button>}
        {isUser && <button aria-current={effectiveView === "materials" ? "page" : undefined} type="button" onClick={() => { setCitationTarget(null); setView("materials") }}>Материалы</button>}
        {activeSession.user.role === "admin" && <button aria-current={effectiveView === "admin" ? "page" : undefined} type="button" onClick={() => setView("admin")}>Админка</button>}
      </nav><div className="header-actions">
      <button className="theme-toggle" type="button" onClick={toggleTheme}>{theme === "dark" ? "Светлая тема" : "Тёмная тема"}</button>
      <button className="signout" type="button" onClick={() => auth.signOut.mutate(activeSession.csrf_token, { onSuccess: () => { setSelectedId(null); setPendingRequest(null); setDraft(""); setView("chat") } })} disabled={auth.signOut.isPending}>Выйти</button>
      </div></div>
    </header>
    {auth.signOut.isError && <p className="auth-error" role="alert">Не удалось выйти. Повторите попытку.</p>}
    {effectiveView === "chat" && isUser && <main className="workspace">
      <aside ref={listRef} className={`chat-rail ${listOpen ? "open" : ""}`} aria-label="Список чатов" onKeyDown={onListKeyDown}>
        <button className="mobile-list-close" type="button" onClick={closeList}>Закрыть список чатов</button>
        <button className="new-chat-button" type="button" onClick={() => { setSelectedId(null); setDraft(""); setStarterId(null); setPendingRequest(null); setListOpen(false); window.setTimeout(() => composerRef.current?.focus(), 0) }}><span aria-hidden="true">＋</span> Новый чат</button>
        <div className="rail-heading"><h2>История</h2></div>
        {chats.isPending && <p role="status">Загружаем чаты…</p>}
        {chats.isError && <p role="alert">Не удалось загрузить чаты. <button type="button" onClick={() => void chats.refetch()}>Повторить</button></p>}
        {chats.isSuccess && allChats.length === 0 && <p>Пока нет чатов. Начните с задачи.</p>}
        <ul>{allChats.map((chat) => <li key={chat.id}><button aria-current={selectedId === chat.id ? "page" : undefined} type="button" onClick={() => { setSelectedId(chat.id); setPendingRequest(null); setListOpen(false) }}>{chat.title}</button></li>)}</ul>
      </aside>
      <div className={`chat-main ${selected ? "has-chat" : "is-empty"}`}>
        {!selected && <TreeOrnament />}
        <div className="chat-topline"><button ref={listTriggerRef} className="mobile-list" type="button" aria-expanded={listOpen} onClick={() => setListOpen(!listOpen)}>Чаты</button>{selected && <span>Чат</span>}{selected && <button ref={guideTriggerRef} type="button" onClick={() => setGuideOpen(true)}>Что можно сделать?</button>}</div>
        {selected ? <ChatDialogue summary={selected} detail={detail.data} pending={detail.isPending} error={detail.isError} onRetry={() => void detail.refetch()} onCitation={(citation) => { setCitationTarget(citation); setView("materials") }} onDelete={() => { void actions.remove.mutateAsync(selected.id).then(() => setSelectedId(null)).catch(() => setSendError(true)) }} deleting={actions.remove.isPending} onRate={(requestId, rating, comment) => actions.rate.mutateAsync({ chatId: selected.id, requestId, rating, comment })} /> : <div className="chat-launch"><section className="chat-empty"><Embroidery variant="band" /><p className="eyebrow">Творческая задача</p><h1>Идея с культурным контекстом</h1><p>Что вы хотите создать?</p></section>
        <ChatComposer value={draft} onChange={(text) => { setDraft(text); setPendingRequest(null) }} onSubmit={(event) => { void send(event) }} pending={pending} error={sendError} placeholder="Опишите задачу…" inputRef={composerRef} onKeyDown={onComposerKeyDown} />
        {!draft.trim() && <section className="starter-section" aria-label="Идеи для начала"><div className="starter-heading"><span>Попробуйте начать с идеи</span><button ref={guideTriggerRef} type="button" onClick={() => setGuideOpen(true)}>Что можно сделать?</button></div><div className="starter-grid">{starters.slice(0, 3).map((item) => <button key={item.id} type="button" onClick={() => chooseStarter(item.prompt)}>{item.label}</button>)}</div></section>}</div>}
        {selected && <ChatComposer value={draft} onChange={(text) => { setDraft(text); setPendingRequest(null) }} onSubmit={(event) => { void send(event) }} pending={pending} error={sendError} placeholder="Продолжите разговор…" inputRef={composerRef} onKeyDown={onComposerKeyDown} />}
      </div>
    </main>}
    {effectiveView === "materials" && isUser && <MaterialsView onBack={() => { setView("chat"); window.setTimeout(() => composerRef.current?.focus(), 0) }} citationTarget={citationTarget} />}
    {effectiveView === "admin" && activeSession.user.role === "admin" && <AdminView csrfToken={activeSession.csrf_token} />}
    {guideOpen && <StarterGuide onChoose={chooseStarter} onClose={() => { setGuideOpen(false); guideTriggerRef.current?.focus() }} />}
  </div>
}
