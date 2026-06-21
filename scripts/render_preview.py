#!/usr/bin/env python3
"""Render the full Agent Arcade console to a PNG for Telegram previews.

Mirrors the web layout: masthead, vitals strip, and a dense fleet roster on a
graphite background — the same visual direction as app/.
"""
from __future__ import annotations

from PIL import Image, ImageDraw

import arcade_theme as t

OUT = t.ROOT / "agent-arcade-preview.png"

W, H = 1400, 1140
MARGIN = 84
INNER = W - 2 * MARGIN


def vitals_data(p: dict) -> list[tuple[str, str, str, str]]:
    hermes = p.get("hermes", {})
    repo = p.get("repo", {})
    gateway_up = bool(hermes.get("gateway", {}).get("running"))
    cron_up = bool(hermes.get("cron", {}).get("running"))
    cron_count = hermes.get("cron_list", {}).get("count", 0)
    clean = bool(repo.get("clean"))
    version = hermes.get("version", {})
    pid = hermes.get("gateway", {}).get("pid")
    next_run = hermes.get("cron", {}).get("next_run")

    return [
        ("HERMES", version.get("version") or "unknown",
         f"build {version.get('build')}" if version.get("build") else "version unknown",
         "ok" if version.get("version") else "warn"),
        ("GATEWAY", "Online" if gateway_up else "Offline",
         f"pid {pid}" if pid else ("healthy" if gateway_up else "no process"),
         "ok" if gateway_up else "warn"),
        ("SCHEDULER", f"{cron_count} {'job' if cron_count == 1 else 'jobs'}",
         (f"next {t.fmt_time(next_run)}" if next_run else "running") if cron_up else "stopped",
         "ok" if cron_up else "warn"),
        ("WORKTREE", "Clean" if clean else f"{repo.get('changed_files', 0)} changed",
         f"branch {repo.get('branch')}" if repo.get("branch") else "—",
         "ok" if clean else "active"),
    ]


