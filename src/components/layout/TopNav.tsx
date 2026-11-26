import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ChevronDown, Settings } from "lucide-react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { toast } from "sonner";
import { Wordmark } from "@/components/brand/Wordmark";
import { Popover, PopoverContent, PopoverTrigger, PopoverClose } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { AdvertiseDialog } from "@/components/AdvertiseDialog";
import { TopupDialog } from "@/components/TopupDialog";
import { useAppStore } from "@/stores/appStore";
import { useConfigStore } from "@/stores/configStore";
import { chatModels, useAccountStore } from "@/stores/accountStore";
import { DEFAULT_MENU_ITEMS, fetchMenu, readCachedMenu, type MenuItem } from "@/hooks/menu";
import { errorMessage } from "@/hooks/account";
import { APP_VERSION } from "@/config/version";
import { formatIdr, formatUsd } from "@/utils/format";
import { cn } from "@/lib/utils";

const ROUTES = [
  { to: "/", key: "create" },
  { to: "/clips", key: "clips" },
  { to: "/library", key: "library" },
  { to: "/ai-models", key: "ai" },
  { to: "/repliz", key: "repliz" },
] as const;

const pill = "h-9 rounded-full px-4 text-sm font-medium transition-colors";
const focus =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)] focus-visible:ring-offset-2";

/**
 * The app's navigation: one floating pill at the top, in place of the old
 * sidebar. Pages on the left, help and the AI balance on the right.
 */
export function TopNav() {
  const { t } = useTranslation();
  return (
    <header className="relative z-40 flex shrink-0 justify-center px-4 pt-4 pb-2">
      <nav
        aria-label={t("nav.label")}
        // Pills are 36px, under the 44px touch size: this is a desktop app
        // driven by a mouse, and the window cannot be narrower than 900px.
        // Below that (never in the app) the pill scrolls instead of wrapping.
        className="flex max-w-full items-center gap-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden rounded-full border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-1.5 shadow-[var(--shadow)]"
      >
        <NavLink to="/" className={cn("shrink-0 rounded-full px-3", focus)} aria-label={t("common.appName")}>
          <Wordmark className="text-lg" />
        </NavLink>
        <Divider />
        <div className="flex shrink-0 items-center gap-0.5 rounded-full bg-[var(--color-bg-secondary)] p-1">
          {ROUTES.map((r) => (
            <NavLink
              key={r.to}
              to={r.to}
              end={r.to === "/"}
              className={({ isActive }) =>
                cn(
                  "inline-flex h-8 items-center rounded-full px-4 text-sm font-medium transition-colors",
                  focus,
                  isActive
                    ? "bg-[var(--color-bg-hover)] text-[var(--color-text-primary)]"
                    : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]",
                )
              }
            >
              {t(`nav.${r.key}`)}
            </NavLink>
          ))}
        </div>
        <Divider />
        <HelpMenu />
        <BalanceChip />
        <NavLink
          to="/settings"
          aria-label={t("nav.settings")}
          title={t("nav.settings")}
          className={({ isActive }) =>
            cn(
              "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition-colors",
              focus,
              isActive
                ? "bg-[var(--color-bg-hover)] text-[var(--color-text-primary)]"
                : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]",
            )
          }
        >
          <Settings aria-hidden className="h-[18px] w-[18px]" />
        </NavLink>
      </nav>
    </header>
  );
}

function Divider() {
  return <span aria-hidden className="mx-1 h-5 w-px shrink-0 bg-[var(--color-border)]" />;
}

