import type { Investigation } from "@/lib/types"
import { cn } from "@/lib/utils"
import { formatPercent, formatRelativeTime, severityForAction } from "@/lib/format"
import { Badge } from "@/components/ui/badge"

interface QueueListProps {
  investigations: Investigation[]
  selectedId: number | null
  onSelect: (id: number) => void
}

export function QueueList({ investigations, selectedId, onSelect }: QueueListProps) {
  if (investigations.length === 0) {
    return (
      <div className="px-5 py-10 text-center">
        <p className="text-sm font-serif text-ink-muted leading-relaxed">
          No flagged transactions right now. The queue clears as investigations are decided —
          new cases appear here as soon as the model flags something above threshold.
        </p>
      </div>
    )
  }

  return (
    <ul>
      {investigations.map((inv) => {
        const action = inv.report?.recommended_action
        const sev = severityForAction(action)
        const isSelected = inv.id === selectedId
        return (
          <li key={inv.id}>
            <button
              onClick={() => onSelect(inv.id)}
              className={cn(
                "w-full text-left px-4 py-3 border-b border-hairline transition-colors duration-150 cursor-pointer relative",
                isSelected ? "bg-surface-selected" : "hover:bg-surface-hover"
              )}
            >
              {isSelected && (
                <span className="absolute left-0 top-0 bottom-0 w-0.5 bg-agent" aria-hidden />
              )}
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-sm text-ink">{inv.transaction_id}</span>
                <span className="font-mono text-xs text-ink-faint">{formatRelativeTime(inv.created_at)}</span>
              </div>
              <div className="mt-1.5 flex items-center justify-between gap-2">
                <span className="font-mono text-xs text-ink-muted">
                  risk <span className="text-ink">{formatPercent(inv.risk_score)}</span>
                </span>
                {action ? (
                  <Badge variant={sev === "neutral" ? "neutral" : sev}>{action}</Badge>
                ) : (
                  <Badge variant="neutral">no report</Badge>
                )}
              </div>
            </button>
          </li>
        )
      })}
    </ul>
  )
}
