import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";

/** Routes that lay themselves out edge to edge, like the highlight editor. */
const FULL_BLEED_ROUTES = new Set(["/highlights"]);

export function AppLayout() {
  const { pathname } = useLocation();
  const fullBleed = FULL_BLEED_ROUTES.has(pathname);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--color-bg-secondary)]">
      <Sidebar />
      {fullBleed ? (
        <main className="flex-1 min-w-0 overflow-hidden">
          <Outlet />
        </main>
      ) : (
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-[900px] xl:max-w-[1080px] 2xl:max-w-[1240px] mx-auto p-6 xl:px-10 xl:py-8">
            <Outlet />
          </div>
        </main>
      )}
    </div>
  );
}
