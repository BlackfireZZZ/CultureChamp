import { useState } from "react"
import type { FormEvent } from "react"

import { ApiError } from "../../api/auth"

export function LoginScreen({ onSubmit, pending, error }: {
  onSubmit: (username: string, password: string) => void
  pending: boolean
  error: unknown
}) {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")

  function submit(event: FormEvent) {
    event.preventDefault()
    if (username.trim() && password) onSubmit(username.trim(), password)
  }

  let message = "Не удалось войти. Повторите попытку."
  if (error instanceof ApiError) {
    if (error.status === 401) message = "Неверные данные для входа."
    if (error.status === 429) message = "Слишком много попыток. Повторите позже."
    if (error.status === 503) message = "Вход временно недоступен. Повторите позже."
  }

  return <main className="login-page">
    <p className="eyebrow">Закрытый пилот</p>
    <h1>Войти в мастерскую</h1>
    <p>Для работы с чатом нужна учётная запись. Её создаёт администратор пилота.</p>
    <form onSubmit={submit}>
      <label htmlFor="username">Имя пользователя</label>
      <input id="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required />
      <label htmlFor="password">Пароль</label>
      <input id="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
      {error != null && <p role="alert">{message}</p>}
      {pending && <p role="status">Проверяем вход…</p>}
      <button type="submit" disabled={pending}>Войти</button>
    </form>
  </main>
}
