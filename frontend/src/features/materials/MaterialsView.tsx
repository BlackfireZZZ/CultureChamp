import { useEffect, useRef, useState } from "react"

import { approvedPageUrl } from "../../api/materials"
import { useMaterial, useMaterials } from "./useMaterials"

export function MaterialsView({ onBack }: { onBack: () => void }) {
  const [revisionId, setRevisionId] = useState<string | null>(null)
  const list = useMaterials()
  const detail = useMaterial(revisionId)
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    if (detail.isSuccess && revisionId) headingRef.current?.focus()
  }, [detail.isSuccess, revisionId])

  function choose(id: string) {
    setRevisionId(id)
  }

  return <main className="simple-page materials-page">
    <p className="eyebrow">Материалы</p>
    <h1>Проверенные источники</h1>
    <p>Здесь видны только одобренные ревизии. Страница и текст каждого фрагмента относятся к указанной ревизии.</p>
    {list.isPending && <p role="status">Загружаем материалы…</p>}
    {list.isError && <div role="alert"><p>Не удалось загрузить материалы.</p><button type="button" onClick={() => void list.refetch()}>Повторить</button></div>}
    {list.isSuccess && list.data.length === 0 && <div className="empty-panel"><h2>Одобренных материалов пока нет</h2><p>Кандидатные PDF не показываются до проверки прав, контекста и точной ревизии.</p><button type="button" onClick={onBack}>Вернуться к чату</button></div>}
    {list.isSuccess && list.data.length > 0 && <div className="materials-layout">
      <section aria-label="Список одобренных материалов"><h2>Одобренные ревизии</h2><ul className="material-list">{list.data.map((item) => <li key={item.revision_id}><button type="button" aria-current={revisionId === item.revision_id ? "true" : undefined} onClick={() => choose(item.revision_id)}><strong>{item.title}</strong><span>{item.creator || "Автор не указан"}</span></button></li>)}</ul></section>
      <section aria-label="Точный источник" className="material-detail">
        {!revisionId && <p>Выберите материал, чтобы увидеть точную ревизию и страницы.</p>}
        {revisionId && detail.isPending && <p role="status">Загружаем источник…</p>}
        {revisionId && detail.isError && <div role="alert"><p>Источник сейчас недоступен. Возможно, ревизия была отозвана.</p><button type="button" onClick={() => void detail.refetch()}>Повторить</button></div>}
        {revisionId && detail.isSuccess && <>
          <h2 ref={headingRef} tabIndex={-1}>{detail.data.title}</h2>
          <dl className="material-meta"><dt>Ревизия</dt><dd>{detail.data.revision_id}</dd><dt>Автор</dt><dd>{detail.data.creator || "Не указан"}</dd><dt>Права и условия</dt><dd>{detail.data.rights_usage_note || "Не указаны"}</dd></dl>
          {!detail.data.original_available && <p>Оригинальный файл недоступен по условиям использования. Проверьте страницу и текст фрагмента ниже.</p>}
          {detail.data.segments.length === 0 ? <p>В этой ревизии нет доступных фрагментов.</p> : <ol className="segment-list">{detail.data.segments.map((segment) => {
            const sourceUrl = approvedPageUrl(detail.data.revision_id, segment.locator.page, detail.data.original_available)
            return <li key={segment.segment_id}><h3>Страница {segment.locator.page}</h3><p>{segment.text}</p>{sourceUrl && <a href={sourceUrl} target="_blank" rel="noopener noreferrer">Открыть страницу {segment.locator.page} в источнике</a>}</li>
          })}</ol>}
        </>}
      </section>
    </div>}
  </main>
}
