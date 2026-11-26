# Design direction

Answers from the product owner (2026-11-26), written down as given. This is
the source of direction for UI work; `antislop` is the filter applied on top.

## Personality

Relaxed, friendly, guiding (santai, ramah, membimbing). The app should feel
like someone showing a new user the way, not like a pro tool that assumes they
already know it.

## Colour

- Dark base: near-black background with lifted dark panels.
- One brand colour: **YouTube red `#FF3B30`**.
- Text on a red surface is **black** (`#0A0A0A`, contrast 5.58:1). White on
  `#FF3B30` is only 3.55:1 and fails WCAG AA, so it is not used.
- Red as text or icon on the dark base passes (5.58:1 on `#0A0A0A`, 4.80:1 on
  `#1C1C1C`).

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
