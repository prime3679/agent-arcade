#!/usr/bin/env python3
"""Render the full Agent Arcade console to a PNG for Telegram previews.

Mirrors the AA-8 web layout: a warm plastic plate with corner screws, an inset
phosphor LCD readout, eight mixer channel strips (one per agent), and a patch
bay of scheduled routines on physical toggles.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

import arcade_theme as t

OUT = t.ROOT / "agent-arcade-preview.png"

W = 1400
MARGIN = 46          # paper around the plate
PAD = 40             # plate inner padding


def render() -> Path:
    payload = t.load_data()
    summon = t.load_summon() or {}
    agents = payload.get("agents", [])
    hermes = payload.get("hermes", {})
    repo = payload.get("repo", {})
    entries = hermes.get("cron_list", {}).get("entries", [])
    cartridges = summon.get("cartridges", [])

    x0 = MARGIN + PAD
    x1 = W - MARGIN - PAD
    inner = x1 - x0

    # ---- vertical plan (compute H before painting) ----
    header_h, lcd_h, label_h = 66, 80, 26
    grid_gap, card_w_cols = 14, 4
    card_w = (inner - (card_w_cols - 1) * grid_gap) / card_w_cols
    card_h = 176
    rows = (len(agents) + card_w_cols - 1) // card_w_cols
    mixer_h = rows * card_h + (rows - 1) * grid_gap
    jack_h, patch_pad = 46, 14
    patch_h = max(1, len(entries)) * jack_h + 2 * patch_pad
    summon_cols = 2
    summon_gap = 14
    summon_card_h = 150
    summon_rows = (len(cartridges) + summon_cols - 1) // summon_cols if cartridges else 0
    summon_h = summon_rows * summon_card_h + max(0, summon_rows - 1) * summon_gap if summon_rows else 0
    foot_h = 52

    header_y = MARGIN + PAD
    lcd_y = header_y + header_h
    mixer_label_y = lcd_y + lcd_h + 22
    grid_y = mixer_label_y + label_h
    patch_label_y = grid_y + mixer_h + 26
    patch_y = patch_label_y + label_h
    summon_label_y = patch_y + patch_h + 26 if summon_rows else None
    summon_y = summon_label_y + label_h if summon_label_y is not None else None
    foot_y = (summon_y + summon_h + 24) if summon_y is not None else (patch_y + patch_h + 24)
    plate_bottom = foot_y + foot_h + PAD
    H = plate_bottom + MARGIN

    img = Image.new("RGB", (W, H))
    t.paper_backdrop(img)
    d = ImageDraw.Draw(img)

    # ---- device plate + screws ----
    t.plate(d, (MARGIN, MARGIN, W - MARGIN, plate_bottom), radius=22)
    for sx, sy in ((MARGIN + 16, MARGIN + 16), (W - MARGIN - 16, MARGIN + 16),
                   (MARGIN + 16, plate_bottom - 16), (W - MARGIN - 16, plate_bottom - 16)):
        t.screw(d, sx, sy)

    live = payload.get("__source") != "fallback"

    # ---- header ----
    f_mark = t.font(40, "Heavy")
    title = (payload.get("arcade", {}).get("title", "Agent Arcade")).upper()
    d.text((x0, header_y + 4), title, font=f_mark, fill=t.INK)
    title_w = t.text_len(d, title, f_mark)

    f_model = t.font(15, "Semibold", mono=True)
    model = f"AA-8 · {(payload.get('arcade', {}).get('location', 'local')).upper()}"
    mw = t.text_len(d, model, f_model)
    bx = x0 + title_w + 20
    by = header_y + 14
    d.rounded_rectangle((bx, by, bx + mw + 22, by + 30), radius=6, fill=t.INK)
    d.text((bx + 11, by + 6), model, font=f_model, fill=t.PLATE)

    # right cluster: live indicator + palette chips
    f_rec = t.font(14, "Semibold", mono=True)
    rec = "LIVE" if live else "SAMPLE"
    rec_w = t.text_len(d, rec, f_rec) + len(rec) * 1.4
    rec_x = x1 - rec_w
    t.tracked(d, (rec_x, header_y + 16), rec, f_rec, t.INK2 if live else t.FAINT, tracking=1.4)
    led_x = rec_x - 18
    led_c = t.ORANGE if live else t.BUSY
    d.ellipse((led_x - 6, header_y + 18, led_x + 6, header_y + 30), fill=led_c)
    chips = [(255, 90, 31), (31, 175, 90), (47, 109, 255), (255, 194, 31), (21, 20, 15)]
    cx = led_x - 22 - (len(chips) * 18)
    for c in chips:
        d.rounded_rectangle((cx, header_y + 16, cx + 14, header_y + 30), radius=3, fill=c)
        cx += 18

    # ---- LCD readout ----
    t.lcd_panel(d, (x0, lcd_y, x1, lcd_y + lcd_h))
    version = hermes.get("version", {})
    cron = hermes.get("cron", {})
    jobs = cron.get("active_jobs", hermes.get("cron_list", {}).get("count", 0))
    gateway_up = bool(hermes.get("gateway", {}).get("running"))
    clean = bool(repo.get("clean"))
    segs = [
        ("VER", f"v{version.get('version', '?')}", False),
        ("GATE", "ON" if gateway_up else "OFF", not gateway_up),
        ("CRON", f"{jobs} JOBS", not cron.get("running")),
        ("GIT", "CLEAN" if clean else f"{repo.get('changed_files', 0)}Δ", not clean),
        ("NEXT", t.fmt_time(cron.get("next_run")) if cron.get("running") else "—", not cron.get("running")),
    ]
    f_k = t.font(13, "Medium", mono=True)
    f_v = t.font(23, "Semibold", mono=True)
    seg_x = x0 + 26
    for key, val, warn in segs:
        t.tracked(d, (seg_x, lcd_y + 20), key, f_k, t.LCD_DIM, tracking=1.6)
        d.text((seg_x, lcd_y + 38), val, font=f_v, fill=t.BUSY if warn else t.LCD)
        seg_x += max(150, t.text_len(d, val, f_v) + 70)

    scroll = f"build {version.get('build', '?')} · {repo.get('branch', '—')} @ {repo.get('head', '—')}"
    f_scroll = t.font(15, "Regular", mono=True)
    d.text((x1 - 24 - t.text_len(d, scroll, f_scroll), lcd_y + 30), scroll, font=f_scroll, fill=t.LCD_DIM)

    # ---- mixer channel strips ----
    _strip_label(d, x0, x1, mixer_label_y, f"Fleet · {len(agents)} channels")
    f_num = t.font(30, "Heavy", mono=True)
    f_name = t.font(19, "Bold")
    f_role = t.font(12, "Medium", mono=True)
    f_state = t.font(11, "Bold", mono=True)
    f_cab = t.font(13, "Regular", mono=True)
    for i, a in enumerate(agents):
        col, row = i % card_w_cols, i // card_w_cols
        cx0 = x0 + col * (card_w + grid_gap)
        cy0 = grid_y + row * (card_h + grid_gap)
        t.plate(d, (cx0, cy0, cx0 + card_w, cy0 + card_h), radius=12, recessed=True)

        state = t.state_for(a.get("status", "ready"))
        accent = t.accent_rgb(a.get("accent"))

        d.text((cx0 + 18, cy0 + 14), str(a.get("order", i + 1)).zfill(2), font=f_num, fill=t.INK)
        t.knob(d, cx0 + card_w - 36, cy0 + 32, 18, accent, -58 + i * 16)

        d.text((cx0 + 18, cy0 + 58), t.ellipsize(d, a.get("label", a.get("id", "—")), f_name, card_w - 36), font=f_name, fill=t.INK)
        t.tracked(d, (cx0 + 18, cy0 + 86), (a.get("role", "")).upper(), f_role, t.FAINT, tracking=0.6)

        bottom = cy0 + card_h - 16
        on_color = t.OK if state == "ok" else t.BUSY
        t.meter(d, cx0 + 18, bottom, 5 if state == "ok" else 3, 5, on_color)
        t.fader(d, (cx0 + 44, cy0 + 108, cx0 + 78, bottom), 0.10 if state == "ok" else 0.42, accent)

        # state badge + cabinet
        meta_x = cx0 + 92
        label = (a.get("status", "ready")).upper()
        lw = t.text_len(d, label, f_state) + len(label) * 1.0
        if state == "ok":
            badge_bg, badge_fg = t.mix(t.OK, t.PLATE, 0.22), (10, 94, 47)
        else:
            badge_bg, badge_fg = t.mix(t.BUSY, t.PLATE, 0.30), (138, 74, 0)
        d.rounded_rectangle((meta_x, cy0 + 110, meta_x + lw + 14, cy0 + 130), radius=4, fill=badge_bg)
        t.tracked(d, (meta_x + 7, cy0 + 114), label, f_state, badge_fg, tracking=1.0)
        d.text((meta_x, cy0 + 140), t.ellipsize(d, a.get("cabinet", ""), f_cab, card_w - 92 - 16), font=f_cab, fill=t.FAINT)

    # ---- patch bay ----
    _strip_label(d, x0, x1, patch_label_y, "Patch bay · scheduled routines")
    t.plate(d, (x0, patch_y, x1, patch_y + patch_h), radius=12, recessed=True)
    f_jack = t.font(16, "Semibold")
    f_cron = t.font(14, "Regular", mono=True)
    sched_x = x0 + 560
    for i, c in enumerate(entries):
        ry = patch_y + patch_pad + i * jack_h
        mid = ry + jack_h / 2
        on = (c.get("state", "active") == "active")
        t.toggle(d, x0 + 42, mid, on)
        d.text((x0 + 72, mid - 11), t.ellipsize(d, c.get("name", ""), f_jack, sched_x - (x0 + 72) - 20), font=f_jack, fill=t.INK)
        d.text((sched_x, mid - 9), c.get("schedule", ""), font=f_cron, fill=t.INK2)
        nxt = (c.get("next_run", "") or "")[5:16].replace("T", " ") or "—"
        d.text((x1 - 16 - t.text_len(d, nxt, f_cron), mid - 9), nxt, font=f_cron, fill=t.FAINT)
        if i < len(entries) - 1:
            d.line((x0 + 14, ry + jack_h, x1 - 14, ry + jack_h), fill=t.LINE, width=1)

    # ---- cartridge bay ----
    if summon_rows:
        _strip_label(d, x0, x1, summon_label_y, "Cartridge bay · summon mode")
        summon_card_w = (inner - summon_gap) / summon_cols
        f_cart_num = t.font(24, "Heavy", mono=True)
        f_cart_stamp = t.font(12, "Bold", mono=True)
        f_cart_label = t.font(18, "Heavy")
        f_cart_slot = t.font(12, "Medium", mono=True)
        f_cart_head = t.font(15, "Bold")
        f_cart_body = t.font(14, "Regular")
        accent_map = {
            "orange": t.ORANGE,
            "plum": t.ACCENTS["plum"],
            "cobalt": t.ACCENTS["cobalt"],
            "yellow": t.ACCENTS["gold"],
        }
        for i, cartridge in enumerate(cartridges):
            col, row = i % summon_cols, i // summon_cols
            cx0 = x0 + col * (summon_card_w + summon_gap)
            cy0 = summon_y + row * (summon_card_h + summon_gap)
            t.plate(d, (cx0, cy0, cx0 + summon_card_w, cy0 + summon_card_h), radius=14, recessed=True)
            accent = accent_map.get(cartridge.get("accent"), t.ORANGE)
            d.rounded_rectangle((cx0, cy0, cx0 + 10, cy0 + summon_card_h), radius=14, fill=accent)
            d.text((cx0 + 24, cy0 + 14), str(i + 1).zfill(2), font=f_cart_num, fill=t.INK)
            stamp = (cartridge.get("stamp") or "manual summon").upper()
            t.tracked(d, (cx0 + summon_card_w - 18 - _tracked_w(d, stamp, f_cart_stamp, 1.0), cy0 + 18), stamp, f_cart_stamp, t.INK2, tracking=1.0)
            label = (cartridge.get("label") or cartridge.get("persona") or "Cartridge").upper()
            d.text((cx0 + 24, cy0 + 48), label, font=f_cart_label, fill=t.INK)
            slot = (cartridge.get("slot") or "bay").upper()
            t.tracked(d, (cx0 + 24, cy0 + 74), slot, f_cart_slot, t.FAINT, tracking=1.0)
            headline = t.clamp_text(cartridge.get("headline", ""), 60)
            d.rounded_rectangle((cx0 + 24, cy0 + 94, cx0 + summon_card_w - 18, cy0 + 118), radius=8, fill=t.mix(accent, t.PLATE, 0.16))
            d.text((cx0 + 32, cy0 + 99), headline, font=f_cart_head, fill=t.INK)
            body_lines = t.wrap_text(d, cartridge.get("body", ""), f_cart_body, summon_card_w - 42, 2)
            for line_index, line in enumerate(body_lines):
                d.text((cx0 + 24, cy0 + 123 + line_index * 16), line, font=f_cart_body, fill=t.INK2)

    # ---- transport footer ----
    d.line((x0, foot_y, x1, foot_y), fill=t.LINE2, width=2)
    keys = [("◀", False), ("▶", False), ("●", True), ("■", False)]
    kx = x0
    f_key = t.font(15, "Regular")
    for glyph, accent in keys:
        d.rounded_rectangle((kx, foot_y + 14, kx + 34, foot_y + 42), radius=6,
                            fill=t.ORANGE if accent else t.PLATE, outline=t.LINE2, width=1)
        gw = t.text_len(d, glyph, f_key)
        d.text((kx + 17 - gw / 2, foot_y + 19), glyph, font=f_key, fill=(255, 255, 255) if accent else t.INK2)
        kx += 42

    f_stamp = t.font(14, "Medium", mono=True)
    stamp = (f"LIVE SNAPSHOT · {t.fmt_snapshot(payload.get('generated_at', ''))}"
             if live else "SAMPLE DATA · FILE://")
    t.tracked(d, (x1 - _tracked_w(d, stamp, f_stamp, 0.8), foot_y + 22), stamp, f_stamp, t.FAINT, tracking=0.8)

    img.save(OUT)
    return OUT


def _strip_label(d, x0, x1, y, text) -> None:
    f = t.font(14, "Bold", mono=True)
    end = t.tracked(d, (x0 + 4, y), text.upper(), f, t.INK2, tracking=1.6)
    dash_x = end + 14
    while dash_x < x1:
        d.line((dash_x, y + 9, min(dash_x + 6, x1), y + 9), fill=t.LINE2, width=2)
        dash_x += 10


def _tracked_w(d, text, fnt, tracking) -> float:
    return t.text_len(d, text, fnt) + len(text) * tracking


if __name__ == "__main__":
    print(render())
