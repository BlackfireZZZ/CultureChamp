import { useEffect, useRef, useState } from "react"
import type { ChatCitation, ChatDetail, ChatSummary, ChatTurn } from "../../api/chats"
import { sourceLocationLabel } from "../../api/locators"
import { Embroidery } from "../../components/ui/Embroidery"
import { answerParts } from "./answerParts"
import "./chat-controls.css"

function FeedbackControls({ turn, onRate }: {
  turn: ChatTurn
  onRate: (requestId: string, rating: "up" | "down" | null, comment: string | null) => Promise<unknown>
}) {
  const [comment, setComment] = useState(turn.feedback_comment ?? "")
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(false)
  async function save(rating: "up" | "down" | null, note: string | null): Promise<boolean> {
    setSaving(true)
    setError(false)
    try { await onRate(turn.request_id, rating, note); if (rating === null) { setEditing(false); setComment("") }; return true }
    catch { setError(true); return false }
    finally { setSaving(false) }
  }
  return <div className="response-feedback" aria-label="Оценка ответа">
    <div className="feedback-actions">
      <button type="button" aria-label="Нравится ответ" aria-pressed={turn.rating === "up"} disabled={saving} onClick={() => { void save(turn.rating === "up" ? null : "up", null) }}>👍</button>
      <button type="button" aria-label="Не нравится ответ" aria-pressed={turn.rating === "down"} disabled={saving} onClick={() => { void save(turn.rating === "down" ? null : "down", null) }}>👎</button>
      {turn.rating && <button type="button" onClick={() => setEditing(!editing)} aria-expanded={editing}>Комментарий</button>}
      {saving && <span role="status">Сохраняем оценку…</span>}
    </div>
    {editing && turn.rating && <form onSubmit={(event) => { event.preventDefault(); void save(turn.rating, comment.trim() || null).then((saved) => { if (saved) setEditing(false) }) }}>
      <label>Что стоит улучшить или сохранить?<textarea value={comment} onChange={(event) => setComment(event.target.value)} maxLength={1000} rows={3} /></label>
      <p>Комментарий увидит администратор сервиса.</p>
      <button type="submit" disabled={saving}>Сохранить комментарий</button>
    </form>}
    {turn.feedback_comment && !editing && <p className="feedback-saved">Ваш комментарий: {turn.feedback_comment}</p>}
    {error && <p role="alert">Не удалось сохранить оценку. Повторите попытку.</p>}
  </div>
}

export function ChatDialogue({ summary, detail, pending, error, onRetry, onCitation, onRate, streamingText, isGenerating = false, pendingUserText, pendingUserRequestId }: {
  summary: ChatSummary
  detail: ChatDetail | undefined
  pending: boolean
  error: boolean
  onRetry: () => void
  onCitation: (citation: ChatCitation) => void
  onRate: (requestId: string, rating: "up" | "down" | null, comment: string | null) => Promise<unknown>
  streamingText?: string
  isGenerating?: boolean
  pendingUserText?: string
  pendingUserRequestId?: string
}) {
  const dialogueRef = useRef<HTMLElement>(null)
  const followStream = useRef(true)
  useEffect(() => {
    if (!isGenerating || !dialogueRef.current) return
    followStream.current = true
    dialogueRef.current.scrollTop = dialogueRef.current.scrollHeight
  }, [isGenerating])
  useEffect(() => {
    if (isGenerating && followStream.current && dialogueRef.current) {
      dialogueRef.current.scrollTop = dialogueRef.current.scrollHeight
    }
  }, [isGenerating, streamingText])
  return <section ref={dialogueRef} className="dialogue" aria-label="Диалог" onScroll={(event) => { const target = event.currentTarget; followStream.current = target.scrollHeight - target.clientHeight - target.scrollTop < 120 }}>
    <Embroidery variant="band" />
    <div className="dialogue-heading"><h1 title={summary.title}>{summary.title}</h1></div>
    {pending && <p role="status">Загружаем диалог…</p>}
    {error && <p role="alert">Диалог недоступен. <button type="button" onClick={onRetry}>Повторить</button></p>}
    {detail?.turns.length === 0 && !isGenerating && <p>Этот диалог пока пуст. Опишите задачу ниже.</p>}
    {detail?.turns.map((turn) => <div key={turn.request_id}>
      <article className="message user"><span className="eyebrow">Ваша задача</span><p>{turn.user_text}</p></article>
      {turn.assistant_text && <article className="message assistant"><span className="eyebrow">Ответ · {turn.evidence_status === "grounded" ? "с опорой на источники" : "без подтверждённых источников"}</span>{answerParts(turn.assistant_text)?.map((part) => <section className="answer-part" key={part.title}><h2>{part.title}</h2><p>{part.body}</p>{part.imagePrompt && <p>Это описание можно использовать в любом генераторе изображений. Например, в <a href="https://giga.chat/" target="_blank" rel="noopener noreferrer">GigaChat</a>.</p>}</section>) ?? <p>{turn.assistant_text}</p>}
        {turn.citations.length > 0 && <ul className="chat-citations">{turn.citations.map((citation) => <li key={citation.segment_id}>
          <button type="button" disabled={!citation.available} onClick={() => onCitation(citation)}>{`Источник · ${sourceLocationLabel(citation, true)}`}</button>
          {!citation.available && <span> Источник отозван или недоступен</span>}
        </li>)}</ul>}
        <FeedbackControls key={`${turn.request_id}:${turn.rating}:${turn.feedback_comment ?? ""}`} turn={turn} onRate={onRate} />
      </article>}
      {turn.status === "failed" && <p role="status">Ответ не получен. Повторите отправку с тем же текстом.</p>}
    </div>)}
    {isGenerating && pendingUserText && !detail?.turns.some((turn) => turn.request_id === pendingUserRequestId) && <article className="message user"><span className="eyebrow">Ваша задача</span><p>{pendingUserText}</p></article>}
    {isGenerating && !detail?.turns.some((turn) => turn.request_id === pendingUserRequestId) && <article className="message assistant streaming-answer" aria-label="Ответ формируется">
      <span className="eyebrow">Ответ создаётся</span>
      {streamingText ? <p>{streamingText}</p> : <p role="status">Готовим ответ…</p>}
    </article>}
  </section>
}
