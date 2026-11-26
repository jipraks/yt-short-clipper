import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Search } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export interface ComboboxOption {
  value: string;
  label: string;
  /** Shorter text for the closed control, when the full label would not fit. */
  short?: string;
}

export interface ComboboxGroup {
  label?: string;
  options: ComboboxOption[];
}

/**
 * A searchable, grouped single choice that looks like the rest of the app,
 * for lists too long for a plain select (YouTube can offer 100+ subtitle
 * languages). Arrow keys move, Enter picks, Escape closes, typing filters.
 */
export function Combobox({
  label,
  value,
  groups,
  onChange,
  disabled,
  placeholder,
  searchPlaceholder,
  emptyText,
  triggerClassName,
  onOpenChange,
}: {
  /** Accessible name of the control. */
  label: string;
  value: string;
  groups: ComboboxGroup[];
  onChange: (value: string) => void;
  disabled?: boolean;
  /** Shown on the trigger when nothing is selected (or while disabled). */
  placeholder: string;
  searchPlaceholder: string;
  emptyText: string;
  triggerClassName?: string;
  onOpenChange?: (open: boolean) => void;
}) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const listRef = useRef<HTMLUListElement>(null);

  const selected = groups.flatMap((g) => g.options).find((o) => o.value === value);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return groups;
    return groups
      .map((g) => ({
        ...g,
        options: g.options.filter((o) => o.label.toLowerCase().includes(q) || o.value.toLowerCase().includes(q)),
      }))
      .filter((g) => g.options.length > 0);
  }, [groups, query]);
  const flat = useMemo(() => filtered.flatMap((g) => g.options), [filtered]);

  const setOpenState = (next: boolean) => {
    setOpen(next);
    onOpenChange?.(next);
    if (next) {
      setQuery("");
      const at = groups.flatMap((g) => g.options).findIndex((o) => o.value === value);
      setActive(Math.max(0, at));
    }
  };

  useEffect(() => {
    if (!open) return;
    listRef.current
      ?.querySelector<HTMLElement>(`[data-index="${active}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [active, open, flat]);

  const pick = (option: ComboboxOption) => {
    onChange(option.value);
    setOpenState(false);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => Math.min(flat.length - 1, i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(0, i - 1));
    } else if (e.key === "Home") {
      e.preventDefault();
      setActive(0);
    } else if (e.key === "End") {
      e.preventDefault();
      setActive(flat.length - 1);
    } else if (e.key === "Enter") {
      e.preventDefault();
      const option = flat[active];
      if (option) pick(option);
    }
  };

  let index = -1;
  return (
    <Popover open={open} onOpenChange={setOpenState}>
      <PopoverTrigger
        disabled={disabled}
        aria-label={`${label}: ${selected?.label ?? placeholder}`}
        className={cn("cursor-pointer disabled:cursor-not-allowed", triggerClassName)}
      >
        <span className="max-w-[14rem] truncate">{selected?.short ?? selected?.label ?? placeholder}</span>
        <ChevronDown aria-hidden className="h-4 w-4 shrink-0 text-[var(--color-text-muted)]" />
      </PopoverTrigger>
      <PopoverContent align="start" className="w-[min(320px,calc(100vw-2rem))] p-0">
        <div className="flex items-center gap-2 border-b border-[var(--color-border)] px-3">
          <Search aria-hidden className="h-4 w-4 shrink-0 text-[var(--color-text-muted)]" />
          <input
            autoFocus
            role="combobox"
            aria-expanded="true"
            aria-controls={`${id}-list`}
            aria-activedescendant={flat[active] ? `${id}-opt-${active}` : undefined}
            aria-label={label}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActive(0);
            }}
            onKeyDown={onKeyDown}
            placeholder={searchPlaceholder}
            className="h-11 min-w-0 flex-1 bg-transparent text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none"
          />
        </div>
        <ul
          ref={listRef}
          id={`${id}-list`}
          role="listbox"
          aria-label={label}
          className="max-h-[min(320px,50vh)] overflow-y-auto p-1.5"
        >
          {flat.length === 0 && (
            <li className="px-3 py-6 text-center text-sm text-[var(--color-text-muted)]">{emptyText}</li>
          )}
          {filtered.map((group, gi) => (
            <li key={group.label ?? gi} role="presentation">
              {group.label && (
                <p
                  role="presentation"
                  className="px-3 pt-2.5 pb-1 text-xs font-semibold text-[var(--color-text-muted)]"
                >
                  {group.label}
                </p>
              )}
              <ul role="group" aria-label={group.label}>
                {group.options.map((option) => {
                  index += 1;
                  const i = index;
                  const isSelected = option.value === value;
                  const isActive = i === active;
                  return (
                    <li
                      key={option.value}
                      id={`${id}-opt-${i}`}
                      data-index={i}
                      role="option"
                      aria-selected={isSelected}
                      onMouseMove={() => setActive(i)}
                      onClick={() => pick(option)}
                      className={cn(
                        "flex min-h-10 cursor-pointer items-center gap-2 rounded-[var(--radius-sm)] px-3 text-sm",
                        isActive ? "bg-[var(--color-bg-hover)] text-[var(--color-text-primary)]" : "text-[var(--color-text-secondary)]",
                      )}
                    >
                      <span className="flex-1 truncate">{option.label}</span>
                      {isSelected && <Check aria-hidden className="h-4 w-4 shrink-0 text-[var(--color-accent)]" />}
                    </li>
                  );
                })}
              </ul>
            </li>
          ))}
        </ul>
      </PopoverContent>
    </Popover>
  );
}
