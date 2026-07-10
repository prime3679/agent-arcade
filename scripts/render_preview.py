#!/usr/bin/env python3
"""Render the full Agent Arcade cabinet lineup to a PNG.

The preview mirrors the web dashboard: compact masthead, horizontal power
strip, responsive cabinet units, and grouped routines. It stays static and
truthful: no live LEDs, fake motion, or decorative hardware controls.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

import arcade_theme as t

OUT = t.ROOT / "agent-arcade-preview.png"

W = 1400
MARGIN = 46
PAD = 40


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

    header_h, strip_h, label_h = 64, 72, 28
    gap = 14
    cols = 4
    unit_w = (inner - (cols - 1) * gap) / cols
    unit_h = 178
    priority = next((i for i, a in enumerate(agents) if t.state_for(a.get("status", "ready")) != "ok"), -1)
    unit_boxes = _layout_units(agents, priority, x0, unit_w, unit_h, gap, cols)
    fleet_h = max((box[3] for _, box in unit_boxes), default=0)

    recurring = [entry for entry in entries if _is_recurring(entry.get("schedule"))]
    one_time = [entry for entry in entries if not _is_recurring(entry.get("schedule"))]
    routine_rows = max(len(recurring), 1) + max(len(one_time), 1)
    routines_h = 46 + routine_rows * 34

    summon_cols = 2
    summon_gap = 14
    summon_card_h = 132
    summon_rows = (len(cartridges) + summon_cols - 1) // summon_cols if cartridges else 0
    summon_h = summon_rows * summon_card_h + max(0, summon_rows - 1) * summon_gap
    foot_h = 42

    header_y = MARGIN + PAD
    strip_y = header_y + header_h
    fleet_label_y = strip_y + strip_h + 22
    fleet_y = fleet_label_y + label_h
    routines_label_y = fleet_y + fleet_h + 28
    routines_y = routines_label_y + label_h
    summon_label_y = routines_y + routines_h + 28 if summon_rows else None
    summon_y = summon_label_y + label_h if summon_label_y is not None else None
    foot_y = (summon_y + summon_h + 24) if summon_y is not None else (routines_y + routines_h + 24)
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
    f_title = t.font(36, "Heavy")
    f_small = t.font(15, "Semibold")
    f_mono = t.font(14, "Regular", mono=True)
    title = payload.get("arcade", {}).get("title", "Agent Arcade")
    d.text((x0, header_y + 2), title, font=f_title, fill=t.INK)
    model = f"AA-8 {(payload.get('arcade', {}).get('location', 'local')).lower()} cabinet"
    d.text((x0, header_y + 44), model, font=f_small, fill=t.ORANGE)

    badge = "Snapshot" if live else "Sample"
    stamp = t.fmt_snapshot(payload.get("generated_at", ""))
    badge_w = max(t.text_len(d, badge, f_small), t.text_len(d, stamp, f_mono)) + 34
    bx = x1 - badge_w
    d.rectangle((bx, header_y + 8, x1, header_y + 56), fill=t.PAPER, outline=t.LINE)
    d.rectangle((bx, header_y + 8, bx + 5, header_y + 56), fill=t.ORANGE)
    d.text((bx + 16, header_y + 15), badge, font=f_small, fill=t.INK2)
    d.text((bx + 16, header_y + 34), stamp, font=f_mono, fill=t.FAINT)

    # ---- power strip ----
    t.plate(d, (x0, strip_y, x1, strip_y + strip_h), radius=8, recessed=True)
    facts = [
        ("Hermes", f"v{version.get('version', '?')}", version.get("build", "build unknown"), "ok" if version.get("ok", True) is not False else "warn"),
        ("Gateway", "running" if gateway_up else "offline", "local process" if gateway_up else "no process", "ok" if gateway_up else "warn"),
        ("Cron", "running" if cron.get("running") else "paused", f"{jobs} jobs", "ok" if cron.get("running") else "warn"),
        ("Repository", "clean" if clean else f"{repo.get('changed_files', 0)} changed", "working tree", "ok" if clean else "busy"),
        ("Next Run", t.fmt_time(cron.get("next_run")) if cron.get("running") else "-", t.fmt_snapshot(cron.get("next_run")), "ok" if cron.get("running") else "warn"),
    ]
    _power_strip(d, facts, x0, strip_y, inner, strip_h)

    # ---- fleet lineup ----
    _section_label(d, x0, x1, fleet_label_y, "Cabinet lineup", f"{len(agents)} agents")
    for idx, box in unit_boxes:
        bx0, by0, bx1, by1 = box
        _agent_unit(d, agents[idx], idx, (bx0, by0 + fleet_y, bx1, by1 + fleet_y), priority == idx)

    # ---- routines ----
    _section_label(d, x0, x1, routines_label_y, "Routines", f"{len(entries)} scheduled")
    t.plate(d, (x0, routines_y, x1, routines_y + routines_h), radius=8, recessed=False)
    mid_x = x0 + inner * 0.64
    d.line((mid_x, routines_y + 16, mid_x, routines_y + routines_h - 16), fill=t.LINE2, width=1)
    _routine_group(d, "Recurring", recurring, x0 + 18, routines_y + 18, mid_x - x0 - 36)
    _routine_group(d, "One-time", one_time, mid_x + 18, routines_y + 18, x1 - mid_x - 36)

    # ---- cartridges ----
    if summon_rows:
        _section_label(d, x0, x1, summon_label_y, "Cartridge story", f"{len(cartridges)} cartridges")
        card_w = (inner - summon_gap) / summon_cols
        for i, cartridge in enumerate(cartridges):
            col, row = i % summon_cols, i // summon_cols
            cx0 = x0 + col * (card_w + summon_gap)
            cy0 = summon_y + row * (summon_card_h + summon_gap)
            _cartridge(d, cartridge, i, (cx0, cy0, cx0 + card_w, cy0 + summon_card_h))

    # ---- footer ----
    d.line((x0, foot_y, x1, foot_y), fill=t.LINE2, width=1)
    f_foot = t.font(14, "Medium")
    f_time = t.font(14, "Regular", mono=True)
    d.text((x0, foot_y + 14), "read-only · no sends · no config writes", font=f_foot, fill=t.FAINT)
    build = f"hermes v{version.get('version', '?')}"
    if version.get("build"):
        build += f" · {version.get('build')}"
    d.text((x1 - t.text_len(d, build, f_time), foot_y + 14), build, font=f_time, fill=t.FAINT)

    img.save(OUT)
    return OUT


def _is_recurring(schedule: str | None) -> bool:
    value = str(schedule or "")
    if "once" in value.lower():
        return False
    return any(ch in value for ch in ("*", "/", ",", "-"))


def _layout_units(agents, priority: int, x0: float, unit_w: float, unit_h: float, gap: float, cols: int):
    boxes = []
    col = 0
    row = 0
    for idx, _agent in enumerate(agents):
        span = 2 if idx == priority else 1
        if span > cols:
            span = cols
        if col + span > cols:
            row += 1
            col = 0
        w = unit_w * span + gap * (span - 1)
        h = unit_h + (18 if span > 1 else 0)
        boxes.append((idx, (x0 + col * (unit_w + gap), row * (unit_h + gap), x0 + col * (unit_w + gap) + w, row * (unit_h + gap) + h)))
        col += span
        if col >= cols:
            row += 1
            col = 0
    return boxes


def _section_label(d, x0, x1, y, title, count) -> None:
    f_title = t.font(18, "Bold")
    f_count = t.font(14, "Medium")
    d.text((x0, y), title, font=f_title, fill=t.INK)
    d.text((x1 - t.text_len(d, count, f_count), y + 2), count, font=f_count, fill=t.INK2)


def _power_strip(d, facts, x0, y, inner, h) -> None:
    f_label = t.font(12, "Medium")
    f_value = t.font(20, "Bold")
    f_detail = t.font(12, "Regular")
    seg = inner / len(facts)
    for i, (label, value, detail, state) in enumerate(facts):
        sx = x0 + i * seg
        if i:
            d.line((sx, y + 10, sx, y + h - 10), fill=t.LINE2, width=1)
        if state != "ok":
            d.rectangle((sx + 1, y + 1, sx + seg - 1, y + h - 1), fill=t.mix(t.STATE_COLORS[state], t.PLATE2, 0.08))
        d.text((sx + 16, y + 13), label, font=f_label, fill=t.INK2)
        d.text((sx + 16, y + 30), t.ellipsize(d, value, f_value, seg - 32), font=f_value, fill=t.INK)
        d.text((sx + 16, y + 53), t.ellipsize(d, detail, f_detail, seg - 32), font=f_detail, fill=t.FAINT)


def _agent_unit(d, agent, idx: int, box, priority: bool) -> None:
    x0, y0, x1, y1 = box
    state = t.state_for(agent.get("status", "ready"))
    state_color = t.STATE_COLORS.get(state, t.BUSY)
    fill = t.mix(state_color, t.PLATE, 0.055 if state != "ok" else 0.0)
    d.rectangle(box, fill=fill, outline=t.LINE2, width=1)
    d.rectangle((x0, y0, x1, y0 + 6), fill=state_color)

    f_num = t.font(23 if priority else 19, "Heavy", mono=True)
    f_name = t.font(26 if priority else 20, "Heavy")
    f_role = t.font(14, "Medium")
    f_signal = t.font(16 if priority else 14, "Regular")
    f_base = t.font(13, "Semibold")

    d.text((x0 + 18, y0 + 22), str(agent.get("order", idx + 1)).zfill(2), font=f_num, fill=t.FAINT)
    name_x = x0 + (62 if priority else 58)
    d.text((name_x, y0 + 18), t.ellipsize(d, agent.get("label", agent.get("id", "-")), f_name, x1 - name_x - 16), font=f_name, fill=t.INK)
    d.text((name_x, y0 + (51 if priority else 46)), t.ellipsize(d, agent.get("role", ""), f_role, x1 - name_x - 16), font=f_role, fill=t.INK2)

    well = (x0 + 16, y0 + (78 if priority else 72), x1 - 16, y1 - 48)
    d.rectangle(well, fill=t.WELL, outline=t.LINE2, width=1)
    signal = agent.get("signal") or agent.get("tagline") or "No signal"
    for line_index, line in enumerate(t.wrap_text(d, signal, f_signal, well[2] - well[0] - 22, 3 if priority else 2)):
        d.text((well[0] + 11, well[1] + 12 + line_index * (19 if priority else 17)), line, font=f_signal, fill=t.INK2)

    d.line((x0, y1 - 38, x1, y1 - 38), fill=t.LINE, width=1)
    status = agent.get("status", "ready")
    slot = agent.get("cabinet", "cabinet")
    d.text((x0 + 18, y1 - 27), status, font=f_base, fill=t.INK)
    slot_text = t.ellipsize(d, slot, f_base, (x1 - x0) * 0.48)
    d.text((x1 - 18 - t.text_len(d, slot_text, f_base), y1 - 27), slot_text, font=f_base, fill=t.FAINT)


def _routine_group(d, title, rows, x, y, w) -> None:
    f_title = t.font(16, "Bold")
    f_name = t.font(15, "Semibold")
    f_small = t.font(13, "Regular", mono=True)
    f_state = t.font(13, "Medium")
    d.text((x, y), title, font=f_title, fill=t.INK)
    cy = y + 30
    if not rows:
        d.text((x, cy), "None configured", font=f_state, fill=t.FAINT)
        return
    for idx, row in enumerate(rows):
        if idx:
            d.line((x, cy - 7, x + w, cy - 7), fill=t.LINE, width=1)
        name = t.ellipsize(d, row.get("name", ""), f_name, w * 0.5)
        d.text((x, cy), name, font=f_name, fill=t.INK)
        state = row.get("state", "active")
        d.text((x + w * 0.53, cy + 1), state, font=f_state, fill=t.OK if state == "active" else t.WARN)
        schedule_value = row.get("schedule", "")
        if "once" in str(schedule_value).lower():
            schedule_value = "once"
        schedule = t.ellipsize(d, schedule_value, f_small, w * 0.15)
        d.text((x + w * 0.66, cy + 1), schedule, font=f_small, fill=t.INK2)
        nxt = t.fmt_snapshot(row.get("next_run", ""))
        d.text((x + w - t.text_len(d, nxt, f_small), cy + 1), nxt, font=f_small, fill=t.FAINT)
        cy += 34


def _cartridge(d, cartridge, idx: int, box) -> None:
    x0, y0, x1, y1 = box
    accent = t.accent_rgb(cartridge.get("accent"))
    t.plate(d, box, radius=8, recessed=True)
    d.rectangle((x0, y0, x0 + 6, y1), fill=accent)
    f_num = t.font(20, "Heavy", mono=True)
    f_label = t.font(18, "Heavy")
    f_small = t.font(12, "Medium")
    f_body = t.font(14, "Regular")
    d.text((x0 + 18, y0 + 14), str(idx + 1).zfill(2), font=f_num, fill=t.INK)
    label = cartridge.get("label") or cartridge.get("persona") or "Cartridge"
    d.text((x0 + 58, y0 + 15), t.ellipsize(d, label, f_label, x1 - x0 - 76), font=f_label, fill=t.INK)
    d.text((x0 + 58, y0 + 42), t.ellipsize(d, cartridge.get("slot", "bay"), f_small, x1 - x0 - 76), font=f_small, fill=t.FAINT)
    for line_index, line in enumerate(t.wrap_text(d, cartridge.get("headline", ""), f_body, x1 - x0 - 36, 2)):
        d.text((x0 + 18, y0 + 74 + line_index * 17), line, font=f_body, fill=t.INK2)


if __name__ == "__main__":
    print(render())
