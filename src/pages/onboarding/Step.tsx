import { useTranslation } from "react-i18next";

/** One numbered instruction in a setup step. */
export function Step({
  n,
  title,
  body,
  children,
}: {
  n: number;
  title: string;
  body: string;
  children?: React.ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <li className="grid grid-cols-[2rem_minmax(0,1fr)] gap-x-3">
      <span aria-hidden className="pt-0.5 text-base font-bold tabular-nums text-[var(--color-accent)]">
        {n}
      </span>
      <div className="space-y-3">
        <div>
          <span className="sr-only">{t("onboarding.stepLabel", { n })}: </span>
          <h2 className="text-base font-semibold text-[var(--color-text-primary)]">{title}</h2>
          <p className="mt-1 text-sm text-[var(--color-text-secondary)] leading-relaxed">{body}</p>
        </div>
        {children}
      </div>
    </li>
  );
}

/** A screenshot of the real Chrome screen, framed so it reads as a picture. */
export function Shot({ src, alt, maxWidth }: { src: string; alt: string; maxWidth?: number }) {
  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      style={maxWidth ? { maxWidth } : undefined}
      className="block w-full h-auto rounded-[var(--radius-sm)] border border-[var(--color-border)]"
    />
  );
}
