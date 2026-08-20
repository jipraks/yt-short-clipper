import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import {
  PlusCircle,
  FolderOpen,
  Bot,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { useAppStore } from "@/stores/appStore";
import { cn } from "@/lib/utils";
import { APP_VERSION } from "@/config/version";
import { menuIcon } from "@/config/menuIcons";
import { DEFAULT_MENU_ITEMS, fetchMenu, readCachedMenu, type MenuItem } from "@/hooks/menu";
import { AdvertiseDialog } from "@/components/AdvertiseDialog";
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
      {/* Nav items */}
      <nav className="flex-1 flex flex-col gap-1 p-3 pt-5">
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
