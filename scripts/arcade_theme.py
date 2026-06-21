#!/usr/bin/env python3
"""Shared visual language for the Agent Arcade PNG renderers.

Keeps the Telegram preview and status card consistent with the web console:
the AA-8 hardware look — warm plastic plate, an inset phosphor LCD, primary
signal colours, and native macOS type (SF Pro / SF Mono). No third-party
fonts, no network.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "latest.json"
SUMMON = ROOT / "data" / "summon.json"

# ---- Palette (RGB), mirrors app/style.css ----------------------------------
PAPER = (231, 228, 218)   # desk / negative space
PLATE = (243, 241, 234)   # device plastic
PLATE2 = (233, 230, 221)  # recessed plastic
INK = (21, 20, 15)        # near-black
INK2 = (75, 73, 64)
FAINT = (140, 137, 124)
LINE = (212, 208, 196)
LINE2 = (196, 192, 178)

ORANGE = (255, 90, 31)    # TE signal orange
LCD_BG = (20, 24, 15)     # phosphor panel
LCD = (199, 227, 106)     # phosphor green
LCD_DIM = (92, 107, 58)

OK = (31, 175, 90)
BUSY = (255, 158, 31)

# Bright, primary-leaning identity colours for the channel knobs.
ACCENTS = {
    "ember": (255, 90, 31),
    "laser": (47, 109, 255),
    "mint": (31, 175, 90),
    "cobalt": (124, 92, 255),
    "gold": (255, 194, 31),
    "coral": (255, 138, 63),
    "ice": (31, 198, 198),
    "plum": (197, 74, 214),
}

STATE_COLORS = {"ok": OK, "busy": BUSY}
_STATUS_TO_STATE = {"ready": "ok"}  # everything else reads as busy

# San Francisco is a variable font; weights are applied via variation names.
_SF = "/System/Library/Fonts/SFNS.ttf"
_SF_MONO = "/System/Library/Fonts/SFNSMono.ttf"
_FALLBACK = "/System/Library/Fonts/Helvetica.ttc"
_FALLBACK_MONO = "/System/Library/Fonts/Menlo.ttc"


def load_data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def load_optional_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_summon() -> dict | None:
    return load_optional_json(SUMMON)


def font(size: int, weight: str = "Regular", mono: bool = False) -> ImageFont.FreeTypeFont:
    """Load SF Pro / SF Mono at a given pixel size and named weight."""
    primary = _SF_MONO if mono else _SF
    fallback = _FALLBACK_MONO if mono else _FALLBACK
    try:
        f = ImageFont.truetype(primary, size)
        try:
            f.set_variation_by_name(weight)
        except Exception:
            pass
        return f
    except Exception:
        try:
            return ImageFont.truetype(fallback, size)
        except Exception:
            return ImageFont.load_default()


def state_for(status: str) -> str:
    return _STATUS_TO_STATE.get((status or "").lower(), "busy")


def accent_rgb(name: str) -> tuple[int, int, int]:
    return ACCENTS.get((name or "").lower(), INK)


def mix(fg: tuple[int, int, int], bg: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """Blend fg over bg with weight t in [0, 1] (t = share of fg)."""
    return tuple(round(a * t + b * (1 - t)) for a, b in zip(fg, bg))


def paper_backdrop(img) -> None:
    """Warm paper desk with faint horizontal scanlines — no glow."""
    w, h = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, w, h), fill=PAPER)
    shade = mix((0, 0, 0), PAPER, 0.012)
    for y in range(0, h, 4):
        draw.line((0, y, w, y), fill=shade)


def text_len(draw: ImageDraw.ImageDraw, text: str, fnt) -> float:
    return draw.textlength(text, font=fnt)


def tracked(draw, xy, text, fnt, fill, tracking: float = 0.0) -> float:
    """Draw text with letter-spacing (for uppercase labels). Returns end x."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += text_len(draw, ch, fnt) + tracking
    return x


def ellipsize(draw, text: str, fnt, max_w: float) -> str:
    if text_len(draw, text, fnt) <= max_w:
        return text
    while text and text_len(draw, text + "…", fnt) > max_w:
        text = text[:-1]
    return text + "…"


# ---- Hardware primitives ----------------------------------------------------

def plate(draw, box, radius=22, recessed=False) -> None:
    fill = PLATE2 if recessed else PLATE
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=LINE2, width=1)


