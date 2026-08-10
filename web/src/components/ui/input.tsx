import * as React from "react"
import { cn } from "@/lib/utils"

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "flex h-9 w-full rounded-md border border-hairline-strong bg-canvas px-3 text-sm font-sans text-ink placeholder:text-ink-faint focus-visible:outline-none disabled:opacity-50",
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
        "flex min-h-20 w-full rounded-md border border-hairline-strong bg-canvas px-3 py-2 text-sm font-sans text-ink placeholder:text-ink-faint focus-visible:outline-none disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}
