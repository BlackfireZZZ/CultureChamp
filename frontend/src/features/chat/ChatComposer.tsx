import { useEffect, useRef, useState } from "react"
import type { FormEvent, KeyboardEvent } from "react"

type Recognition = {
  lang: string
  continuous: boolean
  interimResults: boolean
  onresult: ((event: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void) | null
  onerror: ((event: { error: string }) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
  abort: () => void
}

type RecognitionConstructor = new () => Recognition

function recognitionConstructor(): RecognitionConstructor | undefined {
  const browser = window as Window & { SpeechRecognition?: RecognitionConstructor; webkitSpeechRecognition?: RecognitionConstructor }
  return browser.SpeechRecognition ?? browser.webkitSpeechRecognition
}

export function ChatComposer({ value, onChange, onSubmit, pending, error, placeholder, inputRef, onKeyDown }: {
  value: string
  onChange: (value: string) => void
  onSubmit: (event: FormEvent) => void
  pending: boolean
  error: boolean
  placeholder: string
  inputRef: React.RefObject<HTMLTextAreaElement | null>
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void
}) {
  const recognitionRef = useRef<Recognition | null>(null)
  const valueRef = useRef(value)
  const [listening, setListening] = useState(false)
  const [voiceError, setVoiceError] = useState("")
  const voiceAvailable = Boolean(recognitionConstructor())

  useEffect(() => { valueRef.current = value }, [value])
  useEffect(() => () => recognitionRef.current?.abort(), [])

  function toggleVoice() {
    if (listening) { recognitionRef.current?.stop(); return }
    const Constructor = recognitionConstructor()
    if (!Constructor) return
    const recognition = new Constructor()
    recognition.lang = "ru-RU"
    recognition.continuous = true
    recognition.interimResults = false
    recognition.onresult = (event) => {
      const spoken = Array.from(event.results).slice(event.resultIndex).filter((result) => result.isFinal).map((result) => result[0].transcript.trim()).filter(Boolean).join(" ")
      if (spoken) {
        const next = `${valueRef.current.trim()} ${spoken}`.trim()
        valueRef.current = next
        onChange(next)
      }
    }
    recognition.onerror = (event) => {
      setVoiceError(event.error === "not-allowed" ? "Разрешите доступ к микрофону в браузере." : "Не удалось распознать речь. Попробуйте ещё раз.")
      setListening(false)
    }
    recognition.onend = () => { setListening(false); recognitionRef.current = null }
    recognitionRef.current = recognition
    setVoiceError("")
    try { recognition.start(); setListening(true) }
    catch { recognitionRef.current = null; setVoiceError("Не удалось включить микрофон.") }
  }

  return <form className="composer" onSubmit={onSubmit}>
    <label htmlFor="task">Ваша задача</label>
    <textarea id="task" ref={inputRef} value={value} onChange={(event) => onChange(event.target.value)} onKeyDown={onKeyDown} placeholder={placeholder} rows={1} />
    <div className="composer-actions"><span>Enter — отправить · Shift+Enter — новая строка</span><div className="composer-tools">
      <button className={`composer-icon voice-button ${listening ? "is-listening" : ""}`} type="button" aria-label={listening ? "Остановить голосовой ввод" : "Голосовой ввод"} aria-pressed={listening} title={voiceAvailable ? "Голосовой ввод через браузер" : "Голосовой ввод недоступен в этом браузере"} disabled={!voiceAvailable || pending} onClick={toggleVoice}><svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="2" width="6" height="13" rx="3"/><path d="M5 10a7 7 0 0 0 14 0M12 17v5m-4 0h8"/></svg></button>
      <button className="composer-icon send-button" type="submit" aria-label="Отправить" title="Отправить" disabled={!value.trim() || pending}><svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 19V5m-6 6 6-6 6 6"/></svg></button>
    </div></div>
    {listening && <p className="voice-status" role="status">Слушаю… Нажмите на микрофон, чтобы остановить.</p>}
    {voiceError && <p role="alert">{voiceError}</p>}
    {pending && <p role="status">Ищем источники и готовим ответ…</p>}
    {error && <p role="alert">Не удалось отправить задачу. Текст сохранён; повторите отправку.</p>}
  </form>
}
