#!/usr/bin/env python3
"""Shared visual language for the Agent Arcade PNG renderers.

Keeps the Telegram preview and status card consistent with the web console:
warm paper, bordered cabinet units, recessed signal wells, semantic state
colour, and native macOS type (SF Pro / SF Mono). No third-party fonts, no
network.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "latest.json"
SUMMON = ROOT / "data" / "summon.json"

# ---- Palette (RGB), mirrors app/style.css ----------------------------------
PAPER = (231, 228, 218)   # desk / negative space
PLATE = (243, 241, 234)   # device plastic
PLATE2 = (233, 230, 221)  # recessed plastic
WELL = (216, 211, 197)    # signal well
INK = (21, 20, 15)        # near-black
INK2 = (75, 73, 64)
FAINT = (140, 137, 124)
LINE = (212, 208, 196)
LINE2 = (196, 192, 178)

ORANGE = (196, 91, 34)    # ember accent
LCD_BG = (216, 211, 197)  # recessed well
LCD = INK
LCD_DIM = INK2

OK = (43, 122, 75)
BUSY = (154, 106, 27)
WARN = (163, 60, 47)

# Muted identity colours retained for cartridge accents.
ACCENTS = {
    "ember": (196, 91, 34),
    "laser": (61, 99, 143),
    "mint": (43, 122, 75),
    "cobalt": (61, 99, 143),
    "gold": (154, 106, 27),
    "coral": (183, 107, 52),
    "ice": (77, 119, 117),
    "plum": (123, 90, 121),
}

STATE_COLORS = {"ok": OK, "busy": BUSY, "warn": WARN}
_STATUS_TO_STATE = {"ready": "ok", "warning": "warn"}  # everything else reads as busy

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
    """Warm paper desk with faint horizontal grain and no glow."""
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


# ---- Cabinet primitives -----------------------------------------------------

def plate(draw, box, radius=22, recessed=False) -> None:
    fill = PLATE2 if recessed else PLATE
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=LINE2, width=1)


def fmt_time(value: str) -> str:
    """HH:MM from an ISO-ish timestamp, best-effort."""
    if not value or "T" not in value:
        return value or "-"
    return value.split("T", 1)[1][:5]


def fmt_snapshot(value: str) -> str:
    if not value or "T" not in value:
        return value or "-"
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