def screw(draw, cx, cy, r=7) -> None:
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(196, 192, 178), outline=mix(INK, PAPER, 0.4))
    draw.ellipse((cx - r + 2, cy - r + 2, cx + r - 3, cy + r - 3), fill=(232, 229, 219))
    draw.line((cx - r + 3, cy, cx + r - 3, cy), fill=INK2, width=1)


def status_dot(draw, cx, cy, state: str, r: int = 5) -> None:
    color = STATE_COLORS.get(state, FAINT)
    draw.ellipse((cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3), fill=mix(color, PAPER, 0.22))
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)


def knob(draw, cx, cy, r, accent, rot_deg: float) -> None:
    """Plastic knob with an accent indicator and a soft accent ring."""
    draw.ellipse((cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4),
                 outline=mix(accent, PLATE2, 0.45), width=2)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=PLATE, outline=LINE2, width=1)
    # indicator: 0deg points up, increasing clockwise
    theta = math.radians(rot_deg)
    dx, dy = math.sin(theta), -math.cos(theta)
    x0, y0 = cx + dx * (r * 0.32), cy + dy * (r * 0.32)
    x1, y1 = cx + dx * (r * 0.88), cy + dy * (r * 0.88)
    draw.line((x0, y0, x1, y1), fill=accent, width=3)


def meter(draw, x, y_bottom, lit: int, total: int, on_color, seg_h=7, gap=3, w=15) -> None:
    """Vertical segment meter, drawn bottom-up."""
    for i in range(total):
        top = y_bottom - (i + 1) * seg_h - i * gap
        color = on_color if i < lit else LINE
        draw.rounded_rectangle((x, top, x + w, top + seg_h), radius=2, fill=color)


def fader(draw, box, cap_frac: float, accent) -> None:
    """Recessed fader slot with a centred track and a dark cap."""
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=6, fill=PLATE, outline=LINE, width=1)
    cx = (x0 + x1) / 2
    draw.line((cx, y0 + 8, cx, y1 - 8), fill=LINE2, width=3)
    cap_y = y0 + 10 + cap_frac * (y1 - y0 - 20)
    cw, ch = 24, 13
    draw.rounded_rectangle((cx - cw / 2, cap_y - ch / 2, cx + cw / 2, cap_y + ch / 2),
                           radius=4, fill=INK)
    draw.line((cx - cw / 2 + 4, cap_y, cx + cw / 2 - 4, cap_y), fill=accent, width=2)


def toggle(draw, cx, cy, on: bool, w=38, h=20) -> None:
    """Rounded rocker switch — green when on, plate when off."""
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    fill = mix(OK, PLATE, 0.32) if on else PLATE
    draw.rounded_rectangle(box, radius=h / 2, fill=fill, outline=LINE2, width=1)
    kr = h / 2 - 3
    kx = cx + w / 2 - kr - 3 if on else cx - w / 2 + kr + 3
    draw.ellipse((kx - kr, cy - kr, kx + kr, cy + kr), fill=(248, 246, 240), outline=LINE2)


def lcd_panel(draw, box, radius=10) -> None:
    """Dark phosphor LCD with horizontal scanlines."""
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=radius, fill=LCD_BG, outline=(10, 13, 6), width=1)
    for y in range(int(y0) + 3, int(y1) - 2, 3):
        draw.line((x0 + 3, y, x1 - 3, y), fill=mix((0, 0, 0), LCD_BG, 0.4))


def fmt_time(value: str) -> str:
    """HH:MM from an ISO-ish timestamp, best-effort."""
    if not value or "T" not in value:
        return value or "—"
    return value.split("T", 1)[1][:5]


def fmt_snapshot(value: str) -> str:
    if not value or "T" not in value:
        return value or "—"
    date, rest = value.split("T", 1)
    return f"{date} {rest[:5]}"


def clamp_text(value: str, limit: int) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    clipped = text[: max(0, limit - 1)].rstrip()
    return f"{clipped}…"


def wrap_text(draw, text: str, fnt, max_w: float, max_lines: int) -> list[str]:
    words = (text or "").split()
    if not words:
        return []

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if text_len(draw, candidate, fnt) <= max_w:
            current = candidate
            continue
        lines.append(current)
        current = word
        if len(lines) == max_lines - 1:
            break

    if len(lines) < max_lines:
        remainder = current
        if len(lines) == max_lines - 1:
            remainder = ellipsize(draw, remainder, fnt, max_w)
        lines.append(remainder)

    if len(lines) > max_lines:
        lines = lines[:max_lines]
    if lines:
        lines[-1] = ellipsize(draw, lines[-1], fnt, max_w)
    return lines
