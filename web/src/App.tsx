import { useEffect, useState } from "react"
import { Home } from "@/components/Home"
import { Dashboard } from "@/components/Dashboard"
import { Console } from "@/components/Console"
import { WaveBackground } from "@/components/WaveBackground"

type View = "home" | "dashboard" | "console"

function useTheme() {
  const [dark, setDark] = useState(false)
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark)
  }, [dark])
  return { dark, toggle: () => setDark((d) => !d) }
}

function App() {
  const [view, setView] = useState<View>("home")
  const { dark, toggle } = useTheme()

  const navLinkClass = (active: boolean) =>
    `cursor-pointer rounded-md px-3 py-1.5 text-sm font-medium transition-colors duration-150 ${
      active ? "bg-surface-selected text-ink" : "text-ink-muted hover:bg-surface-hover hover:text-ink"
    }`

  return (
    <div className="relative flex h-screen flex-col bg-canvas">
      {view !== "home" && (
        <WaveBackground
          ambient
          strokeColor="var(--accent)"
          className="opacity-[var(--wave-ambient-opacity)]"
        />
      )}

      <header className="relative z-10 flex h-16 shrink-0 flex-wrap items-center justify-between gap-3 border-b border-hairline bg-canvas-elevated px-6">
        <div className="flex flex-wrap items-center gap-6">
          <button
            onClick={() => setView("home")}
            className="cursor-pointer font-display text-lg font-bold tracking-tight text-ink"
          >
            Fraud Console
          </button>
          <nav className="flex items-center gap-1">
            <button onClick={() => setView("dashboard")} className={navLinkClass(view === "dashboard")}>
              Dashboard
            </button>
            <button onClick={() => setView("console")} className={navLinkClass(view === "console")}>
              Console
            </button>
          </nav>
        </div>
        <button
          onClick={toggle}
          aria-label="Toggle theme"
          className="cursor-pointer rounded-md px-3 py-1.5 text-sm font-medium text-ink-muted transition-colors duration-150 hover:bg-surface-hover hover:text-ink"
        >
          {dark ? "Light" : "Dark"}
        </button>
      </header>

      <div className="relative z-10 flex min-h-0 flex-1">
        {view === "home" && (
          <Home onEnterDashboard={() => setView("dashboard")} onEnterConsole={() => setView("console")} />
        )}
        {view === "dashboard" && <Dashboard />}
        {view === "console" && <Console />}
      </div>
    </div>
  )
}

export default App
