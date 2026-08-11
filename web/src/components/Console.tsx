import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { api } from "@/lib/api"
import type { Investigation } from "@/lib/types"
import { QueueList } from "@/components/QueueList"
import { CaseFile } from "@/components/CaseFile"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export function Console() {
  const [investigations, setInvestigations] = useState<Investigation[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [newTxnId, setNewTxnId] = useState("")
  const [launching, setLaunching] = useState(false)
  const [launchError, setLaunchError] = useState<string | null>(null)

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
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-hairline px-6">
        <span className="font-display text-lg font-semibold text-ink">Console</span>
        <div className="flex items-center gap-2">
          <Input
            value={newTxnId}
            onChange={(e) => setNewTxnId(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLaunch()}
            placeholder="TXN123456"
            className="h-9 w-40 font-mono text-xs"
          />
          <Button size="sm" variant="outline" onClick={handleLaunch} disabled={launching}>
            {launching ? "Investigating…" : "Investigate"}
          </Button>
        </div>
      </div>

      {launchError && (
        <div className="border-b border-hairline bg-sev-high-bg px-6 py-2.5">
          <p className="text-xs text-sev-high">{launchError}</p>
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <aside className="max-h-72 w-full shrink-0 overflow-y-auto border-b border-hairline md:h-auto md:max-h-none md:w-80 md:border-b-0 md:border-r">
          <div className="flex items-center justify-between border-b border-hairline px-5 py-4">
            <span className="text-[13px] font-semibold text-ink-muted">
              Queue
              {investigations.filter((i) => i.status === "pending_review").length > 0 &&
                ` (${investigations.filter((i) => i.status === "pending_review").length})`}
            </span>
            <button
              onClick={loadQueue}
              className="cursor-pointer text-xs text-ink-faint transition-colors duration-150 hover:text-ink-muted"
            >
              Refresh
            </button>
          </div>
          {loading ? (
            <p className="px-5 py-8 text-sm text-ink-faint">Loading queue…</p>
          ) : error ? (
            <p className="px-5 py-8 text-sm text-sev-high">{error}</p>
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
            <motion.div
              key={selected.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            >
              <CaseFile
                investigation={selected}
                onDecided={(updated) => {
                  setInvestigations((prev) => prev.map((i) => (i.id === updated.id ? updated : i)))
                }}
              />
            </motion.div>
          ) : (
            <div className="flex h-full items-center justify-center px-8">
              <p className="max-w-sm text-center leading-relaxed text-ink-faint">
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
