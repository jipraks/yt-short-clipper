import { useEffect, useRef } from "react";

/**
 * Paint thumbnails of [viewStart, viewEnd] across a canvas by seeking a hidden
 * <video> to evenly spaced times. Repaints when the window or size changes.
 */
export function useFilmstrip(
  src: string | null,
  viewStart: number,
  viewEnd: number,
  width: number,
  height: number,
) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    if (!src) return;
    const video = document.createElement("video");
    video.muted = true;
    video.preload = "auto";
    video.src = src;
    videoRef.current = video;
    return () => {
      video.removeAttribute("src");
      video.load();
      videoRef.current = null;
    };
  }, [src]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || width <= 0 || height <= 0) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = "#1a1a1a";
    ctx.fillRect(0, 0, width, height);
    if (!video || viewEnd <= viewStart) return;

    let cancelled = false;

    const seek = (t: number) =>
      new Promise<boolean>((resolve) => {
        const done = (ok: boolean) => {
          clearTimeout(timer);
          video.removeEventListener("seeked", onSeeked);
          resolve(ok);
        };
        const onSeeked = () => done(true);
        const timer = setTimeout(() => done(false), 3000);
        video.addEventListener("seeked", onSeeked);
        video.currentTime = t;
      });

    const ready = () =>
      video.readyState >= 1
        ? Promise.resolve()
        : new Promise<void>((resolve) =>
            video.addEventListener("loadedmetadata", () => resolve(), { once: true }),
          );

    const paint = async () => {
      await ready();
      const tileW = (height * 16) / 9;
      const count = Math.max(1, Math.ceil(width / tileW));
      const span = viewEnd - viewStart;
      for (let i = 0; i < count && !cancelled; i++) {
        const t = Math.min(video.duration || viewEnd, viewStart + ((i + 0.5) * span) / count);
        if (!(await seek(t)) || cancelled) continue;
        ctx.drawImage(video, i * tileW, 0, tileW, height);
      }
    };

    // Let a run of resizes or zoom clicks settle before seeking.
    const timer = setTimeout(() => void paint(), 150);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [src, viewStart, viewEnd, width, height]);

  return canvasRef;
}
