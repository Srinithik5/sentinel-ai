import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

export interface PaginationProps {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  className?: string;
}

function getPageNumbers(page: number, pageCount: number): (number | "ellipsis")[] {
  if (pageCount <= 7) {
    return Array.from({ length: pageCount }, (_, index) => index + 1);
  }

  const pages = new Set<number>([1, pageCount, page, page - 1, page + 1]);
  const sorted = [...pages].filter((value) => value >= 1 && value <= pageCount).sort((a, b) => a - b);

  const result: (number | "ellipsis")[] = [];
  sorted.forEach((value, index) => {
    if (index > 0 && value - sorted[index - 1] > 1) {
      result.push("ellipsis");
    }
    result.push(value);
  });
  return result;
}

export function Pagination({ page, pageCount, onPageChange, className }: PaginationProps) {
  if (pageCount <= 1) return null;

  return (
    <nav
      aria-label="Pagination"
      className={cn("flex items-center justify-between gap-4 border-t border-slate-200 px-4 py-3", className)}
    >
      <Button
        variant="outline"
        size="sm"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        aria-label="Previous page"
      >
        <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        Previous
      </Button>

      <ul className="flex items-center gap-1">
        {getPageNumbers(page, pageCount).map((value, index) =>
          value === "ellipsis" ? (
            <li key={`ellipsis-${index}`} className="px-2 text-sm text-slate-400" aria-hidden="true">
              …
            </li>
          ) : (
            <li key={value}>
              <button
                type="button"
                onClick={() => onPageChange(value)}
                aria-current={value === page ? "page" : undefined}
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-md text-sm font-medium transition-colors",
                  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
                  value === page ? "bg-primary text-white" : "text-slate-600 hover:bg-slate-100",
                )}
              >
                {value}
              </button>
            </li>
          ),
        )}
      </ul>

      <Button
        variant="outline"
        size="sm"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= pageCount}
        aria-label="Next page"
      >
        Next
        <ChevronRight className="h-4 w-4" aria-hidden="true" />
      </Button>
    </nav>
  );
}