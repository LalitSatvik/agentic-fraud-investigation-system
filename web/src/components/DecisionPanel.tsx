import { useState } from "react"
import type { Investigation } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Input, Textarea } from "@/components/ui/input"
import { Card, CardTitle } from "@/components/ui/card"
import { formatRelativeTime } from "@/lib/format"

interface DecisionPanelProps {
  investigation: Investigation
  onDecide: (decision: string, reviewer: string, notes: string) => Promise<void>
  reviewer: string
  onReviewerChange: (value: string) => void
}

const DECISION_LABELS: Record<string, string> = {
  approved: "Approved",
  rejected: "Rejected",
  more_investigation_requested: "More investigation requested",
}

export function DecisionPanel({ investigation, onDecide, reviewer, onReviewerChange }: DecisionPanelProps) {
  const [notes, setNotes] = useState("")
  const [submitting, setSubmitting] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  if (investigation.status !== "pending_review") {
    return (
      <Card className="px-6 py-5">
        <CardTitle className="mb-2">Reviewed</CardTitle>
        <p className="text-sm text-ink">
          {DECISION_LABELS[investigation.status] ?? investigation.status} by{" "}
          <span className="font-medium">{investigation.decided_by}</span>
          {investigation.decided_at && (
            <span className="text-ink-faint"> · {formatRelativeTime(investigation.decided_at)}</span>
          )}
        </p>
        {investigation.decision_notes && (
          <p className="mt-2.5 text-sm leading-relaxed text-ink-muted">"{investigation.decision_notes}"</p>
        )}
      </Card>
    )
  }

  const handleDecide = async (decision: string) => {
    if (!reviewer.trim()) {
      setError("Enter your name before recording a decision.")
      return
    }
    setError(null)
    setSubmitting(decision)
    try {
      await onDecide(decision, reviewer.trim(), notes.trim())
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit decision.")
    } finally {
      setSubmitting(null)
    }
  }

  return (
    <Card className="px-6 py-5">
      <CardTitle className="mb-4">Your decision</CardTitle>

      <div className="space-y-4">
        <div>
          <label htmlFor="reviewer" className="mb-1.5 block text-xs text-ink-muted">
            Reviewer name
          </label>
          <Input
            id="reviewer"
            value={reviewer}
            onChange={(e) => onReviewerChange(e.target.value)}
            placeholder="you@company.com"
          />
        </div>
        <div>
          <label htmlFor="notes" className="mb-1.5 block text-xs text-ink-muted">
            Notes <span className="text-ink-faint">(optional)</span>
          </label>
          <Textarea
            id="notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Anything the next reviewer or an auditor should know about this call."
          />
        </div>

        {error && <p className="text-sm text-sev-high">{error}</p>}

        <div className="flex flex-wrap gap-2 pt-1">
          <Button variant="approve" disabled={submitting !== null} onClick={() => handleDecide("approved")}>
            {submitting === "approved" ? "Approving…" : "Approve"}
          </Button>
          <Button variant="deny" disabled={submitting !== null} onClick={() => handleDecide("rejected")}>
            {submitting === "rejected" ? "Rejecting…" : "Reject"}
          </Button>
          <Button
            variant="escalate"
            disabled={submitting !== null}
            onClick={() => handleDecide("more_investigation_requested")}
          >
            {submitting === "more_investigation_requested" ? "Requesting…" : "Request more investigation"}
          </Button>
        </div>
      </div>
    </Card>
  )
}
