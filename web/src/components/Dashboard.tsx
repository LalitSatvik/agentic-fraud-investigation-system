import { useEffect, useState } from "react"
import { motion, cubicBezier } from "framer-motion"
import { api } from "@/lib/api"
import type { InvestigationStats, RiskBandStats } from "@/lib/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const ACTION_COLUMNS: { key: string; label: string; dot: string }[] = [
  { key: "deny", label: "Deny", dot: "var(--sev-high)" },
  { key: "escalate", label: "Escalate", dot: "var(--sev-medium)" },
  { key: "approve", label: "Approve", dot: "var(--sev-low)" },
  { key: "none", label: "No report", dot: "var(--ink-faint)" },
]

function StatTile({
  label,
  value,
  dot,
  hero = false,
}: {
  label: string
  value: number
  dot?: string
  hero?: boolean
}) {
  return (
    <Card className={hero ? "flex flex-col justify-between lg:col-span-2 lg:row-span-2" : "flex flex-col justify-between"}>
      <CardContent className="flex h-full flex-col justify-between">
        <div className="flex items-center gap-2">
          {dot && <span className="h-2 w-2 rounded-full" style={{ background: dot }} aria-hidden />}
          <span className="text-[13px] font-medium text-ink-muted">{label}</span>
        </div>
        <span className={`font-display font-bold text-ink ${hero ? "mt-6 text-6xl" : "mt-4 text-3xl"}`}>
          {value.toLocaleString()}
        </span>
      </CardContent>
    </Card>
  )
}

function RiskHeatmap({ bands }: { bands: RiskBandStats[] }) {
  const maxCount = Math.max(
    1,
    ...bands.flatMap((b) => ACTION_COLUMNS.map((c) => b.by_recommended_action[c.key] ?? 0))
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk score × recommendation</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full border-separate" style={{ borderSpacing: "2px" }}>
            <thead>
              <tr>
                <th className="p-0" />
                {ACTION_COLUMNS.map((col) => (
                  <th key={col.key} className="pb-3 text-left">
                    <span className="inline-flex items-center gap-1.5 text-[13px] font-medium text-ink-muted">
                      <span className="h-1.5 w-1.5 rounded-full" style={{ background: col.dot }} aria-hidden />
                      {col.label}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {bands.map((band) => (
                <tr key={band.label}>
                  <td className="whitespace-nowrap py-1 pr-4 font-mono text-xs text-ink-faint">{band.label}</td>
                  {ACTION_COLUMNS.map((col) => {
                    const count = band.by_recommended_action[col.key] ?? 0
                    const intensity = count === 0 ? 0 : Math.max(1, Math.ceil((count / maxCount) * 5))
                    return (
                      <td key={col.key} className="p-0">
                        <div
                          title={`${band.label} · ${col.label}: ${count}`}
                          tabIndex={0}
                          className={`flex h-14 min-w-16 items-center justify-center rounded-md text-sm font-medium tabular-nums ${
                            intensity >= 3 ? "text-white" : intensity > 0 ? "text-ink" : "text-ink-faint"
                          }`}
                          style={{
                            background: intensity === 0 ? "var(--surface-hover)" : `var(--seq-${intensity})`,
                          }}
                        >
                          {count}
                        </div>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex items-center gap-2 text-xs text-ink-faint">
          <span>Fewer</span>
          <div className="flex gap-0.5">
            <span className="h-2 w-4 rounded-sm" style={{ background: "var(--surface-hover)" }} />
            {[1, 2, 3, 4, 5].map((n) => (
              <span key={n} className="h-2 w-4 rounded-sm" style={{ background: `var(--seq-${n})` }} />
            ))}
          </div>
          <span>More</span>
        </div>
      </CardContent>
    </Card>
  )
}

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
}
const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: cubicBezier(0.16, 1, 0.3, 1) } },
}

export function Dashboard() {
  const [stats, setStats] = useState<InvestigationStats | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .getStats()
      .then(setStats)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load dashboard"))
  }, [])

  return (
    <div className="flex-1 overflow-y-auto px-6 py-10 sm:px-10">
      <div className="mx-auto max-w-5xl">
        <h1 className="font-display text-3xl font-bold text-ink">Portfolio overview</h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-muted">
          Aggregate view of every investigation the model has flagged, regardless of review status.
        </p>

        {error && <p className="mt-6 text-sm text-sev-high">{error}</p>}
        {!stats && !error && <p className="mt-10 text-sm text-ink-faint">Loading…</p>}

        {stats && (
          <motion.div variants={container} initial="hidden" animate="show" className="mt-8 space-y-8">
            <motion.div variants={item} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatTile hero label="Total investigations" value={stats.total} />
              <StatTile label="Pending review" value={stats.by_status.pending_review ?? 0} dot="var(--accent)" />
              <StatTile label="Approved" value={stats.by_status.approved ?? 0} dot="var(--sev-low)" />
              <StatTile label="Rejected" value={stats.by_status.rejected ?? 0} dot="var(--sev-high)" />
              <StatTile
                label="Escalated"
                value={stats.by_status.more_investigation_requested ?? 0}
                dot="var(--sev-medium)"
              />
            </motion.div>

            <motion.div variants={item}>
              <RiskHeatmap bands={stats.risk_score_histogram} />
            </motion.div>
          </motion.div>
        )}
      </div>
    </div>
  )
}
