import { useQuery } from "@tanstack/react-query"
import { useState } from "react"

import { getHealth } from "./api/health"

export function App() {
  const health = useQuery({ queryKey: ["health"], queryFn: ({ signal }) => getHealth(signal) })
  const [theme, setTheme] = useState<"light" | "dark">(
    document.documentElement.dataset.theme === "dark" ? "dark" : "light",
  )

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark"
    document.documentElement.dataset.theme = next
    try { localStorage.setItem("culturechamp-theme", next) } catch { /* Storage may be disabled. */ }
    setTheme(next)
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <span className="wordmark">CultureChamp</span>
        <button className="theme-toggle" type="button" onClick={toggleTheme}>
          {theme === "dark" ? "Светлая тема" : "Тёмная тема"}
        </button>
      </header>
      <main className="shell">
        <svg className="stitch-trim" viewBox="0 0 112 16" aria-hidden="true" focusable="false">
          <path d="M4 4l8 8m0-8l-8 8m16-8l8 8m0-8l-8 8m16-8l8 8m0-8l-8 8m16-8l8 8m0-8l-8 8m16-8l8 8m0-8l-8 8m16-8l8 8m0-8l-8 8m16-8l8 8m0-8l-8 8" />
        </svg>
        <p className="eyebrow">Новая глава</p>
        <h1>Новая концепция<br />в работе</h1>
        <p className="intro">Техническая основа готова. Продуктовые разделы появятся после утверждения концепции.</p>
        <p role="status" className="status">
          {health.isPending && "Проверяем API…"}
          {health.isError && "API недоступен"}
          {health.isSuccess && "API работает"}
        </p>
      </main>
    </div>
  )
}
