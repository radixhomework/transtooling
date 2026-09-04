---
name: TransTooLing
description: Local transcription and translation workshop — radixhomework editorial charte.
colors:
  accent: "#4D5947"
  accent-hover: "#3F4A3B"
  accent-soft: "#e3e7dd"
  copper: "#9A7656"
  copper-soft: "#efe6dc"
  bg: "#fcfcfa"
  surface: "#fdfaf3"
  surface-sunken: "#eae5d8"
  parchment: "#d8d0bd"
  ink: "#1E211C"
  ink-soft: "#76604E"
  ink-faint: "#a18f7c"
  border: "rgba(30, 33, 28, 0.2)"
  border-strong: "rgba(30, 33, 28, 0.4)"
  status-pending: "#9A7656"
  status-pending-soft: "#efe6dc"
  status-done: "#4D5947"
  status-done-soft: "#e3e7dd"
  status-error: "#8A5E61"
  status-error-soft: "#efe1e0"
typography:
  display:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "1.85rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "0.01em"
  body:
    fontFamily: "Source Sans 3, Segoe UI, sans-serif"
    fontSize: "0.95rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "IBM Plex Mono, SFMono-Regular, Consolas, monospace"
    fontSize: "0.68rem"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "0.06em"
rounded:
  sm: "0"
  md: "0"
  lg: "0"
spacing:
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.sm}"
    padding: "9px 16px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "9px 16px"
  button-danger:
    backgroundColor: "transparent"
    textColor: "{colors.status-error}"
    rounded: "{rounded.sm}"
    padding: "9px 16px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "20px"
  badge:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent}"
    rounded: "0"
    padding: "3px 8px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "10px 12px"
---

# Design System: TransTooLing

## Overview

**Creative North Star: "The workshop that takes root"**

TransTooLing adopts the radixhomework.github.io editorial charte: a
personal workshop in earth tones — root black, ivory, moss green, patinated
copper — set on warm paper surfaces. Typography leads: Cormorant Garamond
carries headings in letter-spaced capitals, like a workshop's facade;
Source Sans 3 carries sentences; IBM Plex Mono remains the discreet voice
of data (logins, models, sizes, dates). The logo — a dark ringed emblem —
replaces the former bar mark in the header, the login page and the
favicon.

The language is editorial and flat: square corners everywhere, no shadows,
thin translucent root-black borders to separate surfaces. Color is rare —
moss green to act, copper for pending states and link hovers, faded pink
for errors. The waveform remains the only animated processing indicator.

**Key Characteristics:**
- radixhomework palette: root black, ivory, moss green, patinated copper, faded pink, parchment
- Cormorant Garamond in letter-spaced capitals for headings, brand and navigation; Source Sans 3 for body
- Square corners everywhere, no shadows: separation comes from thin borders
- Emblem logo (logo-96/64/32.png) in the header, login page and favicon
- IBM Plex Mono remains the data voice; the waveform remains the processing indicator

## Colors

The radixhomework earth palette: two papers, a root black, three natural
accents (moss, copper, faded pink) and a parchment for depth.

