import { invoke } from "@tauri-apps/api/core";

export interface CookiesStatus {
  exists: boolean;
  valid: boolean;
  path: string;
  foundCookies: string[];
  error: string | null;
}

export async function saveCookies(content: string): Promise<CookiesStatus> {
  return invoke<CookiesStatus>("save_cookies", { content });
}

export async function getCookiesStatus(): Promise<CookiesStatus> {
  return invoke<CookiesStatus>("get_cookies_status");
}
