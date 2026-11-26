/**
 * Microsoft Store builds are updated by the Store, so they must never point
 * users at a download of their own. `scripts/build-msix.ps1` sets this.
 */
export const IS_STORE_BUILD = import.meta.env.VITE_STORE_BUILD === "1";
