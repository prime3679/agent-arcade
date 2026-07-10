// Agent Arcade cabinet renderer.
// Reads the generated snapshot (data/latest.json) and paints a local-only
// fleet instrument. Falls back to embedded sample data under file:// where
// fetch is blocked. Consumes the raw snapshot shape directly, so it stays in
// lockstep with collect_state.py.

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

const esc = (s) =>
  String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const stateOf = (status) => {
  if (status === "ready") return "ok";
  if (status === "warning") return "warn";
  return "busy";
};
const hhmm = (iso) => (iso && iso.includes("T") ? iso.split("T")[1].slice(0, 5) : "—");
const shortDateTime = (iso) => (iso && iso.includes("T") ? iso.slice(5, 16).replace("T", " ") : "—");
const sentence = (text) => (text ? String(text).replace(/\.$/, "") : "");

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
    payload.__source = "snapshot";
    return payload;
  } catch (error) {
    console.warn("Falling back to embedded sample data.", error);
    return { ...sampleData, summon: sampleSummon, __source: "fallback" };
  }
}

function renderChrome(payload) {
  const fromSnapshot = payload.__source !== "fallback";
  const arcade = payload.arcade || {};

  document.getElementById("arcade-title").textContent = arcade.title || "Agent Arcade";
  document.getElementById("subtitle").textContent = arcade.subtitle || "Local-first dashboard for Hermes operators";
  document.getElementById("model").textContent = `AA-8 ${(arcade.location || "local").toLowerCase()} cabinet`;

  const badge = document.getElementById("source-badge");
  badge.dataset.source = fromSnapshot ? "snapshot" : "fallback";

  const stamp = (payload.generated_at || "").slice(0, 16).replace("T", " ");
  document.getElementById("source-label").textContent = fromSnapshot ? "Snapshot" : "Sample";
  document.getElementById("source-text").textContent = stamp || "Generated";
  document.getElementById("stamp").textContent = fromSnapshot
    ? `snapshot generated - ${stamp} - read-only, no sends, no config writes`
    : "sample data - file:// fallback - read-only";
}

function renderReadout(payload) {
  const hermes = payload.hermes || {};
  const repo = payload.repo || {};
  const version = hermes.version || {};
  const cron = hermes.cron || {};
  const jobs = cron.active_jobs ?? hermes.cron_list?.count ?? 0;
  const gatewayUp = !!hermes.gateway?.running;
  const clean = !!repo.clean;

  const facts = [
    ["Hermes", `v${version.version || "?"}`, version.build ? `build ${version.build}` : "build unknown", version.ok === false ? "warn" : "ok"],
    ["Gateway", gatewayUp ? "running" : "offline", hermes.gateway?.pid ? `pid ${hermes.gateway.pid}` : "no pid", gatewayUp ? "ok" : "warn"],
    ["Cron", cron.running ? "running" : "paused", `${jobs} jobs`, cron.running ? "ok" : "warn"],
    ["Repository", clean ? "clean" : `${repo.changed_files ?? 0} changed`, repo.branch ? `${repo.branch} @ ${repo.head || "—"}` : "branch unavailable", clean ? "ok" : "busy"],
    ["Next Run", cron.running ? hhmm(cron.next_run) : "—", shortDateTime(cron.next_run), cron.running ? "ok" : "warn"],
  ];

  document.getElementById("readout").innerHTML = facts
    .map(
      ([label, value, detail, state]) => `
      <div class="readout-fact" data-state="${esc(state)}">
        <span class="fact-label">${esc(label)}</span>
        <strong>${esc(value)}</strong>
        <span class="fact-detail">${esc(detail)}</span>
      </div>`
    )
    .join("");
}

function renderFleet(payload) {
  const agents = payload.agents || [];
  document.getElementById("fleet-count").textContent = `${agents.length} agents`;

  document.getElementById("fleet").innerHTML = agents
    .map((a, i) => {
      const s = stateOf(a.status);
      const num = String(a.order ?? i + 1).padStart(2, "0");
      return `
      <article class="fleet-row" data-state="${s}" data-accent="${esc(a.accent || "none")}">
        <span class="row-index">${esc(num)}</span>
        <div class="agent-main">
          <h3>${esc(a.label || a.id || "—")}</h3>
          <p>${esc(a.role || "")}</p>
        </div>
        <div class="agent-signal">
          <span>${esc(sentence(a.signal) || sentence(a.tagline) || "No signal")}</span>
        </div>
        <div class="agent-meta">
          <span class="state-word">${esc(a.status || "ready")}</span>
          <span>${esc(a.cabinet || "cabinet")}</span>
        </div>
      </article>`;
    })
    .join("");
}

function renderRoutines(payload) {
  const entries = payload.hermes?.cron_list?.entries || [];
  document.getElementById("routine-count").textContent = `${entries.length} routines`;
  document.getElementById("routines").innerHTML = entries
    .map((c) => {
      const on = (c.state || "active") === "active";
      const next = shortDateTime(c.next_run);
      return `
      <div class="routine-row" data-state="${on ? "ok" : "warn"}">
        <span class="routine-state">${esc(c.state || "active")}</span>
        <span class="routine-name">${esc(c.name)}</span>
        <span class="routine-schedule">${esc(c.schedule || "")}</span>
        <span class="routine-next">${esc(next)}</span>
      </div>`;
    })
    .join("");
}

function renderSummon(payload) {
  const summon = payload.summon;
  const panel = document.getElementById("story-panel");
  const count = document.getElementById("story-count");
  const story = document.getElementById("story");
  const cartridges = summon?.cartridges || [];

  if (!cartridges.length) {
    panel.classList.add("is-hidden");
    story.innerHTML = "";
    return;
  }

  panel.classList.remove("is-hidden");
  count.textContent = `${cartridges.length} cartridges`;

  const telegram = summon.telegram
    ? `<p class="story-telegram">${esc(summon.telegram)}</p>`
    : "";
  const source = summon.source_snapshot
    ? `<p class="story-source">Snapshot ${esc(summon.source_snapshot)}</p>`
    : "";

  story.innerHTML =
    `<div class="story-lede">${source}${telegram}</div>` +
    cartridges
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
  renderReadout(payload);
  renderFleet(payload);
  renderRoutines(payload);
  renderSummon(payload);
}

loadData().then(renderDashboard);
