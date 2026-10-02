import { useCallback, useEffect, useRef, useState } from "react"
import type { FormEvent } from "react"

import { approvedPageUrl } from "../../api/materials"
import { sourceLocationLabel } from "../../api/locators"
import type { MaterialFilters } from "../../api/materials"
import type { ChatCitation } from "../../api/chats"
import { useMaterial, useMaterials, useVisualSearch } from "./useMaterials"

const xlsxMediaType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
function safeOriginUrl(value: string): string | null {
  try {
    const url = new URL(value)
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : null
  } catch { return null }
}
const formatLabel = (mediaType: string) => {
  if (mediaType === "application/pdf") return "PDF"
  if (mediaType === "text/plain") return "TXT"
  if (mediaType === "text/csv") return "CSV"
  if (mediaType === xlsxMediaType) return "XLSX"
  return mediaType
}

export function MaterialsView({ onBack, citationTarget = null }: { onBack: () => void; citationTarget?: ChatCitation | null }) {
  const [revisionId, setRevisionId] = useState<string | null>(citationTarget?.revision_id ?? null)
  const [filters, setFilters] = useState<MaterialFilters>({})
  const [visualDraft, setVisualDraft] = useState("")
  const [visualQuery, setVisualQuery] = useState("")
  const list = useMaterials(filters)
  const visuals = useVisualSearch(visualQuery)
  const detail = useMaterial(revisionId)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const citedSegmentRef = useCallback((node: HTMLLIElement | null) => {
    if (node) window.requestAnimationFrame(() => { if (node.isConnected) node.focus() })
  }, [])

  useEffect(() => {
    if (!detail.isSuccess || !revisionId) return
    const timer = window.setTimeout(() => {
      if (citationTarget?.revision_id === revisionId) {
        const segment = document.getElementById(`segment-${citationTarget.segment_id}`)
        if (segment) segment.focus()
        else headingRef.current?.focus()
      } else headingRef.current?.focus()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [detail.isSuccess, detail.dataUpdatedAt, revisionId, citationTarget])

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
      media_type: mediaType === "application/pdf" || mediaType === "text/plain" || mediaType === "text/csv" || mediaType === xlsxMediaType ? mediaType : undefined,
    })
    setRevisionId(null)
  }

  const hasFilters = Object.values(filters).some(Boolean)

  return <main className="simple-page materials-page">
    <div className="materials-intro"><button className="back-to-chat" type="button" onClick={onBack}>← К чату</button>
    <p className="eyebrow">Библиотека Лада</p>
    <h1>Материалы</h1>
    <p>Найдите источник и откройте его фрагменты. Здесь показаны проверенные материалы.</p></div>
    <div className="materials-tools">
    <form className="material-filters" onSubmit={applyFilters} aria-label="Поиск материалов">
      <label className="material-search">Поиск материалов<input name="q" maxLength={100} placeholder="Название, автор или тема" /></label>
      <div className="material-filter-actions"><button type="submit">Найти</button><button type="reset" onClick={() => { setFilters({}); setRevisionId(null) }}>Сбросить</button></div>
      <details className="advanced-filters"><summary>Дополнительные фильтры</summary><div className="advanced-filter-grid">
      <label>Регион<input name="region" maxLength={100} /></label>
      <label>Народ<input name="people" maxLength={100} /></label>
      <label>Период<input name="period" maxLength={100} /></label>
      <label>Тип документа<select name="media_type"><option value="">Все типы</option><option value="application/pdf">PDF</option><option value="text/plain">TXT</option><option value="text/csv">CSV</option><option value={xlsxMediaType}>XLSX</option></select></label>
      </div></details>
    </form>
    <details className="visual-search"><summary>Поиск по изображениям PDF</summary>
    <form className="material-filters" onSubmit={(event) => { event.preventDefault(); setVisualQuery(visualDraft.trim()) }} aria-label="Поиск по изображениям PDF">
      <label>Описание изображения<input value={visualDraft} onChange={(event) => setVisualDraft(event.target.value)} minLength={2} maxLength={200} placeholder="Например: красный круг и синие полосы" /></label>
      <div className="material-filter-actions"><button type="submit" disabled={visualDraft.trim().length < 2}>Найти изображения</button></div>
    </form>
    </details></div>
    {visualQuery && <section aria-label="Найденные изображения">
      <h2>Совпадения по изображению</h2>
      <p>Экспериментальный поиск: совпадение изображения не подтверждает культурный факт. Проверьте страницу и контекст оригинала.</p>
      {visuals.isPending && <p role="status">Ищем изображения…</p>}
      {visuals.isError && <div role="alert"><p>Поиск изображений сейчас недоступен.</p><button type="button" onClick={() => void visuals.refetch()}>Повторить</button></div>}
      {visuals.isSuccess && visuals.data.length === 0 && <p>Изображений по запросу не найдено.</p>}
      {visuals.isSuccess && visuals.data.length > 0 && <ol className="segment-list">{visuals.data.map((item) => <li key={item.image_id}><h3>{item.title} · страница {item.page}</h3><p>{item.creator || "Автор не указан"}</p><a href={approvedPageUrl(item.revision_id, item.page, true)!} target="_blank" rel="noopener noreferrer">Открыть страницу {item.page} в одобренном PDF</a></li>)}</ol>}
    </section>}
    {list.isPending && <p role="status">Загружаем материалы…</p>}
    {list.isError && <div role="alert"><p>Не удалось загрузить материалы.</p><button type="button" onClick={() => void list.refetch()}>Повторить</button></div>}
    {list.isSuccess && list.data.length === 0 && <div className="empty-panel"><h2>{hasFilters ? "Материалов по запросу не найдено" : "Материалов пока нет"}</h2><p>{hasFilters ? "Попробуйте другое слово или сбросьте фильтры." : "Источники появятся здесь после проверки и одобрения."}</p><button type="button" onClick={onBack}>Вернуться к чату</button></div>}
    {list.isSuccess && list.data.length > 0 && <div className="materials-layout">
      <section aria-label="Список одобренных материалов"><h2>Одобренные ревизии</h2><ul className="material-list">{list.data.map((item) => <li key={item.revision_id}><button type="button" aria-current={revisionId === item.revision_id ? "true" : undefined} onClick={() => choose(item.revision_id)}><strong>{item.title}</strong>{item.description && <span>{item.description}</span>}<span>{item.creator || "Автор не указан"} · {formatLabel(item.media_type)}</span><span>{item.tags.map((tag) => tag.value).join(" · ") || "Без меток"}</span></button></li>)}</ul></section>
      <section aria-label="Точный источник" className="material-detail">
        {!revisionId && <p>Выберите материал, чтобы увидеть точную ревизию и фрагменты.</p>}
        {revisionId && detail.isPending && <p role="status">Загружаем источник…</p>}
        {revisionId && detail.isError && <div role="alert"><p>Источник сейчас недоступен. Возможно, ревизия была отозвана.</p><button type="button" onClick={() => void detail.refetch()}>Повторить</button></div>}
        {revisionId && detail.isSuccess && <>
          <h2 ref={headingRef} tabIndex={-1}>{detail.data.title}</h2>
          {citationTarget?.revision_id === revisionId && !detail.data.segments.some((segment) => segment.segment_id === citationTarget.segment_id) && <p role="alert">Цитируемый фрагмент больше недоступен в этой ревизии. Откройте другой доступный фрагмент или вернитесь к чату.</p>}
          {detail.data.description && <p>{detail.data.description}</p>}
          <dl className="material-meta"><dt>Ревизия</dt><dd>{detail.data.revision_id}</dd><dt>Автор</dt><dd>{detail.data.creator || "Не указан"}</dd><dt>Происхождение</dt><dd>{safeOriginUrl(detail.data.origin_url) ? <a href={safeOriginUrl(detail.data.origin_url)!} target="_blank" rel="noopener noreferrer">Ссылка на источник</a> : "Не указано"}</dd><dt>Тип</dt><dd>{formatLabel(detail.data.media_type)}</dd><dt>Метки</dt><dd>{detail.data.tags.map((tag) => `${tag.kind}: ${tag.value}`).join(" · ") || "Не указаны"}</dd><dt>Права и условия</dt><dd>{detail.data.rights_usage_note || "Не указаны"}</dd></dl>
          {!detail.data.original_available && <p>Оригинальный файл недоступен по условиям использования. Проверьте страницу и текст фрагмента ниже.</p>}
          {detail.data.original_available && detail.data.media_type === "text/csv" && <a href={`/api/v1/materials/${encodeURIComponent(detail.data.revision_id)}/original`}>Скачать исходную таблицу CSV</a>}
          {detail.data.original_available && detail.data.media_type === "text/plain" && <a href={`/api/v1/materials/${encodeURIComponent(detail.data.revision_id)}/original`}>Скачать исходный текст TXT</a>}
          {detail.data.original_available && detail.data.media_type === xlsxMediaType && <a href={`/api/v1/materials/${encodeURIComponent(detail.data.revision_id)}/original`}>Скачать исходную книгу XLSX</a>}
          {detail.data.segments.length === 0 ? <p>В этой ревизии нет доступных фрагментов.</p> : <ol className="segment-list">{detail.data.segments.map((segment) => {
            const page = segment.locator.page
            const sourceUrl = page === null ? null : approvedPageUrl(detail.data.revision_id, page, detail.data.original_available)
            const location = sourceLocationLabel(segment.locator)
            return <li id={`segment-${segment.segment_id}`} tabIndex={-1} ref={citationTarget?.segment_id === segment.segment_id ? citedSegmentRef : undefined} className={citationTarget?.segment_id === segment.segment_id ? "cited-segment" : undefined} key={segment.segment_id}><h3>{location}</h3><p>{segment.text}</p>{sourceUrl && <a href={sourceUrl} target="_blank" rel="noopener noreferrer">Открыть страницу {page} в источнике</a>}</li>
          })}</ol>}
        </>}
      </section>
    </div>}
  </main>
}
