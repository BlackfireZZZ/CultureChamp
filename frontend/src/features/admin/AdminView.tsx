import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import type { FormEvent } from "react"

import { ApiError } from "../../api/auth"
import { amendAdminMetadata, approveAdminRevision, getAdminMetadataHistory, getAdminRevision, getAdminSegmentHistory, getAdminSources, reviewAdminSegments, retryAdminRevision, revokeAdminRevision, uploadAdminSource } from "../../api/admin"
import type { AdminFilters, MetadataInput, SegmentReviewInput } from "../../api/admin"
import { sourceLocationLabel } from "../../api/locators"
import { starters } from "../onboarding/starters"
import { useRequestStatistics } from "./useRequestStatistics"

const sourceStatusLabels: Record<string, string> = {
  candidate: "Ожидает обработки", processing: "Обрабатывается",
  review_pending: "Ожидает проверки", failed: "Ошибка обработки",
}
const decisionLabels: Record<string, string> = { approve: "Одобрено", revoke: "Отозвано" }
const tagLabels: Record<string, string> = { region: "Регион", people: "Народ", period: "Период", topic: "Тема", sensitivity: "Чувствительность" }
const formatLabels: Record<string, string> = {
  "application/pdf": "PDF", "text/plain": "TXT", "text/csv": "CSV",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "XLSX",
}

function sourceStatusLabel(status: string): string { return sourceStatusLabels[status] ?? "Статус неизвестен" }
function decisionLabel(decision: string | null): string { return decision ? decisionLabels[decision] ?? "Решение неизвестно" : "Нет решения" }
function starterLabel(id: string): string { return starters.find((item) => item.id === id)?.label ?? "Другая задача" }
function tagLabel(kind: string): string { return tagLabels[kind] ?? "Другая метка" }
function formatLabel(mediaType: string): string { return formatLabels[mediaType] ?? "Другой формат" }

function textField(form: FormData, name: string): string {
  const value = form.get(name)
  return typeof value === "string" ? value : ""
}

function safeOriginUrl(value: string): string | null {
  try {
    const url = new URL(value)
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : null
  } catch {
    return null
  }
}

function OriginReference({ value }: { value: string }) {
  const href = safeOriginUrl(value)
  return href ? <a href={href} target="_blank" rel="noopener noreferrer">{value}</a> : value
}

