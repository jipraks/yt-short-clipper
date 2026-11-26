import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { loadSession } from "@/hooks/sessions";
import { useSessionStore } from "@/stores/sessionStore";

/**
 * Loads a session from disk into the editor and goes there. Library rows and
 * the session link on every clip both use it, so a session opens the same
 * way from either side.
 */
export function useOpenSession() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { setSession } = useSessionStore();
  const [openingDir, setOpeningDir] = useState<string | null>(null);

  const open = async (sessionDir: string) => {
    if (openingDir) return;
    setOpeningDir(sessionDir);
    try {
      const session = await loadSession(sessionDir);
      setSession(session, "library");
      navigate("/highlights");
    } catch (err) {
      console.error("Failed to open session", err);
      toast.error(t("library.openFailed"));
    } finally {
      setOpeningDir(null);
    }
  };

  return { open, openingDir };
}
