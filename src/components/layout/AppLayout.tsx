import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";

export function AppLayout() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--color-bg-secondary)]">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-[900px] mx-auto p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