/** Links the server publishes (tutorials, community), the ad slot, and the version. */
function HelpMenu() {
  const { t } = useTranslation();
  const availableUpdate = useAppStore((s) => s.availableUpdate);
  const [items, setItems] = useState<MenuItem[]>(() => readCachedMenu() ?? DEFAULT_MENU_ITEMS);
  const [advertise, setAdvertise] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchMenu().then((fresh) => {
      if (!cancelled && fresh) setItems(fresh);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const itemClass =
    "flex min-h-10 cursor-pointer select-none items-center rounded-[var(--radius-sm)] px-3 text-sm text-[var(--color-text-secondary)] outline-none data-[highlighted]:bg-[var(--color-bg-hover)] data-[highlighted]:text-[var(--color-text-primary)]";

  return (
    <>
      <DropdownMenu.Root>
        <DropdownMenu.Trigger
          className={cn(
            pill,
            "inline-flex shrink-0 items-center gap-1 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] data-[state=open]:bg-[var(--color-bg-hover)] data-[state=open]:text-[var(--color-text-primary)] cursor-pointer",
            focus,
          )}
        >
          {t("nav.help")}
          <ChevronDown aria-hidden className="h-4 w-4" />
        </DropdownMenu.Trigger>
        <DropdownMenu.Portal>
          <DropdownMenu.Content
            align="end"
            sideOffset={8}
            className="z-50 min-w-[220px] rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg-card)] p-1.5 shadow-[var(--shadow-lg)]"
          >
            {items.map((item) => (
              <DropdownMenu.Item
                key={item.id}
                className={itemClass}
                onSelect={() => openUrl(item.url).catch(console.error)}
              >
                {item.label}
              </DropdownMenu.Item>
            ))}
            <DropdownMenu.Separator className="my-1.5 h-px bg-[var(--color-border)]" />
            <DropdownMenu.Item className={itemClass} onSelect={() => setAdvertise(true)}>
              {t("nav.advertise")}
            </DropdownMenu.Item>
            {availableUpdate ? (
              <DropdownMenu.Item
                className={cn(itemClass, "text-[var(--color-accent)]")}
                onSelect={() => openUrl(availableUpdate.download_url).catch(console.error)}
              >
                {t("nav.update", { version: availableUpdate.version })}
              </DropdownMenu.Item>
            ) : null}
            <p className="px-3 pt-1.5 pb-1 text-xs text-[var(--color-text-muted)]">
              {t("nav.version", { version: APP_VERSION })}
            </p>
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
      {advertise && <AdvertiseDialog onClose={() => setAdvertise(false)} />}
    </>
  );
}

/**
 * Which AI is in use and, for the in-app wallet, what is left. The chip opens
 * the balance, the model in use, and a top-up. Changing provider stays on the
 * AI page: it is a bigger decision than one click away from a running job.
 */
function BalanceChip() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const source = useConfigStore((s) => s.config.ai.source);
  const configLoaded = useConfigStore((s) => s.loaded);
  const { ready, activated, account, busy } = useAccountStore();
  const [topup, setTopup] = useState(false);

  if (!configLoaded || !ready) return null;

  const chipClass = cn(
    pill,
    "inline-flex shrink-0 items-center gap-1.5 border border-[var(--color-border)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)] data-[state=open]:bg-[var(--color-bg-hover)] cursor-pointer tabular-nums",
    focus,
  );

  if (source === "custom" || !activated) {
    return (
      <button type="button" onClick={() => navigate("/ai-models")} className={chipClass}>
        {source === "custom" ? t("nav.balance.ownKey") : busy ? t("nav.balance.settingUp") : t("nav.balance.inactive")}
      </button>
    );
  }

  return (
    <>
      <Popover>
        <PopoverTrigger className={chipClass}>
          {account ? formatUsd(account.balanceUsd) : t("nav.balance.unknown")}
          <ChevronDown aria-hidden className="h-4 w-4 text-[var(--color-text-muted)]" />
        </PopoverTrigger>
        <PopoverContent align="end" className="w-72">
          <p className="text-xs text-[var(--color-text-muted)]">{t("nav.balance.title")}</p>
          {account && (
            <p className="mt-1 text-2xl font-bold tabular-nums">
              {formatUsd(account.balanceUsd)}
              <span className="ml-2 text-sm font-medium text-[var(--color-text-secondary)]">
                {formatIdr(account.balanceIdr)}
              </span>
            </p>
          )}
          <ModelSelect />
          <div className="mt-4 flex items-center gap-2">
            <PopoverClose asChild>
              <Button onClick={() => setTopup(true)} className="h-10 flex-1">
                {t("nav.balance.topup")}
              </Button>
            </PopoverClose>
            <PopoverClose asChild>
              <Button variant="outline" onClick={() => navigate("/ai-models")} className="h-10 flex-1">
                {t("nav.balance.manage")}
              </Button>
            </PopoverClose>
          </div>
        </PopoverContent>
      </Popover>
      {topup && <TopupDialog onClose={() => setTopup(false)} />}
    </>
  );
}

/**
 * The in-app model, switchable per video. A model the catalogue no longer
 * lists is still offered, so a retired choice is shown rather than swapped.
 */
function ModelSelect() {
  const { t } = useTranslation();
  const model = useConfigStore((s) => s.config.ai.inapp.model);
  const setInappModel = useConfigStore((s) => s.setInappModel);
  const { models, modelsLoading, loadModels } = useAccountStore();

  useEffect(() => {
    void loadModels();
  }, [loadModels]);

  const available = chatModels(models);

  return (
    <label className="mt-4 block">
      <span className="text-xs text-[var(--color-text-muted)]">{t("nav.balance.model")}</span>
      {modelsLoading && !models ? (
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{t("nav.balance.loadingModels")}</p>
      ) : (
        <select
          value={model}
          onChange={(e) =>
            setInappModel(e.target.value).catch((err) =>
              toast.error(t("nav.balance.modelFailed", { reason: errorMessage(err) })),
            )
          }
          className="mt-1 h-10 w-full cursor-pointer rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)] px-2.5 text-sm text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)]"
        >
          {!model && <option value="">{t("nav.balance.chooseModel")}</option>}
          {available.map((m) => (
            <option key={m.id} value={m.name}>
              {m.name}
            </option>
          ))}
          {model && !available.some((m) => m.name === model) && <option value={model}>{model}</option>}
        </select>
      )}
    </label>
  );
}
