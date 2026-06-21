// Agent Arcade — AA-8 Console renderer.
// Reads the generated snapshot (data/latest.json) and paints the hardware
// console: an inset LCD readout, eight mixer channel strips (one per agent),
// and a patch bay of scheduled routines. Falls back to embedded sample data
// under file:// where fetch is blocked. Consumes the raw snapshot shape
// directly, so it stays in lockstep with collect_state.py.

const sampleData = {
  generated_at: "2026-06-21T15:01:44-04:00",
  arcade: { title: "Agent Arcade", location: "local", agent_count: 8 },
  hermes: {
    version: { version: "0.17.0", build: "2026.6.19" },
    gateway: { running: true, pid: 76095 },
    cron: { running: true, active_jobs: 10, next_run: "2026-06-21T18:00:00-04:00" },
    cron_list: {
      count: 10,
      entries: [
        { state: "active", name: "morning-operating-brief", schedule: "0 8 * * 1-5", next_run: "2026-06-22T08:00:00-04:00" },
        { state: "active", name: "weekly-rogue-fiction-draft", schedule: "0 20 * * 0", next_run: "2026-06-21T20:00:00-04:00" },
        { state: "active", name: "rogue-watchdog-health-monitor", schedule: "0 */6 * * *", next_run: "2026-06-21T18:00:00-04:00" },
        { state: "active", name: "Routine 04", schedule: "30 8 * * 5", next_run: "2026-06-26T08:30:00-04:00" },
        { state: "active", name: "Routine 05", schedule: "0 19 * * 0", next_run: "2026-06-21T19:00:00-04:00" },
        { state: "active", name: "rogue-knowledge-curated-sync", schedule: "20 21 * * *", next_run: "2026-06-21T21:20:00-04:00" },
        { state: "active", name: "rogue-pr-babysitter-loop", schedule: "0 8-18 * * 1-5", next_run: "2026-06-22T08:00:00-04:00" },
        { state: "active", name: "rogue-personal-site-loop", schedule: "0 */6 * * *", next_run: "2026-06-21T18:00:00-04:00" },
        { state: "active", name: "rogue-knowledge-hygiene-loop", schedule: "30 21 * * *", next_run: "2026-06-21T21:30:00-04:00" },
        { state: "active", name: "rogue-disk-hygiene-watchdog", schedule: "0 */6 * * *", next_run: "2026-06-21T18:00:00-04:00" },
      ],
    },
  },
  repo: { branch: "main", head: "7ab318b", clean: false, changed_files: 8 },
  agents: [
    { label: "Rogue", role: "Product control plane", cabinet: "command-deck", accent: "ember", order: 1, status: "ready", signal: "All systems stable." },
    { label: "Codex", role: "Primary builder", cabinet: "builder-bay", accent: "laser", order: 2, status: "ready", signal: "All systems stable." },
    { label: "Claude Code", role: "Deep reviewer", cabinet: "review-rail", accent: "mint", order: 3, status: "ready", signal: "All systems stable." },
    { label: "Scout", role: "Repo ranger", cabinet: "branch-radar", accent: "cobalt", order: 4, status: "active", signal: "8 files changed." },
    { label: "Sentinel", role: "Gateway watcher", cabinet: "pulse-tower", accent: "gold", order: 5, status: "ready", signal: "All systems stable." },
    { label: "Ticker", role: "Scheduler monitor", cabinet: "clockwork", accent: "coral", order: 6, status: "ready", signal: "All systems stable." },
    { label: "Patchbay", role: "Local automation", cabinet: "wire-mesh", accent: "ice", order: 7, status: "active", signal: "10 routines detected." },
    { label: "Archivist", role: "Snapshot keeper", cabinet: "memory-vault", accent: "plum", order: 8, status: "active", signal: "Writing snapshots." },
  ],
};

