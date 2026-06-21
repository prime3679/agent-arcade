# Agent Arcade — Design Variants

Three standalone, high-taste design directions for Agent Arcade. Each is a
single self-contained HTML file: no build step, no package installs, no
external network calls, system fonts only. Open any file directly
(`file://`) and it renders from an embedded snapshot that mirrors
`data/latest.json`. When served over HTTP next to the real app, each variant
quietly upgrades itself by fetching `../data/latest.json`.

```bash
# direct — uses embedded fallback data
open variants/01-raycast-command-center.html

# live — fetches data/latest.json
python3 -m http.server 8000
# → http://localhost:8000/variants/01-raycast-command-center.html
```

## Why redesign

The current app is a competent dark "operator console," but it leans on the
exact fingerprints that read as generic: a near-black background, monospace as
shorthand for "technical," and a status table. It's fine. It isn't memorable,
and it doesn't have a point of view. Each variant below commits hard to one
idea instead.

All three render the same real content so they can be judged head to head:
the four system vitals (Hermes version, gateway, scheduler, worktree), the
full 8-agent fleet with roles/cabinets/signals, and all 10 scheduled cron
routines.

---

## 01 · Raycast Command Center
`01-raycast-command-center.html`

**Direction:** refined minimalism, keyboard-first. A command palette, not a
dashboard. One floating graphite window, a single column where *everything* is
searchable — system, fleet, and jobs as one ranked result list.

**Signature moves**
- Live fuzzy filter in the search bar; `↑`/`↓` to move the selection, `Esc` to
  clear. The active row gets the one accent in the whole design — a coral spine.
- Sectioned results (System / Fleet / Scheduled Jobs) with right-aligned
  accessories: status dots for agents, mono values for jobs, keycap hints that
  only appear on the focused row.
- Neutral palette with tinted neutrals; coral used exactly where it earns
  attention and nowhere else. Footer action bar with `↵` / `⌘K` affordances.

**Best when** the operator lives in the keyboard and wants to *find* a thing
fast. Scales to hundreds of agents without redesign — it's a list, and the
list is searchable.

---

## 02 · Teenage Engineering Console
`02-teenage-engineering-console.html`

**Direction:** industrial / utilitarian, light. Not a webpage — a piece of
hardware. Warm plastic plate, corner screws, an inset phosphor-green LCD
readout, and the fleet rendered as **eight mixer channel strips**.

**Signature moves**
- Each agent is a channel: a numbered strip with an accent knob (rotated for
  visual rhythm), a 5-segment LED meter and a fader cap whose position encodes
  status — green/seated for ready, amber/raised for active.
- A segmented LCD band reads out the vitals like gear: `VER · GATE · CRON ·
  GIT · NEXT`, with the dirty worktree shown in alert amber.
- The 10 cron jobs become a **patch bay** — physical toggle switches (all ON),
  schedule in mono, next run on the right. (Fitting: "Patchbay" is an agent.)
- Light, flat, primary-coloured — the deliberate opposite of dark-dashboard
  default. Decorative transport buttons close it out.

**Best when** you want the dashboard to feel *owned* and physical — a desk
object with personality. The most distinctive of the three; also the most
opinionated, so it's the boldest bet.

---

## 03 · Panic Playdate Lab
`03-panic-playdate-lab.html`

**Direction:** playful / toy-like. A yellow handheld console wrapping a **1-bit
memory-LCD screen**. No colour inside the glass — because a 1-bit screen can't
have any. Constraint as concept.

**Signature moves**
- Status is encoded as **dither**, not colour: Ready is a solid fill, Busy is a
  diagonal hatch. The fleet is a handheld **game menu** with a chunky `►`
  cursor and a fully inverted (black-on-paper) selected row.
- A working **crank** on the side. It spins idle, faster on hover, and the
  mouse wheel over the screen actually cranks through the fleet. `↑`/`↓` and
  click work too.
- Console chrome: status bar with 1-bit battery/wifi glyphs, system vitals as
  bordered tiles (dirty git inverts to alert), cron jobs listed as
  "background jobs," a live caret in the detail strip.

**Best when** Agent Arcade should feel like something you *play*, not just
read. Highest delight, strongest personality, narrowest range — text-heavy
signals get tight inside a 1-bit frame.

---

## Recommendation

**Ship 01 (Command Center) as the primary direction; borrow from 02.**

Agent Arcade is an operator tool. The job is read state fast and find a
specific thing — which is exactly what a command palette is *for*. Variant 01
is the only one that gets categorically better as the fleet grows (search +
keyboard nav), reads instantly to anyone who's used a modern dev tool, and
carries the least redesign risk. It's restrained without being the bland thing
we're replacing.

Variant 02 is the strongest pure *design* artifact and the one people will
remember — the light hardware aesthetic and the mixer/patch-bay metaphor are a
genuine point of view. Its risk is density: channel strips are gorgeous at 8
agents and get cramped well before 30. My recommendation is to make 01 the
daily driver and graft 02's ideas onto it — the LCD vitals readout and the
patch-bay treatment for cron both drop cleanly into the palette's System and
Jobs sections.

Variant 03 is the showpiece. Keep it as the marketing/landing face or an
easter-egg "arcade mode" — it's too charming to throw away and too constrained
(1-bit, text-tight) to run an operator's whole day on.

| Variant | Aesthetic | Layout metaphor | Scales to a big fleet | Risk |
|---|---|---|---|---|
| 01 Command Center | refined dark, neutral | searchable single column | **yes** | low |
| 02 TE Console | light industrial | mixer strips + patch bay | weak past ~30 | medium |
| 03 Playdate Lab | yellow 1-bit toy | handheld game menu | weak (text-tight) | high |

### Shared properties
- Single file each · no dependencies · no network except the optional
  same-origin `data/latest.json` upgrade.
- System fonts only (`-apple-system` / `ui-monospace`) — offline-safe, native
  on the target Mac, and a deliberate rejection of mono-as-decoration.
- Responsive to mobile (channel/menu grids reflow, crank and non-essential
  columns drop, nothing critical is amputated).
- `prefers-reduced-motion` respected in all three.
- Status uses redundant encoding (colour **and** shape/pattern/position), so it
  survives greyscale and colour-blindness — and in 03, has to.
- None of the main app files are touched; these live entirely under `variants/`.
