import type { ChatCitation, ChatDetail, ChatSummary } from "../../api/chats"
import { sourceLocationLabel } from "../../api/locators"

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
  return <section className="dialogue" aria-label="Диалог">
    <div className="dialogue-heading"><h1>{summary.title}</h1><button type="button" onClick={onDelete} disabled={deleting}>Удалить чат</button></div>
    {pending && <p role="status">Загружаем диалог…</p>}
    {error && <p role="alert">Диалог недоступен. <button type="button" onClick={onRetry}>Повторить</button></p>}
    {detail?.turns.length === 0 && <p>Этот диалог пока пуст. Опишите задачу ниже.</p>}
    {detail?.turns.map((turn) => <div key={turn.request_id}>
      <article className="message user"><span className="eyebrow">Ваш бриф</span><p>{turn.user_text}</p></article>
      {turn.assistant_text && <article className="message assistant"><span className="eyebrow">Ответ</span><p>{turn.assistant_text}</p>
        {turn.citations.length > 0 && <ul className="chat-citations">{turn.citations.map((citation) => <li key={citation.segment_id}>
          <button type="button" disabled={!citation.available} onClick={() => onCitation(citation)}>{`Источник · ${sourceLocationLabel(citation, true)}`}</button>
          {!citation.available && <span> Источник отозван или недоступен</span>}
        </li>)}</ul>}
      </article>}
      {turn.status === "failed" && <p role="status">Ответ не получен. Повторите отправку с тем же текстом.</p>}
    </div>)}
  </section>
}
