#!/usr/bin/env python3
"""Render a compact, Telegram-friendly status card from data/latest.json.

Glanceable summary of the fleet: system vitals across the top, fleet health,
and a tight two-column agent list. Smaller and denser than the full preview so
it reads well inline in a chat. Same graphite language as the web console.
"""
from __future__ import annotations

from PIL import Image, ImageDraw

import arcade_theme as t

OUT = t.ROOT / "agent-arcade-status.png"

W, H = 1000, 600
PAD = 52


def render():
    p = t.load_data()
    agents = p.get("agents", [])
    hermes = p.get("hermes", {})
    repo = p.get("repo", {})

    img = Image.new("RGB", (W, H))
    t.vertical_backdrop(img)
    d = ImageDraw.Draw(img)

    f_title = t.font(34, "Semibold")
    f_label = t.font(12, "Medium")
    f_val = t.font(24, "Medium", mono=True)
    f_sub = t.font(13, "Regular", mono=True)
    f_meta = t.font(14, "Regular", mono=True)
    f_name = t.font(17, "Medium")
    f_cab = t.font(12, "Regular", mono=True)
    f_section = t.font(13, "Semibold")

    live = p.get("__source") != "fallback"

    # ---- Header ----
    d.text((PAD, 44), p.get("arcade", {}).get("title", "Agent Arcade"), font=f_title, fill=t.TEXT)
    t.status_dot(d, PAD + 5, 92, "ok" if live else "default", r=4)
    t.tracked(d, (PAD + 18, 86), "LIVE" if live else "SAMPLE", f_label, t.DIM if live else t.FAINT, tracking=2.0)
    snap = t.fmt_snapshot(p.get("generated_at", ""))
    d.text((W - PAD - t.text_len(d, snap, f_meta), 50), snap, font=f_meta, fill=t.FAINT)
    branch = repo.get("branch") or "local"
    d.text((W - PAD - t.text_len(d, branch, f_sub), 76), branch, font=f_sub, fill=t.FAINT)

    d.line((PAD, 122, W - PAD, 122), fill=t.LINE, width=1)

    # ---- Vitals ----
    gateway_up = bool(hermes.get("gateway", {}).get("running"))
    cron_up = bool(hermes.get("cron", {}).get("running"))
    cron_count = hermes.get("cron_list", {}).get("count", 0)
    clean = bool(repo.get("clean"))
    version = hermes.get("version", {}).get("version") or "unknown"

    vitals = [
        ("HERMES", f"v{version}" if version != "unknown" else version, "ok" if version != "unknown" else "warn"),
        ("GATEWAY", "Online" if gateway_up else "Offline", "ok" if gateway_up else "warn"),
        ("SCHEDULER", f"{cron_count} jobs", "ok" if cron_up else "warn"),
        ("WORKTREE", "Clean" if clean else f"{repo.get('changed_files', 0)} chg", "ok" if clean else "active"),
    ]
    vy = 150
    seg = (W - 2 * PAD) / len(vitals)
    for i, (label, value, state) in enumerate(vitals):
        sx = PAD + i * seg
        if i:
            d.line((sx - 1, vy + 6, sx - 1, vy + 70), fill=t.LINE, width=1)
        t.tracked(d, (sx + (0 if i == 0 else 22), vy), label, f_label, t.FAINT, tracking=1.8)
        tx = sx + (0 if i == 0 else 22)
        d.rounded_rectangle((tx, vy + 30, tx + 7, vy + 37), radius=2, fill=t.STATE_COLORS.get(state, t.FAINT))
        d.text((tx + 15, vy + 24), value, font=f_val, fill=t.TEXT)

    d.line((PAD, 252, W - PAD, 252), fill=t.LINE, width=1)

    # ---- Fleet header + health ----
    counts = {"ok": 0, "active": 0, "warn": 0}
    for a in agents:
        counts[t.state_for(a.get("status", "ready"))] += 1
    t.tracked(d, (PAD, 274), "FLEET", f_section, t.DIM, tracking=2.2)

    chips = [("ready", counts["ok"], "ok"), ("active", counts["active"], "active"), ("warning", counts["warn"], "warn")]
    cx = W - PAD
    for word, n, state in reversed(chips):
        label = f"{n} {word}"
        cx -= t.text_len(d, label, f_sub)
        d.text((cx, 276), label, font=f_sub, fill=t.DIM)
        cx -= 14
        t.status_dot(d, cx - 2, 282, state, r=4)
        cx -= 20

    # ---- Two-column agent list ----
    gy = 314
    row_h = 56
    col_w = (W - 2 * PAD - 32) / 2
    for idx, a in enumerate(agents[:8]):
        col = idx % 2
        row = idx // 2
        ax = PAD + col * (col_w + 32)
        ay = gy + row * row_h
        mid = ay + 18
        state = t.state_for(a.get("status", "ready"))
        t.status_dot(d, ax + 5, mid, state, r=4)
        tile = (ax + 20, mid - 15, ax + 50, mid + 15)
        t.monogram(d, tile, (a.get("label", "?")[:1] or "?").upper(), a.get("accent", ""))
        d.text((ax + 62, mid - 17), a.get("label", a.get("id", "—")), font=f_name, fill=t.TEXT)
        d.text((ax + 62, mid + 3), a.get("cabinet", ""), font=f_cab, fill=t.FAINT)

    img.save(OUT)
    return OUT


if __name__ == "__main__":
    print(render())