### Primary
- **Moss green** (#4D5947): the action color — primary buttons, links,
  active navigation, focus, waveform, "done" status.
- **Deep moss** (#3F4A3B): single variant, on primary button hover.
- **Veiled moss** (#e3e7dd): badge backgrounds and soft green fills.

### Secondary
- **Patinated copper** (#9A7656): secondary accent — "pending /
  processing / cancelling" statuses, link hovers. With its veil (#efe6dc).

### Tertiary
- **Faded pink** (#8A5E61): errors and destructive actions, with its veil
  (#efe1e0).

### Neutral
- **Paper** (#fcfcfa): page background.
- **Ivory** (#fdfaf3): cards, header, inputs.
- **Parchment** (#d8d0bd) and its half-tone (#eae5d8): sunken surfaces,
  progress tracks, inactive tabs, preformatted text.
- **Root black** (#1E211C): main text; its semi-transparent borders
  (20% / 40%) separate all surfaces.
- **Earth brown** (#76604E): secondary text.
- **Pale brown** (#a18f7c): metadata, captions.

### Named Rules (optional, powerful)
**The Rare Color Rule.** Moss green covers at most ~10% of any screen;
copper and faded pink are states only. Nothing decorative.

## Typography

**Display Font:** Cormorant Garamond (Georgia, serif)
**Body Font:** Source Sans 3 (Segoe UI, sans-serif)
**Label/Mono Font:** IBM Plex Mono (SFMono-Regular, Consolas, monospace)

**Character:** A contemporary garamond in letter-spaced capitals for the
facade, a humanist sans for daily work, a sober mono for measurements —
the workshop and its ledger.

### Hierarchy
- **Display** (600, 1.85rem, 1.15): the single page heading (h1); 2rem in
  letter-spaced capitals (0.06em) on the login page; header brand in
  1.15rem capitals (0.08em).
- **Body** (400, 0.95rem, 1.6): paragraphs, descriptions, form fields.
- **Label** (600, 0.72–0.78rem, letter-spacing 0.06–0.08em, UPPERCASE):
  buttons, navigation, table headers, field labels — the charte's
  "ledger" voice, in Source Sans 3.
- **Data** (500, 0.68–0.72rem, letter-spacing 0.06em, UPPERCASE): badges
  and technical values, in IBM Plex Mono.

### Named Rules (optional)
**The Two Voices Rule.** Any measurable or technical value (model name,
login, timestamp, size) goes in IBM Plex Mono; any sentence goes in Source
Sans 3. Never the other way around.

## Layout

Unchanged app shell: sticky header (64px, ivory, bottom border) with logo
+ brand + navigation + account; centered content (max-width 1040px,
padding 40px 24px 80px); flex columns on a 24px rhythm; card grids as
auto-fill minmax(220px, 1fr). Below 720px, the header wraps and the
navigation scrolls horizontally. Navigation is now textual: letter-spaced
capitals, bottom underline in the active state — no background pills.

## Elevation & Depth

**Completely flat.** No shadows exist in the system; depth comes from the
paper/ivory/parchment contrast and thin root-black translucent borders.
States never lift anything.

### Named Rules (optional)
**The Absolutely Flat Rule.** Adding a shadow, a state gradient or an
elevation is forbidden; states are expressed through color (border, text,
veiled background), always at 0.2s.

## Shapes

Square corners everywhere (radii 0) — the only residual rounding is
invisible (2px on the waveform's 3px bars). Badges are squared tags with
an invisible hairline, not pills. The signature geometry is the emblem
logo's circle, a deliberate contrast in a world of right angles.

## Components

### Buttons
- **Shape:** square corners
- **Primary:** solid moss green, ivory text, letter-spaced capitals
  0.78rem (600, 0.06em), padding 9px 16px; compact variant 6px 12px
- **Hover / Focus:** deep moss (0.2s); visible focus: 2px moss outline,
  offset 2px
- **Secondary:** transparent, root-black 40% border, ink text; hover:
  moss border and text
- **Danger:** transparent, faded-pink border and text; hover: veiled pink
  background
- **Disabled:** opacity 0.5

### Chips / Badges
- **Style:** squared tag, IBM Plex Mono 0.68rem capitals (0.06em); veiled
  background + colored text: moss (done/active), copper (pending,
  processing, cancelling), faded pink (error), parchment (cancelled:
  half-tone background, earth-brown text)
- **Behavior:** the "processing" badge embeds the sm waveform and can show
  a percentage ("En cours · 42%")

### Cards / Containers
- **Corner Style:** square corners
- **Background:** ivory on paper
- **Shadow Strategy:** none (Absolutely Flat rule)
- **Border:** 1px root black 20%; moss border on the "default" model card
- **Internal Padding:** 16–24px, flex column, 12px gap

### Inputs / Fields
- **Style:** ivory, root-black 40% border, square corners, padding 10px 12px
- **Focus:** border switches to moss green (no halo)
- **Labels:** 0.8rem, 600, earth brown, above the field

### Navigation
- Text links in letter-spaced capitals (0.78rem, 600, 0.08em): ink at
  rest, moss green on hover; active: moss green + 1px bottom underline;
  padding 8px 2px

### Logo / Brand
Provided emblem (frontend/public/logo.png, declined as 96/64/32 px):
dark mark on transparency, with a ring. Header: 34px to the left of the
TRANSTOOLING name (Cormorant 600, 1.15rem, 0.08em). Login page: 64px above
the title. Favicon: 64/32 px.

### Waveform (signature component)
Five vertical moss-green bars (3px) pulsing in a soft oscillation (0.9s,
ease-in-out, height 25% ↔ 100%, staggered per bar). Three sizes: sm (14px,
badges), md (20px), lg (32px). The only animated waiting indicator;
disabled under prefers-reduced-motion.

### Progress bar
Half-tone parchment track (6px) and moss-green fill scaled horizontally
(scaleX, 0.4s — no reflow); percentage in IBM Plex Mono 0.72rem.

## Do's and Don'ts

### Do:
- **Do** keep moss green a minority: actions, active, done — nothing else.
- **Do** put all technical data in IBM Plex Mono (Two Voices rule).
- **Do** separate surfaces with thin root-black translucent borders, never
  shadows.
- **Do** use Cormorant in letter-spaced capitals for headings, brand and
  navigation — it is the charte's facade.
- **Do** use the waveform as the only animated waiting indicator.

### Don't:
- **Don't** introduce a shadow, a gradient, a rounded corner or a second
  expression color.
- **Don't** set long text in IBM Plex Mono — mono is reserved for short
  values.
- **Don't** bring back background pills in navigation or pill badges.
- **Don't** animate anything but the waveform, the progress bars' scaleX
  and the 0.2s color transitions.
