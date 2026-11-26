import * as React from "react";
import { cn } from "@/lib/utils";

interface SwitchProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  disabled?: boolean;
  id?: string;
}

const Switch = React.forwardRef<HTMLButtonElement, SwitchProps>(
  ({ checked, onCheckedChange, disabled, id }, ref) => {
    return (
      <button
        ref={ref}
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onCheckedChange(!checked)}
        className={cn(
          "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer",
          checked ? "bg-[var(--color-accent)]" : "bg-[var(--color-border)]"
        )}
      >
        <span
          className={cn(
            "inline-block h-5 w-5 transform rounded-full shadow-[var(--shadow-sm)] transition-transform duration-200",
            checked
              ? "translate-x-[22px] bg-[var(--color-text-on-accent)]"
              : "translate-x-0.5 bg-[var(--color-text-secondary)]"
          )}
        />
      </button>
    );
  }
);
Switch.displayName = "Switch";

export { Switch };
