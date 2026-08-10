import { useEffect, useState } from "react"
import type { Investigation, RiskFactor, TransactionDetail } from "@/lib/types"
import { api } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { DecisionPanel } from "@/components/DecisionPanel"
import { formatCurrency, formatPercent, formatRelativeTime, severityForAction } from "@/lib/format"
import { cn } from "@/lib/utils"

interface CaseFileProps {
  investigation: Investigation
  onDecided: (updated: Investigation) => void
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">{label}</div>
      <div className="font-mono text-sm text-ink mt-0.5">{value}</div>
    </div>
  )
}

function RiskFactorCard({ rf }: { rf: RiskFactor }) {
  return (
    <div className="rounded-md border border-hairline bg-canvas px-4 py-3">
      <div className="flex items-center gap-2 mb-1.5">
        <Badge variant={rf.severity}>{rf.severity}</Badge>
        <span className="font-sans text-sm font-medium text-ink">{rf.factor}</span>
      </div>
      <p className="font-serif text-[15px] text-ink-muted leading-relaxed">{rf.evidence}</p>
    </div>
  )
}

export function CaseFile({ investigation, onDecided }: CaseFileProps) {
  const [txn, setTxn] = useState<TransactionDetail | null>(null)
  const [showTrace, setShowTrace] = useState(false)

  useEffect(() => {
    setTxn(null)
    api.getTransaction(investigation.transaction_id).then(setTxn).catch(() => setTxn(null))
  }, [investigation.transaction_id])

  const report = investigation.report
  const verdictSeverity = severityForAction(report?.recommended_action)

  return (
    <div className="max-w-3xl mx-auto px-8 py-8 space-y-6">
      {/* Header: case facts, always monospace — this is the hard ledger data */}
      <div>
        <div className="flex items-baseline justify-between flex-wrap gap-2">
          <h1 className="font-mono text-xl text-ink">{investigation.transaction_id}</h1>
          <span className="font-mono text-xs text-ink-faint">
            investigation #{investigation.id} · flagged {formatRelativeTime(investigation.created_at)}
          </span>
        </div>

        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-4 rounded-lg border border-hairline bg-surface px-5 py-4">
          <Fact label="Risk score" value={formatPercent(investigation.risk_score)} />
          <Fact label="Anomaly score" value={formatPercent(investigation.anomaly_score)} />
          {txn && <Fact label="Amount" value={formatCurrency(txn.amount)} />}
          {txn && <Fact label="Type" value={txn.type} />}
          {txn && <Fact label="Customer" value={txn.customer_id} />}
          {txn && <Fact label="Counterparty" value={txn.counterparty_id} />}
          {txn && <Fact label="Balance before" value={formatCurrency(txn.orig_balance_before)} />}
          {txn && <Fact label="Balance after" value={formatCurrency(txn.orig_balance_after)} />}
        </div>
      </div>

      {investigation.agent_is_error || !report ? (
        <div className="rounded-lg border border-sev-high/40 bg-sev-high-bg px-5 py-4">
          <p className="font-sans text-sm text-sev-high font-medium">Investigation did not complete</p>
          <p className="font-serif text-sm text-ink-muted mt-1">
            {investigation.report_error ?? "The agent did not return a structured report. Check server logs."}
          </p>
        </div>
      ) : (
        <>
          {/* Narrative: always serif — this is the agent's own writing */}
          <section>
            <h2 className="text-xs font-mono uppercase tracking-widest text-ink-muted mb-2">Summary</h2>
            <p className="font-serif text-[16px] text-ink leading-relaxed">{report.summary}</p>
          </section>

          <section>
            <h2 className="text-xs font-mono uppercase tracking-widest text-ink-muted mb-2">
              Risk factors {report.risk_factors.length > 0 && `(${report.risk_factors.length})`}
            </h2>
            {report.risk_factors.length === 0 ? (
              <p className="font-serif text-sm text-ink-faint italic">None identified.</p>
            ) : (
              <div className="space-y-2">
                {report.risk_factors.map((rf, i) => (
                  <RiskFactorCard key={i} rf={rf} />
                ))}
              </div>
            )}
          </section>

          {report.mitigating_factors.length > 0 && (
            <section>
              <h2 className="text-xs font-mono uppercase tracking-widest text-ink-muted mb-2">
                Mitigating factors
              </h2>
              <ul className="space-y-1.5">
                {report.mitigating_factors.map((m, i) => (
                  <li key={i} className="font-serif text-[15px] text-ink-muted leading-relaxed flex gap-2">
                    <span className="text-sev-low select-none">–</span>
                    <span>{m}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <h2 className="text-xs font-mono uppercase tracking-widest text-ink-muted mb-2">
              Tools consulted
            </h2>
            <div className="flex flex-wrap gap-1.5">
              {report.tools_consulted.map((t) => (
                <Badge key={t} variant="agent">
                  {t}
                </Badge>
              ))}
            </div>
          </section>

          {/* Verdict: the agent's recommendation, framed like a stamp — it is NOT the final decision */}
          <section
            className={cn(
              "rounded-lg border-2 px-5 py-4",
              verdictSeverity === "high" && "border-sev-high/50 bg-sev-high-bg",
              verdictSeverity === "medium" && "border-sev-medium/50 bg-sev-medium-bg",
              verdictSeverity === "low" && "border-sev-low/50 bg-sev-low-bg"
            )}
          >
            <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
              <span className="text-xs font-mono uppercase tracking-widest text-ink-muted">
                Agent recommendation
              </span>
              <span className="text-xs font-mono uppercase tracking-widest text-ink-faint">
                confidence: {report.confidence}
              </span>
            </div>
            <p
              className={cn(
                "font-mono text-2xl uppercase tracking-wide",
                verdictSeverity === "high" && "text-sev-high",
                verdictSeverity === "medium" && "text-sev-medium",
                verdictSeverity === "low" && "text-sev-low"
              )}
            >
              {report.recommended_action}
            </p>
            <p className="font-serif text-[15px] text-ink-muted leading-relaxed mt-3">{report.rationale}</p>
          </section>

          {investigation.trace && investigation.trace.length > 0 && (
            <section>
              <button
                onClick={() => setShowTrace((s) => !s)}
                className="text-xs font-mono uppercase tracking-widest text-ink-faint hover:text-ink-muted cursor-pointer transition-colors duration-150"
              >
                {showTrace ? "Hide" : "Show"} raw agent trace ({investigation.trace.length} events)
                {investigation.total_cost_usd != null && ` · $${investigation.total_cost_usd.toFixed(4)}`}
              </button>
              {showTrace && (
                <pre className="mt-2 rounded-md border border-hairline bg-canvas px-4 py-3 text-xs font-mono text-ink-muted overflow-x-auto max-h-96 overflow-y-auto">
                  {JSON.stringify(investigation.trace, null, 2)}
                </pre>
              )}
            </section>
          )}
        </>
      )}

      <DecisionPanel
        investigation={investigation}
        onDecide={async (decision, reviewer, notes) => {
          const updated = await api.submitDecision(investigation.id, { decision, reviewer, notes })
          onDecided(updated)
        }}
      />
    </div>
  )
}