const sampleSummon = {
  generated_at: "2026-06-21T15:41:22-04:00",
  source_snapshot: "2026-06-21T15:40:25-04:00",
  requested: ["gremlin", "archivist", "scout", "bard"],
  cartridge_count: 4,
  cartridges: [
    {
      persona: "gremlin",
      label: "Gremlin",
      slot: "fault-lab",
      accent: "orange",
      stamp: "stress pass",
      headline: "Probe the seams without touching config.",
      body: "Workspace drift is visible: 3 changed, 1 staged, 2 untracked. Gateway is up, with 10 scheduled routines in the bay. Focus on awkward edges and anything that could jam a local-only flow.",
    },
    {
      persona: "archivist",
      label: "Archivist",
      slot: "memory-vault",
      accent: "plum",
      stamp: "snapshot note",
      headline: "Preserve the operator story in clean public-safe notes.",
      body: "Latest snapshot landed this afternoon. Replayable state is active, Hermes is stable, and the scheduler inventory is visible for future diffing.",
    },
    {
      persona: "scout",
      label: "Scout",
      slot: "branch-radar",
      accent: "cobalt",
      stamp: "repo sweep",
      headline: "Sweep for drift, friction, and next repair targets.",
      body: "Scout sees local change pressure and the next scheduler tick already lined up. Map the sharpest risks before they turn into operator confusion.",
    },
    {
      persona: "bard",
      label: "Bard",
      slot: "signal-stage",
      accent: "yellow",
      stamp: "operator brief",
      headline: "Turn the cabinet state into a crisp operator briefing.",
      body: "Agent Arcade is local, the gateway is online, cron is loaded, and the fleet reads a little restless. Keep the copy sharp, warm, and compressed.",
    },
  ],
};

// Bright, primary-leaning identity colours for the channel knobs.
const ACCENTS = {
  ember: "#ff5a1f",
  laser: "#2f6dff",
  mint: "#1faf5a",
  cobalt: "#7c5cff",
  gold: "#ffc21f",
  coral: "#ff8a3f",
  ice: "#1fc6c6",
  plum: "#c54ad6",
};

const esc = (s) =>
  String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// Two visual channel states: steady green (ready) vs. lit amber (everything else).
const stateOf = (status) => (status === "ready" ? "ok" : "busy");
const accentOf = (agent) => ACCENTS[agent.accent] || (agent.accent && agent.accent.startsWith("#") ? agent.accent : "#15140f");
const hhmm = (iso) => (iso && iso.includes("T") ? iso.split("T")[1].slice(0, 5) : "—");

async function loadData() {
  try {
    const [latestResponse, summonResponse] = await Promise.all([
      fetch("../data/latest.json", { cache: "no-store" }),
      fetch("../data/summon.json", { cache: "no-store" }).catch(() => null),
    ]);
    if (!latestResponse.ok) throw new Error(`HTTP ${latestResponse.status}`);
    const payload = await latestResponse.json();
    if (summonResponse && summonResponse.ok) {
      payload.summon = await summonResponse.json();
    }
    payload.__source = "live";
    return payload;
  } catch (error) {
    console.warn("Falling back to embedded sample data.", error);
    return { ...sampleData, summon: sampleSummon, __source: "fallback" };
  }
}

function renderChrome(payload) {
  const live = payload.__source !== "fallback";
  const arcade = payload.arcade || {};

  document.getElementById("arcade-title").textContent = arcade.title || "Agent Arcade";
  document.getElementById("model").textContent = `AA-8 · ${(arcade.location || "local").toUpperCase()}`;

  const badge = document.getElementById("source-badge");
  badge.dataset.live = String(live);
  document.getElementById("source-text").textContent = live ? "Live" : "Sample";

  const stamp = (payload.generated_at || "").slice(0, 16).replace("T", " ");
  document.getElementById("stamp").textContent = live
    ? `live snapshot · ${stamp}`
    : "sample data · file://";
}

function renderLCD(payload) {
  const hermes = payload.hermes || {};
  const repo = payload.repo || {};
  const version = hermes.version || {};
  const cron = hermes.cron || {};
  const jobs = cron.active_jobs ?? hermes.cron_list?.count ?? 0;
  const gatewayUp = !!hermes.gateway?.running;
  const clean = !!repo.clean;

  const segs = [
    ["VER", `v${version.version || "?"}`, false],
    ["GATE", gatewayUp ? "ON" : "OFF", !gatewayUp],
    ["CRON", `${jobs} JOBS`, !cron.running],
    ["GIT", clean ? "CLEAN" : `${repo.changed_files ?? 0}Δ`, !clean],
    ["NEXT", cron.running ? hhmm(cron.next_run) : "—", !cron.running],
  ];

  const scroll = `build ${version.build || "?"} · ${repo.branch || "—"} @ ${repo.head || "—"}`;
  document.getElementById("lcd").innerHTML =
    segs
      .map(([k, v, warn]) => `<div class="seg"><span class="k">${k}</span><span class="v${warn ? " warn" : ""}">${esc(v)}</span></div>`)
      .join("") +
    `<span class="spacer"></span><span class="scroll">${esc(scroll)}</span>`;
}

