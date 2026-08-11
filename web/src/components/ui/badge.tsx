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
