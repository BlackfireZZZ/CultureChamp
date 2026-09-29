import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "@fontsource/oswald/cyrillic-600.css"
import "@fontsource/oswald/latin-600.css"
import "@fontsource/noto-sans/cyrillic-400.css"
import "@fontsource/noto-sans/cyrillic-600.css"
import "@fontsource/noto-sans/latin-400.css"
import "@fontsource/noto-sans/latin-600.css"

import { App } from "./App"
import "./index.css"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={new QueryClient()}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
