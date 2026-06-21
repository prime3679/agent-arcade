// Agent Arcade — console renderer.
// Reads the generated snapshot (data/latest.json) and paints the operator
// console. Falls back to embedded sample data under file:// where fetch fails.

const sampleData = {
  generated_at: "2026-06-21T12:00:00-04:00",
  arcade: {
    title: "Agent Arcade",
    subtitle: "Local-first command console for the Hermes agent fleet.",
    location: "local",
    agent_count: 8,
  },
  hermes: {
    version: { ok: true, version: "0.17.0", build: "2026.6.19" },
    gateway: { ok: true, running: true, pid: 76095 },
    cron: { ok: true, running: true, next_run: "2026-06-21T18:00:00-04:00" },
    cron_list: { count: 10 },
  },
  repo: { branch: "main", clean: false, changed_files: 6, untracked_files: 6 },
  agents: [
    { id: "rogue", label: "Rogue", role: "Product control plane", cabinet: "command-deck", accent: "ember", order: 1, status: "ready", signal: "All systems stable." },
    { id: "codex", label: "Codex", role: "Primary builder", cabinet: "builder-bay", accent: "laser", order: 2, status: "ready", signal: "Standing by for build." },
    { id: "claude-code", label: "Claude Code", role: "Deep reviewer", cabinet: "review-rail", accent: "mint", order: 3, status: "ready", signal: "No review queued." },
    { id: "scout", label: "Scout", role: "Repo ranger", cabinet: "branch-radar", accent: "cobalt", order: 4, status: "active", signal: "6 files changed in this repo." },
    { id: "sentinel", label: "Sentinel", role: "Gateway watcher", cabinet: "pulse-tower", accent: "gold", order: 5, status: "ready", signal: "Gateway responsive." },
    { id: "ticker", label: "Ticker", role: "Scheduler monitor", cabinet: "clockwork", accent: "coral", order: 6, status: "ready", signal: "Next run 18:00." },
    { id: "patchbay", label: "Patchbay", role: "Local automation", cabinet: "wire-mesh", accent: "ice", order: 7, status: "active", signal: "10 cron definitions tracked." },
    { id: "archivist", label: "Archivist", role: "Snapshot keeper", cabinet: "memory-vault", accent: "plum", order: 8, status: "active", signal: "Writing snapshots to data/runs/." },
  ],
};

// Muted, low-chroma identity tints — applied only to the small monogram tiles.
const ACCENTS = {
  ember: "#b5765a",
  laser: "#5f8fb0",
  mint: "#6fa886",
  cobalt: "#6b80b8",
  gold: "#b39152",
  coral: "#bd7a6a",
  ice: "#7f93a6",
  plum: "#9b7faf",
};

// Roster status -> semantic console state.
const STATE = { ready: "ok", active: "active", warning: "warn" };

async function loadData() {
  try {
    const response = await fetch("../data/latest.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    payload.__source = "live";
    return payload;
  } catch (error) {
    console.warn("Falling back to embedded sample data.", error);
    return { ...sampleData, __source: "fallback" };
  }
}

function renderDashboard(payload) {
  const live = payload.__source === "live";

  document.getElementById("arcade-title").textContent = payload.arcade.title;
  document.getElementById("arcade-subtitle").textContent = payload.arcade.subtitle;

  const badge = document.getElementById("source-badge");
  badge.dataset.live = String(live);
  document.getElementById("source-text").textContent = live
    ? "Live snapshot"
    : "Sample data · file://";

  document.getElementById("generated-at").textContent = formatDate(payload.generated_at);
  document.getElementById("location").textContent = payload.arcade.location || "local";
  document.getElementById("branch").textContent = payload.repo?.branch || "—";

  renderVitals(payload);
  renderFleet(payload.agents || []);

  const version = payload.hermes?.version?.version;
  const build = payload.hermes?.version?.build;
  document.getElementById("foot-version").textContent = version
    ? `hermes v${version}${build ? ` · ${build}` : ""}`
    : "hermes · unknown";
}

function renderVitals(payload) {
  const hermes = payload.hermes || {};
  const repo = payload.repo || {};
  const gatewayUp = !!hermes.gateway?.running;
  const cronUp = !!hermes.cron?.running;
  const cronCount = hermes.cron_list?.count ?? 0;
  const clean = !!repo.clean;

  setVital("vital-hermes", {
    value: hermes.version?.version || "unknown",
    sub: hermes.version?.build ? `build ${hermes.version.build}` : "version unknown",
    state: hermes.version?.version ? "ok" : "warn",
  });

  setVital("vital-gateway", {
    value: gatewayUp ? "Online" : "Offline",
    sub: hermes.gateway?.pid ? `pid ${hermes.gateway.pid}` : gatewayUp ? "healthy" : "no process",
    state: gatewayUp ? "ok" : "warn",
  });

  setVital("vital-cron", {
    value: `${cronCount} ${cronCount === 1 ? "job" : "jobs"}`,
    sub: cronUp
      ? hermes.cron?.next_run
        ? `next ${formatTime(hermes.cron.next_run)}`
        : "running"
      : "stopped",
    state: cronUp ? "ok" : "warn",
  });

  setVital("vital-git", {
    value: clean ? "Clean" : `${repo.changed_files ?? 0} changed`,
    sub: repo.branch ? `branch ${repo.branch}` : "—",
    state: clean ? "ok" : "active",
  });
}

function setVital(id, { value, sub, state }) {
  const el = document.getElementById(id);
  if (!el) return;
  el.dataset.state = state;
  el.querySelector(".vital-num").textContent = value;
  el.querySelector(".vital-sub").textContent = sub;
}

function renderFleet(agents) {
  const list = document.getElementById("fleet");
  const template = document.getElementById("agent-row");
  list.replaceChildren();

  const counts = { ok: 0, active: 0, warn: 0 };

  agents.forEach((agent, index) => {
    const state = STATE[agent.status] || "ok";
    counts[state] += 1;

    const fragment = template.content.cloneNode(true);
    const row = fragment.querySelector(".unit");
    row.dataset.state = state;

    const mono = fragment.querySelector(".unit-mono");
    mono.textContent = (agent.label || "?").trim().charAt(0).toUpperCase();
    if (ACCENTS[agent.accent]) mono.style.setProperty("--accent", ACCENTS[agent.accent]);

    fragment.querySelector(".unit-name").textContent = agent.label || agent.id || "Unknown";
    fragment.querySelector(".unit-cabinet").textContent = agent.cabinet || agent.id || "";
    fragment.querySelector(".unit-role").textContent = agent.role || "";
    fragment.querySelector(".unit-signal").textContent = agent.signal || "Standing by.";
    fragment.querySelector(".unit-status").textContent = agent.status || "ready";
    fragment.querySelector(".unit-index").textContent = String(agent.order ?? index + 1);

    row.style.transitionDelay = `${Math.min(index * 45, 400)}ms`;
    list.appendChild(fragment);
  });

  const summary = [
    `${counts.ok} ready`,
    `${counts.active} active`,
    counts.warn ? `${counts.warn} warning` : null,
  ].filter(Boolean);
  document.getElementById("roster-summary").textContent =
    `${agents.length} agents · ${summary.join(" · ")}`;

  // One orchestrated reveal — stagger the rows on the next frame.
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      list.querySelectorAll(".unit").forEach((row) => row.classList.add("is-in"));
    });
  });
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || "—";
  return date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function formatTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

loadData().then(renderDashboard);
