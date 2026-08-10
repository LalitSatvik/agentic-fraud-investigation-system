import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import type { Investigation } from "@/lib/types"
import { QueueList } from "@/components/QueueList"
import { CaseFile } from "@/components/CaseFile"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

function useTheme() {
  const [light, setLight] = useState(false)
  useEffect(() => {
    document.documentElement.classList.toggle("light", light)
  }, [light])
  return { light, toggle: () => setLight((l) => !l) }
}

function App() {
  const [investigations, setInvestigations] = useState<Investigation[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [newTxnId, setNewTxnId] = useState("")
  const [launching, setLaunching] = useState(false)
  const [launchError, setLaunchError] = useState<string | null>(null)

  const { light, toggle } = useTheme()

  const loadQueue = () => {
    setLoading(true)
    api
      .listFlagged()
      .then((data) => {
        setInvestigations((prev) => {
          // keep any already-decided investigation currently open in view, so a
          // reviewer's just-submitted decision doesn't vanish from under them
          const openButDecided = prev.find((p) => p.id === selectedId && p.status !== "pending_review")
          return openButDecided ? [...data, openButDecided] : data
        })
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load queue"))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadQueue()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const selected = investigations.find((i) => i.id === selectedId) ?? null

  const handleLaunch = async () => {
    const txnId = newTxnId.trim()
    if (!txnId) return
    setLaunching(true)
    setLaunchError(null)
    try {
      const inv = await api.runInvestigation(txnId)
      setInvestigations((prev) => [inv, ...prev.filter((p) => p.id !== inv.id)])
      setSelectedId(inv.id)
      setNewTxnId("")
    } catch (e) {
      setLaunchError(e instanceof Error ? e.message : "Investigation failed")
    } finally {
      setLaunching(false)
    }
  }

  return (
    <div className="h-screen flex flex-col bg-canvas">
      <header className="flex items-center justify-between gap-4 px-5 h-14 border-b border-hairline bg-canvas-elevated shrink-0">
        <h1 className="font-mono text-sm uppercase tracking-[0.15em] text-ink">
          Fraud Investigation Console
        </h1>
        <div className="flex items-center gap-2">
          <Input
            value={newTxnId}
            onChange={(e) => setNewTxnId(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLaunch()}
            placeholder="TXN123456"
            className="w-36 h-8 text-xs"
          />
          <Button size="sm" variant="outline" onClick={handleLaunch} disabled={launching}>
            {launching ? "Investigating…" : "Investigate"}
          </Button>
          <Button size="sm" variant="ghost" onClick={toggle} aria-label="Toggle theme">
            {light ? "Dark" : "Light"}
          </Button>
        </div>
      </header>

      {launchError && (
        <div className="px-5 py-2 bg-sev-high-bg border-b border-hairline">
          <p className="font-sans text-xs text-sev-high">{launchError}</p>
        </div>
      )}

      <div className="flex flex-1 min-h-0">
        <aside className="w-72 shrink-0 border-r border-hairline overflow-y-auto">
          <div className="px-4 py-3 border-b border-hairline flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-widest text-ink-muted">
              Queue
              {investigations.filter((i) => i.status === "pending_review").length > 0 &&
                ` (${investigations.filter((i) => i.status === "pending_review").length})`}
            </span>
            <button
              onClick={loadQueue}
              className="text-xs font-mono text-ink-faint hover:text-ink-muted cursor-pointer transition-colors duration-150"
            >
              refresh
            </button>
          </div>
          {loading ? (
            <p className="px-5 py-6 text-sm font-serif text-ink-faint">Loading queue…</p>
          ) : error ? (
            <p className="px-5 py-6 text-sm font-sans text-sev-high">{error}</p>
          ) : (
            <QueueList
              investigations={investigations.filter((i) => i.status === "pending_review")}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          )}
        </aside>

        <main className="flex-1 overflow-y-auto">
          {selected ? (
            <CaseFile
              investigation={selected}
              onDecided={(updated) => {
                setInvestigations((prev) => prev.map((i) => (i.id === updated.id ? updated : i)))
              }}
            />
          ) : (
            <div className="h-full flex items-center justify-center px-8">
              <p className="font-serif text-ink-faint text-center max-w-sm leading-relaxed">
                Select a case from the queue to begin your review, or investigate a specific
                transaction using the box above.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

export default App
