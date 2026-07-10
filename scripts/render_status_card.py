#!/usr/bin/env python3
"""Render a compact Agent Arcade status card from data/latest.json."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

import arcade_theme as t

OUT = t.ROOT / "agent-arcade-status.png"

W = 1000
MARGIN = 34
PAD = 30


def render() -> Path:
    payload = t.load_data()
    summon = t.load_summon() or {}
    agents = payload.get("agents", [])
    hermes = payload.get("hermes", {})
    repo = payload.get("repo", {})
    cartridges = summon.get("cartridges", [])

    x0 = MARGIN + PAD
    x1 = W - MARGIN - PAD
    inner = x1 - x0

    header_h, strip_h, label_h = 54, 62, 24
    gap = 12
    chip_w = (inner - gap) / 2
    chip_h = 76
    rows = (len(agents[:8]) + 1) // 2
    fleet_h = rows * chip_h + max(0, rows - 1) * gap
    summon_h = 64 if cartridges else 0
    foot_h = 28

    header_y = MARGIN + PAD
    strip_y = header_y + header_h
    fleet_label_y = strip_y + strip_h + 18
    grid_y = fleet_label_y + label_h
    summon_label_y = grid_y + fleet_h + 18 if cartridges else None
    summon_y = summon_label_y + label_h if summon_label_y is not None else None
    foot_y = (summon_y + summon_h + 18) if summon_y is not None else (grid_y + fleet_h + 18)
    plate_bottom = foot_y + foot_h + PAD
    H = plate_bottom + MARGIN

    img = Image.new("RGB", (W, H))
    t.paper_backdrop(img)
    d = ImageDraw.Draw(img)

    t.plate(d, (MARGIN, MARGIN, W - MARGIN, plate_bottom), radius=14)

    live = payload.get("__source") != "fallback"
    version = hermes.get("version", {})
    cron = hermes.get("cron", {})
    jobs = cron.get("active_jobs", hermes.get("cron_list", {}).get("count", 0))
    gateway_up = bool(hermes.get("gateway", {}).get("running"))
    clean = bool(repo.get("clean"))

    # ---- masthead ----
    f_title = t.font(28, "Heavy")
    f_badge = t.font(13, "Semibold")
    f_time = t.font(13, "Regular", mono=True)
    title = payload.get("arcade", {}).get("title", "Agent Arcade")
    d.text((x0, header_y + 4), title, font=f_title, fill=t.INK)
    d.text((x0, header_y + 36), "AA-8 local cabinet", font=f_badge, fill=t.ORANGE)

    badge = "Snapshot" if live else "Sample"
    stamp = t.fmt_snapshot(payload.get("generated_at", ""))
    d.text((x1 - t.text_len(d, badge, f_badge), header_y + 8), badge, font=f_badge, fill=t.INK2)
    d.text((x1 - t.text_len(d, stamp, f_time), header_y + 30), stamp, font=f_time, fill=t.FAINT)

    # ---- compact power strip ----
    t.plate(d, (x0, strip_y, x1, strip_y + strip_h), radius=8, recessed=True)
    facts = [
        ("HER", f"v{version.get('version', '?')}", "ok" if version.get("ok", True) is not False else "warn"),
        ("GATE", "on" if gateway_up else "off", "ok" if gateway_up else "warn"),
        ("CRON", f"{jobs}", "ok" if cron.get("running") else "warn"),
        ("GIT", "clean" if clean else f"{repo.get('changed_files', 0)} changed", "ok" if clean else "busy"),
        ("NEXT", t.fmt_time(cron.get("next_run")) if cron.get("running") else "-", "ok" if cron.get("running") else "warn"),
    ]
    _mini_strip(d, facts, x0, strip_y, inner, strip_h)

    # ---- cabinet units ----
    _label(d, x0, x1, fleet_label_y, "Cabinet lineup", f"{len(agents)} agents")
    priority = next((i for i, a in enumerate(agents) if t.state_for(a.get("status", "ready")) != "ok"), -1)
    for idx, agent in enumerate(agents[:8]):
        col, row = idx % 2, idx // 2
        cx0 = x0 + col * (chip_w + gap)
        cy0 = grid_y + row * (chip_h + gap)
        _mini_unit(d, agent, idx, (cx0, cy0, cx0 + chip_w, cy0 + chip_h), idx == priority)

    # ---- summon strip ----
    if cartridges:
        _label(d, x0, x1, summon_label_y, "Cartridge story", f"{len(cartridges)} loaded")
        t.plate(d, (x0, summon_y, x1, summon_y + summon_h), radius=8, recessed=True)
        f_cart = t.font(14, "Bold")
        f_body = t.font(12, "Regular")
        card_gap = 10
        card_w = (inner - card_gap * (len(cartridges) - 1)) / max(1, len(cartridges))
        for idx, cartridge in enumerate(cartridges):
            cx0 = x0 + idx * (card_w + card_gap)
            accent = t.accent_rgb(cartridge.get("accent"))
            d.rectangle((cx0, summon_y, cx0 + card_w, summon_y + summon_h), fill=t.PLATE, outline=t.LINE)
            d.rectangle((cx0, summon_y, cx0 + 5, summon_y + summon_h), fill=accent)
            d.text((cx0 + 14, summon_y + 10), t.ellipsize(d, cartridge.get("label", cartridge.get("persona", "Cartridge")), f_cart, card_w - 28), font=f_cart, fill=t.INK)
            for line_index, line in enumerate(t.wrap_text(d, cartridge.get("headline", ""), f_body, card_w - 28, 2)):
                d.text((cx0 + 14, summon_y + 31 + line_index * 14), line, font=f_body, fill=t.INK2)

    # ---- footer ----
    d.line((x0, foot_y, x1, foot_y), fill=t.LINE2, width=1)
    f_foot = t.font(13, "Medium")
    d.text((x0, foot_y + 10), "read-only · no sends · no config writes", font=f_foot, fill=t.FAINT)
    build = f"hermes v{version.get('version', '?')}"
    d.text((x1 - t.text_len(d, build, f_time), foot_y + 10), build, font=f_time, fill=t.FAINT)

    img.save(OUT)
    return OUT


def _label(d, x0, x1, y, title, count) -> None:
    f_title = t.font(15, "Bold")
    f_count = t.font(13, "Medium")
    d.text((x0, y), title, font=f_title, fill=t.INK)
    d.text((x1 - t.text_len(d, count, f_count), y + 1), count, font=f_count, fill=t.INK2)


def _mini_strip(d, facts, x0, y, inner, h) -> None:
    f_key = t.font(10, "Bold")
    f_val = t.font(17, "Bold")
    seg = inner / len(facts)
    for i, (key, val, state) in enumerate(facts):
        sx = x0 + i * seg
        if i:
            d.line((sx, y + 9, sx, y + h - 9), fill=t.LINE2, width=1)
        if state != "ok":
            d.rectangle((sx + 1, y + 1, sx + seg - 1, y + h - 1), fill=t.mix(t.STATE_COLORS[state], t.PLATE2, 0.09))
        d.text((sx + 12, y + 13), key, font=f_key, fill=t.INK2)
        d.text((sx + 12, y + 31), t.ellipsize(d, val, f_val, seg - 24), font=f_val, fill=t.INK)


def _mini_unit(d, agent, idx: int, box, priority: bool) -> None:
    x0, y0, x1, y1 = box
    state = t.state_for(agent.get("status", "ready"))
    state_color = t.STATE_COLORS.get(state, t.BUSY)
    fill = t.mix(state_color, t.PLATE, 0.06 if state != "ok" else 0.0)
    d.rectangle(box, fill=fill, outline=t.LINE2, width=1)
    d.rectangle((x0, y0, x1, y0 + 5), fill=state_color)

    f_num = t.font(18, "Heavy", mono=True)
    f_name = t.font(17 if not priority else 19, "Heavy")
    f_base = t.font(12, "Medium")
    f_signal = t.font(12, "Regular")
    d.text((x0 + 14, y0 + 18), str(agent.get("order", idx + 1)).zfill(2), font=f_num, fill=t.FAINT)
    d.text((x0 + 52, y0 + 16), t.ellipsize(d, agent.get("label", agent.get("id", "-")), f_name, x1 - x0 - 66), font=f_name, fill=t.INK)
    d.text((x0 + 52, y0 + 39), t.ellipsize(d, agent.get("role", ""), f_base, x1 - x0 - 66), font=f_base, fill=t.INK2)
    signal = agent.get("signal") or agent.get("tagline") or "No signal"
    d.text((x0 + 14, y1 - 24), t.ellipsize(d, signal, f_signal, x1 - x0 - 28), font=f_signal, fill=t.FAINT)


if __name__ == "__main__":
    print(render())
