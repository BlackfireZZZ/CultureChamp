import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import type { FormEvent } from "react"

import { approveAdminRevision, getAdminRevision, getAdminSources, retryAdminRevision, revokeAdminRevision, uploadAdminSource } from "../../api/admin"
import type { AdminFilters } from "../../api/admin"

function textField(form: FormData, name: string): string {
  const value = form.get(name)
  return typeof value === "string" ? value : ""
}

export function AdminView({ csrfToken }: { csrfToken: string }) {
  const client = useQueryClient()
  const [revisionId, setRevisionId] = useState<string | null>(null)
  const [status, setStatus] = useState<NonNullable<AdminFilters["status"]> | "">("")
  const [decision, setDecision] = useState<NonNullable<AdminFilters["decision"]> | "">("")
  const filters: AdminFilters = { status: status || undefined, decision: decision || undefined, limit: 100 }
  const sources = useQuery({ queryKey: ["admin", "sources", status, decision], queryFn: ({ signal }) => getAdminSources(filters, signal), retry: false })
  const revision = useQuery({ queryKey: ["admin", "revision", revisionId], queryFn: ({ signal }) => getAdminRevision(revisionId!, signal), enabled: revisionId !== null, retry: false })
  const refresh = async () => client.invalidateQueries({ queryKey: ["admin"] })
  const upload = useMutation({ mutationFn: (form: FormData) => uploadAdminSource(form, csrfToken), onSuccess: async (value) => { setRevisionId(value.revision_id); await refresh() } })
  const approve = useMutation({ mutationFn: ({ id, data }: { id: string; data: { reason: string; evidence_url: string; user_text: boolean; original_file: boolean; provider_transfer: boolean; sensitivity_cleared: boolean } }) => approveAdminRevision(id, data, csrfToken), onSuccess: refresh })
  const revoke = useMutation({ mutationFn: ({ id, reason }: { id: string; reason: string }) => revokeAdminRevision(id, reason, csrfToken), onSuccess: refresh })
  const retry = useMutation({ mutationFn: (id: string) => retryAdminRevision(id, csrfToken), onSuccess: refresh })

  function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    upload.mutate(new FormData(event.currentTarget))
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

  return <main className="simple-page materials-page">
    <p className="eyebrow">Администрация · проверка источников</p>
    <h1>Кандидаты и ревизии</h1>
    <p>Загружайте кандидаты, проверяйте извлечение и права точной ревизии. Только явное одобрение делает материал доступным пользователям.</p>
    <form className="admin-form" onSubmit={submitUpload} aria-label="Загрузка кандидата">
      <h2>Загрузить PDF-кандидат</h2>
      <label>Оригинальный файл<input type="file" name="file" accept="application/pdf,.pdf" required /></label>
      <label>Ссылка на источник<input name="origin_url" type="url" required /></label>
      <label>Название<input name="title" required maxLength={500} /></label>
      <label>Автор или организация<input name="creator" /></label>
      <label>Примечание о правах<input name="rights_note" /></label>
      <button type="submit" disabled={upload.isPending}>Загрузить на проверку</button>
      {upload.isError && <p role="alert">Не удалось загрузить файл. Проверьте формат, размер и поля.</p>}
      {upload.isSuccess && <p role="status">Кандидат принят. Дождитесь обработки перед решением.</p>}
    </form>
    <div className="admin-filters"><label>Обработка<select value={status} onChange={(event) => { setStatus(event.target.value as typeof status); setRevisionId(null) }}><option value="">Все статусы</option><option value="candidate">Кандидат</option><option value="processing">Обработка</option><option value="review_pending">Ожидает проверки</option><option value="failed">Ошибка</option></select></label><label>Решение<select value={decision} onChange={(event) => { setDecision(event.target.value as typeof decision); setRevisionId(null) }}><option value="">Все решения</option><option value="approve">Одобрено</option><option value="revoke">Отозвано</option><option value="none">Без решения</option></select></label></div>
    <p className="result-limit">Показаны первые 100 ревизий по выбранным фильтрам.</p>
    {sources.isPending && <p role="status">Загружаем инвентарь…</p>}
    {sources.isError && <div role="alert"><p>Не удалось загрузить инвентарь.</p><button type="button" onClick={() => void sources.refetch()}>Повторить</button></div>}
    {sources.isSuccess && sources.data.length === 0 && <div className="empty-panel"><h2>Ревизий не найдено</h2><p>Измените фильтры или загрузите кандидат.</p></div>}
    {sources.isSuccess && sources.data.length > 0 && <div className="materials-layout">
      <section aria-label="Инвентарь кандидатов"><h2>Ревизии</h2><ul className="material-list">{sources.data.map((item) => <li key={item.revision_id}><button type="button" aria-current={revisionId === item.revision_id ? "true" : undefined} onClick={() => setRevisionId(item.revision_id)}><strong>{item.title}</strong><span>Обработка: {item.status} · Решение: {item.decision || "нет"}</span></button></li>)}</ul></section>
      <section aria-label="Детали ревизии" className="material-detail">
        {!revisionId && <p>Выберите ревизию для проверки статуса и страниц.</p>}
        {revisionId && revision.isPending && <p role="status">Загружаем ревизию…</p>}
        {revisionId && revision.isError && <div role="alert"><p>Не удалось загрузить ревизию.</p><button type="button" onClick={() => void revision.refetch()}>Повторить</button></div>}
        {revisionId && revision.isSuccess && <><h2>{revision.data.title}</h2><dl className="material-meta"><dt>Ревизия</dt><dd>{revision.data.revision_id}</dd><dt>Обработка</dt><dd>{revision.data.status}</dd><dt>Ошибка</dt><dd>{revision.data.error_code || "Нет"}</dd><dt>Решение</dt><dd>{revision.data.decision || "Нет"}</dd><dt>Права</dt><dd>{revision.data.rights_usage_note || "Не подтверждены"}</dd><dt>Метки</dt><dd>{revision.data.tags.length ? revision.data.tags.map((tag) => `${tag.kind}: ${tag.value}`).join(" · ") : "Не указаны"}</dd><dt>SHA-256</dt><dd>{revision.data.sha256}</dd></dl><h3>Фрагменты ({revision.data.segments.length})</h3><ol className="segment-list">{revision.data.segments.map((segment) => <li key={segment.segment_id}><strong>Страница {segment.locator.page}</strong><p>{segment.text}</p></li>)}</ol>
          {revision.data.status === "failed" && <div className="admin-form"><button type="button" onClick={() => retry.mutate(revisionId)} disabled={retry.isPending}>Повторить обработку</button>{retry.isError && <p role="alert">Повтор обработки не запущен.</p>}</div>}
          {revision.data.status === "review_pending" && !revision.data.decision && <form className="admin-form" onSubmit={submitApproval} aria-label="Одобрение ревизии"><h3>Решение по точной ревизии</h3><p>Подтвердите права на каждый выбранный способ использования и проверку чувствительности. Ссылка должна вести на документальное основание решения.</p><label>Основание и ограничения<textarea name="reason" required minLength={10} /></label><label>HTTPS-ссылка на доказательство прав<input name="evidence_url" type="url" pattern="https://.*" required /></label><label><input name="user_text" type="checkbox" required /> Показ текстовых фрагментов пользователям разрешён</label><label><input name="sensitivity_cleared" type="checkbox" required /> Чувствительность материала проверена</label><label><input name="original_file" type="checkbox" /> Показ оригинального файла разрешён</label><label><input name="provider_transfer" type="checkbox" /> Передача внешнему провайдеру разрешена</label><button type="submit" disabled={approve.isPending}>Одобрить эту ревизию</button>{approve.isError && <p role="alert">Ревизия не одобрена. Проверьте основание и права.</p>}</form>}
          {revision.data.decision === "approve" && <form className="admin-form" onSubmit={submitRevocation} aria-label="Отзыв ревизии"><h3>Отозвать ревизию</h3><label>Причина отзыва<textarea name="reason" required minLength={10} /></label><button type="submit" disabled={revoke.isPending}>Отозвать эту ревизию</button>{revoke.isError && <p role="alert">Не удалось отозвать ревизию.</p>}</form>}
        </>}
      </section>
    </div>}
  </main>
}
