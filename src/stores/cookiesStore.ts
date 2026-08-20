import { create } from "zustand";

interface CookiesState {
  hasCookies: boolean;
  cookiesValid: boolean;
  setCookiesStatus: (has: boolean, valid: boolean) => void;
  checkCookies: () => void;
}

export const useCookiesStore = create<CookiesState>((set) => ({
  hasCookies: false,
  cookiesValid: false,
  setCookiesStatus: (has, valid) => set({ hasCookies: has, cookiesValid: valid }),
  checkCookies: async () => {
    try {
      const { getCookiesStatus } = await import("@/hooks/cookies");
      const result = await getCookiesStatus();
      set({ hasCookies: result.exists, cookiesValid: result.valid });
    } catch {
      set({ hasCookies: false, cookiesValid: false });
    }
  },
}));
