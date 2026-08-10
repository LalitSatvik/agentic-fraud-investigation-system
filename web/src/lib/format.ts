export function formatCurrency(n: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(n)
}

export function formatPercent(n: number, digits = 1): string {
  return `${(n * 100).toFixed(digits)}%`
}

export function formatRelativeTime(iso: string): string {
  const then = new Date(iso.endsWith("Z") ? iso : `${iso}Z`).getTime()
  const diffSec = Math.round((Date.now() - then) / 1000)
  if (diffSec < 60) return "just now"
  const diffMin = Math.round(diffSec / 60)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.round(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.round(diffHr / 24)
  return `${diffDay}d ago`
}

export function severityForAction(action: string | undefined): "high" | "medium" | "low" | "neutral" {
  if (action === "deny" || action === "rejected") return "high"
  if (action === "escalate" || action === "more_investigation_requested") return "medium"
  if (action === "approve" || action === "approved") return "low"
  return "neutral"
}
