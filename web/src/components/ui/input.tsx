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
