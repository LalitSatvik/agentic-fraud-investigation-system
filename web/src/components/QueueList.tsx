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
        <p className="text-sm leading-relaxed text-ink-muted">
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
                "relative w-full cursor-pointer border-b border-hairline px-5 py-4 text-left transition-colors duration-150",
                isSelected ? "bg-surface-selected" : "hover:bg-surface-hover"
              )}
            >
              {isSelected && (
                <span className="absolute bottom-0 left-0 top-0 w-[3px] bg-accent" aria-hidden />
              )}
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-sm font-medium text-ink">{inv.transaction_id}</span>
                <span className="font-mono text-xs text-ink-faint">{formatRelativeTime(inv.created_at)}</span>
              </div>
              <div className="mt-2 flex items-center justify-between gap-2">
                <span className="text-xs text-ink-muted">
                  risk <span className="font-mono text-ink">{formatPercent(inv.risk_score)}</span>
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
