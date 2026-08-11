# Fraud Console Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fraud console's dark "terminal" visual system with a warm-neutral, editorial-typography design system (Increase-inspired), and add two new views — a Home intro page and an aggregate Dashboard — built on the same system.

**Architecture:** Design tokens live entirely in `web/src/index.css` (Tailwind v4 CSS-first `@theme`, no JS config file). Four shared primitives (`badge`, `button`, `card`, `input`) sit under `web/src/components/ui/`. Three top-level views (Home, Dashboard, Console) are switched by local state in `App.tsx` — no router. The existing queue+case-file workflow is extracted unchanged (same state/handlers/props) from today's `App.tsx` into a new `Console.tsx`. One new read-only backend endpoint (`GET /investigations/stats`) feeds the Dashboard; every existing endpoint is untouched.

**Tech Stack:** React 19, TypeScript, Tailwind CSS v4, Radix UI primitives, lucide-react, class-variance-authority, `simplex-noise` (new), `framer-motion` (new). Backend: FastAPI + SQLModel (Python), no new backend dependencies.

## Global Constraints

- No changes to `/agent` or `/ml`. Exactly one new backend endpoint (`GET /investigations/stats`, read-only, additive); every existing route/response shape is byte-for-byte unchanged.
- No changes to existing data-fetching logic, TypeScript types, or component props/behavior in the console — only markup/styling/structure. (New, additive types/functions for the Dashboard are in-scope.)
- Stay on React + TypeScript + Tailwind + Radix + lucide-react. `simplex-noise` and `framer-motion` are the only new dependencies.
- No custom WebGL/GLSL shader work — the wave-noise technique (ported from the supplied component) is the app's one motion signature, full expression on Home, a quiet ambient layer elsewhere.
- No test framework exists for `web/` or `api/` today (verified: no `vitest`/`jest` config, no `pytest` installed, no `tests/` directory) — this plan does not introduce one. Verification is `npm run build` (TypeScript + Vite build must succeed) for every frontend task, plus an explicit manual/visual check per task; the one backend task is verified by curl against the local dev server.
- Design tokens (typeface pairing, palette, radii) were approved via a published preview: https://claude.ai/code/artifact/2c496da6-dbe4-4256-86ea-1685783ceff9
- Full spec: `docs/superpowers/specs/2026-08-11-fraud-console-redesign-design.md`

---

## Task 1: Design tokens

**Files:**
- Modify: `web/src/index.css`
- Modify: `web/index.html`

**Interfaces:**
- Produces: CSS custom properties consumed via Tailwind utilities in every later task — `--color-canvas`, `--color-canvas-elevated`, `--color-surface`, `--color-surface-hover`, `--color-surface-selected`, `--color-hairline`, `--color-hairline-strong`, `--color-ink`, `--color-ink-muted`, `--color-ink-faint`, `--color-accent`, `--color-accent-bg`, `--color-sev-high(-bg)`, `--color-sev-medium(-bg)`, `--color-sev-low(-bg)`, plain vars `--seq-1`…`--seq-5` (sequential ramp, referenced directly by `var(--seq-N)` in Task 15, not exposed as Tailwind utilities), `--wave-ambient-opacity`. Font families `font-sans` (Inter), `font-display` (Space Grotesk), `font-mono` (JetBrains Mono). Radii `rounded-sm` (6px) / `rounded-md` (10px) / `rounded-lg` (16px). Theme is toggled by a `.dark` class on `<html>` (light is the bare-`:root` default) — Task 16 drives this class.

- [ ] **Step 1: Replace `web/index.html`'s font `<link>` and color-scheme meta**

Find the existing `<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono...">` line and the `<meta name="color-scheme" content="dark light" />` line. Replace them:

```html
<meta name="color-scheme" content="light dark" />
<title>Fraud Investigation Console</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link
  href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
  rel="stylesheet"
/>
```

