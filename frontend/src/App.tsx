import { useEffect, useRef, useState } from "react"
import type { CSSProperties, FormEvent, KeyboardEvent, PointerEvent } from "react"

import { ApiError } from "./api/auth"
import type { ChatCitation } from "./api/chats"
import { Embroidery } from "./components/ui/Embroidery"
import { TreeOrnament } from "./components/ui/TreeOrnament"
import { AdminView } from "./features/admin/AdminView"
import { LoginScreen } from "./features/auth/LoginScreen"
import { useAuth } from "./features/auth/useAuth"
import { useChat, useChatActions, useChats } from "./features/chat/useChats"
import { ChatDialogue } from "./features/chat/ChatDialogue"
import { ChatRailItem } from "./features/chat/ChatRailItem"
import { ChatComposer } from "./features/chat/ChatComposer"
import { MaterialsView } from "./features/materials/MaterialsView"
import { StarterGuide } from "./features/onboarding/StarterGuide"
import { starters } from "./features/onboarding/starters"

type View = "chat" | "materials" | "admin"
const RAIL_MIN = 220
const RAIL_DEFAULT = 250
const RAIL_MAX = 480
const RAIL_STORAGE_KEY = "lad-chat-rail-width"

function boundedRailWidth(width: number): number {
  const viewportMax = Math.max(RAIL_MIN, window.innerWidth - 620)
  return Math.round(Math.min(Math.max(width, RAIL_MIN), RAIL_MAX, viewportMax))
}

function savedRailWidth(): number {
  try {
    const value = Number(window.localStorage.getItem(RAIL_STORAGE_KEY))
    return boundedRailWidth(value > 0 ? value : RAIL_DEFAULT)
  } catch { return RAIL_DEFAULT }
}

function ThemeIcon({ theme }: { theme: "light" | "dark" }) {
  return theme === "light"
    ? <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M20.2 15.4A8.5 8.5 0 0 1 8.6 3.8 8.5 8.5 0 1 0 20.2 15.4Z" /></svg>
    : <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
}

function ExitIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M10 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h5M15 8l4 4-4 4M8 12h11" /></svg>
}

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
  const [railWidth, setRailWidth] = useState(savedRailWidth)
  const [resizingRail, setResizingRail] = useState(false)
  const resizeStyles = useRef<{ cursor: string; userSelect: string } | null>(null)
  const [pending, setPending] = useState(false)
  const [streamingText, setStreamingText] = useState("")
  const [streamingChatId, setStreamingChatId] = useState<string | null>(null)
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

  useEffect(() => {
    try { window.localStorage.setItem(RAIL_STORAGE_KEY, String(railWidth)) } catch { /* Storage may be disabled. */ }
  }, [railWidth])

  useEffect(() => {
    const onResize = () => setRailWidth((current) => boundedRailWidth(current))
    window.addEventListener("resize", onResize)
    return () => window.removeEventListener("resize", onResize)
  }, [])

  function finishRailResize(event: PointerEvent<HTMLDivElement>) {
    if (!resizingRail) return
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
    setResizingRail(false)
    if (resizeStyles.current) {
      document.body.style.cursor = resizeStyles.current.cursor
      document.body.style.userSelect = resizeStyles.current.userSelect
      resizeStyles.current = null
    }
  }

  function resizeRailWithKeys(event: KeyboardEvent<HTMLDivElement>) {
    const step = event.shiftKey ? 64 : 24
    if (event.key === "ArrowLeft") setRailWidth((current) => boundedRailWidth(current - step))
    else if (event.key === "ArrowRight") setRailWidth((current) => boundedRailWidth(current + step))
    else if (event.key === "Home") setRailWidth(boundedRailWidth(RAIL_MIN))
    else if (event.key === "End") setRailWidth(boundedRailWidth(RAIL_MAX))
    else return
    event.preventDefault()
  }

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
    setDraft("")
    try {
      const request = pendingRequest?.text === text && pendingRequest.chatId === selectedId
        ? pendingRequest : { text, id: crypto.randomUUID(), chatId: selectedId, starterId }
      setPendingRequest(request)
      const chatId = request.chatId ?? (await actions.create.mutateAsync()).id
      setSelectedId(chatId)
      setStreamingChatId(chatId)
      setStreamingText("")
      setPendingRequest({ ...request, chatId })
      await actions.stream.mutateAsync({ chatId, text, requestId: request.id, starterId: request.starterId ?? undefined, onDelta: (delta) => setStreamingText((current) => current + delta) })
      setStarterId(null)
      setPendingRequest(null)
    } catch {
      setDraft((current) => current || text)
      setSendError(true)
    } finally {
      setStreamingText("")
      setStreamingChatId(null)
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
    return <div className="app-shell"><header className="site-header"><span className="wordmark">Лад</span><button className="theme-toggle" type="button" aria-label={theme === "dark" ? "Светлая тема" : "Тёмная тема"} title={theme === "dark" ? "Светлая тема" : "Тёмная тема"} onClick={toggleTheme}><ThemeIcon theme={theme} /></button></header><LoginScreen onSubmit={(username, password) => auth.signIn.mutate({ username, password })} pending={auth.signIn.isPending} error={auth.signIn.error} /></div>
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
      <button className="theme-toggle" type="button" aria-label={theme === "dark" ? "Светлая тема" : "Тёмная тема"} title={theme === "dark" ? "Светлая тема" : "Тёмная тема"} onClick={toggleTheme}><ThemeIcon theme={theme} /></button>
      <button className="signout" type="button" aria-label="Выйти" title="Выйти" onClick={() => auth.signOut.mutate(activeSession.csrf_token, { onSuccess: () => { setSelectedId(null); setPendingRequest(null); setDraft(""); setView("chat") } })} disabled={auth.signOut.isPending}><ExitIcon /></button>
      </div></div>
    </header>
    {auth.signOut.isError && <p className="auth-error" role="alert">Не удалось выйти. Повторите попытку.</p>}
    {effectiveView === "chat" && isUser && <main className="workspace" style={{ "--chat-rail-width": `${railWidth}px` } as CSSProperties}>
      <aside id="chat-history-panel" ref={listRef} className={`chat-rail ${listOpen ? "open" : ""}`} aria-label="Список чатов" onKeyDown={onListKeyDown}>
        <button className="mobile-list-close" type="button" onClick={closeList}>Закрыть список чатов</button>
        <button className="new-chat-button" type="button" onClick={() => { setSelectedId(null); setDraft(""); setStarterId(null); setPendingRequest(null); setListOpen(false); window.setTimeout(() => composerRef.current?.focus(), 0) }}><span aria-hidden="true">＋</span> Новый чат</button>
        <div className="rail-heading"><h2>История</h2></div>
        {chats.isPending && <p role="status">Загружаем чаты…</p>}
        {chats.isError && <p role="alert">Не удалось загрузить чаты. <button type="button" onClick={() => void chats.refetch()}>Повторить</button></p>}
        {chats.isSuccess && allChats.length === 0 && <p>Пока нет чатов. Начните с задачи.</p>}
        <ul>{allChats.map((chat) => <ChatRailItem key={chat.id} chat={chat} active={selectedId === chat.id} onSelect={() => { setSelectedId(chat.id); setPendingRequest(null); setListOpen(false) }} onRename={(title) => actions.rename.mutateAsync({ chatId: chat.id, title }).then(() => undefined)} onDelete={async () => { await actions.remove.mutateAsync(chat.id); if (selectedId === chat.id) setSelectedId(null) }} renaming={actions.rename.isPending} deleting={actions.remove.isPending} />)}</ul>
      </aside>
      <div className={`rail-resize-handle ${resizingRail ? "is-dragging" : ""}`} role="separator" tabIndex={0} aria-label="Ширина панели чатов" aria-controls="chat-history-panel" aria-orientation="vertical" aria-valuemin={RAIL_MIN} aria-valuemax={boundedRailWidth(RAIL_MAX)} aria-valuenow={railWidth} title="Перетащите для изменения ширины; двойной щелчок — ширина по умолчанию" onKeyDown={resizeRailWithKeys} onDoubleClick={() => setRailWidth(boundedRailWidth(RAIL_DEFAULT))} onPointerDown={(event) => { if (event.button !== 0) return; event.currentTarget.setPointerCapture(event.pointerId); resizeStyles.current = { cursor: document.body.style.cursor, userSelect: document.body.style.userSelect }; document.body.style.cursor = "col-resize"; document.body.style.userSelect = "none"; setResizingRail(true); event.preventDefault() }} onPointerMove={(event) => { if (event.currentTarget.hasPointerCapture(event.pointerId) && listRef.current) setRailWidth(boundedRailWidth(event.clientX - listRef.current.getBoundingClientRect().left)) }} onPointerUp={finishRailResize} onPointerCancel={finishRailResize} />
      <div className={`chat-main ${selected ? "has-chat" : "is-empty"} ${draft.trim() ? "is-drafting" : ""}`}>
        {!selected && <TreeOrnament />}
        <div className="chat-topline"><button ref={listTriggerRef} className="mobile-list" type="button" aria-expanded={listOpen} onClick={() => setListOpen(!listOpen)}>Чаты</button>{selected && <span>Чат</span>}{selected && <button ref={guideTriggerRef} type="button" onClick={() => setGuideOpen(true)}>Что можно сделать?</button>}</div>
        {selected ? <ChatDialogue summary={selected} detail={detail.data} pending={detail.isPending} error={detail.isError} onRetry={() => void detail.refetch()} onCitation={(citation) => { setCitationTarget(citation); setView("materials") }} onRate={(requestId, rating, comment) => actions.rate.mutateAsync({ chatId: selected.id, requestId, rating, comment })} streamingText={streamingText} isGenerating={pending && streamingChatId === selected.id} pendingUserText={pendingRequest?.chatId === selected.id ? pendingRequest.text : undefined} pendingUserRequestId={pendingRequest?.chatId === selected.id ? pendingRequest.id : undefined} /> : <div className="chat-launch"><section className="chat-empty"><Embroidery variant="band" /><p className="eyebrow">Творческая задача</p><h1>Идея с культурным контекстом</h1><p>Что вы хотите создать?</p></section>
        <ChatComposer value={draft} onChange={(text) => { setDraft(text); setPendingRequest(null) }} onSubmit={(event) => { void send(event) }} pending={pending} error={sendError} placeholder="Опишите задачу…" inputRef={composerRef} onKeyDown={onComposerKeyDown} />
        {!draft.trim() && !pending && <section className="starter-section" aria-label="Идеи для начала"><div className="starter-heading"><span>Попробуйте начать с идеи</span><button ref={guideTriggerRef} type="button" onClick={() => setGuideOpen(true)}>Что можно сделать?</button></div><div className="starter-grid">{starters.slice(0, 3).map((item) => <button key={item.id} type="button" onClick={() => chooseStarter(item.prompt)}>{item.label}</button>)}</div></section>}</div>}
        {selected && <ChatComposer value={draft} onChange={(text) => { setDraft(text); setPendingRequest(null) }} onSubmit={(event) => { void send(event) }} pending={pending} error={sendError} placeholder="Продолжите разговор…" inputRef={composerRef} onKeyDown={onComposerKeyDown} />}
      </div>
    </main>}
    {effectiveView === "materials" && isUser && <MaterialsView onBack={() => { setView("chat"); window.setTimeout(() => composerRef.current?.focus(), 0) }} citationTarget={citationTarget} citations={citationTarget ? detail.data?.turns.flatMap((turn) => turn.citations) : undefined} />}
    {effectiveView === "admin" && activeSession.user.role === "admin" && <AdminView csrfToken={activeSession.csrf_token} />}
    {guideOpen && <StarterGuide onChoose={chooseStarter} onClose={() => { setGuideOpen(false); guideTriggerRef.current?.focus() }} />}
  </div>
}
