# Design direction

Answers from the product owner (2026-11-26), written down as given. This is
the source of direction for UI work; `antislop` is the filter applied on top.

## Personality

Relaxed, friendly, guiding (santai, ramah, membimbing). The app should feel
like someone showing a new user the way, not like a pro tool that assumes they
already know it.

## Colour

Revised by the owner on 2026-11-26 to be easier on the eyes: charcoal instead
of pure black, and a warmer, muted red instead of the bright YouTube red.

- Base: charcoal `#1A1A1A`. Cards and the selected item: blue-grey `#24272C`.
- Text: white `#FFFFFF`, secondary grey `#A0A0A0`.
- One brand colour, red, in two tones by job:
  - **Button red `#D34033`** with **white** text (4.61:1). Black text on it
    fails (4.29:1).
  - **Red text `#EA7060`** for red text, icons, error messages and focus rings.
    It clears 4.5:1 on every surface. The owner's first pick for error text,
    `#E05A47`, was 4.08:1 on cards, so the owner chose this lighter tone.

## Typography

**Plus Jakarta Sans** for the whole UI.

## Motion

Calm (kalem): hover and state changes only. No entrance animations, no
decorative motion.

## Name and logo

The app is **Cuplik** (from "cuplikan", a clip or excerpt), renamed on
2026-11-26 to drop "YT". The landing page will live at cuplik.jipraks.id.

The wordmark follows the owner's sketch, rebuilt in Plus Jakarta Sans so it
matches the UI: **CUPLIK** in uppercase, semibold, with **CUP** in the red text
tone `#EA7060` and **LIK** in white (`src/components/brand/Wordmark.tsx`). It
is live text, not an image. `icon.png` is still the old window and taskbar
icon until a new one is made.

Only the visible name changed. The app identifier `com.jipraks.ytshortclipper-v2`
stays, because it names the folder that holds every user's cookies, config,
account key and sessions. The exe and release zip names (`YTShortClipperV2`),
the sidecar name and the `ytclip.org` service domains are left for the release
work.

## Language

Indonesian and English, chosen on first launch. Pages are translated one at a
time as each is redesigned.

## Dials

Dial: ENERGY 2 / RHYTHM 1 / MOTION 1

- MOTION 1 comes straight from "calm".
- ENERGY 2 and RHYTHM 1 are inferred, not answered: a friendly, guiding app
  with one strong brand colour (ENERGY 2), and an app UI where pages and wizard
  steps should feel consistent and predictable (RHYTHM 1). Change them if they
  are wrong.