(Space Grotesk replaces Source Serif 4 — the redesign drops serif entirely. `title` stays where it already is relative to the other head tags; just move the meta tag above it if it isn't already.)

- [ ] **Step 2: Replace `web/src/index.css` in full**

```css
@import "tailwindcss";

/*
  Design concept: editorial console. A confident display face (Space Grotesk)
  carries the few oversized, high-stakes moments — the transaction ID, the
  agent's verdict, the home-page headline. Inter carries everything else:
  body copy, labels, buttons, nav. Monospace (JetBrains Mono) is reserved for
  genuine data values — IDs, hashes, amounts, timestamps, raw trace JSON —
  never used to decorate a whole screen. Section labels are sentence-case
  Inter, not tracked all-caps.

  Light is the primary mode (warm-neutral, editorial, Increase-inspired);
  dark is fully supported as a secondary mode via the `.dark` class on <html>.
*/

@theme {
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
  --font-display: "Space Grotesk", "Inter", ui-sans-serif, system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace;

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;

  --color-canvas: var(--canvas);
  --color-canvas-elevated: var(--canvas-elevated);
  --color-surface: var(--surface);
  --color-surface-hover: var(--surface-hover);
  --color-surface-selected: var(--surface-selected);
  --color-hairline: var(--hairline);
  --color-hairline-strong: var(--hairline-strong);

  --color-ink: var(--ink);
  --color-ink-muted: var(--ink-muted);
  --color-ink-faint: var(--ink-faint);

  --color-accent: var(--accent);
  --color-accent-bg: var(--accent-bg);

  --color-sev-high: var(--sev-high);
  --color-sev-high-bg: var(--sev-high-bg);
  --color-sev-medium: var(--sev-medium);
  --color-sev-medium-bg: var(--sev-medium-bg);
  --color-sev-low: var(--sev-low);
  --color-sev-low-bg: var(--sev-low-bg);
}

:root {
  --canvas: #f7f5f0;
  --canvas-elevated: #fdfcfa;
  --surface: #ffffff;
  --surface-hover: #f1efe8;
  --surface-selected: #eae6da;
  --hairline: #e3ddd0;
  --hairline-strong: #cec5b2;

  --ink: #17181a;
  --ink-muted: #5c5d54;
  --ink-faint: #92948a;

  --accent: #2c5aa3;
  --accent-bg: rgba(44, 90, 163, 0.08);

  --sev-high: #b7302f;
  --sev-high-bg: rgba(183, 48, 47, 0.07);
  --sev-medium: #96650f;
  --sev-medium-bg: rgba(150, 101, 15, 0.08);
  --sev-low: #1e7a4c;
  --sev-low-bg: rgba(30, 122, 76, 0.07);

  /* Sequential ramp — magnitude, one hue, light -> dark. Dashboard heatmap
     only (Task 15); referenced directly as var(--seq-N), not a Tailwind
     color utility. Validated against this surface (#ffffff) with
     dataviz's ordinal-ramp check: light-end contrast 2.11:1, monotone L,
     single hue (spread 3°). */
  --seq-1: #86b6ef;
  --seq-2: #5598e7;
  --seq-3: #2a78d6;
  --seq-4: #1c5cab;
  --seq-5: #104281;

  /* Opacity of the ambient WaveBackground layer behind Dashboard/Console. */
  --wave-ambient-opacity: 0.06;

  color-scheme: light;
}

:root.dark {
  --canvas: #0a0b0d;
  --canvas-elevated: #101216;
  --surface: #15171c;
  --surface-hover: #1c1f26;
  --surface-selected: #232733;
  --hairline: #262a33;
  --hairline-strong: #363c49;

  --ink: #f2f1ec;
  --ink-muted: #a3a598;
  --ink-faint: #6b6d64;

  --accent: #7ba6e8;
  --accent-bg: rgba(123, 166, 232, 0.12);

  --sev-high: #ef6a68;
  --sev-high-bg: rgba(239, 106, 104, 0.13);
  --sev-medium: #e4b15a;
  --sev-medium-bg: rgba(228, 177, 90, 0.13);
  --sev-low: #56d199;
  --sev-low-bg: rgba(86, 209, 153, 0.12);

  /* Validated against surface #15171c: light-end (darkest step) contrast
     2.21:1, monotone L, single hue (spread 3°). */
  --seq-1: #184f95;
  --seq-2: #256abf;
  --seq-3: #3987e5;
  --seq-4: #6da7ec;
  --seq-5: #9ec5f4;

  --wave-ambient-opacity: 0.14;

  color-scheme: dark;
}

* {
  border-color: var(--hairline);
}

body {
  background: var(--canvas);
  color: var(--ink);
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
}

::selection {
  background: var(--accent-bg);
  color: var(--ink);
}

/* Visible keyboard focus everywhere — never remove this. */
:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  border-radius: 2px;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

- [ ] **Step 3: Run the build**

```bash
cd web && npm run build
```

Expected: succeeds. Colors will visibly shift (existing components reference `--color-sev-*`, `--color-ink*`, `--color-surface*`, `--color-hairline*` — all kept, just re-valued) but a few things will look temporarily off until later tasks land: `font-serif` classes (removed from `@theme`) fall back to Tailwind's built-in generic serif; `bg-agent-bg`/`text-agent` classes (removed from `@theme`) render unstyled until Task 2. Both are expected and fixed in later tasks — this task's job is only to land the tokens and confirm nothing fails to compile.

- [ ] **Step 4: Commit**

```bash
git add web/index.html web/src/index.css
git commit -m "feat(web): editorial design tokens (Space Grotesk/Inter/JetBrains Mono, warm-neutral palette)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: `ui/badge.tsx`

**Files:**
- Modify: `web/src/components/ui/badge.tsx`

**Interfaces:**
- Consumes: tokens from Task 1 (`--color-sev-*`, `--color-accent*`, `--color-surface-hover`, `--color-ink-muted`).
- Produces: `Badge` component, `BadgeProps`, variant keys **unchanged**: `"neutral" | "high" | "medium" | "low" | "agent"` (the `"agent"` key name is kept as-is — only its color implementation moves to the new `--color-accent`/`--color-accent-bg` tokens — so every existing call site in `QueueList.tsx`/`CaseFile.tsx` keeps compiling with zero edits needed at this step).

- [ ] **Step 1: Replace `web/src/components/ui/badge.tsx` in full**

```tsx
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium font-sans",
  {
    variants: {
      variant: {
        neutral: "bg-surface-hover text-ink-muted",
        high: "bg-sev-high-bg text-sev-high",
        medium: "bg-sev-medium-bg text-sev-medium",
        low: "bg-sev-low-bg text-sev-low",
        agent: "bg-accent-bg text-accent",
      },
    },
    defaultVariants: { variant: "neutral" },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}
```

Changes from the current file: dropped `uppercase tracking-wide font-mono` (the redesign reserves monospace/all-caps for genuine data, not UI chrome — badge text now renders in whatever case the caller passes, which is already lowercase everywhere it's used); `agent` variant repointed from the removed `--color-agent*` tokens to `--color-accent*`.

- [ ] **Step 2: Run the build**

```bash
cd web && npm run build
```

Expected: succeeds.

- [ ] **Step 3: Visual check**

```bash
npm run dev
```

Open the app, select a queued case — badges (queue-row action tag, risk-factor severity tags, tools-consulted tags) should render as soft-filled pills in sentence case, not shouting uppercase mono. The `agent`-variant tools-consulted badges should now be a muted blue, not the old cyan.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/ui/badge.tsx
git commit -m "feat(web): restyle Badge — pill shape, sentence case, accent tokens

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: `ui/button.tsx`

**Files:**
- Modify: `web/src/components/ui/button.tsx`

**Interfaces:**
- Consumes: tokens from Task 1.
- Produces: `Button` component, `ButtonProps`, variant keys **unchanged**: `"default" | "approve" | "deny" | "escalate" | "outline" | "ghost"`; size keys **unchanged**: `"default" | "sm" | "lg"`.

- [ ] **Step 1: Replace `web/src/components/ui/button.tsx` in full**

```tsx
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium font-sans transition-colors duration-150 disabled:pointer-events-none disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed",
  {
    variants: {
      variant: {
        default: "bg-ink text-canvas hover:opacity-90",
        approve: "bg-sev-low text-canvas hover:opacity-90",
        deny: "bg-sev-high text-canvas hover:opacity-90",
        escalate: "bg-sev-medium text-canvas hover:opacity-90",
        outline: "border border-hairline-strong text-ink hover:bg-surface-hover",
        ghost: "text-ink-muted hover:text-ink hover:bg-surface-hover",
      },
      size: {
        default: "h-10 px-5",
        sm: "h-8 px-3.5 text-xs",
        lg: "h-12 px-7 text-base",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />
}
```

Changes from the current file: `text-canvas` is kept deliberately on the colored variants — `canvas` is near-white in light mode and near-black in dark mode, so it stays high-contrast against a colored fill in both themes without a separate dark-mode override. Sizes grew slightly (`h-9`→`h-10`, `px-4`→`px-5`, etc.) for the "generous whitespace" direction.

- [ ] **Step 2: Run the build**

```bash
cd web && npm run build
```

Expected: succeeds.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/ui/button.tsx
git commit -m "feat(web): restyle Button — larger touch targets, new tokens

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: `ui/card.tsx`

**Files:**
- Modify: `web/src/components/ui/card.tsx`

**Interfaces:**
- Consumes: tokens from Task 1.
- Produces: `Card`, `CardHeader`, `CardTitle`, `CardContent` — all four are currently unused anywhere outside this file (verified by repo-wide grep), so this task is free to change their internals without touching any call site. Later tasks (10–15) newly consume all four: `Card` (bordered container, accepts `className`/children directly, no mandatory sub-parts), `CardHeader`/`CardContent` (padded wrapper divs), `CardTitle` (sentence-case label with a short accent-colored dash before the text — this is the redesign's "signature" section-label treatment, reused everywhere a label like "Summary" or "Risk factors" appears).

- [ ] **Step 1: Replace `web/src/components/ui/card.tsx` in full**

```tsx
import * as React from "react"
import { cn } from "@/lib/utils"

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-lg border border-hairline bg-surface", className)}
      {...props}
    />
  )
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-6 py-5", className)} {...props} />
}

export function CardTitle({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h2
      className={cn("flex items-center gap-2.5 text-[13px] font-semibold text-ink-muted", className)}
      {...props}
    >
      <span className="h-px w-3.5 shrink-0 bg-accent" aria-hidden />
      {children}
    </h2>
  )
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-6 py-5", className)} {...props} />
}
```

- [ ] **Step 2: Run the build**

```bash
cd web && npm run build
```

Expected: succeeds (no call sites to break yet).

- [ ] **Step 3: Commit**

```bash
git add web/src/components/ui/card.tsx
git commit -m "feat(web): restyle Card family — CardTitle carries the accent-dash section-label treatment

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: `ui/input.tsx`

**Files:**
- Modify: `web/src/components/ui/input.tsx`

**Interfaces:**
- Consumes: tokens from Task 1.
- Produces: `Input`, `Textarea` — unchanged props (both spread `React.InputHTMLAttributes`/`React.TextareaHTMLAttributes` and accept `className`).

- [ ] **Step 1: Replace `web/src/components/ui/input.tsx` in full**

```tsx
import * as React from "react"
import { cn } from "@/lib/utils"

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "flex h-10 w-full rounded-md border border-hairline-strong bg-canvas px-3.5 text-sm font-sans text-ink placeholder:text-ink-faint focus-visible:outline-none disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}

export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "flex min-h-24 w-full rounded-md border border-hairline-strong bg-canvas px-3.5 py-2.5 text-sm font-sans text-ink placeholder:text-ink-faint focus-visible:outline-none disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}
```

`bg-canvas` (rather than `bg-surface`) is deliberate: inputs usually sit inside a white `Card`/`CardContent` (`bg-surface`), so the slightly-warmer `canvas` tone reads as a subtly recessed field, same idea as the original design.

- [ ] **Step 2: Run the build**

```bash
cd web && npm run build
```

Expected: succeeds.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/ui/input.tsx
git commit -m "feat(web): restyle Input/Textarea — larger targets, canvas-recessed fields

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 6: Install new frontend dependencies

**Files:**
- Modify: `web/package.json`, `web/package-lock.json`

**Interfaces:**
- Produces: `simplex-noise` (consumed by Task 7's `WaveBackground`), `framer-motion` (consumed by Tasks 13/14/15's `Console`/`Home`/`Dashboard`).

- [ ] **Step 1: Install**

```bash
cd web && npm install simplex-noise framer-motion
```

- [ ] **Step 2: Run the build**

```bash
npm run build
```

Expected: succeeds (nothing imports the new packages yet — this step only confirms the install didn't break anything).

- [ ] **Step 3: Commit**

```bash
git add web/package.json web/package-lock.json
git commit -m "chore(web): add simplex-noise and framer-motion

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 7: `WaveBackground` component

**Files:**
- Create: `web/src/components/WaveBackground.tsx`

**Interfaces:**
- Consumes: `simplex-noise`'s `createNoise2D` (Task 6); CSS custom properties `--ink`/`--accent` via `var()` defaults (Task 1).
- Produces: `WaveBackground` component with props `{ className?: string; strokeColor?: string; pointerSize?: number; ambient?: boolean }`. Consumed by Task 14 (`Home`, full expression, `ambient` omitted) and Task 16 (`App` shell, `ambient` set, low opacity via the `--wave-ambient-opacity` token from Task 1).

This is a port of the supplied `wave-background.tsx` reference component (mouse/touch-reactive noise-driven SVG line field), re-themed onto CSS custom properties instead of hardcoded black/white, with an added `ambient` mode (lower amplitude, no mouse/touch tracking, no pointer dot — for use as a quiet background layer behind working screens) and an early return under `prefers-reduced-motion: reduce`.

- [ ] **Step 1: Create `web/src/components/WaveBackground.tsx`**

```tsx
import * as React from "react"
import { useEffect, useRef } from "react"
import { createNoise2D } from "simplex-noise"

interface Point {
  x: number
  y: number
  wave: { x: number; y: number }
  cursor: { x: number; y: number; vx: number; vy: number }
}

interface WaveBackgroundProps {
  className?: string
  strokeColor?: string
  pointerSize?: number
  /**
   * Quiet mode: lower amplitude, no pointer tracking, no pointer dot — used
   * as a low-opacity background layer behind working screens (Dashboard,
   * Console). Omit for the full expressive hero treatment (Home).
   */
  ambient?: boolean
}

export function WaveBackground({
  className = "",
  strokeColor = "var(--ink)",
  pointerSize = 0.5,
  ambient = false,
}: WaveBackgroundProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const svgRef = useRef<SVGSVGElement>(null)
  const mouseRef = useRef({
    x: -10,
    y: 0,
    lx: 0,
    ly: 0,
    sx: 0,
    sy: 0,
    v: 0,
    vs: 0,
    a: 0,
    set: false,
  })
  const pathsRef = useRef<SVGPathElement[]>([])
  const linesRef = useRef<Point[][]>([])
  const noiseRef = useRef<((x: number, y: number) => number) | null>(null)
  const rafRef = useRef<number | null>(null)
  const boundingRef = useRef<DOMRect | null>(null)

  useEffect(() => {
    if (!containerRef.current || !svgRef.current) return
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return

    noiseRef.current = createNoise2D()
    setSize()
    setLines()

    window.addEventListener("resize", onResize)
    if (!ambient) {
      window.addEventListener("mousemove", onMouseMove)
      containerRef.current.addEventListener("touchmove", onTouchMove, { passive: false })
    }

    rafRef.current = requestAnimationFrame(tick)

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      window.removeEventListener("resize", onResize)
      window.removeEventListener("mousemove", onMouseMove)
      containerRef.current?.removeEventListener("touchmove", onTouchMove)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const setSize = () => {
    if (!containerRef.current || !svgRef.current) return
    boundingRef.current = containerRef.current.getBoundingClientRect()
    const { width, height } = boundingRef.current
    svgRef.current.style.width = `${width}px`
    svgRef.current.style.height = `${height}px`
  }

  const setLines = () => {
    if (!svgRef.current || !boundingRef.current) return
    const { width, height } = boundingRef.current
    linesRef.current = []

    pathsRef.current.forEach((path) => path.remove())
    pathsRef.current = []

    const gap = ambient ? 16 : 8
    const oWidth = width + 200
    const oHeight = height + 30
    const totalLines = Math.ceil(oWidth / gap)
    const totalPoints = Math.ceil(oHeight / gap)
    const xStart = (width - gap * totalLines) / 2
    const yStart = (height - gap * totalPoints) / 2

    for (let i = 0; i < totalLines; i++) {
      const points: Point[] = []
      for (let j = 0; j < totalPoints; j++) {
        points.push({
          x: xStart + gap * i,
          y: yStart + gap * j,
          wave: { x: 0, y: 0 },
          cursor: { x: 0, y: 0, vx: 0, vy: 0 },
        })
      }

      const path = document.createElementNS("http://www.w3.org/2000/svg", "path")
      path.setAttribute("fill", "none")
      path.setAttribute("stroke", strokeColor)
      path.setAttribute("stroke-width", "1")
      svgRef.current!.appendChild(path)
      pathsRef.current.push(path)
      linesRef.current.push(points)
    }
  }

  const onResize = () => {
    setSize()
    setLines()
  }

  const onMouseMove = (e: MouseEvent) => updateMousePosition(e.pageX, e.pageY)

  const onTouchMove = (e: TouchEvent) => {
    e.preventDefault()
    const touch = e.touches[0]
    updateMousePosition(touch.clientX, touch.clientY)
  }

  const updateMousePosition = (x: number, y: number) => {
    if (!boundingRef.current) return
    const mouse = mouseRef.current
    mouse.x = x - boundingRef.current.left
    mouse.y = y - boundingRef.current.top + window.scrollY

    if (!mouse.set) {
      mouse.sx = mouse.x
      mouse.sy = mouse.y
      mouse.lx = mouse.x
      mouse.ly = mouse.y
      mouse.set = true
    }

    if (containerRef.current) {
      containerRef.current.style.setProperty("--x", `${mouse.sx}px`)
      containerRef.current.style.setProperty("--y", `${mouse.sy}px`)
    }
  }

  const movePoints = (time: number) => {
    const { current: lines } = linesRef
    const { current: mouse } = mouseRef
    const { current: noise } = noiseRef
    if (!noise) return

    const amplitude = ambient ? 3 : 8

    lines.forEach((points) => {
      points.forEach((p) => {
        const move =
          noise((p.x + time * 0.008) * 0.003, (p.y + time * 0.003) * 0.002) * amplitude

        p.wave.x = Math.cos(move) * (ambient ? 5 : 12)
        p.wave.y = Math.sin(move) * (ambient ? 3 : 6)

        if (ambient) return

        const dx = p.x - mouse.sx
        const dy = p.y - mouse.sy
        const d = Math.hypot(dx, dy)
        const l = Math.max(175, mouse.vs)

        if (d < l) {
          const s = 1 - d / l
          const f = Math.cos(d * 0.001) * s
          p.cursor.vx += Math.cos(mouse.a) * f * l * mouse.vs * 0.00035
          p.cursor.vy += Math.sin(mouse.a) * f * l * mouse.vs * 0.00035
        }

        p.cursor.vx += (0 - p.cursor.x) * 0.01
        p.cursor.vy += (0 - p.cursor.y) * 0.01
        p.cursor.vx *= 0.95
        p.cursor.vy *= 0.95
        p.cursor.x += p.cursor.vx
        p.cursor.y += p.cursor.vy
        p.cursor.x = Math.min(50, Math.max(-50, p.cursor.x))
        p.cursor.y = Math.min(50, Math.max(-50, p.cursor.y))
      })
    })
  }

  const moved = (point: Point, withCursorForce = true) => ({
    x: point.x + point.wave.x + (withCursorForce ? point.cursor.x : 0),
    y: point.y + point.wave.y + (withCursorForce ? point.cursor.y : 0),
  })

  const drawLines = () => {
    const { current: lines } = linesRef
    const { current: paths } = pathsRef

    lines.forEach((points, lIndex) => {
      if (points.length < 2 || !paths[lIndex]) return
      const first = moved(points[0], false)
      let d = `M ${first.x} ${first.y}`
      for (let i = 1; i < points.length; i++) {
        const current = moved(points[i])
        d += `L ${current.x} ${current.y}`
      }
      paths[lIndex].setAttribute("d", d)
    })
  }

  const tick = (time: number) => {
    const { current: mouse } = mouseRef
    mouse.sx += (mouse.x - mouse.sx) * 0.1
    mouse.sy += (mouse.y - mouse.sy) * 0.1

    const dx = mouse.x - mouse.lx
    const dy = mouse.y - mouse.ly
    const d = Math.hypot(dx, dy)

    mouse.v = d
    mouse.vs += (d - mouse.vs) * 0.1
    mouse.vs = Math.min(100, mouse.vs)
    mouse.lx = mouse.x
    mouse.ly = mouse.y
    mouse.a = Math.atan2(dy, dx)

    movePoints(time)
    drawLines()

    rafRef.current = requestAnimationFrame(tick)
  }

  return (
    <div
      ref={containerRef}
      className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}
      style={{ "--x": "-0.5rem", "--y": "50%" } as React.CSSProperties}
    >
      <svg ref={svgRef} className="block h-full w-full" xmlns="http://www.w3.org/2000/svg" />
      {!ambient && (
        <div
          className="absolute left-0 top-0 rounded-full"
          style={{
            width: `${pointerSize}rem`,
            height: `${pointerSize}rem`,
            background: strokeColor,
            transform: "translate3d(calc(var(--x) - 50%), calc(var(--y) - 50%), 0)",
            willChange: "transform",
          }}
        />
      )}
    </div>
  )
}
```

Notable deltas from the supplied reference: default colors are CSS variables (`var(--ink)`) instead of hardcoded `#ffffff`/`#000000`; the `backgroundColor` prop is dropped (this component is always transparent — the call site supplies its own backdrop); the whole thing is `pointer-events-none` so it never blocks clicks on content stacked above it (mouse tracking uses `window`-level listeners, not the container, so this doesn't break interactivity); the `ambient` prop gates amplitude, line density, and mouse physics; a `prefers-reduced-motion` check skips animation setup entirely.

- [ ] **Step 2: Run the build**

```bash
cd web && npm run build
```

Expected: succeeds. (Nothing imports `WaveBackground` yet — this only confirms the file itself compiles.)

- [ ] **Step 3: Commit**

```bash
git add web/src/components/WaveBackground.tsx
git commit -m "feat(web): add WaveBackground (ported wave-noise component, token-themed, ambient mode)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 8: Backend — `GET /investigations/stats`

**Files:**
- Modify: `api/routes/investigations.py`

**Interfaces:**
- Consumes: `Investigation` model (`api/models/investigation.py`) — `status`, `risk_score`, `report` (JSON, may be `None`) fields. No schema changes.
- Produces: `GET /investigations/stats` → `InvestigationStats` JSON. Consumed by Task 9's frontend `api.getStats()`.

```json
{
  "total": 5,
  "by_status": { "approved": 3, "pending_review": 2 },
  "by_recommended_action": { "deny": 1, "escalate": 1, "approve": 3 },
  "by_confidence": { "high": 4, "medium": 1 },
  "risk_score_histogram": [
    { "label": "0–20%", "min": 0.0, "max": 0.2, "count": 0, "by_recommended_action": {} },
    { "label": "20–40%", "min": 0.2, "max": 0.4, "count": 0, "by_recommended_action": {} },
    { "label": "40–60%", "min": 0.4, "max": 0.6, "count": 5, "by_recommended_action": { "deny": 1, "escalate": 1, "approve": 3 } },
    { "label": "60–80%", "min": 0.6, "max": 0.8, "count": 0, "by_recommended_action": {} },
    { "label": "80–100%", "min": 0.8, "max": 1.0, "count": 0, "by_recommended_action": {} }
  ]
}
```

**Critical ordering note:** FastAPI matches routes in registration order. `/{investigation_id}` is typed `int`, so a request to `/investigations/stats` would otherwise match that route first and 422 (`"stats"` isn't a valid int). The new route **must** be registered before `@router.get("/{investigation_id}", ...)` in the file.

- [ ] **Step 1: Add the `Dict` import**

In `api/routes/investigations.py`, find the existing import line:

```python
from typing import List, Optional
```

Replace with:

```python
from collections import Counter
from typing import Dict, List, Optional
```

- [ ] **Step 2: Insert the new route and its response models**

Insert this immediately after the `list_flagged` function (after its closing `return session.exec(statement).all()` line) and **before** `@router.get("/{investigation_id}", ...)`:

```python
RISK_BANDS = [
    (0.0, 0.2, "0–20%"),
    (0.2, 0.4, "20–40%"),
    (0.4, 0.6, "40–60%"),
    (0.6, 0.8, "60–80%"),
    (0.8, 1.0, "80–100%"),
]


class RiskBandStats(BaseModel):
    label: str
    min: float
    max: float
    count: int
    by_recommended_action: Dict[str, int]


class InvestigationStats(BaseModel):
    total: int
    by_status: Dict[str, int]
    by_recommended_action: Dict[str, int]
    by_confidence: Dict[str, int]
    risk_score_histogram: List[RiskBandStats]


@router.get("/stats", response_model=InvestigationStats)
def get_stats(session: Session = Depends(get_session)):
    """Aggregate counts for the dashboard — read-only, computed from the
    existing Investigation table, no schema change."""
    rows = session.exec(select(Investigation)).all()

    by_status = Counter(r.status for r in rows)
    by_recommended_action = Counter((r.report or {}).get("recommended_action", "none") for r in rows)
    by_confidence = Counter((r.report or {}).get("confidence", "none") for r in rows)

    histogram = []
    for low, high, label in RISK_BANDS:
        in_band = [
            r for r in rows
            if low <= r.risk_score < high or (high == 1.0 and r.risk_score == 1.0)
        ]
        band_actions = Counter((r.report or {}).get("recommended_action", "none") for r in in_band)
        histogram.append(
            RiskBandStats(
                label=label,
                min=low,
                max=high,
                count=len(in_band),
                by_recommended_action=dict(band_actions),
            )
        )

    return InvestigationStats(
        total=len(rows),
        by_status=dict(by_status),
        by_recommended_action=dict(by_recommended_action),
        by_confidence=dict(by_confidence),
        risk_score_histogram=histogram,
    )
```

Also update the file's module docstring (top of file) to add a line documenting the new route, next to the existing `GET  /investigations/flagged` line:

```
GET  /investigations/stats                  — aggregate counts for the dashboard
```

- [ ] **Step 3: Start the API server**

```bash
conda run -n lalitenv uvicorn api.main:app --port 8000 --app-dir /Volumes/Lalit/Projects/agentic-fraud-investigation-system
```

(Run in the background or a separate terminal — leave it running for the next step. `lalitenv` is this machine's conda env with `fastapi`/`sqlmodel`/`uvicorn` installed; substitute whatever env/venv actually has the API's dependencies if that's changed since this plan was written.)

- [ ] **Step 4: Curl the new endpoint and confirm the shape**

```bash
curl -s http://localhost:8000/investigations/stats | python3 -m json.tool
```

Expected: valid JSON matching the shape above — `total` is a non-negative integer, `by_status`/`by_recommended_action`/`by_confidence` are string→int maps, `risk_score_histogram` has exactly 5 entries in band order with `count` fields that sum to `total`.

- [ ] **Step 5: Confirm existing endpoints are unaffected**

```bash
curl -s http://localhost:8000/investigations/flagged | python3 -m json.tool | head -20
```

Expected: same response shape/behavior as before this task (a list of pending-review investigations) — this route's position in the file didn't move, only a new route was inserted above it.

Stop the server (`Ctrl-C` or kill the background process) once both checks pass.

- [ ] **Step 6: Commit**

```bash
git add api/routes/investigations.py
git commit -m "feat(api): add read-only GET /investigations/stats for the dashboard

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 9: Frontend stats types + API client

**Files:**
- Modify: `web/src/lib/types.ts`
- Modify: `web/src/lib/api.ts`

**Interfaces:**
- Consumes: the JSON shape from Task 8.
- Produces: `RiskBandStats`, `InvestigationStats` types; `api.getStats(): Promise<InvestigationStats>`. Consumed by Task 15's `Dashboard`.

- [ ] **Step 1: Append to `web/src/lib/types.ts`**

Add at the end of the file (after the existing `TransactionDetail` interface — every existing type in this file is untouched):

```ts
export interface RiskBandStats {
  label: string
  min: number
  max: number
  count: number
  by_recommended_action: Record<string, number>
}

export interface InvestigationStats {
  total: number
  by_status: Record<string, number>
  by_recommended_action: Record<string, number>
  by_confidence: Record<string, number>
  risk_score_histogram: RiskBandStats[]
}
```

- [ ] **Step 2: Update `web/src/lib/api.ts`**

Change the top import line from:

```ts
import type { AuditLogEntry, Investigation, TransactionDetail } from "./types"
```

to:

```ts
import type { AuditLogEntry, Investigation, InvestigationStats, TransactionDetail } from "./types"
```

Add a new entry to the `api` object (after `listFlagged`, alongside the other `request<T>` calls — every existing entry is untouched):

```ts
  getStats: () => request<InvestigationStats>("/investigations/stats"),
```

- [ ] **Step 3: Run the build**

```bash
cd web && npm run build
```

Expected: succeeds.

- [ ] **Step 4: Commit**

```bash
git add web/src/lib/types.ts web/src/lib/api.ts
git commit -m "feat(web): add InvestigationStats type and api.getStats()

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 10: `QueueList.tsx` redesign

**Files:**
- Modify: `web/src/components/QueueList.tsx`

**Interfaces:**
- Consumes: `Badge` (Task 2). Props **unchanged**: `{ investigations: Investigation[]; selectedId: number | null; onSelect: (id: number) => void }`.
- Produces: same as before — no change to what `App.tsx`/`Console.tsx` pass in or read out.

- [ ] **Step 1: Replace `web/src/components/QueueList.tsx` in full**

```tsx
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
```

- [ ] **Step 2: Run the build**

```bash
cd web && npm run build
```

Expected: succeeds.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/QueueList.tsx
git commit -m "feat(web): redesign QueueList — sentence case, accent selection rule

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 11: `CaseFile.tsx` redesign

**Files:**
- Modify: `web/src/components/CaseFile.tsx`

**Interfaces:**
- Consumes: `Badge` (Task 2), `Card`/`CardTitle` (Task 4), `DecisionPanel` (Task 12 — import path unchanged).
- Produces: same as before — props **unchanged**: `{ investigation: Investigation; onDecided: (updated: Investigation) => void }`. All data-fetching (`api.getTransaction` on mount) and state (`txn`, `showTrace`) are unchanged.

- [ ] **Step 1: Replace `web/src/components/CaseFile.tsx` in full**

```tsx
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
```

The `agent`-variant `Badge` call site is unchanged (Task 2 kept that variant key stable while repointing its color). The only logic in this file — the `useEffect` fetch, `showTrace` toggle, `onDecided`/`onDecide` wiring — is byte-for-byte the same as before; every edit here is markup/class only.

- [ ] **Step 2: Run the build**

```bash
cd web && npm run build
```

Expected: succeeds.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/CaseFile.tsx
git commit -m "feat(web): redesign CaseFile — display face for txn id/verdict, verdict as headline not badge

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 12: `DecisionPanel.tsx` redesign

**Files:**
- Modify: `web/src/components/DecisionPanel.tsx`

**Interfaces:**
- Consumes: `Button`, `Input`/`Textarea` (Tasks 3/5), `Card`/`CardTitle` (Task 4).
- Produces: same as before — props **unchanged**: `{ investigation: Investigation; onDecide: (decision: string, reviewer: string, notes: string) => Promise<void> }`.

- [ ] **Step 1: Replace `web/src/components/DecisionPanel.tsx` in full**

```tsx
import { useState } from "react"
import type { Investigation } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Input, Textarea } from "@/components/ui/input"
import { Card, CardTitle } from "@/components/ui/card"
import { formatRelativeTime } from "@/lib/format"

interface DecisionPanelProps {
  investigation: Investigation
  onDecide: (decision: string, reviewer: string, notes: string) => Promise<void>
}

const DECISION_LABELS: Record<string, string> = {
  approved: "Approved",
  rejected: "Rejected",
  more_investigation_requested: "More investigation requested",
}

export function DecisionPanel({ investigation, onDecide }: DecisionPanelProps) {
  const [reviewer, setReviewer] = useState("")
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
            onChange={(e) => setReviewer(e.target.value)}
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
```

`reviewer`/`notes`/`submitting`/`error` state and `handleDecide` are byte-for-byte unchanged — only markup/classes changed.

- [ ] **Step 2: Run the build**

```bash
cd web && npm run build
```

Expected: succeeds.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/DecisionPanel.tsx
git commit -m "feat(web): redesign DecisionPanel — Card-based container, restrained labels

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 13: Extract `Console.tsx`

**Files:**
- Create: `web/src/components/Console.tsx`

**Interfaces:**
- Consumes: `api` (`web/src/lib/api.ts`, unchanged), `Investigation` type, `QueueList` (Task 10), `CaseFile` (Task 11), `Button`/`Input` (Tasks 3/5), `framer-motion`'s `motion` (Task 6).
- Produces: `Console` component, no props. Consumed by Task 16's `App` shell.

This task moves the queue-loading state, launch-investigation state, and the aside/main layout **verbatim** out of today's `App.tsx` into a new file — no logic changes, only relocation plus the responsive/visual pass and a `framer-motion` transition (the approved spec calls for motion "used consistently across Home, Dashboard, and Console" — this is Console's share of it: the case file cross-fades in when the selected case changes). `App.tsx` itself is not touched until Task 16 (it still works exactly as today until then; `Console.tsx` is simply unused until that task wires it in).

- [ ] **Step 1: Create `web/src/components/Console.tsx`**

```tsx
import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { api } from "@/lib/api"
import type { Investigation } from "@/lib/types"
import { QueueList } from "@/components/QueueList"
import { CaseFile } from "@/components/CaseFile"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export function Console() {
  const [investigations, setInvestigations] = useState<Investigation[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [newTxnId, setNewTxnId] = useState("")
  const [launching, setLaunching] = useState(false)
  const [launchError, setLaunchError] = useState<string | null>(null)

  const loadQueue = () => {
    setLoading(true)
    api
      .listFlagged()
      .then((data) => {
        setInvestigations((prev) => {
          // keep any already-decided investigation currently open in view, so a
          // reviewer's just-submitted decision doesn't vanish from under them
          const openButDecided = prev.find((p) => p.id === selectedId && p.status !== "pending_review")
          return openButDecided ? [...data, openButDecided] : data
        })
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load queue"))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadQueue()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const selected = investigations.find((i) => i.id === selectedId) ?? null

  const handleLaunch = async () => {
    const txnId = newTxnId.trim()
    if (!txnId) return
    setLaunching(true)
    setLaunchError(null)
    try {
      const inv = await api.runInvestigation(txnId)
      setInvestigations((prev) => [inv, ...prev.filter((p) => p.id !== inv.id)])
      setSelectedId(inv.id)
      setNewTxnId("")
    } catch (e) {
      setLaunchError(e instanceof Error ? e.message : "Investigation failed")
    } finally {
      setLaunching(false)
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-hairline px-6">
        <span className="font-display text-lg font-semibold text-ink">Console</span>
        <div className="flex items-center gap-2">
          <Input
            value={newTxnId}
            onChange={(e) => setNewTxnId(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLaunch()}
            placeholder="TXN123456"
            className="h-9 w-40 font-mono text-xs"
          />
          <Button size="sm" variant="outline" onClick={handleLaunch} disabled={launching}>
            {launching ? "Investigating…" : "Investigate"}
          </Button>
        </div>
      </div>

      {launchError && (
        <div className="border-b border-hairline bg-sev-high-bg px-6 py-2.5">
          <p className="text-xs text-sev-high">{launchError}</p>
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <aside className="max-h-72 w-full shrink-0 overflow-y-auto border-b border-hairline md:h-auto md:max-h-none md:w-80 md:border-b-0 md:border-r">
          <div className="flex items-center justify-between border-b border-hairline px-5 py-4">
            <span className="text-[13px] font-semibold text-ink-muted">
              Queue
              {investigations.filter((i) => i.status === "pending_review").length > 0 &&
                ` (${investigations.filter((i) => i.status === "pending_review").length})`}
            </span>
            <button
              onClick={loadQueue}
              className="cursor-pointer text-xs text-ink-faint transition-colors duration-150 hover:text-ink-muted"
            >
              Refresh
            </button>
          </div>
          {loading ? (
            <p className="px-5 py-8 text-sm text-ink-faint">Loading queue…</p>
          ) : error ? (
            <p className="px-5 py-8 text-sm text-sev-high">{error}</p>
          ) : (
            <QueueList
              investigations={investigations.filter((i) => i.status === "pending_review")}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          )}
        </aside>

        <main className="flex-1 overflow-y-auto">
          {selected ? (
            <motion.div
              key={selected.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            >
              <CaseFile
                investigation={selected}
                onDecided={(updated) => {
                  setInvestigations((prev) => prev.map((i) => (i.id === updated.id ? updated : i)))
                }}
              />
            </motion.div>
          ) : (
            <div className="flex h-full items-center justify-center px-8">
              <p className="max-w-sm text-center leading-relaxed text-ink-faint">
                Select a case from the queue to begin your review, or investigate a specific
                transaction using the box above.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
```

Responsive behavior added here (didn't exist before): below the `md` breakpoint, the queue becomes a height-capped, scrollable list stacked above the case file (`flex-col` + `max-h-72` aside) instead of a fixed-width side rail — there wasn't a viable "fixed 320px sidebar + main" layout on a phone-width screen before this. The `motion.div key={selected.id}` wrapper is enter-only (no `AnimatePresence`/exit animation, deliberately — it's a light cross-fade when switching cases, not a full choreographed transition): giving it `selected.id` as a `key` is what makes framer-motion treat each new selection as a fresh element to animate in, and since `CaseFile` already resets/refetches its own state whenever `investigation.transaction_id` changes (its existing `useEffect`), this doesn't introduce any behavior beyond what already happened on every selection change.

- [ ] **Step 2: Run the build**

```bash
cd web && npm run build
```

Expected: succeeds (new unused file, doesn't affect the still-untouched `App.tsx`).

- [ ] **Step 3: Commit**

```bash
git add web/src/components/Console.tsx
git commit -m "feat(web): extract Console (queue + case file) from App.tsx, add responsive stacking

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 14: `Home.tsx`

**Files:**
- Create: `web/src/components/Home.tsx`

**Interfaces:**
- Consumes: `WaveBackground` (Task 7), `Button` (Task 3), `framer-motion`'s `motion` (Task 6).
- Produces: `Home` component with props `{ onEnterDashboard: () => void; onEnterConsole: () => void }`. Consumed by Task 16's `App` shell.

- [ ] **Step 1: Create `web/src/components/Home.tsx`**

```tsx
import { motion } from "framer-motion"
import { WaveBackground } from "@/components/WaveBackground"
import { Button } from "@/components/ui/button"

interface HomeProps {
  onEnterDashboard: () => void
  onEnterConsole: () => void
}

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12, delayChildren: 0.1 } },
}

const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
}

export function Home({ onEnterDashboard, onEnterConsole }: HomeProps) {
  return (
    <div className="relative flex-1 overflow-y-auto">
      <div className="relative flex min-h-full flex-col items-center justify-center px-6 py-20 text-center">
        <WaveBackground className="opacity-70" />
        <motion.div
          variants={container}
          initial="hidden"
          animate="show"
          className="relative z-10 flex max-w-2xl flex-col items-center gap-6"
        >
          <motion.span variants={item} className="text-[13px] font-semibold text-ink-muted">
            Fraud Investigation Console
          </motion.span>
          <motion.h1
            variants={item}
            className="font-display text-5xl font-bold leading-[1.05] tracking-tight text-ink sm:text-6xl"
          >
            An agent investigates.
            <br />
            You decide.
          </motion.h1>
          <motion.p variants={item} className="max-w-lg text-base leading-relaxed text-ink-muted sm:text-lg">
            Every transaction that crosses the risk threshold gets a full investigation —
            device graphs, counterparty history, geo signals — argued into a recommendation.
            Nothing is final until a reviewer signs it.
          </motion.p>
          <motion.div variants={item} className="mt-2 flex flex-wrap items-center justify-center gap-3">
            <Button size="lg" onClick={onEnterConsole}>
              Open the queue
            </Button>
            <Button size="lg" variant="outline" onClick={onEnterDashboard}>
              View portfolio dashboard
            </Button>
          </motion.div>
        </motion.div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Run the build**

```bash
cd web && npm run build
```

Expected: succeeds.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/Home.tsx
git commit -m "feat(web): add Home page — full wave hero, staggered entrance

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 15: `Dashboard.tsx`

**Files:**
- Create: `web/src/components/Dashboard.tsx`

**Interfaces:**
- Consumes: `api.getStats()` (Task 9), `InvestigationStats`/`RiskBandStats` types (Task 9), `Card`/`CardHeader`/`CardTitle`/`CardContent` (Task 4), `framer-motion`'s `motion` (Task 6), the `--seq-1`…`--seq-5` CSS variables (Task 1).
- Produces: `Dashboard` component, no props. Consumed by Task 16's `App` shell.

Chart design follows the `dataviz` skill: KPI counts are **stat tiles** (not charts — a handful of headline numbers), laid out in the asymmetric bento-grid *structure* borrowed from the supplied `features-8.tsx` reference (one large hero tile + four regular tiles; its marketing copy, decorative SVGs, and avatar stacks are not used). The risk-band × action breakdown is a **heatmap** (comparing magnitude across a grid — the correct form per `choosing-a-form.md`), colored with a single sequential hue (validated 5-step blue ramp from Task 1, `--seq-1`…`--seq-5`, light→dark = low→high count) — never the categorical deny/escalate/approve colors, which appear only as small identity dots beside the column headers (status colors "ship with icon + label, never color alone," per the skill). Every cell is directly labeled with its count (a small, ~20-cell matrix, read like a lookup table) and carries a native-tooltip + keyboard-focusable hit target; the grid is a literal `<table>`, which doubles as the "table view" accessibility fallback the skill requires.

- [ ] **Step 1: Create `web/src/components/Dashboard.tsx`**

```tsx
import { useEffect, useState } from "react"
import { motion } from "framer-motion"
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
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
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
```

- [ ] **Step 2: Run the build**

```bash
cd web && npm run build
```

Expected: succeeds.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/Dashboard.tsx
git commit -m "feat(web): add Dashboard — bento KPI tiles + risk/action heatmap

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 16: `App.tsx` shell

**Files:**
- Modify: `web/src/App.tsx`

**Interfaces:**
- Consumes: `Home` (Task 14), `Dashboard` (Task 15), `Console` (Task 13), `WaveBackground` (Task 7).
- Produces: the app's root component (default export), unchanged externally (still mounted by `main.tsx` with no props).

This is the last structural task — it replaces the old single-view shell (queue + case file inlined) with a three-view switcher. The `useTheme` hook is renamed internally from a `light`-tracking boolean to a `dark`-tracking one so bare `:root` (Task 1's light palette) is the default with no class needed, and toggling adds/removes `.dark` — this is the mechanism that makes light the primary mode.

- [ ] **Step 1: Replace `web/src/App.tsx` in full**

```tsx
import { useEffect, useState } from "react"
import { Home } from "@/components/Home"
import { Dashboard } from "@/components/Dashboard"
import { Console } from "@/components/Console"
import { WaveBackground } from "@/components/WaveBackground"

type View = "home" | "dashboard" | "console"

function useTheme() {
  const [dark, setDark] = useState(false)
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark)
  }, [dark])
  return { dark, toggle: () => setDark((d) => !d) }
}

function App() {
  const [view, setView] = useState<View>("home")
  const { dark, toggle } = useTheme()

  const navLinkClass = (active: boolean) =>
    `cursor-pointer rounded-md px-3 py-1.5 text-sm font-medium transition-colors duration-150 ${
      active ? "bg-surface-selected text-ink" : "text-ink-muted hover:bg-surface-hover hover:text-ink"
    }`

  return (
    <div className="relative flex h-screen flex-col bg-canvas">
      {view !== "home" && (
        <WaveBackground
          ambient
          strokeColor="var(--accent)"
          className="opacity-[var(--wave-ambient-opacity)]"
        />
      )}

      <header className="relative z-10 flex h-16 shrink-0 flex-wrap items-center justify-between gap-3 border-b border-hairline bg-canvas-elevated px-6">
        <div className="flex flex-wrap items-center gap-6">
          <button
            onClick={() => setView("home")}
            className="cursor-pointer font-display text-lg font-bold tracking-tight text-ink"
          >
            Fraud Console
          </button>
          <nav className="flex items-center gap-1">
            <button onClick={() => setView("dashboard")} className={navLinkClass(view === "dashboard")}>
              Dashboard
            </button>
            <button onClick={() => setView("console")} className={navLinkClass(view === "console")}>
              Console
            </button>
          </nav>
        </div>
        <button
          onClick={toggle}
          aria-label="Toggle theme"
          className="cursor-pointer rounded-md px-3 py-1.5 text-sm font-medium text-ink-muted transition-colors duration-150 hover:bg-surface-hover hover:text-ink"
        >
          {dark ? "Light" : "Dark"}
        </button>
      </header>

      <div className="relative z-10 flex min-h-0 flex-1">
        {view === "home" && (
          <Home onEnterDashboard={() => setView("dashboard")} onEnterConsole={() => setView("console")} />
        )}
        {view === "dashboard" && <Dashboard />}
        {view === "console" && <Console />}
      </div>
    </div>
  )
}

export default App
```

- [ ] **Step 2: Run the build**

```bash
cd web && npm run build
```

Expected: succeeds.

- [ ] **Step 3: Commit**

```bash
git add web/src/App.tsx
git commit -m "feat(web): App shell — Home/Dashboard/Console nav, light-primary theme toggle, ambient wave

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 17: Full-app verification pass

**Files:** none (verification only).

**Interfaces:** none — this task exercises the whole app built by Tasks 1–16.

- [ ] **Step 1: Start the backend**

```bash
conda run -n lalitenv uvicorn api.main:app --port 8000 --app-dir /Volumes/Lalit/Projects/agentic-fraud-investigation-system
```

- [ ] **Step 2: Start the frontend dev server**

```bash
cd web && npm run dev
```

- [ ] **Step 3: Walk through every view in light mode**

Open the printed local URL. Confirm:
- **Home** loads as the default view: full wave hero animates and reacts to the mouse; headline/subcopy/CTAs fade in staggered; clicking "Open the queue" goes to Console, "View portfolio dashboard" goes to Dashboard.
- **Dashboard**: KPI tiles show real numbers (not zeros unless the DB is genuinely empty); the heatmap renders 5 rows × 4 columns with counts, hovering a cell shows its tooltip, the legend strip is visible.
- **Console**: queue list on the left, selecting a case shows the case file with the transaction ID in the large display face, the verdict rendered as a colored headline word with a left rule (not a boxed badge), risk factors/mitigating factors/tools-consulted all render, the decision form at the bottom accepts a reviewer name and submits (Approve/Reject/Request more investigation) without error, and the queue updates afterward.
- Ambient wave is faintly visible behind Dashboard and Console (not distracting, doesn't block clicks — try clicking through where it overlaps a card).

- [ ] **Step 4: Toggle dark mode and repeat**

Click "Dark" in the header. Confirm the whole app (Home, Dashboard, Console) re-themes correctly — canvas/surface/ink/accent/severity colors all flip, nothing is left rendering the old near-black terminal palette or unstyled (no `bg-agent-bg`-class remnants, no serif fallback text).

- [ ] **Step 5: Resize to a narrow viewport (~375px wide)**

Confirm: header nav wraps without overlapping; Home's headline/CTAs stay legible and don't overflow; Dashboard's KPI grid collapses to one column; Console's queue list stacks above the case file (scrollable, height-capped) instead of squeezing into an unusably narrow sidebar.

- [ ] **Step 6: Final build**

```bash
cd web && npm run build
```

Expected: succeeds with no TypeScript errors.

- [ ] **Step 7: Stop both servers**

Stop the `npm run dev` and `uvicorn` processes (`Ctrl-C` each, or kill the backgrounded PIDs).

No commit for this task — it's verification only, over work already committed in Tasks 1–16.
