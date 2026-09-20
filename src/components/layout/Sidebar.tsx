import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  PlusCircle,
  FolderOpen,
  Bot,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
  Coins,
  KeyRound,
  Loader2,
  Plus,
} from "lucide-react";
import { useAppStore } from "@/stores/appStore";
import { useConfigStore } from "@/stores/configStore";
import { useAccountStore } from "@/stores/accountStore";
import { cn } from "@/lib/utils";
import { APP_VERSION } from "@/config/version";
import { menuIcon } from "@/config/menuIcons";
import { DEFAULT_MENU_ITEMS, fetchMenu, readCachedMenu, type MenuItem } from "@/hooks/menu";
import { AdvertiseDialog } from "@/components/AdvertiseDialog";
import { TopupDialog } from "@/components/TopupDialog";
import { formatUsd } from "@/utils/format";
import { open as openUrl } from "@tauri-apps/plugin-shell";

const navItems = [
  { to: "/", icon: PlusCircle, label: "Create" },
  { to: "/library", icon: FolderOpen, label: "Library" },
  { to: "/ai-models", icon: Bot, label: "AI Models" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar, availableUpdate } = useAppStore();
  const [showAdvertise, setShowAdvertise] = useState(false);

  // Render from cache (or the built-in defaults) on the first paint, then
  // refresh in the background. The sidebar never waits on the network.
  const [menuItems, setMenuItems] = useState<MenuItem[]>(
    () => readCachedMenu() ?? DEFAULT_MENU_ITEMS
  );

  useEffect(() => {
    let cancelled = false;
    fetchMenu().then((items) => {
      if (!cancelled && items) setMenuItems(items);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const linkClass = cn(
    "flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-sm)] text-sm font-medium transition-all duration-200 cursor-pointer",
    "text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)]",
    sidebarCollapsed && "justify-center px-0"
  );

  return (
    <aside
      className={cn(
        "flex flex-col h-full bg-[var(--color-bg-sidebar)] border-r border-[var(--color-border-light)] transition-all duration-300 ease-in-out",
        sidebarCollapsed ? "w-16" : "w-[220px]"
      )}
    >
      <AIStatus collapsed={sidebarCollapsed} />

      {/* Nav items */}
      <nav className="flex-1 flex flex-col gap-1 p-3 pt-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-sm)] text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-[var(--color-accent-light)] text-[var(--color-accent)] border-l-[3px] border-[var(--color-accent)] ml-0 pl-2.5"
                  : "text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)]",
                sidebarCollapsed && "justify-center px-0"
              )
            }
          >
            <item.icon className="w-5 h-5 shrink-0" />
            {!sidebarCollapsed && <span>{item.label}</span>}
          </NavLink>
        ))}

        {/* External links, served by the menu API */}
        {menuItems.length > 0 && (
          <div className="my-2 border-t border-[var(--color-border-light)]" />
        )}

        {menuItems.map((item) => {
          const Icon = menuIcon(item.icon);
          return (
            <button
              key={item.id}
              onClick={() => openUrl(item.url).catch(console.error)}
              className={linkClass}
              title={item.label}
            >
              <Icon className="w-5 h-5 shrink-0" />
              {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
            </button>
          );
        })}
      </nav>

      {/* Advertise + version + collapse toggle */}
      <div className="p-3 border-t border-[var(--color-border-light)]">
        {!sidebarCollapsed && (
          <>
            <button
              onClick={() => setShowAdvertise(true)}
              className="w-full mb-2 text-[10px] leading-tight text-[var(--color-text-muted)] hover:text-[var(--color-accent)] hover:underline transition-colors cursor-pointer"
            >
              Want your link here?
            </button>

            <div className="mb-2 text-center">
              <p className="text-[10px] text-[var(--color-text-muted)]">
                v{APP_VERSION}
              </p>
              {availableUpdate && (
                <button
                  onClick={() => openUrl(availableUpdate.download_url)}
                  className="text-[10px] text-[var(--color-accent)] hover:underline mt-0.5"
                >
                  Update: v{availableUpdate.version}
                </button>
              )}
            </div>
          </>
        )}

        <button
          onClick={toggleSidebar}
          className="flex items-center justify-center w-full gap-2 px-3 py-2 rounded-[var(--radius-sm)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-secondary)] transition-all duration-200 cursor-pointer"
          title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {sidebarCollapsed ? (
            <PanelLeftOpen className="w-5 h-5" />
          ) : (
            <>
              <PanelLeftClose className="w-5 h-5" />
              <span className="text-xs">Collapse</span>
            </>
          )}
        </button>
      </div>

      {showAdvertise && <AdvertiseDialog onClose={() => setShowAdvertise(false)} />}
    </aside>
  );
}

