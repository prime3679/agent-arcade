#!/usr/bin/env python3
"""Render a compact, Telegram-friendly status card from data/latest.json.

A glanceable AA-8 face: the plastic plate, a phosphor LCD vitals strip, and a
tight two-column channel list. Smaller and denser than the full preview so it
reads well inline in a chat. Same hardware language as the web console.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

import arcade_theme as t

OUT = t.ROOT / "agent-arcade-status.png"

W = 1000
MARGIN = 34
PAD = 30


def render() -> Path:
    p = t.load_data()
    summon = t.load_summon() or {}
    agents = p.get("agents", [])
    hermes = p.get("hermes", {})
    repo = p.get("repo", {})
    cartridges = summon.get("cartridges", [])

    x0 = MARGIN + PAD
    x1 = W - MARGIN - PAD
    inner = x1 - x0

    header_h, lcd_h, label_h = 58, 66, 24
    chip_w = (inner - 14) / 2
    chip_h, chip_gap = 64, 12
    rows = (len(agents[:8]) + 1) // 2
    fleet_h = rows * chip_h + (rows - 1) * chip_gap
    summon_h = 70 if cartridges else 0
    foot_h = 30

    header_y = MARGIN + PAD
    lcd_y = header_y + header_h
    fleet_label_y = lcd_y + lcd_h + 18
    grid_y = fleet_label_y + label_h
    summon_label_y = grid_y + fleet_h + 18 if cartridges else None
    summon_y = summon_label_y + label_h if summon_label_y is not None else None
    foot_y = (summon_y + summon_h + 18) if summon_y is not None else (grid_y + fleet_h + 18)
    plate_bottom = foot_y + foot_h + PAD
    H = plate_bottom + MARGIN

    img = Image.new("RGB", (W, H))
    t.paper_backdrop(img)
    d = ImageDraw.Draw(img)

    t.plate(d, (MARGIN, MARGIN, W - MARGIN, plate_bottom), radius=18)
    for sx, sy in ((MARGIN + 14, MARGIN + 14), (W - MARGIN - 14, MARGIN + 14),
                   (MARGIN + 14, plate_bottom - 14), (W - MARGIN - 14, plate_bottom - 14)):
        t.screw(d, sx, sy, r=6)

    live = p.get("__source") != "fallback"

    # ---- header ----
    f_mark = t.font(28, "Heavy")
    title = (p.get("arcade", {}).get("title", "Agent Arcade")).upper()
    d.text((x0, header_y + 4), title, font=f_mark, fill=t.INK)
    title_w = t.text_len(d, title, f_mark)

    f_model = t.font(13, "Semibold", mono=True)
    model = f"AA-8 · {(p.get('arcade', {}).get('location', 'local')).upper()}"
    mw = t.text_len(d, model, f_model)
    bx = x0 + title_w + 16
    d.rounded_rectangle((bx, header_y + 8, bx + mw + 18, header_y + 32), radius=5, fill=t.INK)
    d.text((bx + 9, header_y + 13), model, font=f_model, fill=t.PLATE)

    f_rec = t.font(13, "Semibold", mono=True)
    rec = "LIVE" if live else "SAMPLE"
    rec_w = t.text_len(d, rec, f_rec) + len(rec) * 1.2
    rec_x = x1 - rec_w
    t.tracked(d, (rec_x, header_y + 6), rec, f_rec, t.INK2 if live else t.FAINT, tracking=1.2)
    led_x = rec_x - 16
    d.ellipse((led_x - 5, header_y + 7, led_x + 5, header_y + 17), fill=t.ORANGE if live else t.BUSY)
    snap = t.fmt_snapshot(p.get("generated_at", ""))
    f_snap = t.font(13, "Regular", mono=True)
    d.text((x1 - t.text_len(d, snap, f_snap), header_y + 30), snap, font=f_snap, fill=t.FAINT)

    # ---- LCD vitals strip ----
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
    f_k = t.font(11, "Medium", mono=True)
    f_v = t.font(19, "Semibold", mono=True)
    seg = inner / len(segs)
    for i, (key, val, warn) in enumerate(segs):
        sx = x0 + 18 + i * seg
        t.tracked(d, (sx, lcd_y + 16), key, f_k, t.LCD_DIM, tracking=1.3)
        d.text((sx, lcd_y + 32), val, font=f_v, fill=t.BUSY if warn else t.LCD)

    # ---- fleet header + health ----
    f_label = t.font(13, "Bold", mono=True)
    t.tracked(d, (x0 + 2, fleet_label_y), f"FLEET · {len(agents)} CHANNELS", f_label, t.INK2, tracking=1.5)
    counts = {"ok": 0, "busy": 0}
    for a in agents:
        counts[t.state_for(a.get("status", "ready"))] += 1
    f_sub = t.font(13, "Regular", mono=True)
    summary = f"{counts['ok']} ready · {counts['busy']} active"
    d.text((x1 - t.text_len(d, summary, f_sub), fleet_label_y + 1), summary, font=f_sub, fill=t.FAINT)

    # ---- two-column channel list ----
    f_num = t.font(20, "Heavy", mono=True)
    f_name = t.font(16, "Bold")
    f_cab = t.font(12, "Regular", mono=True)
    f_state = t.font(10, "Bold", mono=True)
    for idx, a in enumerate(agents[:8]):
        col, row = idx % 2, idx // 2
        cx0 = x0 + col * (chip_w + 14)
        cy0 = grid_y + row * (chip_h + chip_gap)
        t.plate(d, (cx0, cy0, cx0 + chip_w, cy0 + chip_h), radius=10, recessed=True)

        state = t.state_for(a.get("status", "ready"))
        accent = t.accent_rgb(a.get("accent"))
        mid = cy0 + chip_h / 2

        d.text((cx0 + 16, mid - 13), str(a.get("order", idx + 1)).zfill(2), font=f_num, fill=t.INK)
        t.knob(d, cx0 + 60, mid, 13, accent, -58 + idx * 16)
        d.text((cx0 + 88, cy0 + 12), t.ellipsize(d, a.get("label", a.get("id", "—")), f_name, chx := chip_w - 88 - 96), font=f_name, fill=t.INK)
        d.text((cx0 + 88, cy0 + 36), t.ellipsize(d, a.get("cabinet", ""), f_cab, chx), font=f_cab, fill=t.FAINT)

        label = (a.get("status", "ready")).upper()
        lw = t.text_len(d, label, f_state) + len(label)
        if state == "ok":
            bg, fg = t.mix(t.OK, t.PLATE, 0.22), (10, 94, 47)
        else:
            bg, fg = t.mix(t.BUSY, t.PLATE, 0.30), (138, 74, 0)
        bxr = cx0 + chip_w - 14
        d.rounded_rectangle((bxr - lw - 14, mid - 10, bxr, mid + 10), radius=4, fill=bg)
        t.tracked(d, (bxr - lw - 7, mid - 6), label, f_state, fg, tracking=1.0)

    # ---- summon strip ----
    if cartridges:
        t.tracked(d, (x0 + 2, summon_label_y), "CARTRIDGE BAY · SUMMON MODE", f_label, t.INK2, tracking=1.5)
        summary = f"{len(cartridges)} loaded"
        d.text((x1 - t.text_len(d, summary, f_sub), summon_label_y + 1), summary, font=f_sub, fill=t.FAINT)
        t.plate(d, (x0, summon_y, x1, summon_y + summon_h), radius=10, recessed=True)

        f_cart = t.font(14, "Bold")
        f_body = t.font(12, "Regular", mono=True)
        card_gap = 10
        card_w = (inner - card_gap * (len(cartridges) - 1)) / max(1, len(cartridges))
        accent_map = {
            "orange": t.ORANGE,
            "plum": t.ACCENTS["plum"],
            "cobalt": t.ACCENTS["cobalt"],
            "yellow": t.ACCENTS["gold"],
        }
        for idx, cartridge in enumerate(cartridges):
            cx0 = x0 + idx * (card_w + card_gap)
            accent = accent_map.get(cartridge.get("accent"), t.ORANGE)
            d.rounded_rectangle((cx0, summon_y, cx0 + card_w, summon_y + summon_h), radius=9, fill=t.PLATE, outline=t.LINE, width=1)
            d.rounded_rectangle((cx0, summon_y, cx0 + 8, summon_y + summon_h), radius=9, fill=accent)
            d.text((cx0 + 18, summon_y + 12), cartridge.get("label", cartridge.get("persona", "Cartridge")), font=f_cart, fill=t.INK)
            for line_index, line in enumerate(t.wrap_text(d, cartridge.get("headline", ""), f_body, card_w - 28, 2)):
                d.text((cx0 + 18, summon_y + 34 + line_index * 14), line, font=f_body, fill=t.INK2)

    # ---- footer ----
    d.line((x0, foot_y, x1, foot_y), fill=t.LINE2, width=1)
    f_foot = t.font(13, "Medium", mono=True)
    t.tracked(d, (x0, foot_y + 12), "READ-ONLY · NO SENDS", f_foot, t.FAINT, tracking=0.8)
    vtxt = f"hermes v{version.get('version', '?')}" + (f" · {version.get('build')}" if version.get("build") else "")
    d.text((x1 - t.text_len(d, vtxt, f_foot), foot_y + 12), vtxt, font=f_foot, fill=t.FAINT)

    img.save(OUT)
    return OUT


if __name__ == "__main__":
    print(render())
