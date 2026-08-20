import type { ReactNode } from "react";

interface SettingRowProps {
  title: string;
  description?: string;
  children?: ReactNode;
  className?: string;
}

export function SettingRow({ title, description, children, className }: SettingRowProps) {
  return (
    <div
      className={`flex items-center justify-between gap-4 py-4 border-b border-[var(--color-border-light)] last:border-b-0 ${className ?? ""}`}
    >
      <div className="space-y-0.5 min-w-0">
        <p className="text-sm font-medium text-[var(--color-text-primary)]">{title}</p>
        {description && (
          <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">{description}</p>
        )}
      </div>
      {children && <div className="shrink-0">{children}</div>}
    </div>
  );
}

interface SettingSectionProps {
  title: string;
  description?: string;
  children: ReactNode;
}

export function SettingSection({ title, description, children }: SettingSectionProps) {
  return (
    <section className="space-y-1">
      <div className="space-y-0.5 mb-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
          {title}
        </h2>
        {description && (
          <p className="text-xs text-[var(--color-text-muted)]">{description}</p>
        )}
      </div>
      <div className="rounded-[var(--radius)] border border-[var(--color-border-light)] bg-[var(--color-bg-card)] px-4">
        {children}
      </div>
    </section>
  );
}