export function AdminView({ csrfToken }: { csrfToken: string }) {
  const client = useQueryClient()
  const [section, setSection] = useState<"sources" | "statistics">("sources")
  const [feedback, setFeedback] = useState("")
  const statistics = useRequestStatistics(section === "statistics")
  const [revisionId, setRevisionId] = useState<string | null>(null)
  const [status, setStatus] = useState<NonNullable<AdminFilters["status"]> | "">("")
  const [decision, setDecision] = useState<NonNullable<AdminFilters["decision"]> | "">("")
  const [queryDraft, setQueryDraft] = useState("")
  const [tagDraft, setTagDraft] = useState("")
  const [query, setQuery] = useState("")
  const [tagValue, setTagValue] = useState("")
  const [mediaType, setMediaType] = useState<NonNullable<AdminFilters["media_type"]> | "">("")
  const [tagKind, setTagKind] = useState<NonNullable<AdminFilters["tag_kind"]> | "">("")
  const filters: AdminFilters = { status: status || undefined, decision: decision || undefined, q: query || undefined, media_type: mediaType || undefined, tag_kind: tagKind || undefined, tag_value: tagValue || undefined, limit: 100 }
  const sources = useQuery({ queryKey: ["admin", "sources", status, decision, query, mediaType, tagKind, tagValue], queryFn: ({ signal }) => getAdminSources(filters, signal), retry: false })
  const revision = useQuery({ queryKey: ["admin", "revision", revisionId], queryFn: ({ signal }) => getAdminRevision(revisionId!, signal), enabled: revisionId !== null, retry: false })
  const metadataHistory = useQuery({ queryKey: ["admin", "metadata-history", revisionId], queryFn: ({ signal }) => getAdminMetadataHistory(revisionId!, signal), enabled: revisionId !== null, retry: false })
  const segmentHistory = useQuery({ queryKey: ["admin", "segment-history", revisionId], queryFn: ({ signal }) => getAdminSegmentHistory(revisionId!, signal), enabled: revisionId !== null && Boolean(revision.data?.segments.length), retry: false })
  const refresh = async () => client.invalidateQueries({ queryKey: ["admin"] })
  const upload = useMutation({ mutationFn: (form: FormData) => uploadAdminSource(form, csrfToken), onSuccess: async (value) => { setRevisionId(value.revision_id); await refresh() } })
  const approve = useMutation({ mutationFn: ({ id, data }: { id: string; data: { reason: string; evidence_url: string; user_text: boolean; original_file: boolean; provider_transfer: boolean; sensitivity_cleared: boolean } }) => approveAdminRevision(id, data, csrfToken), onSuccess: async () => { setFeedback("Точная ревизия одобрена."); await refresh() } })
  const revoke = useMutation({ mutationFn: ({ id, reason }: { id: string; reason: string }) => revokeAdminRevision(id, reason, csrfToken), onSuccess: async () => { setFeedback("Точная ревизия отозвана."); await refresh() } })
  const retry = useMutation({ mutationFn: (id: string) => retryAdminRevision(id, csrfToken), onSuccess: async () => { setFeedback("Повторная обработка запущена."); await refresh() } })
  const metadata = useMutation({ mutationFn: ({ id, data }: { id: string; data: MetadataInput }) => amendAdminMetadata(id, data, csrfToken), onSuccess: async () => { setFeedback("Метаданные сохранены."); await refresh() } })
  const segmentReview = useMutation({ mutationFn: ({ id, data }: { id: string; data: SegmentReviewInput }) => reviewAdminSegments(id, data, csrfToken), onSuccess: async () => { setFeedback("Проверка фрагментов сохранена."); await refresh() } })

  function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const entries = textField(form, "tag_entries")
    form.delete("tag_entries")
    for (const line of entries.split(/\r?\n/).map((item) => item.trim()).filter(Boolean)) form.append("tags", line)
    upload.mutate(form)
  }

  function submitApproval(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!revisionId) return
    const form = new FormData(event.currentTarget)
    approve.mutate({ id: revisionId, data: {
      reason: textField(form, "reason"), evidence_url: textField(form, "evidence_url"),
      user_text: form.has("user_text"), original_file: form.has("original_file"),
      provider_transfer: form.has("provider_transfer"), sensitivity_cleared: form.has("sensitivity_cleared"),
    } })
  }

  function submitRevocation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!revisionId) return
    const form = new FormData(event.currentTarget)
    revoke.mutate({ id: revisionId, reason: textField(form, "reason") })
  }

  function submitMetadata(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!revisionId || !revision.data) return
    const form = new FormData(event.currentTarget)
    const tags = textField(form, "tag_entries").split(/\r?\n/).map((item) => item.trim()).filter(Boolean).map((item) => {
      const separator = item.indexOf(":")
      return { kind: item.slice(0, separator), value: item.slice(separator + 1).trim() }
    })
    metadata.mutate({ id: revisionId, data: {
      expected_version: revision.data.metadata_version,
      reason: textField(form, "reason"),
      description: textField(form, "description").trim() || null,
      tags,
    } })
  }

  function submitSegmentReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!revisionId || !revision.data) return
    const form = new FormData(event.currentTarget)
    segmentReview.mutate({ id: revisionId, data: {
      expected_version: revision.data.segment_review_version,
      reason: textField(form, "reason"),
      excluded_segment_ids: form.getAll("excluded_segment_id").filter((item): item is string => typeof item === "string"),
    } })
  }

  function submitFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setQuery(queryDraft.trim())
    setTagValue(tagDraft.trim())
    setRevisionId(null)
  }

  function resetFilters() {
    setStatus("")
    setDecision("")
    setQueryDraft("")
    setTagDraft("")
    setQuery("")
    setTagValue("")
    setMediaType("")
    setTagKind("")
    setRevisionId(null)
  }

  const statisticsUnavailable = statistics.error instanceof ApiError && [404, 501].includes(statistics.error.status)

  return <main className="simple-page materials-page">
    <p className="eyebrow">Администрация · проверка источников</p>
    <h1>{section === "sources" ? "Проверка материалов" : "Статистика запросов"}</h1>
    {feedback && <p role="status">{feedback}</p>}
    <nav className="admin-tabs" aria-label="Разделы администрации"><button type="button" aria-current={section === "sources" ? "page" : undefined} onClick={() => { setFeedback(""); setSection("sources") }}>Источники</button><button type="button" aria-current={section === "statistics" ? "page" : undefined} onClick={() => { setFeedback(""); setSection("statistics") }}>Статистика</button></nav>
    {section === "statistics" ? <section className="statistics-panel" aria-label="Статистика запросов">
      {statistics.isPending && <p role="status">Загружаем статистику запросов…</p>}
      {statistics.isError && <div className="empty-panel" role="alert"><h2>{statisticsUnavailable ? "Статистика недоступна" : "Не удалось загрузить статистику"}</h2><p>{statisticsUnavailable ? "Сервер пока не предоставляет агрегированные числа запросов по времени и использованию стартовых задач." : "Проверьте соединение и повторите запрос."}</p><button type="button" onClick={() => void statistics.refetch()}>Повторить</button></div>}
      {statistics.isSuccess && <><p>Число запросов за период {statistics.data.period_start} — {statistics.data.period_end}. Тексты запросов здесь не показываются.</p><div className="statistics-grid"><section><h2>Запросы по дням</h2>{statistics.data.daily_requests.length ? <ol className="statistics-list">{statistics.data.daily_requests.map((day) => <li key={day.date}><span>{day.date}</span><strong>{day.count}</strong></li>)}</ol> : <p>Запросов за период нет.</p>}</section><section><h2>Стартовые задачи</h2>{statistics.data.starter_requests.length ? <ol className="statistics-list">{statistics.data.starter_requests.map((starter) => <li key={starter.starter_id}><span>{starterLabel(starter.starter_id)}</span><strong>{starter.count}</strong></li>)}</ol> : <p>Стартовые задачи за период не использовались.</p>}</section></div></>}
    </section> : <>
    <p>Загрузите материал, проверьте его содержимое и права. После одобрения он станет доступен пользователям.</p>
    <form className="admin-form" onSubmit={submitUpload} aria-label="Загрузка кандидата">
      <h2>Загрузить PDF, TXT, CSV или XLSX</h2>
      <label>Оригинальный файл<input type="file" name="file" accept="application/pdf,.pdf,text/plain,.txt,text/csv,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,.xlsx" required /></label>
      <label>Ссылка на источник<input name="origin_url" type="url" required /></label>
      <label>Название<input name="title" required maxLength={500} /></label>
      <label>Краткое описание<textarea name="description" rows={2} maxLength={500} /></label>
      <label>Автор или организация<input name="creator" /></label>
      <label>Примечание о правах<input name="rights_note" /></label>
      <label>Метки, по одной в строке<textarea name="tag_entries" rows={3} maxLength={2200} placeholder={"region:Регион\nperiod:Период"} /></label>
      <button type="submit" disabled={upload.isPending}>Загрузить на проверку</button>
      {upload.isError && <p role="alert">Не удалось загрузить файл. Проверьте формат, размер и поля.</p>}
      {upload.isSuccess && <p role="status">Кандидат принят. Дождитесь обработки перед решением.</p>}
    </form>
    <form className="admin-filters" onSubmit={submitFilters} aria-label="Поиск в инвентаре">
      <label>Источник или название<input value={queryDraft} onChange={(event) => setQueryDraft(event.target.value)} maxLength={100} /></label>
      <label>Формат<select value={mediaType} onChange={(event) => { setMediaType(event.target.value as typeof mediaType); setRevisionId(null) }}><option value="">Все форматы</option><option value="application/pdf">PDF</option><option value="text/plain">TXT</option><option value="text/csv">CSV</option><option value="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet">XLSX</option></select></label>
      <label>Тип метки<select value={tagKind} onChange={(event) => { setTagKind(event.target.value as typeof tagKind); setRevisionId(null) }}><option value="">Любая метка</option><option value="region">Регион</option><option value="people">Народ</option><option value="period">Период</option><option value="topic">Тема</option><option value="sensitivity">Чувствительность</option></select></label>
      <label>Значение метки<input value={tagDraft} onChange={(event) => setTagDraft(event.target.value)} maxLength={100} /></label>
      <label>Обработка<select value={status} onChange={(event) => { setStatus(event.target.value as typeof status); setRevisionId(null) }}><option value="">Все статусы</option><option value="candidate">Кандидат</option><option value="processing">Обработка</option><option value="review_pending">Ожидает проверки</option><option value="failed">Ошибка</option></select></label>
      <label>Решение<select value={decision} onChange={(event) => { setDecision(event.target.value as typeof decision); setRevisionId(null) }}><option value="">Все решения</option><option value="approve">Одобрено</option><option value="revoke">Отозвано</option><option value="none">Без решения</option></select></label>
      <div className="admin-filter-actions"><button type="submit">Найти</button><button type="button" onClick={resetFilters}>Сбросить</button></div>
    </form>
    <p className="result-limit">Показаны первые 100 версий материалов по выбранным фильтрам.</p>
    {sources.isPending && <p role="status">Загружаем инвентарь…</p>}
    {sources.isError && <div role="alert"><p>Не удалось загрузить инвентарь.</p><button type="button" onClick={() => void sources.refetch()}>Повторить</button></div>}
    {sources.isSuccess && sources.data.length === 0 && <div className="empty-panel"><h2>Материалы не найдены</h2><p>Измените фильтры или загрузите новый материал.</p></div>}
    {sources.isSuccess && sources.data.length > 0 && <div className="materials-layout">
      <section aria-label="Список материалов"><h2>Материалы</h2><ul className="material-list">{sources.data.map((item) => <li key={item.revision_id}><button type="button" aria-current={revisionId === item.revision_id ? "true" : undefined} onClick={() => setRevisionId(item.revision_id)}><strong>{item.title}</strong><span>Обработка: {sourceStatusLabel(item.status)} · Решение: {decisionLabel(item.decision)}</span></button></li>)}</ul></section>
      <section aria-label="Детали ревизии" className="material-detail">
        {!revisionId && <p>Выберите ревизию для проверки статуса и фрагментов.</p>}
        {revisionId && revision.isPending && <p role="status">Загружаем ревизию…</p>}
        {revisionId && revision.isError && <div role="alert"><p>Не удалось загрузить ревизию.</p><button type="button" onClick={() => void revision.refetch()}>Повторить</button></div>}
        {revisionId && revision.isSuccess && <><h2>{revision.data.title}</h2><p><a href={`/api/v1/admin/revisions/${encodeURIComponent(revisionId)}/original`} target="_blank" rel="noopener noreferrer">Открыть оригинал для проверки</a></p><dl className="material-meta"><dt>Идентификатор версии</dt><dd>{revision.data.revision_id}</dd><dt>Идентификатор источника</dt><dd>{revision.data.source_id}</dd><dt>Происхождение</dt><dd><OriginReference value={revision.data.origin_url} /></dd><dt>Автор</dt><dd>{revision.data.creator || "Не указан"}</dd><dt>Формат</dt><dd>{formatLabel(revision.data.media_type)}</dd><dt>Описание</dt><dd>{revision.data.description || "Не добавлено"}</dd><dt>Обработка</dt><dd>{sourceStatusLabel(revision.data.status)}</dd><dt>Код ошибки</dt><dd>{revision.data.error_code || "Нет"}</dd><dt>Решение</dt><dd>{decisionLabel(revision.data.decision)}</dd><dt>Права</dt><dd>{revision.data.rights_usage_note || "Не подтверждены"}</dd><dt>Метки</dt><dd>{revision.data.tags.length ? revision.data.tags.map((tag) => `${tagLabel(tag.kind)}: ${tag.value}`).join(" · ") : "Не указаны"}</dd><dt>SHA-256</dt><dd>{revision.data.sha256}</dd></dl><h3>Фрагменты ({revision.data.segments.length})</h3><ol className="segment-list">{revision.data.segments.map((segment) => <li key={segment.segment_id}><strong>{sourceLocationLabel(segment.locator)}</strong><p>{segment.text}</p></li>)}</ol>
          {revision.data.status === "review_pending" && !revision.data.decision && <form key={`${revisionId}-metadata-${revision.data.metadata_version}`} className="admin-form" onSubmit={submitMetadata} aria-label="Правка метаданных"><h3>Уточнить описание и метки</h3><p>Сверьте их с оригиналом и извлечёнными фрагментами до одобрения. Каждая правка сохраняется в истории ревизии.</p><label>Краткое описание<textarea name="description" rows={3} maxLength={500} defaultValue={revision.data.description || ""} /></label><label>Метки, по одной в строке<textarea name="tag_entries" rows={4} maxLength={2200} defaultValue={revision.data.tags.map((tag) => `${tag.kind}:${tag.value}`).join("\n")} /></label><label>Причина изменения<textarea name="reason" required minLength={10} maxLength={2000} /></label><button type="submit" disabled={metadata.isPending}>Сохранить описание и метки</button>{metadata.isError && <div role="alert"><p>Правка не сохранена. Проверьте поля или обновите ревизию, если её уже изменили.</p><button type="button" onClick={() => { metadata.reset(); void revision.refetch(); void metadataHistory.refetch() }}>Обновить ревизию</button></div>}</form>}
          {revision.data.status === "review_pending" && !revision.data.decision && revision.data.segments.length > 0 && <form key={`${revisionId}-segments-${revision.data.segment_review_version}`} className="admin-form" onSubmit={submitSegmentReview} aria-label="Проверка фрагментов"><h3>Проверить фрагменты</h3><p>Отметьте ошибочные или неподходящие фрагменты. Они останутся в архиве администратора, но не попадут в поиск и ответы. Если исключён хотя бы один фрагмент, оригинальный файл нельзя открыть пользователю.</p>{revision.data.segments.map((segment) => <label key={segment.segment_id}><input type="checkbox" name="excluded_segment_id" value={segment.segment_id} defaultChecked={!segment.included} /> Исключить: {sourceLocationLabel(segment.locator)} — {segment.text.slice(0, 120)}</label>)}<label>Причина изменения<textarea name="reason" required minLength={10} maxLength={2000} /></label><button type="submit" disabled={segmentReview.isPending}>Сохранить исключения</button>{segmentReview.isError && <div role="alert"><p>Проверка не сохранена. Оставьте хотя бы один фрагмент и обновите ревизию, если её уже изменили.</p><button type="button" onClick={() => { segmentReview.reset(); void revision.refetch(); void segmentHistory.refetch() }}>Обновить ревизию</button></div>}</form>}
          {revision.data.segments.length > 0 && <details className="metadata-history"><summary>История фрагментов</summary>{segmentHistory.isPending && <p role="status">Загружаем историю фрагментов…</p>}{segmentHistory.isError && <p role="alert">Не удалось загрузить историю фрагментов.</p>}{segmentHistory.isSuccess && (segmentHistory.data.length ? <ol>{segmentHistory.data.map((event) => <li key={event.version}><strong>Версия {event.version}</strong> · {event.reason} · {event.reviewer_id}<p>Исключено: {event.excluded_segment_ids.length}</p></li>)}</ol> : <p>Изменений нет.</p>)}</details>}
          <details className="metadata-history"><summary>История метаданных</summary>{metadataHistory.isPending && <p role="status">Загружаем историю…</p>}{metadataHistory.isError && <p role="alert">Не удалось загрузить историю.</p>}{metadataHistory.isSuccess && <ol>{metadataHistory.data.map((event) => <li key={event.version}><strong>Версия {event.version}</strong> · {event.reason} · {event.reviewer_id}<p>{event.description || "Без описания"}</p><p>{event.tags.map((tag) => `${tagLabel(tag.kind)}: ${tag.value}`).join(" · ") || "Без меток"}</p></li>)}</ol>}</details>
          {revision.data.status === "failed" && <div className="admin-form"><button type="button" onClick={() => retry.mutate(revisionId)} disabled={retry.isPending}>Повторить обработку</button>{retry.isError && <p role="alert">Повтор обработки не запущен.</p>}</div>}
          {revision.data.status === "review_pending" && !revision.data.decision && <form className="admin-form" onSubmit={submitApproval} aria-label="Одобрение ревизии"><h3>Решение по точной ревизии</h3><p>Подтвердите права на каждый выбранный способ использования и проверку чувствительности. Ссылка должна вести на документальное основание решения.</p><label>Основание и ограничения<textarea name="reason" required minLength={10} /></label><label>HTTPS-ссылка на доказательство прав<input name="evidence_url" type="url" pattern="https://.*" required /></label><label><input name="user_text" type="checkbox" required /> Показ текстовых фрагментов пользователям разрешён</label><label><input name="sensitivity_cleared" type="checkbox" required /> Чувствительность материала проверена</label>{revision.data.segments.some((segment) => !segment.included) && <p>Оригинал содержит исключённые фрагменты и недоступен пользователю.</p>}<label><input name="original_file" type="checkbox" disabled={revision.data.segments.some((segment) => !segment.included)} /> Показ оригинального файла разрешён</label><label><input name="provider_transfer" type="checkbox" /> Передача внешнему провайдеру разрешена</label><button type="submit" disabled={approve.isPending}>Одобрить эту ревизию</button>{approve.isError && <p role="alert">Ревизия не одобрена. Проверьте основание и права.</p>}</form>}
          {revision.data.decision === "approve" && <form className="admin-form" onSubmit={submitRevocation} aria-label="Отзыв ревизии"><h3>Отозвать ревизию</h3><label>Причина отзыва<textarea name="reason" required minLength={10} /></label><button type="submit" disabled={revoke.isPending}>Отозвать эту ревизию</button>{revoke.isError && <p role="alert">Не удалось отозвать ревизию.</p>}</form>}
        </>}
      </section>
    </div>}
    </>}
  </main>
}
