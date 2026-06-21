const sampleData = {
  generated_at: "2026-06-21T12:00:00-04:00",
  arcade: {
    title: "Agent Arcade",
    subtitle: "Fallback cabinet data for file:// preview mode.",
    location: "local",
    agent_count: 8,
  },
  hermes: {
    version: { version: "0.17.0" },
    gateway: { running: true },
    cron: { running: true },
    cron_list: { count: 8 },
  },
  repo: {
    clean: false,
    changed_files: 4,
  },
  agents: [
    {
      id: "rogue",
      label: "Rogue",
      role: "Product control plane",
      tagline: "Keeps the cabinet lineup coordinated and safe.",
      cabinet: "command-deck",
      accent: "ember",
      status: "ready",
      signal: "Fallback mode is active.",
    },
    {
      id: "codex",
      label: "Codex",
      role: "Primary builder",
      tagline: "Ships features, fixes, and pragmatic implementation details.",
      cabinet: "builder-bay",
      accent: "laser",
      status: "active",
      signal: "Previewing sample data.",
    },
    {
      id: "claude-code",
      label: "Claude Code",
      role: "Deep reviewer",
      tagline: "Audits risky changes and pressure-tests tricky logic.",
      cabinet: "review-rail",
      accent: "mint",
      status: "ready",
      signal: "Static preview is healthy.",
    },
    {
      id: "scout",
      label: "Scout",
      role: "Repo ranger",
      tagline: "Tracks git drift, branch shape, and workspace hygiene.",
      cabinet: "branch-radar",
      accent: "cobalt",
      status: "active",
      signal: "Sample repo drift detected.",
    },
    {
      id: "sentinel",
      label: "Sentinel",
      role: "Gateway watcher",
      tagline: "Watches the messaging gateway heartbeat and service health.",
      cabinet: "pulse-tower",
      accent: "gold",
      status: "ready",
      signal: "Gateway looks responsive.",
    },
    {
      id: "ticker",
      label: "Ticker",
      role: "Scheduler monitor",
      tagline: "Keeps an eye on cron activity, next runs, and load.",
      cabinet: "clockwork",
      accent: "coral",
      status: "ready",
      signal: "Eight preview jobs queued.",
    },
    {
      id: "patchbay",
      label: "Patchbay",
      role: "Local automation",
      tagline: "Runs small maintenance loops without touching config.",
      cabinet: "wire-mesh",
      accent: "ice",
      status: "active",
      signal: "No external services involved.",
    },
    {
      id: "archivist",
      label: "Archivist",
      role: "Snapshot keeper",
      tagline: "Preserves each state capture as a replayable run artifact.",
      cabinet: "memory-vault",
      accent: "plum",
      status: "active",
      signal: "Using embedded fallback replay.",
    },
  ],
};

async function loadData() {
  try {
    const response = await fetch("../data/latest.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    payload.__source = "live";
    return payload;
  } catch (error) {
    console.warn("Falling back to embedded sample data.", error);
    return { ...sampleData, __source: "fallback" };
  }
}

function renderDashboard(payload) {
  document.getElementById("arcade-title").textContent = payload.arcade.title;
  document.getElementById("arcade-subtitle").textContent = payload.arcade.subtitle;
  document.getElementById("score-hermes").textContent = payload.hermes.version.version || "unknown";
  document.getElementById("score-gateway").textContent = payload.hermes.gateway.running ? "Online" : "Offline";
  document.getElementById("score-cron").textContent = String(payload.hermes.cron_list.count ?? 0);
  document.getElementById("score-git").textContent = payload.repo.clean
    ? "Clean"
    : `${payload.repo.changed_files} changed`;

  document.getElementById("data-source").textContent =
    payload.__source === "live"
      ? "Live snapshot loaded from ../data/latest.json"
      : "Embedded sample data loaded because fetch is unavailable in file:// mode";
  document.getElementById("generated-at").textContent = `Snapshot: ${formatDate(payload.generated_at)}`;

  const grid = document.getElementById("agent-grid");
  const template = document.getElementById("agent-template");
  grid.replaceChildren();

  payload.agents.forEach((agent) => {
    const fragment = template.content.cloneNode(true);
    const card = fragment.querySelector(".cabinet");
    card.dataset.accent = agent.accent || "ember";
    fragment.querySelector(".cabinet-role").textContent = agent.role;
    fragment.querySelector(".cabinet-label").textContent = agent.label;
    fragment.querySelector(".cabinet-tagline").textContent = agent.tagline;
    fragment.querySelector(".cabinet-name").textContent = agent.cabinet;
    fragment.querySelector(".cabinet-signal").textContent = agent.signal || "Standing by.";

    const status = fragment.querySelector(".cabinet-status");
    status.textContent = agent.status;
    status.classList.add(`status-${agent.status}`);

    grid.appendChild(fragment);
  });
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

loadData().then(renderDashboard);
