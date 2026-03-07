import { cn } from "@/lib/utils";
import type { SortDirection } from "@/lib/types";

import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Checkbox } from "@/components/ui/checkbox";
import { ArrowUpDown, ChevronDown, X } from "lucide-react";

interface FiltersBarProps {
  children: React.ReactNode;
  isFiltered: boolean;
  clearAll: () => void;
  filteredCount: number;
  totalCount: number;
}

interface MultiFilterPopoverProps {
  label: string;
  options: string[];
  selected: Set<string>;
  onChange: (next: Set<string>) => void;
}

interface SortButtonProps {
  direction: SortDirection;
  onClick: () => void;
  labels: { idle: string; asc: string; desc: string };
  /** Active accent colour — defaults to emerald */
  accent?: "emerald" | "blue";
}

const ACCENT = {
  emerald: "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
  blue: "border-blue-500/40 bg-blue-500/10 text-blue-400",
} as const;

export const FiltersBar = ({ children, isFiltered, clearAll, filteredCount, totalCount }: FiltersBarProps) => {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {children}

      {isFiltered && (
        <button
          onClick={clearAll}
          className="inline-flex items-center gap-1 rounded-md px-2.5 h-8 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <X className="w-3.5 h-3.5" />
          Clear
        </button>
      )}

      <span className="ml-auto text-xs text-muted-foreground">
        {isFiltered ? `Showing ${filteredCount} of ${totalCount}` : `${totalCount} tasks`}
      </span>
    </div>
  );
};

export const MultiFilterPopover = ({ label, options, selected, onChange }: MultiFilterPopoverProps) => {
  const toggle = (value: string) => {
    const next = new Set(selected);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    onChange(next);
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          className={`inline-flex items-center gap-1.5 rounded-md border px-3 h-8 text-xs transition-colors ${
            selected.size > 0
              ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
              : "border-input bg-transparent text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          }`}
        >
          {label}
          {selected.size > 0 && (
            <Badge className="ml-1 h-4 min-w-4 px-1 text-[10px] bg-emerald-500/20 text-emerald-400 border-0">{selected.size}</Badge>
          )}
          <ChevronDown className="w-3.5 h-3.5 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-48 p-2" align="start">
        <div className="space-y-1">
          {options.map((opt) => (
            <label
              key={opt}
              className="flex items-center gap-2 rounded-sm px-2 py-1.5 text-sm cursor-pointer hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              <Checkbox checked={selected.has(opt)} onCheckedChange={() => toggle(opt)} className="h-3.5 w-3.5" />
              <span className={cn("text-xs", opt.includes(".") ? "font-mono" : "capitalize")}>{opt.replace("_", " ")}</span>
            </label>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
};

export const SortButton = ({ direction, onClick, labels, accent = "emerald" }: SortButtonProps) => {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-md border px-3 h-8 text-xs transition-colors ${
        direction !== "none" ? ACCENT[accent] : "border-input bg-transparent text-muted-foreground hover:bg-accent hover:text-accent-foreground"
      }`}
    >
      <ArrowUpDown className="w-3.5 h-3.5" />
      {direction === "none" ? labels.idle : direction === "desc" ? labels.desc : labels.asc}
    </button>
  );
};
