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
        default: "h-9 px-4",
        sm: "h-8 px-3 text-xs",
        lg: "h-11 px-6 text-base",
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
