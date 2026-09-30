import { useQuery } from "@tanstack/react-query"
import { useState } from "react"

import { getAdminRevision, getAdminSources } from "../../api/admin"

export function AdminView({ onBack }: { onBack: () => void }) {
  const [revisionId, setRevisionId] = useState<string | null>(null)
  const sources = useQuery({ queryKey: ["admin", "sources"], queryFn: ({ signal }) => getAdminSources(signal), retry: false })
  const revision = useQuery({ queryKey: ["admin", "revision", revisionId], queryFn: ({ signal }) => getAdminRevision(revisionId!, signal), enabled: revisionId !== null, retry: false })

  return <main className="simple-page materials-page">
    <p className="eyebrow">Администрация · только просмотр</p>
    <h1>Кандидаты и ревизии</h1>
    <p>Статус обработки и решение по каждой ревизии приходят с сервера. Одобрение требует проверки прав, точности и чувствительности материала.</p>
    {sources.isPending && <p role="status">Загружаем инвентарь…</p>}
    {sources.isError && <div role="alert"><p>Не удалось загрузить инвентарь.</p><button type="button" onClick={() => void sources.refetch()}>Повторить</button></div>}
    {sources.isSuccess && sources.data.length === 0 && <div className="empty-panel"><h2>Источников пока нет</h2><p>Инвентарь появится после загрузки и обработки кандидатов.</p><button type="button" onClick={onBack}>Вернуться к чату</button></div>}
    {sources.isSuccess && sources.data.length > 0 && <div className="materials-layout">
      <section aria-label="Инвентарь кандидатов"><h2>Ревизии</h2><ul className="material-list">{sources.data.map((item) => <li key={item.revision_id}><button type="button" aria-current={revisionId === item.revision_id ? "true" : undefined} onClick={() => setRevisionId(item.revision_id)}><strong>{item.title}</strong><span>Обработка: {item.status} · Решение: {item.decision || "нет"}</span></button></li>)}</ul></section>
      <section aria-label="Детали ревизии" className="material-detail">
        {!revisionId && <p>Выберите ревизию для проверки статуса и страниц.</p>}
        {revisionId && revision.isPending && <p role="status">Загружаем ревизию…</p>}
        {revisionId && revision.isError && <div role="alert"><p>Не удалось загрузить ревизию.</p><button type="button" onClick={() => void revision.refetch()}>Повторить</button></div>}
        {revisionId && revision.isSuccess && <><h2>{revision.data.title}</h2><dl className="material-meta"><dt>Ревизия</dt><dd>{revision.data.revision_id}</dd><dt>Обработка</dt><dd>{revision.data.status}</dd><dt>Решение</dt><dd>{revision.data.decision || "Нет"}</dd><dt>Права</dt><dd>{revision.data.rights_usage_note || "Не подтверждены"}</dd><dt>SHA-256</dt><dd>{revision.data.sha256}</dd></dl><h3>Страницы ({revision.data.segments.length})</h3><ol className="segment-list">{revision.data.segments.map((segment) => <li key={segment.segment_id}><strong>Страница {segment.locator.page}</strong><p>{segment.text}</p></li>)}</ol></>}
      </section>
    </div>}
  </main>
}
