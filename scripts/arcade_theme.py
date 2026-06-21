#!/usr/bin/env python3
"""Shared visual language for the Agent Arcade PNG renderers.

Keeps the Telegram preview and status card consistent with the web console:
the same graphite palette, the same native macOS type (SF Pro / SF Mono), and
the same semantic status colours. No third-party fonts, no network.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from PIL import ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "latest.json"

# ---- Palette (RGB), mirrors app/style.css ----------------------------------
BG0 = (11, 12, 15)
BG1 = (16, 18, 24)
BG2 = (20, 22, 30)
ROW = (18, 20, 30)
HOVER = (25, 28, 39)
LINE = (34, 37, 46)
LINE2 = (48, 52, 62)
TEXT = (236, 238, 243)
DIM = (154, 161, 174)
FAINT = (100, 107, 120)

OK = (78, 199, 122)
ACTIVE = (226, 168, 63)
WARN = (239, 111, 99)

# Muted, low-chroma identity tints — monogram tiles only.
ACCENTS = {
    "ember": (181, 118, 90),
    "laser": (95, 143, 176),
    "mint": (111, 168, 134),
    "cobalt": (107, 128, 184),
    "gold": (179, 145, 82),
    "coral": (189, 122, 106),
    "ice": (127, 147, 166),
    "plum": (155, 127, 175),
}

STATE_COLORS = {"ok": OK, "active": ACTIVE, "warn": WARN}
_STATUS_TO_STATE = {"ready": "ok", "active": "active", "warning": "warn"}

# Font weight files (San Francisco is a variable font; weights via variation).
_SF = "/System/Library/Fonts/SFNS.ttf"
_SF_MONO = "/System/Library/Fonts/SFNSMono.ttf"
_FALLBACK = "/System/Library/Fonts/Helvetica.ttc"
_FALLBACK_MONO = "/System/Library/Fonts/Menlo.ttc"


def load_data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


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
    return _STATUS_TO_STATE.get((status or "").lower(), "ok")


def mix(fg: tuple[int, int, int], bg: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """Blend fg over bg with weight t in [0, 1] (t = share of fg)."""
    return tuple(round(a * t + b * (1 - t)) for a, b in zip(fg, bg))


def vertical_backdrop(img) -> None:
    """Subtle top-lit graphite gradient — no neon, no glow."""
    w, h = img.size
    draw = ImageDraw.Draw(img)
    top = (16, 18, 25)
    bottom = (9, 10, 13)
    for y in range(h):
        t = y / max(h - 1, 1)
        draw.line((0, y, w, y), fill=mix(bottom, top, t))


def text_len(draw: ImageDraw.ImageDraw, text: str, fnt) -> float:
    return draw.textlength(text, font=fnt)


def tracked(draw, xy, text, fnt, fill, tracking: float = 0.0) -> float:
    """Draw text with letter-spacing (for uppercase labels). Returns end x."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += text_len(draw, ch, fnt) + tracking
    return x


def wrap(draw, text: str, fnt, max_width: float) -> list[str]:
    words = (text or "").split()
    lines: list[str] = []
    line = ""
    for word in words:
        probe = f"{line} {word}".strip()
        if text_len(draw, probe, fnt) <= max_width or not line:
            line = probe
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def status_dot(draw, cx, cy, state: str, r: int = 5) -> None:
    color = STATE_COLORS.get(state, FAINT)
    ring = mix(color, BG0, 0.18)
    draw.ellipse((cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4), fill=ring)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)


def monogram(draw, box, letter: str, accent_name: str) -> None:
    """Rounded identity tile with a muted accent tint."""
    x0, y0, x1, y1 = box
    accent = ACCENTS.get(accent_name)
    if accent:
        fill = mix(accent, BG2, 0.16)
        outline = mix(accent, LINE2, 0.30)
        glyph = mix(accent, TEXT, 0.60)
    else:
        fill, outline, glyph = BG2, LINE2, TEXT
    draw.rounded_rectangle(box, radius=8, fill=fill, outline=outline, width=1)
    fnt = font(round((y1 - y0) * 0.5), "Semibold")
    w = text_len(draw, letter, fnt)
    ascent, descent = fnt.getmetrics()
    cx = (x0 + x1) / 2 - w / 2
    cy = (y0 + y1) / 2 - (ascent + descent) / 2
    draw.text((cx, cy), letter, font=fnt, fill=glyph)


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
