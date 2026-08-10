# web/

Reviewer dashboard: the review queue, an investigation's full report, and the
approve/reject/request-more-investigation decision panel. React, TypeScript, Tailwind CSS v4.

## Design

The layout is built around one distinction, kept consistent throughout: hard evidence pulled
from tools (transaction facts, tool output) is always set in monospace, like a ledger; the
agent's own writing (summary, risk-factor descriptions, rationale) is always set in a text
serif, like a written memo. The agent's recommendation is displayed as a distinct "verdict"
block, separate from the human decision panel below it, since the two are not the same thing —
one is a recommendation, the other is the actual decision.

Color is used semantically, not decoratively: a consistent severity scale (red / amber / green)
maps to both risk-factor severity and recommended/decided actions, and a separate accent color
is reserved for tool/agent-sourced badges.

## Structure

- `src/lib/api.ts` — typed API client
- `src/lib/types.ts` — types mirroring the API's response shapes
- `src/components/QueueList.tsx` — the review queue
- `src/components/CaseFile.tsx` — investigation detail view
- `src/components/DecisionPanel.tsx` — the human decision form
- `src/components/ui/` — shared primitives (button, badge, card, input)

## Running

```bash
npm install
npm run dev
```

Set `VITE_API_BASE_URL` (see `.env.example`) if the API isn't at `http://localhost:8000`.
