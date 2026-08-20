import { Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import { useEffect, useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { CreatePage } from "@/pages/CreatePage";
import { ProcessingPage } from "@/pages/ProcessingPage";
import { HighlightSelectionPage } from "@/pages/HighlightSelectionPage";
import { LibraryPage } from "@/pages/LibraryPage";
import { AIModelsPage } from "@/pages/AIModelsPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { WatermarkSettingsPage } from "@/pages/WatermarkSettingsPage";
import { CreditWatermarkSettingsPage } from "@/pages/CreditWatermarkSettingsPage";
import { HookStyleSettingsPage } from "@/pages/HookStyleSettingsPage";
import { ProcessingClipsPage } from "@/pages/ProcessingClipsPage";
import { ClipDetailPage } from "@/pages/ClipDetailPage";
import { ReplizSettingsPage } from "@/pages/ReplizSettingsPage";
import { CreditsPage } from "@/pages/CreditsPage";
import { UpdateDialog } from "@/components/UpdateDialog";
import { NotificationDialog } from "@/components/NotificationDialog";
import { checkForUpdate, type LatestVersionResponse } from "@/hooks/versionCheck";
import { checkNotification, type NotificationResponse } from "@/hooks/notificationCheck";
import { useAppStore } from "@/stores/appStore";

function App() {
  const [update, setUpdate] = useState<LatestVersionResponse | null>(null);
  const [notification, setNotification] = useState<NotificationResponse | null>(null);
  const setStoreUpdate = useAppStore((s) => s.setAvailableUpdate);

  useEffect(() => {
    checkForUpdate().then((result) => {
      if (result) {
        setUpdate(result);
        setStoreUpdate(result);
      }
    });

    checkNotification().then((result) => {
      if (result) setNotification(result);
    });
  }, []);

  return (
    <>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<CreatePage />} />
          <Route path="/processing" element={<ProcessingPage />} />
          <Route path="/highlights" element={<HighlightSelectionPage />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/ai-models" element={<AIModelsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/settings/watermark" element={<WatermarkSettingsPage />} />
          <Route path="/settings/credit" element={<CreditWatermarkSettingsPage />} />
          <Route path="/settings/hook-style" element={<HookStyleSettingsPage />} />
          <Route path="/settings/repliz" element={<ReplizSettingsPage />} />
          <Route path="/settings/credits" element={<CreditsPage />} />
          <Route path="/processing-clips" element={<ProcessingClipsPage />} />
          <Route path="/clip" element={<ClipDetailPage />} />
        </Route>
      </Routes>
      {notification && (
        <NotificationDialog notification={notification} onClose={() => setNotification(null)} />
      )}
      {!notification && update && (
        <UpdateDialog update={update} onClose={() => setUpdate(null)} />
      )}
      <Toaster position="bottom-right" richColors />
    </>
  );
}

export default App;
