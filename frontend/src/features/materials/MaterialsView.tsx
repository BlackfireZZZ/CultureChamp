import { useEffect, useRef, useState } from "react"
import type { FormEvent } from "react"

import { approvedPageUrl } from "../../api/materials"
import type { MaterialFilters } from "../../api/materials"
import type { ChatCitation } from "../../api/chats"
import { useMaterial, useMaterials } from "./useMaterials"

export function MaterialsView({ onBack, citationTarget = null }: { onBack: () => void; citationTarget?: ChatCitation | null }) {
  const [revisionId, setRevisionId] = useState<string | null>(citationTarget?.revision_id ?? null)
  const [filters, setFilters] = useState<MaterialFilters>({})
  const list = useMaterials(filters)
  const detail = useMaterial(revisionId)
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    if (!detail.isSuccess || !revisionId) return
    if (citationTarget?.revision_id === revisionId) {
      document.getElementById(`segment-${citationTarget.segment_id}`)?.focus()
    } else headingRef.current?.focus()
  }, [detail.isSuccess, revisionId, citationTarget])

  function choose(id: string) {
    setRevisionId(id)
  }

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const value = (name: string) => {
      const entry = form.get(name)
      return typeof entry === "string" ? entry.trim() : ""
    }
    const mediaType = value("media_type")
    setFilters({
      q: value("q"), region: value("region"), people: value("people"),
      period: value("period"),
      media_type: mediaType === "application/pdf" || mediaType === "text/csv" ? mediaType : undefined,
    })
    setRevisionId(null)
  }

  const hasFilters = Object.values(filters).some(Boolean)

  return <main className="simple-page materials-page">
    <button type="button" onClick={onBack}>Вернуться к чату</button>
    <p className="eyebrow">Материалы</p>
    <h1>Проверенные источники</h1>
    <p>Здесь видны только одобренные ревизии. Локатор и текст каждого фрагмента относятся к указанной ревизии.</p>
    <form className="material-filters" onSubmit={applyFilters} aria-label="Поиск материалов">
      <label>Поиск по названию, автору или метке<input name="q" maxLength={100} /></label>
      <label>Регион<input name="region" maxLength={100} /></label>
      <label>Народ<input name="people" maxLength={100} /></label>
      <label>Период<input name="period" maxLength={100} /></label>
      <label>Тип документа<select name="media_type"><option value="">Все типы</option><option value="application/pdf">PDF</option><option value="text/csv">CSV</option></select></label>
      <div className="material-filter-actions"><button type="submit">Найти</button><button type="reset" onClick={() => { setFilters({}); setRevisionId(null) }}>Сбросить</button></div>
    </form>
    {list.isPending && <p role="status">Загружаем материалы…</p>}
    {list.isError && <div role="alert"><p>Не удалось загрузить материалы.</p><button type="button" onClick={() => void list.refetch()}>Повторить</button></div>}
    {list.isSuccess && list.data.length === 0 && <div className="empty-panel"><h2>{hasFilters ? "Материалов по запросу не найдено" : "Одобренных материалов пока нет"}</h2><p>{hasFilters ? "Уточните поиск или сбросьте фильтры." : "Кандидатные источники не показываются до проверки прав, контекста и точной ревизии."}</p><button type="button" onClick={onBack}>Вернуться к чату</button></div>}
    {list.isSuccess && list.data.length > 0 && <div className="materials-layout">
      <section aria-label="Список одобренных материалов"><h2>Одобренные ревизии</h2><ul className="material-list">{list.data.map((item) => <li key={item.revision_id}><button type="button" aria-current={revisionId === item.revision_id ? "true" : undefined} onClick={() => choose(item.revision_id)}><strong>{item.title}</strong><span>{item.creator || "Автор не указан"} · {item.media_type === "application/pdf" ? "PDF" : "CSV"}</span><span>{item.tags.map((tag) => tag.value).join(" · ") || "Без меток"}</span></button></li>)}</ul></section>
      <section aria-label="Точный источник" className="material-detail">
        {!revisionId && <p>Выберите материал, чтобы увидеть точную ревизию и фрагменты.</p>}
        {revisionId && detail.isPending && <p role="status">Загружаем источник…</p>}
        {revisionId && detail.isError && <div role="alert"><p>Источник сейчас недоступен. Возможно, ревизия была отозвана.</p><button type="button" onClick={() => void detail.refetch()}>Повторить</button></div>}
        {revisionId && detail.isSuccess && <>
          <h2 ref={headingRef} tabIndex={-1}>{detail.data.title}</h2>
          <dl className="material-meta"><dt>Ревизия</dt><dd>{detail.data.revision_id}</dd><dt>Автор</dt><dd>{detail.data.creator || "Не указан"}</dd><dt>Тип</dt><dd>{detail.data.media_type === "application/pdf" ? "PDF" : "CSV"}</dd><dt>Метки</dt><dd>{detail.data.tags.map((tag) => `${tag.kind}: ${tag.value}`).join(" · ") || "Не указаны"}</dd><dt>Права и условия</dt><dd>{detail.data.rights_usage_note || "Не указаны"}</dd></dl>
          {!detail.data.original_available && <p>Оригинальный файл недоступен по условиям использования. Проверьте страницу и текст фрагмента ниже.</p>}
          {detail.data.original_available && detail.data.media_type === "text/csv" && <a href={`/api/v1/materials/${encodeURIComponent(detail.data.revision_id)}/original`}>Скачать исходную таблицу CSV</a>}
          {detail.data.segments.length === 0 ? <p>В этой ревизии нет доступных фрагментов.</p> : <ol className="segment-list">{detail.data.segments.map((segment) => {
            const page = segment.locator.page
            const sourceUrl = page === null ? null : approvedPageUrl(detail.data.revision_id, page, detail.data.original_available)
            const location = segment.locator.kind === "table"
              ? `Таблица ${segment.locator.sheet || segment.locator.table || ""}, строка ${segment.locator.row_start}, столбец ${segment.locator.column_start}`
              : `Страница ${page}`
            return <li id={`segment-${segment.segment_id}`} tabIndex={-1} className={citationTarget?.segment_id === segment.segment_id ? "cited-segment" : undefined} key={segment.segment_id}><h3>{location}</h3><p>{segment.text}</p>{sourceUrl && <a href={sourceUrl} target="_blank" rel="noopener noreferrer">Открыть страницу {page} в источнике</a>}</li>
          })}</ol>}
        </>}
      </section>
    </div>}
  </main>
}