/**
 * Which AI is active, and how much is left when that answer is "the in-app one".
 *
 * This is a status readout, not a switch. Changing provider mid-session is a
 * decision worth a page, and a toggle here would sit one stray click away from
 * a running job.
 */
function AIStatus({ collapsed }: { collapsed: boolean }) {
  const navigate = useNavigate();
  const source = useConfigStore((s) => s.config.ai.source);
  const configLoaded = useConfigStore((s) => s.loaded);
  const { ready, activated, account, refreshing, busy } = useAccountStore();
  const [showTopup, setShowTopup] = useState(false);

  if (!configLoaded || !ready) {
    return <div className="p-3 pt-5" />;
  }

  const custom = source === "custom";
  const balance = account ? formatUsd(account.balanceUsd) : null;

  if (collapsed) {
    return (
      <div className="p-3 pt-5">
        <button
          onClick={() => (custom || !activated ? navigate("/ai-models") : setShowTopup(true))}
          title={
            custom
              ? "Using your own API key"
              : activated
                ? `In-app AI · ${balance ?? "balance unavailable"}`
                : "In-app AI is not active"
          }
          className="w-full flex flex-col items-center gap-0.5 py-2 rounded-[var(--radius-sm)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] transition-all duration-200 cursor-pointer"
        >
          {custom ? <KeyRound className="w-5 h-5" /> : <Coins className="w-5 h-5" />}
          {!custom && balance && (
            <span className="text-[9px] leading-none font-medium">{balance}</span>
          )}
        </button>
        {showTopup && <TopupDialog onClose={() => setShowTopup(false)} />}
      </div>
    );
  }

  return (
    <div className="p-3 pt-5">
      <div className="rounded-[var(--radius-sm)] border border-[var(--color-border-light)] bg-[var(--color-bg-card)] p-2.5">
        <button
          onClick={() => navigate("/ai-models")}
          className="w-full flex items-center gap-2 text-left cursor-pointer group"
        >
          {custom ? (
            <KeyRound className="w-4 h-4 text-[var(--color-text-muted)] shrink-0" />
          ) : (
            <Coins className="w-4 h-4 text-[var(--color-accent)] shrink-0" />
          )}
          <div className="min-w-0 flex-1">
            <p className="text-[10px] uppercase tracking-wide text-[var(--color-text-muted)] leading-none">
              {custom ? "Own API key" : "In-app AI"}
            </p>
            <p className="text-sm font-semibold text-[var(--color-text-primary)] truncate group-hover:text-[var(--color-accent)] transition-colors">
              {custom
                ? "Custom"
                : activated
                  ? (balance ?? "—")
                  : busy
                    ? "Setting up..."
                    : "Not active"}
            </p>
          </div>
          {(refreshing || (!custom && busy)) && (
            <Loader2 className="w-3 h-3 animate-spin text-[var(--color-text-muted)] shrink-0" />
          )}
        </button>

        {!custom && activated && (
          <button
            onClick={() => setShowTopup(true)}
            className="mt-2 w-full flex items-center justify-center gap-1 py-1.5 rounded-[var(--radius-sm)] bg-[var(--color-accent-light)] text-[var(--color-accent)] text-xs font-medium hover:bg-[var(--color-accent-light)]/70 transition-all duration-200 cursor-pointer"
          >
            <Plus className="w-3 h-3" />
            Top Up
          </button>
        )}
      </div>

      {showTopup && <TopupDialog onClose={() => setShowTopup(false)} />}
    </div>
  );
}
