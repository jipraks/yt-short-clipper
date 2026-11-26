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

## Logo

The app name as text, **"YT Short Clipper"**, set in Plus Jakarta Sans. No
symbol until a real logo exists. (`icon.png` stays as the window and taskbar
icon.)

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
