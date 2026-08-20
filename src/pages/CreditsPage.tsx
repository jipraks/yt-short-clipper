import { useNavigate } from "react-router-dom";
import { ArrowLeft, ExternalLink, Info } from "lucide-react";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { APP_VERSION } from "@/config/version";

interface LibraryInfo {
  name: string;
  version?: string;
  description: string;
  license: string;
  url: string;
  note?: string;
}

const LIBRARIES: LibraryInfo[] = [
  {
    name: "FFmpeg",
    version: "latest master (BtbN GPL)",
    description: "Audio/video processing, encoding, and format conversion",
    license: "GPL v2+",
    url: "https://ffmpeg.org",
    note: "FFmpeg is used as a separate process. Source code available at the link above.",
  },
  {
    name: "yt-dlp",
    version: "2026.08.19",
    description: "YouTube video and subtitle downloading",
    license: "Unlicense (Public Domain)",
    url: "https://github.com/yt-dlp/yt-dlp",
  },
  {
    name: "MediaPipe",
    version: "0.10+",
    description: "Face detection and landmark tracking for portrait conversion",
    license: "Apache 2.0",
    url: "https://github.com/google-ai-edge/mediapipe",
  },
  {
    name: "Deno",
    version: "latest",
    description: "JavaScript runtime for yt-dlp remote components",
    license: "MIT",
    url: "https://github.com/denoland/deno",
  },
  {
    name: "OpenCV",
    version: "4.8+",
    description: "Computer vision and image processing",
    license: "Apache 2.0",
    url: "https://github.com/opencv/opencv",
  },
  {
    name: "Pillow",
    version: "10+",
    description: "Image rendering for hook text overlays",
    license: "HPND (open source)",
    url: "https://github.com/python-pillow/Pillow",
  },
  {
    name: "Tauri",
    version: "v2",
    description: "Desktop application framework",
    license: "MIT / Apache 2.0",
    url: "https://github.com/tauri-apps/tauri",
  },
  {
    name: "React",
    version: "19",
    description: "User interface library",
    license: "MIT",
    url: "https://github.com/facebook/react",
  },
  {
    name: "OpenAI Python SDK",
    version: "1.0+",
    description: "AI API client for TTS, Whisper, and chat completions",
    license: "Apache 2.0",
    url: "https://github.com/openai/openai-python",
  },
];

export function CreditsPage() {
  const navigate = useNavigate();

  const handleLink = (url: string) => {
    openUrl(url).catch(console.error);
  };

  return (
    <div className="space-y-5 max-w-2xl">
      <Button
        variant="ghost"
        onClick={() => navigate("/settings")}
        className="gap-2 text-[var(--color-text-secondary)]"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Settings
      </Button>

      <div>
        <h1 className="text-xl font-bold text-[var(--color-text-primary)]">
          Open Source Credits
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          YT Short Clipper is built with the following open source libraries. We are grateful to
          their authors and contributors.
        </p>
      </div>

      <Card className="bg-[var(--color-bg-secondary)]/50">
        <CardContent className="pt-5">
          <div className="flex items-center gap-2 text-[var(--color-text-secondary)]">
            <Info className="w-4 h-4" />
            <p className="text-sm font-medium">Version {APP_VERSION}</p>
          </div>
          <p className="text-xs text-[var(--color-text-muted)] mt-1">
            YT Short Clipper v2 — built with React 19, Tauri v2, and Python 3.13.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Libraries & Tools</CardTitle>
        </CardHeader>
        <CardContent className="space-y-0 divide-y divide-[var(--color-border-light)]">
          {LIBRARIES.map((lib) => (
            <div key={lib.name} className="py-3 first:pt-0 last:pb-0">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-sm font-semibold text-[var(--color-text-primary)]">
                      {lib.name}
                    </p>
                    {lib.version && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-[var(--color-bg-secondary)] text-[var(--color-accent)]">
                        v{lib.version}
                      </span>
                    )}
                    <span className="text-xs px-1.5 py-0.5 rounded bg-[var(--color-bg-secondary)] text-[var(--color-text-muted)]">
                      {lib.license}
                    </span>
                  </div>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    {lib.description}
                  </p>
                  {lib.note && (
                    <p className="text-xs text-[var(--color-text-muted)] mt-1 italic">
                      {lib.note}
                    </p>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleLink(lib.url)}
                  className="h-7 px-2 gap-1 text-xs text-[var(--color-accent)] shrink-0"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  Source
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="bg-[var(--color-bg-secondary)]/50">
        <CardContent className="pt-5">
          <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
            This software uses FFmpeg, which is licensed under the GPL v2+ license. FFmpeg is
            invoked as a separate process and its source code is available at{" "}
            <button
              onClick={() => handleLink("https://ffmpeg.org")}
              className="text-[var(--color-accent)] underline"
            >
              ffmpeg.org
            </button>
            . The FFmpeg build bundled with this application is provided by{" "}
            <button
              onClick={() => handleLink("https://github.com/BtbN/FFmpeg-Builds")}
              className="text-[var(--color-accent)] underline"
            >
              BtbN/FFmpeg-Builds
            </button>
            .
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
