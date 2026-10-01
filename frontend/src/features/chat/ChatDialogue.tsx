import { useEffect, useRef, useState } from "react"
import type { ChatCitation, ChatDetail, ChatSummary } from "../../api/chats"
import { sourceLocationLabel } from "../../api/locators"
import { Embroidery } from "../../components/ui/Embroidery"
import { answerParts } from "./answerParts"

export function ChatDialogue({ summary, detail, pending, error, onRetry, onCitation, onDelete, deleting }: {
  summary: ChatSummary
  detail: ChatDetail | undefined
  pending: boolean
  error: boolean
  onRetry: () => void
  onCitation: (citation: ChatCitation) => void
  onDelete: () => void
  deleting: boolean
}) {
  const [confirmDelete, setConfirmDelete] = useState(false)
  const cancelRef = useRef<HTMLButtonElement>(null)
  const deleteTriggerRef = useRef<HTMLButtonElement>(null)
  useEffect(() => { if (confirmDelete) cancelRef.current?.focus() }, [confirmDelete])
  function cancelDelete() { setConfirmDelete(false); deleteTriggerRef.current?.focus() }
  return <section className="dialogue" aria-label="Диалог">
    <Embroidery variant="band" />
    <div className="dialogue-heading"><h1>{summary.title}</h1><button ref={deleteTriggerRef} type="button" onClick={() => setConfirmDelete(true)} disabled={deleting}>Удалить чат</button></div>
    {confirmDelete && <div className="delete-confirm" role="group" aria-label="Подтверждение удаления чата" onKeyDown={(event) => { if (event.key === "Escape") cancelDelete() }}><p>Удалить этот чат и его сообщения? Это действие нельзя отменить.</p><button ref={cancelRef} type="button" onClick={cancelDelete}>Отмена</button><button type="button" disabled={deleting} onClick={onDelete}>{deleting ? "Удаляем…" : "Подтвердить удаление"}</button></div>}
    {pending && <p role="status">Загружаем диалог…</p>}
    {error && <p role="alert">Диалог недоступен. <button type="button" onClick={onRetry}>Повторить</button></p>}
    {detail?.turns.length === 0 && <p>Этот диалог пока пуст. Опишите задачу ниже.</p>}
    {detail?.turns.map((turn) => <div key={turn.request_id}>
      <article className="message user"><span className="eyebrow">Ваш бриф</span><p>{turn.user_text}</p></article>
      {turn.assistant_text && <article className="message assistant"><span className="eyebrow">Ответ · {turn.evidence_status === "grounded" ? "с опорой на источники" : "без подтверждённых источников"}</span>{answerParts(turn.assistant_text)?.map((part) => <section className="answer-part" key={part.title}><h2>{part.title}</h2><p>{part.body}</p></section>) ?? <p>{turn.assistant_text}</p>}
        {turn.citations.length > 0 && <ul className="chat-citations">{turn.citations.map((citation) => <li key={citation.segment_id}>
          <button type="button" disabled={!citation.available} onClick={() => onCitation(citation)}>{`Источник · ${sourceLocationLabel(citation, true)}`}</button>
          {!citation.available && <span> Источник отозван или недоступен</span>}
        </li>)}</ul>}
      </article>}
      {turn.status === "failed" && <p role="status">Ответ не получен. Повторите отправку с тем же текстом.</p>}
    </div>)}
  </section>
}
