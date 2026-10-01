export function Embroidery({ variant }: { variant: "panel" | "band" }) {
  if (variant === "band") return <svg className="embroidery embroidery-band" viewBox="0 0 360 70" aria-hidden="true" focusable="false">
    <path className="thread-muted" d="M0 6H360M0 64H360" />
    <path className="thread-main" d="M0 18h20l8 9 8-9h84l8 9 8-9h88l8 9 8-9h84l8 9 8-9h20M0 52h20l8-9 8 9h84l8-9 8 9h88l8-9 8 9h84l8-9 8 9h20" />
    {[72, 180, 288].map((x) => <g key={x}><path className="thread-strong" d={`M${x} 55V24M${x} 40l-19-13 3 14zM${x} 46l19-13-3 14z`} /><path className="thread-main" d={`M${x} 13l12 11-12 11-12-11zM${x} 17l8 7-8 7-8-7z`} /><path className="thread-muted" d={`M${x - 16} 48l5 5m0-5l-5 5m32-5l-5 5m0-5l5 5`} /></g>)}
    {[18, 126, 234, 342].map((x) => <path key={x} className="thread-strong" d={`M${x} 30l5 5-5 5-5-5zM${x} 28v14`} />)}
  </svg>

  return <svg className="embroidery embroidery-panel" viewBox="0 0 190 420" aria-hidden="true" focusable="false">
    <path className="thread-muted" d="M7 0v420M183 0v420M14 0v420M176 0v420" />
    <path className="thread-main" d="M22 0v25l9 9-9 9v25l9 9-9 9v25l9 9-9 9v25l9 9-9 9v25l9 9-9 9v25l9 9-9 9v25l9 9-9 9v25l9 9-9 9v25l9 9-9 9v25M168 0v25l-9 9 9 9v25l-9 9 9 9v25l-9 9 9 9v25l-9 9 9 9v25l-9 9 9 9v25l-9 9 9 9v25l-9 9 9 9v25l-9 9 9 9v25" />
    <path className="thread-strong" d="M95 397C94 336 67 311 74 269c7-36 52-35 43-78-8-35-44-44-38-81 5-28 30-48 16-90" />
    <path className="thread-main" d="M75 292c-29-7-36-24-39-45 25 2 39 13 39 45zm10-37c25-9 40-27 42-50-28 8-41 25-42 50zm-2-116c-25-8-37-23-40-47 27 7 39 20 40 47zm19-40c24-9 38-24 42-48-27 6-40 21-42 48z" />
    <path className="thread-strong" d="M54 253l8 8m-8-1l8 8m-8-1l8 8m42-43l8-8m-8 16l8-8m-8 16l8-8M62 106l8 8m-8-1l8 8m42-47l8-8m-8 16l8-8" />
    <path className="thread-main" d="M95 17l16 16-16 16-16-16zM95 22l11 11-11 11-11-11zM95 157l20 20-20 20-20-20zM95 163l14 14-14 14-14-14zM95 327l25 25-25 25-25-25zM95 334l18 18-18 18-18-18z" />
    <path className="thread-strong" d="M95 5v14M95 48v14M67 33h14M109 33h14M95 140v17M95 197v17M59 177h16M115 177h16M95 308v19M95 377v19M51 352h19M120 352h19" />
    <path className="thread-muted" d="M45 24l7 7m0-7l-7 7m93-7l7 7m0-7l-7 7M43 171l7 7m0-7l-7 7m97-7l7 7m0-7l-7 7M40 350l7 7m0-7l-7 7m103-7l7 7m0-7l-7 7" />
    <path className="thread-main" d="M30 410h130M43 402l8 8-8 8m25-16l8 8-8 8m25-16l8 8-8 8m25-16l8 8-8 8" />
  </svg>
}
