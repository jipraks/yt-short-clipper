import { Outlet, useLocation } from "react-router-dom";
import { TopNav } from "./TopNav";

/** Routes that lay themselves out edge to edge, like the highlight editor. */
const FULL_BLEED_ROUTES = new Set(["/highlights"]);

export function AppLayout() {
  const { pathname } = useLocation();
  const fullBleed = FULL_BLEED_ROUTES.has(pathname);

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-[var(--color-bg-secondary)]">
      {/* Outside the scrolling area, so it stays in view on every page. */}
      <TopNav />
      {fullBleed ? (
        <main className="min-h-0 flex-1 overflow-hidden">
          <Outlet />
        </main>
      ) : (
        <main className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[900px] p-6 xl:max-w-[1080px] xl:px-10 xl:py-8 2xl:max-w-[1240px]">
            <Outlet />
          </div>
        </main>
      )}
    </div>
  );
}