function renderMixer(payload) {
  const agents = payload.agents || [];
  document.getElementById("mixer-label").textContent = `Fleet · ${agents.length} channels`;

  document.getElementById("mixer").innerHTML = agents
    .map((a, i) => {
      const s = stateOf(a.status);
      const lit = s === "ok" ? 5 : 3;
      const meter = Array.from({ length: 5 }, (_, m) => `<i class="${m < lit ? "on" : ""}"></i>`).join("");
      const capTop = s === "ok" ? 10 : 42; // fader cap position (%)
      const rot = `${-58 + i * 16}deg`; // varied knob angle for visual rhythm
      const num = String(a.order ?? i + 1).padStart(2, "0");
      return `
      <div class="ch" data-s="${s}" style="--ac:${esc(accentOf(a))}">
        <div class="ch-top">
          <span class="ch-num">${esc(num)}</span>
          <span class="knob" style="--rot:${rot}"></span>
        </div>
        <div>
          <div class="ch-name">${esc(a.label || a.id || "—")}</div>
          <div class="ch-role">${esc(a.role || "")}</div>
        </div>
        <div class="ch-bottom">
          <div class="meter">${meter}</div>
          <div class="fader"><div class="track"></div><div class="cap" style="top:${capTop}%"></div></div>
          <div class="ch-meta">
            <span class="ch-state">${esc(a.status || "ready")}</span>
            <span class="ch-cab">${esc(a.cabinet || "")}</span>
          </div>
        </div>
      </div>`;
    })
    .join("");
}

function renderPatch(payload) {
  const entries = payload.hermes?.cron_list?.entries || [];
  document.getElementById("patch").innerHTML = entries
    .map((c) => {
      const on = (c.state || "active") === "active";
      const next = (c.next_run || "").slice(5, 16).replace("T", " ") || "—";
      return `
      <div class="jack">
        <span class="toggle${on ? "" : " off"}" role="img" aria-label="${on ? "enabled" : "disabled"}"></span>
        <span class="jack-name">${esc(c.name)}</span>
        <span class="jack-cron">${esc(c.schedule || "")}</span>
        <span class="jack-next">${esc(next)}</span>
      </div>`;
    })
    .join("");
}

function renderSummon(payload) {
  const summon = payload.summon;
  const label = document.getElementById("summon-label");
  const bay = document.getElementById("summon");
  const cartridges = summon?.cartridges || [];

  if (!cartridges.length) {
    label.classList.add("is-hidden");
    bay.classList.add("is-hidden");
    bay.innerHTML = "";
    return;
  }

  label.classList.remove("is-hidden");
  bay.classList.remove("is-hidden");
  bay.innerHTML = cartridges
    .map((cartridge, index) => {
      const num = String(index + 1).padStart(2, "0");
      return `
      <article class="cart" data-accent="${esc(cartridge.accent || "orange")}">
        <div class="cart-top">
          <span class="cart-num">${esc(num)}</span>
          <span class="cart-stamp">${esc(cartridge.stamp || "manual summon")}</span>
        </div>
        <div class="cart-label">${esc(cartridge.label || cartridge.persona || "Cartridge")}</div>
        <div class="cart-slot">${esc(cartridge.slot || "bay")}</div>
        <div class="cart-head">${esc(cartridge.headline || "")}</div>
        <p class="cart-body">${esc(cartridge.body || "")}</p>
      </article>`;
    })
    .join("");
}

function renderDashboard(payload) {
  renderChrome(payload);
  renderLCD(payload);
  renderMixer(payload);
  renderPatch(payload);
  renderSummon(payload);
}

loadData().then(renderDashboard);
