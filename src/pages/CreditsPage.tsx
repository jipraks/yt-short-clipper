import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Trans, useTranslation } from "react-i18next";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { APP_VERSION } from "@/config/version";

// License texts are legal text and stay in English, word for word.
const MIT = `Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.`;

const APACHE = `Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.`;

const GPL3 = `This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.`;

const UNLICENSE = `This is free and unencumbered software released into the public domain.

For more information, please refer to <https://unlicense.org>`;

const OFL = `This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is available with a FAQ at: https://openfontlicense.org`;

const MIT_CMU = `Pillow is licensed under the MIT-CMU License.
The full license text is in the LICENSE file of the source repository linked above.`;

const MIT_OR_APACHE = `Licensed under either of the Apache License, Version 2.0 or the MIT license, at your option.

${MIT}

${APACHE}`;

type LibKey =
  | "ffmpeg"
  | "ytdlp"
  | "mediapipe"
  | "deno"
  | "opencv"
  | "pillow"
  | "tauri"
  | "react"
  | "radix"
  | "i18next"
  | "jakarta"
  | "openai"
  | "antislop";

interface LibraryInfo {
  key: LibKey;
  name: string;
  version?: string;
  license: string;
  url: string;
  /** Copyright line, required for MIT-licensed code copied into this app. */
  copyright?: string;
  licenseText: string;
}

const LIBRARIES: LibraryInfo[] = [
  { key: "ffmpeg", name: "FFmpeg", version: "8.0.1 (gyan.dev)", license: "GPL v3", url: "https://ffmpeg.org", licenseText: GPL3 },
  { key: "ytdlp", name: "yt-dlp", version: "2026.11.23", license: "Unlicense (Public Domain)", url: "https://github.com/yt-dlp/yt-dlp", licenseText: UNLICENSE },
  { key: "mediapipe", name: "MediaPipe", version: "0.10.31", license: "Apache 2.0", url: "https://github.com/google-ai-edge/mediapipe", licenseText: APACHE },
  { key: "deno", name: "Deno", version: "2.8.1", license: "MIT", url: "https://github.com/denoland/deno", licenseText: MIT },
  { key: "opencv", name: "OpenCV", version: "4.12", license: "Apache 2.0", url: "https://github.com/opencv/opencv", licenseText: APACHE },
  { key: "pillow", name: "Pillow", version: "11.3", license: "MIT-CMU", url: "https://github.com/python-pillow/Pillow", licenseText: MIT_CMU },
  { key: "tauri", name: "Tauri", version: "2", license: "MIT / Apache 2.0", url: "https://github.com/tauri-apps/tauri", licenseText: MIT_OR_APACHE },
  { key: "react", name: "React", version: "19", license: "MIT", url: "https://github.com/facebook/react", licenseText: MIT },
  {
    key: "radix",
    name: "Radix UI Primitives",
    license: "MIT",
    url: "https://github.com/radix-ui/primitives",
    copyright: "Copyright (c) 2022 WorkOS",
    licenseText: MIT,
  },
  { key: "i18next", name: "i18next, react-i18next", version: "27 / 18", license: "MIT", url: "https://github.com/i18next/react-i18next", licenseText: MIT },
  {
    key: "jakarta",
    name: "Plus Jakarta Sans",
    version: "5.3 (Fontsource)",
    license: "SIL Open Font License 1.1",
    url: "https://github.com/tokotype/PlusJakartaSans",
    copyright: "Copyright 2020 The Plus Jakarta Sans Project Authors",
    licenseText: OFL,
  },
  { key: "openai", name: "OpenAI Python SDK", version: "2.9", license: "Apache 2.0", url: "https://github.com/openai/openai-python", licenseText: APACHE },
  {
    key: "antislop",
    name: "antislop",
    license: "MIT",
    url: "https://github.com/miqdadbadjuber/anti-slop",
    copyright: "Copyright (c) 2026 Miqdad Badjuber",
    licenseText: MIT,
  },
];

const focusRing =
  "cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]";

function openLink(url: string) {
  openUrl(url).catch(console.error);
}

export function CreditsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <div className="mx-auto max-w-2xl py-4">
      <button
        type="button"
        onClick={() => navigate("/settings")}
        className={`-ml-2 inline-flex min-h-10 items-center gap-1.5 rounded-full px-2 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] ${focusRing}`}
      >
        <ArrowLeft aria-hidden className="h-4 w-4" />
        {t("creditsPage.back")}
      </button>

      <h1 className="mt-6 text-2xl font-bold text-[var(--color-text-primary)]">{t("creditsPage.title")}</h1>
      <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{t("creditsPage.subtitle")}</p>
      <p className="mt-3 text-xs text-[var(--color-text-muted)]">{t("creditsPage.version", { version: APP_VERSION })}</p>

      <section className="mt-9">
        <h2 className="text-base font-semibold text-[var(--color-text-primary)]">{t("creditsPage.listTitle")}</h2>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">{t("creditsPage.listBody")}</p>
        <ul className="mt-4 divide-y divide-[var(--color-border)] rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-bg-primary)]">
          {LIBRARIES.map((lib) => (
            <LibraryRow key={lib.key} lib={lib} />
          ))}
        </ul>
      </section>
    </div>
  );
}

function LibraryRow({ lib }: { lib: LibraryInfo }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const panelId = `license-${lib.key}`;

  return (
    <li className="px-5 py-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-[var(--color-text-primary)]">
            {lib.name}
            {lib.version && (
              <span className="ml-2 font-normal text-[var(--color-text-muted)]">{lib.version}</span>
            )}
          </p>
          <p className="mt-0.5 text-sm text-[var(--color-text-secondary)]">{t(`creditsPage.libs.${lib.key}`)}</p>
          <p className="mt-1 text-xs text-[var(--color-text-muted)]">
            {lib.license}
            {lib.copyright && <> · {lib.copyright}</>}
          </p>
          {lib.key === "ffmpeg" && (
            <p className="mt-1 text-xs text-[var(--color-text-muted)] leading-relaxed">
              <Trans
                i18nKey="creditsPage.ffmpegNote"
                components={{
                  src: <InlineLink url="https://ffmpeg.org" />,
                  build: <InlineLink url="https://www.gyan.dev/ffmpeg/builds/" />,
                }}
              />
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => openLink(lib.url)}
          aria-label={t("creditsPage.sourceLabel", { name: lib.name })}
          className={`-mr-2 inline-flex min-h-9 shrink-0 items-center gap-1.5 rounded-[var(--radius-sm)] px-2 text-sm font-medium text-[var(--color-accent)] hover:underline ${focusRing}`}
        >
          {t("creditsPage.source")}
          <ExternalLink aria-hidden className="h-3.5 w-3.5" />
        </button>
      </div>

      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((o) => !o)}
        className={`-ml-1 mt-1 inline-flex min-h-9 items-center rounded-[var(--radius-sm)] px-1 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] ${focusRing}`}
      >
        {open ? t("creditsPage.hideLicense") : t("creditsPage.showLicense")}
      </button>
      {open && (
        <pre
          id={panelId}
          lang="en"
          className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg-input)] p-3 font-mono text-xs text-[var(--color-text-secondary)] leading-relaxed"
        >
          {lib.copyright ? `${lib.copyright}\n\n${lib.licenseText}` : lib.licenseText}
        </pre>
      )}
    </li>
  );
}

/** Trans fills in the link text from the translation. */
function InlineLink({ url, children }: { url: string; children?: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={() => openLink(url)}
      className={`rounded-sm text-[var(--color-accent)] underline underline-offset-2 ${focusRing}`}
    >
      {children}
    </button>
  );
}