def render() -> Path:
    payload = t.load_data()
    agents = payload.get("agents", [])

    img = Image.new("RGB", (W, H))
    t.vertical_backdrop(img)
    d = ImageDraw.Draw(img)

    f_title = t.font(46, "Semibold")
    f_sub = t.font(20, "Regular")
    f_label = t.font(13, "Medium")
    f_meta_k = t.font(12, "Medium")
    f_meta_v = t.font(17, "Regular", mono=True)
    f_vital = t.font(30, "Medium", mono=True)
    f_vital_sub = t.font(15, "Regular", mono=True)
    f_name = t.font(20, "Medium")
    f_role = t.font(17, "Regular")
    f_signal = t.font(17, "Regular")
    f_mono_sm = t.font(14, "Regular", mono=True)

    x0 = MARGIN

    # ---- Masthead ----
    badge_y = 80
    live = payload.get("__source") != "fallback"
    t.status_dot(d, x0 + 5, badge_y + 6, "ok" if live else "default", r=4)
    t.tracked(d, (x0 + 18, badge_y), "LIVE SNAPSHOT" if live else "SAMPLE DATA",
              f_label, t.DIM if live else t.FAINT, tracking=2.2)

    arcade = payload.get("arcade", {})
    d.text((x0, badge_y + 26), arcade.get("title", "Agent Arcade"), font=f_title, fill=t.TEXT)
    d.text((x0, badge_y + 86), arcade.get("subtitle", ""), font=f_sub, fill=t.DIM)

    # right-aligned meta block
    repo = payload.get("repo", {})
    meta = [
        ("SNAPSHOT", t.fmt_snapshot(payload.get("generated_at", "")) ),
        ("LOCATION", arcade.get("location", "local")),
        ("BRANCH", repo.get("branch") or "—"),
    ]
    mx = W - MARGIN
    col_w = 175
    for i, (k, v) in enumerate(meta):
        cx = mx - (len(meta) - i) * col_w + col_w
        kx = cx - t.text_len(d, k, f_meta_k)
        d.text((kx, badge_y), k, font=f_meta_k, fill=t.FAINT)
        vx = cx - t.text_len(d, v, f_meta_v)
        d.text((vx, badge_y + 18), v, font=f_meta_v, fill=t.TEXT)

    d.line((x0, 218, W - MARGIN, 218), fill=t.LINE, width=1)

    # ---- Vitals strip ----
    vy0, vh = 256, 116
    d.rounded_rectangle((x0, vy0, W - MARGIN, vy0 + vh), radius=12, fill=t.BG1, outline=t.LINE, width=1)
    cells = vitals_data(payload)
    seg_w = INNER / len(cells)
    for i, (label, value, sub, state) in enumerate(cells):
        sx = x0 + i * seg_w
        if i:
            d.line((sx, vy0 + 14, sx, vy0 + vh - 14), fill=t.LINE, width=1)
        px = sx + 26
        t.tracked(d, (px, vy0 + 22), label, f_label, t.FAINT, tracking=2.0)
        tick = sx + 26
        d.rounded_rectangle((tick, vy0 + 52, tick + 8, vy0 + 60), radius=2,
                            fill=t.STATE_COLORS.get(state, t.FAINT))
        d.text((tick + 18, vy0 + 46), value, font=f_vital, fill=t.TEXT)
        d.text((px, vy0 + 84), sub, font=f_vital_sub, fill=t.FAINT)

    # ---- Fleet roster ----
    fy = vy0 + vh + 48
    t.tracked(d, (x0, fy), "FLEET", t.font(15, "Semibold"), t.DIM, tracking=2.4)
    counts = {"ok": 0, "active": 0, "warn": 0}
    for a in agents:
        counts[t.state_for(a.get("status", "ready"))] += 1
    summary = f"{len(agents)} agents · {counts['ok']} ready · {counts['active']} active · {counts['warn']} warning"
    d.text((W - MARGIN - t.text_len(d, summary, f_mono_sm), fy + 2), summary, font=f_mono_sm, fill=t.FAINT)

    # column header
    hy = fy + 34
    cols_x = {
        "state": x0 + 12,
        "agent": x0 + 56,
        "role": x0 + 430,
        "signal": x0 + 700,
        "index": W - MARGIN - 14,
    }
    f_col = t.font(11, "Medium")
    t.tracked(d, (cols_x["state"], hy), "STATE", f_col, t.FAINT, tracking=1.6)
    t.tracked(d, (cols_x["agent"], hy), "AGENT", f_col, t.FAINT, tracking=1.6)
    t.tracked(d, (cols_x["role"], hy), "ROLE", f_col, t.FAINT, tracking=1.6)
    t.tracked(d, (cols_x["signal"], hy), "SIGNAL", f_col, t.FAINT, tracking=1.6)
    d.text((cols_x["index"] - t.text_len(d, "#", f_col), hy), "#", font=f_col, fill=t.FAINT)
    d.line((x0, hy + 22, W - MARGIN, hy + 22), fill=t.LINE, width=1)

    row_h = 70
    ry = hy + 22
    for idx, a in enumerate(agents):
        top = ry + idx * row_h
        mid = top + row_h / 2
        state = t.state_for(a.get("status", "ready"))

        t.status_dot(d, cols_x["state"] + 4, mid, state, r=5)

        tile = (cols_x["agent"], mid - 18, cols_x["agent"] + 36, mid + 18)
        t.monogram(d, tile, (a.get("label", "?")[:1] or "?").upper(), a.get("accent", ""))
        name_x = cols_x["agent"] + 50
        d.text((name_x, mid - 21), a.get("label", a.get("id", "—")), font=f_name, fill=t.TEXT)
        d.text((name_x, mid + 4), a.get("cabinet", ""), font=f_mono_sm, fill=t.FAINT)

        role = a.get("role", "")
        d.text((cols_x["role"], mid - 9), _ellipsize(d, role, f_role, 250), font=f_role, fill=t.DIM)

        signal = a.get("signal", "Standing by.")
        sig_color = {"active": (232, 193, 132), "warn": (243, 153, 143)}.get(state, t.DIM)
        d.text((cols_x["signal"], mid - 9),
               _ellipsize(d, signal, f_signal, W - MARGIN - cols_x["signal"] - 50),
               font=f_signal, fill=sig_color)

        order = str(a.get("order", idx + 1))
        d.text((cols_x["index"] - t.text_len(d, order, f_mono_sm), mid - 9), order, font=f_mono_sm, fill=t.FAINT)

        d.line((x0, top + row_h, W - MARGIN, top + row_h), fill=t.LINE, width=1)

    # ---- Footer ----
    foot_y = ry + len(agents) * row_h + 24
    d.text((x0, foot_y), "Agent Arcade · local-first, read-only", font=f_mono_sm, fill=t.FAINT)
    version = payload.get("hermes", {}).get("version", {})
    vtxt = f"hermes v{version.get('version', '?')}" + (f" · {version.get('build')}" if version.get("build") else "")
    d.text((W - MARGIN - t.text_len(d, vtxt, f_mono_sm), foot_y), vtxt, font=f_mono_sm, fill=t.FAINT)

    img.save(OUT)
    return OUT


def _ellipsize(d, text: str, fnt, max_w: float) -> str:
    if t.text_len(d, text, fnt) <= max_w:
        return text
    while text and t.text_len(d, text + "…", fnt) > max_w:
        text = text[:-1]
    return text + "…"


if __name__ == "__main__":
    print(render())
