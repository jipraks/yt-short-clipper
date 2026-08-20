import { useState, useRef } from "react";
import { Cookie, Upload, X, CheckCircle2, AlertCircle, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { saveCookies } from "@/hooks/cookies";
import { toast } from "sonner";

interface CookiesDialogProps {
  onDone: (valid: boolean) => void;
}

export function CookiesDialog({ onDone }: CookiesDialogProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  const [foundCookies, setFoundCookies] = useState<string[]>([]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setStatus("loading");
    setMessage("");
    setFoundCookies([]);

    try {
      const content = await file.text();
      const result = await saveCookies(content);

      setFoundCookies(result.foundCookies ?? []);

      if (result.valid) {
        setStatus("success");
        setMessage("YouTube cookies uploaded and validated successfully!");
        toast.success("Cookies uploaded successfully");
        setTimeout(() => onDone(true), 1200);
      } else {
        setStatus("error");
        setMessage(result.error || "Invalid cookies file");
        toast.error("Cookies validation failed");
      }
    } catch (err) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "Failed to upload cookies");
      toast.error("Failed to upload cookies");
    }

    // Reset file input so same file can be selected again
    e.target.value = "";
  };

  return (
    <Card className="max-w-md mx-auto">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Cookie className="w-5 h-5 text-[var(--color-accent)]" />
            YouTube Cookies
          </CardTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onDone(false)}
            className="h-8 w-8"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-[var(--color-text-secondary)]">
          Upload a <code className="text-xs bg-[var(--color-bg-card)] px-1 py-0.5 rounded">cookies.txt</code>{" "}
          file exported from your browser while logged into YouTube.
        </p>

        <input
          ref={fileRef}
          type="file"
          accept=".txt"
          onChange={handleFileSelect}
          className="hidden"
        />

        <Button
          variant="outline"
          onClick={() => fileRef.current?.click()}
          disabled={status === "loading"}
          className="w-full gap-2 h-12"
        >
          {status === "loading" ? (
            <>
              <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
              Validating...
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" />
              Upload cookies.txt
            </>
          )}
        </Button>

        {status === "success" && (
          <div className="flex items-start gap-2 p-3 rounded-[var(--radius-sm)] bg-[var(--color-success-bg)] text-[var(--color-success)]">
            <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
            <div className="text-sm space-y-1">
              <p className="font-medium">{message}</p>
              <div className="flex flex-wrap gap-1">
                {foundCookies.map((c) => (
                  <span
                    key={c}
                    className="text-xs px-1.5 py-0.5 bg-white/60 rounded font-mono"
                  >
                    {c}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {status === "error" && (
          <div className="flex items-start gap-2 p-3 rounded-[var(--radius-sm)] bg-[var(--color-error-bg)] text-[var(--color-error)]">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <div className="text-sm whitespace-pre-line">{message}</div>
          </div>
        )}

        <div className="flex items-start gap-2 p-3 rounded-[var(--radius-sm)] bg-[var(--color-bg-card)]">
          <FileText className="w-4 h-4 text-[var(--color-text-muted)] shrink-0 mt-0.5" />
          <div className="text-xs text-[var(--color-text-muted)] space-y-1">
            <p className="font-medium text-[var(--color-text-secondary)]">How to get cookies:</p>
            <ol className="list-decimal list-inside space-y-0.5">
              <li>Open YouTube in your browser</li>
              <li>Make sure you're logged in</li>
              <li>Use extension "Get cookies.txt LOCALLY"</li>
              <li>Export and upload the file here</li>
            </ol>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
