export type Severity = "low" | "medium" | "high"
export type Confidence = "low" | "medium" | "high"
export type RecommendedAction = "approve" | "deny" | "escalate"
export type DecisionValue = "approved" | "rejected" | "more_investigation_requested"
export type InvestigationStatus = "pending_review" | DecisionValue

export interface RiskFactor {
  factor: string
  evidence: string
  severity: Severity
}

export interface InvestigationReport {
  transaction_id: string
  summary: string
  risk_factors: RiskFactor[]
  mitigating_factors: string[]
  tools_consulted: string[]
  confidence: Confidence
  recommended_action: RecommendedAction
  rationale: string
}

export interface TraceEntry {
  role: "assistant" | "tool"
  type: "text" | "tool_call" | "tool_result" | "thinking"
  tool?: string
  input?: Record<string, unknown>
  text?: string
  tool_use_id?: string
  content?: unknown
  is_error?: boolean | null
}

export interface Investigation {
  id: number
  transaction_id: string
  status: InvestigationStatus
  risk_score: number
  anomaly_score: number
  model_version: string
  report: InvestigationReport | null
  report_error: string | null
  trace: TraceEntry[] | null
  num_turns: number | null
  total_cost_usd: number | null
  agent_is_error: boolean
  created_at: string
  decided_at: string | null
  decided_by: string | null
  decision_notes: string | null
}

export interface AuditLogEntry {
  id: number
  transaction_id: string
  investigation_id: number | null
  event_type: string
  event_data: Record<string, unknown> | null
  created_at: string
}

export interface TransactionDetail {
  transaction_id: string
  step: number
  type: string
  amount: number
  customer_id: string
  counterparty_id: string
  orig_balance_before: number
  orig_balance_after: number
  dest_balance_before: number
  dest_balance_after: number
  risk_score: number
  anomaly_score: number
  above_threshold: boolean
  model_version: string
}
