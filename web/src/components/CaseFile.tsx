import { useEffect, useState } from "react"
import type { Investigation, RiskFactor, TransactionDetail } from "@/lib/types"
import { api } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Card, CardTitle } from "@/components/ui/card"
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
      <div className="text-xs text-ink-faint">{label}</div>
      <div className="mt-1 font-mono text-sm text-ink">{value}</div>
    </div>
  )
}

function RiskFactorCard({ rf }: { rf: RiskFactor }) {
  return (
    <Card className="px-4 py-3.5">
      <div className="mb-2 flex items-center gap-2.5">
        <Badge variant={rf.severity}>{rf.severity}</Badge>
        <span className="text-sm font-medium text-ink">{rf.factor}</span>
      </div>
      <p className="text-[15px] leading-relaxed text-ink-muted">{rf.evidence}</p>
    </Card>
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
    <div className="mx-auto max-w-3xl space-y-10 px-8 py-10">
      {/* Header: case facts, always monospace — this is the hard ledger data */}
      <div>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h1 className="font-display text-3xl font-bold tracking-tight text-ink">
            {investigation.transaction_id}
          </h1>
          <span className="font-mono text-xs text-ink-faint">
            investigation #{investigation.id} · flagged {formatRelativeTime(investigation.created_at)}
          </span>
        </div>

        <Card className="mt-5 grid grid-cols-2 gap-5 px-6 py-5 sm:grid-cols-4">
          <Fact label="Risk score" value={formatPercent(investigation.risk_score)} />
          <Fact label="Anomaly score" value={formatPercent(investigation.anomaly_score)} />
          {txn && <Fact label="Amount" value={formatCurrency(txn.amount)} />}
          {txn && <Fact label="Type" value={txn.type} />}
          {txn && <Fact label="Customer" value={txn.customer_id} />}
          {txn && <Fact label="Counterparty" value={txn.counterparty_id} />}
          {txn && <Fact label="Balance before" value={formatCurrency(txn.orig_balance_before)} />}
          {txn && <Fact label="Balance after" value={formatCurrency(txn.orig_balance_after)} />}
        </Card>
      </div>

      {investigation.agent_is_error || !report ? (
        <Card className="border-sev-high/30 bg-sev-high-bg px-6 py-5">
          <p className="text-sm font-medium text-sev-high">Investigation did not complete</p>
          <p className="mt-1.5 text-sm leading-relaxed text-ink-muted">
            {investigation.report_error ?? "The agent did not return a structured report. Check server logs."}
          </p>
        </Card>
      ) : (
        <>
          <section>
            <CardTitle className="mb-3">Summary</CardTitle>
            <p className="text-base leading-relaxed text-ink">{report.summary}</p>
          </section>

          <section>
            <CardTitle className="mb-3">
              Risk factors {report.risk_factors.length > 0 && `(${report.risk_factors.length})`}
            </CardTitle>
            {report.risk_factors.length === 0 ? (
              <p className="text-sm italic text-ink-faint">None identified.</p>
            ) : (
              <div className="space-y-2.5">
                {report.risk_factors.map((rf, i) => (
                  <RiskFactorCard key={i} rf={rf} />
                ))}
              </div>
            )}
          </section>

          {report.mitigating_factors.length > 0 && (
            <section>
              <CardTitle className="mb-3">Mitigating factors</CardTitle>
              <ul className="space-y-2">
                {report.mitigating_factors.map((m, i) => (
                  <li key={i} className="flex gap-2.5 text-[15px] leading-relaxed text-ink-muted">
                    <span className="select-none text-sev-low">–</span>
                    <span>{m}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <CardTitle className="mb-3">Tools consulted</CardTitle>
            <div className="flex flex-wrap gap-1.5">
              {report.tools_consulted.map((t) => (
                <Badge key={t} variant="agent">
                  {t}
                </Badge>
              ))}
            </div>
          </section>

          {/* Verdict: the agent's recommendation, framed like a headline — it is NOT the final decision */}
          <section
            className={cn(
              "rounded-lg border-l-4 bg-surface px-6 py-6",
              verdictSeverity === "high" && "border-sev-high",
              verdictSeverity === "medium" && "border-sev-medium",
              verdictSeverity === "low" && "border-sev-low"
            )}
          >
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <span className="text-[13px] font-semibold text-ink-muted">Agent recommendation</span>
              <span className="text-xs text-ink-faint">Confidence: {report.confidence}</span>
            </div>
            <p
              className={cn(
                "font-display text-4xl font-bold capitalize tracking-tight",
                verdictSeverity === "high" && "text-sev-high",
                verdictSeverity === "medium" && "text-sev-medium",
                verdictSeverity === "low" && "text-sev-low"
              )}
            >
              {report.recommended_action}
            </p>
            <p className="mt-4 text-[15px] leading-relaxed text-ink-muted">{report.rationale}</p>
          </section>

          {investigation.trace && investigation.trace.length > 0 && (
            <section>
              <button
                onClick={() => setShowTrace((s) => !s)}
                className="cursor-pointer text-xs text-ink-faint transition-colors duration-150 hover:text-ink-muted"
              >
                {showTrace ? "Hide" : "Show"} raw agent trace ({investigation.trace.length} events)
                {investigation.total_cost_usd != null && ` · $${investigation.total_cost_usd.toFixed(4)}`}
              </button>
              {showTrace && (
                <pre className="mt-2 max-h-96 overflow-x-auto overflow-y-auto rounded-md border border-hairline bg-canvas px-4 py-3 font-mono text-xs text-ink-muted">
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
