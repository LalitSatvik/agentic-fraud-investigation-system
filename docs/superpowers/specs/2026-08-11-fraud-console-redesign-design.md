# Fraud console redesign — design

Date: 2026-08-11
Status: approved, ready for implementation planning

## Context

`web/` is a React + TypeScript + Tailwind + Radix + lucide-react frontend for an
internal fraud-investigation review tool. Its current visual system is a dark,
dense, all-monospace "terminal" aesthetic (near-black canvas, all-caps tracked
labels, flat colored badges). The functionality — queue of flagged
transactions, per-case investigation detail, reviewer decision form — is
correct and must not change.

The redesign adopts the spirit (not a literal clone) of increase.com's design
system: confident editorial sans-serif typography, generous whitespace, a
warm-neutral light-mode-primary palette, and color used sparingly as a state
signal rather than as decoration.

Mid-conversation the scope grew beyond a visual-system-only sweep: the user
also asked for a new marketing-style home page (built around a supplied
animated wave-background component) and a new aggregate dashboard (inspired
by a supplied property-portfolio dashboard reference and a supplied
marketing "features" bento-grid component), plus motion inspired by
craft.wild.as (a WebGL/shader-driven design studio's showcase site). Those
decisions are captured below alongside the original visual-system scope.

## Goals

1. Replace the terminal aesthetic with an editorial, warm-neutral,
   Increase-inspired design system, applied to the existing console
   (queue list, case file, decision panel, app shell).
2. Add a new Home page: product introduction, the supplied wave-background
   component (ported and re-themed), full motion choreography.
3. Add a new Dashboard page: aggregate stats about the investigation queue,
   using one small new read-only backend endpoint plus the existing API.
4. Establish a motion system used consistently across all three views.

## Non-goals / constraints

- No changes to `/agent` or `/ml`. `/api` gets exactly one new read-only
  endpoint (§5); every existing endpoint, route, and response shape is
  unchanged.
- No changes to existing data-fetching logic, TypeScript types, or component
  props/behavior in the console — only markup/styling/structure.
- Stay on React + TypeScript + Tailwind + Radix + lucide-react. New
  dependencies are additive (a small animation/noise library), not framework
  replacements.
- No literal WebGL/GLSL shader work — see §4 for the scoped interpretation
  of "full craft treatment" motion.

## 1. Design tokens

Confirmed via the published token/typography/component preview
(https://claude.ai/code/artifact/2c496da6-dbe4-4256-86ea-1685783ceff9).

**Typography** — three roles, one job each. Serif is dropped entirely (this
supersedes the old "mono = data, serif = agent narrative, sans = chrome"
concept documented in the current `index.css`).

| Role | Face | Used for |
|---|---|---|
| Display | Space Grotesk 700 | Verdict word, transaction ID, home-page headline — the few oversized, high-stakes moments |
| Body / UI | Inter 400–600 | Everything else: paragraphs, labels, nav, buttons |
| Data | JetBrains Mono 400–600 | IDs, amounts, hashes, timestamps, raw trace JSON |

Section labels (`Summary`, `Risk factors`, …) become sentence-case Inter
medium, not tracked all-caps — a small colored dash precedes the label
instead of letter-spacing carrying the "label-ness."

**Palette** — named tokens, light is primary:

Light:
- `canvas` `#f7f5f0`, `canvas-elevated` `#fdfcfa`, `surface` `#ffffff`
- `surface-hover` `#f1efe8`, `surface-selected` `#eae6da`
- `hairline` `#e3ddd0`, `hairline-strong` `#cec5b2`
- `ink` `#17181a`, `ink-muted` `#5c5d54`, `ink-faint` `#92948a`
- `accent` `#2c5aa3` (focus rings, links, tool badges, selected-row rule —
  deliberately distinct from the semantic trio so it never reads as a
  fourth "state")
- `sev-high` `#b7302f` (deny/reject), `sev-medium` `#96650f` (escalate),
  `sev-low` `#1e7a4c` (approve) — each with a low-alpha tint variant, used
  as text + a thin rule, never a large opaque fill

Dark: `canvas` `#0a0b0d` … `ink` `#f2f1ec`, `accent` `#7ba6e8`,
`sev-high` `#ef6a68`, `sev-medium` `#e4b15a`, `sev-low` `#56d199` (same
structure, inverted). Both palettes ship together in `index.css`; the
existing light/dark toggle is preserved.

**Radii**: `--radius-sm: 6px` (inputs, chips), `--radius-md: 10px` (cards),
`--radius-lg: 16px` (hero/verdict panels), pill (`9999px`) for badges and
some buttons.

**Signature element**: the agent's verdict is set as a headline, not a
badge — a thin 4px color rule (state color) on an otherwise neutral card,
with the verdict word itself large in Space Grotesk and colored.

## 2. Navigation / IA

Three views, switched via local state in `App.tsx` — no router library is
introduced; this stays an internal tool and nothing here needs deep-linking.

- **Home** (default) — new
- **Dashboard** — new
- **Console** — today's queue + case-file + decision workflow, redesigned

A persistent header lets a reviewer move between Dashboard and Console;
Home carries its own CTAs into both.

## 3. Home page (new)

- Full-viewport hero using the supplied `wave-background.tsx` component,
  ported to match this codebase's conventions and re-themed onto the token
  palette (hardcoded `#ffffff`/`#000000` → `--canvas`/`--ink`/`--accent`)
  rather than used with its original colors.
- Real copy (no lorem ipsum), written to the actual product mechanism —
  draft headline: **"An agent investigates. You decide."** — with
  supporting copy on how a flagged transaction gets a full investigation
  (device graphs, counterparty history, geo signals) that produces a
  recommendation, and nothing is final until a reviewer signs it.
- Two CTAs: into Dashboard, into Console.
- Full `framer-motion` entrance choreography (staggered reveal of headline,
  supporting copy, CTAs).

## 4. Motion system

"Full craft treatment, everywhere" is interpreted deliberately, not
literally: the supplied `wave-background.tsx` is `simplex-noise` + SVG path
drawing, not WebGL — Wild's own site uses bespoke per-client WebGL/shader
work, which is a different scale of effort than a styling sweep. The scoped
plan:

- The noise-wave technique is the app's one signature motion motif.
  - **Home**: full expression, large, mouse-reactive, primary hero.
  - **Dashboard / Console**: a much quieter, low-opacity, slow-drifting
    version as a `pointer-events: none` ambient background layer behind the
    working content — present everywhere, never competing with data
    legibility.
- `framer-motion` (new dependency) drives page-load stagger, section
  reveals, hover micro-interactions, and transitions between the three
  views, used consistently across Home, Dashboard, and Console.
- `prefers-reduced-motion: reduce` (already respected in `index.css`)
  disables both the wave animation and framer-motion transitions.
- No custom WebGL/GLSL shaders are built.

## 5. Dashboard (new)

**Backend** — one new, narrow, read-only, additive endpoint:

```
GET /investigations/stats
```

Computed server-side from the existing `Investigation` table (no schema
change): total count, breakdown by `status`, breakdown by
`recommended_action` (parsed out of the `report` JSON column), a risk-score
histogram (fixed bands), and average confidence. No existing endpoint,
route, or response shape changes.

**Frontend** — a new `Dashboard.tsx`:
- KPI tiles using the *grid structure* borrowed from the supplied
  `features-8.tsx` (asymmetric bento layout) — its marketing copy,
  decorative illustrative SVGs, and avatar stacks are dropped; tiles are
  built from real numbers from `/investigations/stats`.
- A risk-band × recommended-action heatmap grid, in the spirit of the
  supplied property-dashboard reference's EPC-band grid, using our own
  bands/actions.
- The `dataviz` skill is invoked before building the histogram/heatmap
  treatment; no chart library is added unless that pass determines one is
  actually needed (hand-rolled SVG/CSS is expected to be sufficient).

## 6. Console redesign

Original scope, now also carrying the ambient motion layer (§4):

- `web/src/index.css` + Tailwind config: tokens from §1.
- `web/src/components/ui/{badge,button,card,input}.tsx`: rebuilt against
  the new tokens.
- `QueueList.tsx`, `CaseFile.tsx`, `DecisionPanel.tsx`: redesigned per §1's
  hierarchy/typography rules; no prop/behavior changes.
- `App.tsx`: header/shell updated for the new IA (§2), plus responsive pass.

## 7. New dependencies

- `simplex-noise` — required by the wave-background component.
- `framer-motion` — page/section choreography, used across all three views.
- No new chart library (pending the `dataviz` pass).
- One new backend endpoint (§5); no new backend dependencies expected.

## Verification

- Frontend: `npm run build` and `npm run dev` in `web/` after each phase;
  visually confirm light/dark toggle, responsive behavior, and that no
  existing interaction (launching an investigation, submitting a decision,
  toggling the trace) regressed.
- Backend: manually exercise `GET /investigations/stats` against the local
  DB (no existing automated test suite for `api/` was found to extend);
  confirm all pre-existing endpoints are byte-for-byte unchanged in
  behavior.

## Open items for the implementation plan

- Exact risk-score histogram bands for `/investigations/stats`.
- Exact copy for the Home page beyond the draft headline.
- Whether `framer-motion`'s bundle-size cost is acceptable as-is or needs
  tree-shaking/lazy-loading for the Home page specifically.
