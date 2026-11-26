import type { en } from "./locales/en";

/** Same keys as English, with any string as the value. */
type Shape<T> = { [K in keyof T]: T[K] extends string ? string : Shape<T[K]> };

export type Messages = Shape<typeof en>;
