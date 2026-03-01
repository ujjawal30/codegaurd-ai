import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Convert basic markdown (bold, numbered lists, line breaks) to HTML */
export function renderMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-foreground">$1</strong>')
    .replace(/`([^`]+)`/g, '<code class="text-xs px-1 py-0.5 rounded bg-muted font-mono">$1</code>')
    .replace(/^(\d+)\.\s/gm, '<br/><span class="text-emerald-500 font-medium">$1.</span> ')
    .replace(/\n/g, "<br/>");
}
