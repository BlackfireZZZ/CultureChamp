import { useEffect, useMemo, useRef, useState } from "react"
import type { FormEvent } from "react"

import { approvedPageUrl } from "../../api/materials"
import type { MaterialFilters } from "../../api/materials"
import type { ChatCitation } from "../../api/chats"
import { useMaterial, useMaterials, useVisualSearch } from "./useMaterials"
import "./materials.css"

const xlsxMediaType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
const emptyCitations: readonly ChatCitation[] = []
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

export function MaterialsView({ onBack, citationTarget = null, citations = emptyCitations }: { onBack: () => void; citationTarget?: ChatCitation | null; citations?: readonly ChatCitation[] }) {
  const [revisionId, setRevisionId] = useState<string | null>(citationTarget?.revision_id ?? null)
  const [filters, setFilters] = useState<MaterialFilters>({})
  const [visualQuery, setVisualQuery] = useState("")
  const [activeMatch, setActiveMatch] = useState(0)
  const [searchMode, setSearchMode] = useState(false)
  const list = useMaterials(filters)
  const visuals = useVisualSearch(visualQuery)
  const detail = useMaterial(revisionId)
  const lastScrollKey = useRef("")
  const headingRef = useRef<HTMLHeadingElement>(null)
  const chatRevisionIds = useMemo(() => new Set([citationTarget?.revision_id, ...citations.map((item) => item.revision_id)].filter((id): id is string => Boolean(id))), [citationTarget, citations])
  const contextual = citationTarget !== null && !searchMode
  const visibleMaterials = list.isSuccess ? list.data.filter((item) => !contextual || chatRevisionIds.has(item.revision_id)) : []
  const matches = useMemo(() => detail.data?.segments.filter((segment) => citations.some((item) => item.available && item.revision_id === revisionId && item.segment_id === segment.segment_id) || citationTarget?.revision_id === revisionId && citationTarget.segment_id === segment.segment_id) ?? [], [citationTarget, citations, detail.data, revisionId])
  const matchIds = useMemo(() => new Set(matches.map((segment) => segment.segment_id)), [matches])

  useEffect(() => {
    if (!detail.isSuccess || !revisionId) return
    const firstIndex = citationTarget?.revision_id === revisionId ? Math.max(0, matches.findIndex((segment) => segment.segment_id === citationTarget.segment_id)) : 0
    const scrollKey = `${revisionId}:${citationTarget?.segment_id ?? ""}:${detail.dataUpdatedAt}`
    if (lastScrollKey.current === scrollKey) return
    lastScrollKey.current = scrollKey
    const timer = window.setTimeout(() => {
      setActiveMatch(firstIndex)
      if (matches[firstIndex]) {
        const target = document.getElementById(`segment-${matches[firstIndex].segment_id}`)
        target?.scrollIntoView?.({ behavior: "auto", block: "center" })
        target?.focus({ preventScroll: true })
      } else headingRef.current?.focus({ preventScroll: true })
    }, 0)
    return () => window.clearTimeout(timer)
  }, [detail.isSuccess, detail.dataUpdatedAt, revisionId, citationTarget, matches])

  function moveMatch(direction: -1 | 1) {
    if (!matches.length) return
    const next = Math.max(0, Math.min(matches.length - 1, activeMatch + direction))
    setActiveMatch(next)
    const target = document.getElementById(`segment-${matches[next].segment_id}`)
    target?.scrollIntoView?.({ behavior: window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" })
    target?.focus({ preventScroll: true })
  }

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
    const query = value("q")
    setFilters({
      q: query, region: value("region"), people: value("people"),
      period: value("period"),
      media_type: mediaType === "application/pdf" || mediaType === "text/plain" || mediaType === "text/csv" || mediaType === xlsxMediaType ? mediaType : undefined,
    })
    setVisualQuery(query.length >= 2 ? query : "")
    setSearchMode(true)
    setRevisionId(null)
  }

  const hasFilters = Object.values(filters).some(Boolean)
  const source = detail.data
  const originalUrl = source?.original_available ? `/api/v1/materials/${encodeURIComponent(source.revision_id)}/original` : null

  return <main className="simple-page materials-page">
    <div className="materials-intro"><button className="back-to-chat" type="button" onClick={onBack}>← К чату</button>
    <p className="eyebrow">Библиотека Лада</p>
    <h1>{contextual ? "Источники этого чата" : "Материалы"}</h1>
    <p>{contextual ? "Читайте документ целиком. Отмеченные места связаны с ответом." : "Ищите по теме, названию или описанию. Откройте материал и изучите его в контексте."}</p></div>
    <div className="materials-tools">
    <form className="material-filters" onSubmit={applyFilters} aria-label="Поиск материалов">
      <label className="material-search">Поиск материалов<input name="q" maxLength={100} placeholder="Название, автор или тема" /></label>
      <div className="material-filter-actions"><button type="submit">Найти</button><button type="reset" onClick={() => { setFilters({}); setVisualQuery(""); setSearchMode(false); setRevisionId(citationTarget?.revision_id ?? null) }}>Сбросить</button></div>
      <details className="advanced-filters"><summary>Дополнительные фильтры</summary><div className="advanced-filter-grid">
      <label>Регион<input name="region" maxLength={100} /></label>
      <label>Народ<input name="people" maxLength={100} /></label>
      <label>Период<input name="period" maxLength={100} /></label>
      <label>Тип документа<select name="media_type"><option value="">Все типы</option><option value="application/pdf">PDF</option><option value="text/plain">TXT</option><option value="text/csv">CSV</option><option value={xlsxMediaType}>XLSX</option></select></label>
      </div></details>
    </form>
    </div>
    {list.isPending && <p role="status">Загружаем материалы…</p>}
    {list.isError && <div role="alert"><p>Не удалось загрузить материалы.</p><button type="button" onClick={() => void list.refetch()}>Повторить</button></div>}
    {list.isSuccess && visibleMaterials.length === 0 && (!visualQuery || visuals.isSuccess && visuals.data.length === 0) && <div className="empty-panel"><h2>{hasFilters ? "Материалов по запросу не найдено" : contextual ? "Источники чата недоступны" : "Материалов пока нет"}</h2><p>{hasFilters ? "Попробуйте другое слово или сбросьте фильтры." : contextual ? "Возможно, источник был отозван." : "Источники появятся здесь после проверки и одобрения."}</p><button type="button" onClick={onBack}>Вернуться к чату</button></div>}
    {list.isSuccess && visibleMaterials.length > 0 && <div className="materials-layout">
      <aside className="material-catalogue" aria-label="Список материалов"><h2>{contextual ? "В ответе" : "Источники"}</h2><ul className="material-list">{visibleMaterials.map((item) => <li key={item.revision_id}><button type="button" aria-current={revisionId === item.revision_id ? "true" : undefined} onClick={() => choose(item.revision_id)}><strong>{item.title}</strong>{item.description && <span>{item.description}</span>}<span>{item.creator || "Автор не указан"}</span></button></li>)}</ul></aside>
      <section aria-label="Документ" className="material-detail">
        {!revisionId && <p className="material-placeholder">Выберите материал, чтобы прочитать его.</p>}
        {revisionId && detail.isPending && <p role="status">Загружаем документ…</p>}
        {revisionId && detail.isError && <div role="alert"><p>Источник сейчас недоступен. Возможно, ревизия была отозвана.</p><button type="button" onClick={() => void detail.refetch()}>Повторить</button></div>}
        {revisionId && detail.isSuccess && source && <>
          <div className="document-toolbar"><div className="document-heading"><p className="document-kicker">Документ{source.creator ? ` · ${source.creator}` : ""}</p><h2 ref={headingRef} tabIndex={-1}>{source.title}</h2></div><div className="document-actions">
            <details className="document-info"><summary aria-label="Сведения о документе" title="Сведения о документе"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></svg></summary><div className="document-info-popover"><h3>Сведения о документе</h3><dl><dt>Автор</dt><dd>{source.creator || "Не указан"}</dd><dt>Тип</dt><dd>{formatLabel(source.media_type)}</dd><dt>Происхождение</dt><dd>{safeOriginUrl(source.origin_url) ? <a href={safeOriginUrl(source.origin_url)!} target="_blank" rel="noopener noreferrer">Перейти к источнику</a> : "Не указано"}</dd><dt>Оригинал</dt><dd>{originalUrl ? "Доступен для скачивания" : "Не загружен"}</dd></dl></div></details>
            {originalUrl && <a className="document-icon-link" href={originalUrl} download title={`Скачать документ ${formatLabel(source.media_type)}`} aria-label={`Скачать исходн${source.media_type === "text/plain" ? "ый текст" : source.media_type === "text/csv" ? "ую таблицу" : source.media_type === xlsxMediaType ? "ую книгу" : "ый документ"} ${formatLabel(source.media_type)}`}><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v11m-4-4 4 4 4-4M4 17v3h16v-3" /></svg></a>}
          </div></div>
          {citationTarget?.revision_id === revisionId && !source.segments.some((segment) => segment.segment_id === citationTarget.segment_id) && <p role="alert">Цитируемый текст больше недоступен. Вы можете прочитать остальные доступные части документа.</p>}
          {matches.length > 0 && <nav className="document-match-nav" aria-label="Релевантные места"><span><strong>{activeMatch + 1} из {matches.length}</strong> {matches.length === 1 ? "отмеченного места" : "отмеченных мест"}</span><div><button type="button" aria-label="Предыдущее отмеченное место" title="Предыдущее отмеченное место" disabled={activeMatch === 0} onClick={() => moveMatch(-1)}>↑</button><button type="button" aria-label="Следующее отмеченное место" title="Следующее отмеченное место" disabled={activeMatch === matches.length - 1} onClick={() => moveMatch(1)}>↓</button></div></nav>}
          <article className="document-paper" aria-label={`Текст документа «${source.title}»`}>
            {source.segments.length === 0 ? <p>Текст документа сейчас недоступен.</p> : source.segments.map((segment) => {
              const marked = matchIds.has(segment.segment_id)
              const pageLink = segment.locator.page === null ? null : approvedPageUrl(source.revision_id, segment.locator.page, source.original_available)
              return <div className={`document-paragraph${marked ? " is-relevant" : ""}${matches[activeMatch]?.segment_id === segment.segment_id ? " is-current" : ""}`} id={`segment-${segment.segment_id}`} tabIndex={-1} key={segment.segment_id}><p>{marked ? <mark>{segment.text}</mark> : segment.text}</p>{pageLink && <a className="document-page-link" href={pageLink} target="_blank" rel="noopener noreferrer" aria-label={`Открыть страницу ${segment.locator.page} в источнике`} title={`Открыть страницу ${segment.locator.page} в источнике`}>↗</a>}</div>
            })}
          </article>
        </>}
      </section>
    </div>}
    {visualQuery && <section className="visual-results" aria-label="Совпадения на страницах">
      {visuals.isPending && <p role="status">Ищем совпадения на страницах…</p>}
      {visuals.isError && <div role="alert"><p>Часть результатов сейчас недоступна.</p><button type="button" onClick={() => void visuals.refetch()}>Повторить</button></div>}
      {visuals.isSuccess && visuals.data.length > 0 && <><h2>Также найдено на страницах</h2><p>Проверьте страницу и контекст источника перед использованием.</p><ol className="segment-list">{visuals.data.map((item) => <li key={item.image_id}><h3>{item.title} · страница {item.page}</h3><p>{item.creator || "Автор не указан"}</p><a href={approvedPageUrl(item.revision_id, item.page, true)!} target="_blank" rel="noopener noreferrer">Открыть страницу {item.page} в источнике</a></li>)}</ol></>}
    </section>}
  </main>
}
