const STALE_AFTER_MS = 12 * 60 * 60 * 1000;

const sampleData = {
  generated_at: "2026-08-10T08:32:00-04:00",
  visibility: "sample",
  hermes: {
    gateway: {
      status: "up",
      reason: "gateway supervision confirmed",
      checked_at: "2026-08-10T08:32:00-04:00",
    },
    cron: {
      status: "up",
      reason: "scheduler activity confirmed",
      checked_at: "2026-08-10T08:32:00-04:00",
      active_jobs: 3,
      next_run: "2026-08-10T09:00:00-04:00",
    },
    cron_list: {
      count: 3,
      entries: [
        { name: "Morning systems review", state: "active", schedule: "0 9 * * *", next_run: "2026-08-10T09:00:00-04:00" },
        { name: "Archive handoff", state: "active", schedule: "once", next_run: "2026-08-10T13:30:00-04:00" },
        { name: "Evening status review", state: "active", schedule: "0 18 * * *", next_run: "2026-08-10T18:00:00-04:00" },
      ],
    },
  },
  repo: { clean: true, changed_files: 0, branch: "sample", checked_at: "2026-08-10T08:32:00-04:00" },
  run_history_count: 25,
};

const esc = (value) =>
  String(value ?? "").replace(/[&<>\"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[character]);

const validDate = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
};

const timeText = (value) => {
  const date = validDate(value);
  return date ? new Intl.DateTimeFormat([], { hour: "numeric", minute: "2-digit" }).format(date) : "time unknown";
};

const ageDetails = (generatedAt, now = new Date()) => {
  const generated = validDate(generatedAt);
  if (!generated) return { stale: true, text: "snapshot time is unavailable", hours: null };
  const elapsed = now.getTime() - generated.getTime();
  if (elapsed < -5 * 60 * 1000) return { stale: true, text: "snapshot time is in the future", hours: null };
  const minutes = Math.max(0, Math.floor(elapsed / 60000));
  const hours = elapsed / 3600000;
  if (minutes < 1) return { stale: false, text: "snapshot is less than a minute old", hours };
  if (minutes < 60) return { stale: false, text: `snapshot is ${minutes} minute${minutes === 1 ? "" : "s"} old`, hours };
  const wholeHours = Math.floor(hours);
  return { stale: hours > 12, text: `snapshot is ${wholeHours} hour${wholeHours === 1 ? "" : "s"} old`, hours };
};

const normalizeProbe = (probe = {}, label) => {
  if (["up", "down", "unverified"].includes(probe.status)) {
    return { status: probe.status, reason: probe.reason || `${label} supplied no reason`, checkedAt: probe.checked_at };
  }
  if (probe.running === true) return { status: "up", reason: `${label} reported running in a legacy snapshot`, checkedAt: probe.checked_at };
  if (probe.running === false) return { status: "unverified", reason: `${label} used an ambiguous legacy status`, checkedAt: probe.checked_at };
  return { status: "unverified", reason: `${label} status is missing`, checkedAt: probe.checked_at };
};

async function loadData() {
  try {
    const response = await fetch("../data/latest.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return { ...(await response.json()), __source: "snapshot" };
  } catch (error) {
    console.warn("Snapshot unavailable; showing embedded sample data.", error);
    return { ...sampleData, __source: "fallback" };
  }
}

function buildSignals(payload) {
  const hermes = payload.hermes || {};
  const repo = payload.repo || {};
  const age = ageDetails(payload.generated_at);
  const isFallback = payload.__source === "fallback";
  const forceUnverified = age.stale || isFallback;
  const staleReason = isFallback ? "sample data is not an operational reading" : age.text;
  const gateway = normalizeProbe(hermes.gateway, "gateway");
  const scheduler = normalizeProbe(hermes.cron, "scheduler");
  const jobCount = hermes.cron?.active_jobs ?? hermes.cron_list?.count;
  const changed = Number.isFinite(Number(repo.changed_files)) ? Number(repo.changed_files) : null;

  const signals = [
    {
      name: "Gateway",
      status: gateway.status,
      detail: gateway.reason,
      checkedAt: gateway.checkedAt || payload.generated_at,
    },
    {
      name: "Scheduler",
      status: scheduler.status,
      detail: scheduler.status === "up" && jobCount != null
        ? `${jobCount} routine${jobCount === 1 ? "" : "s"} armed${hermes.cron?.next_run ? `, next at ${timeText(hermes.cron.next_run)}` : ""}`
        : scheduler.reason,
      checkedAt: scheduler.checkedAt || payload.generated_at,
    },
    {
      name: "Workspace",
      status: repo.clean === true ? "up" : repo.clean === false ? "attention" : "unverified",
      stateLabel: repo.clean === true ? "clean" : repo.clean === false && changed != null ? `${changed} changed` : "unverified",
      detail: repo.branch ? `branch ${repo.branch}` : repo.clean == null ? "workspace status is missing" : "working tree",
      checkedAt: repo.checked_at || payload.generated_at,
    },
    {
      name: "Snapshot",
      status: age.stale ? "unverified" : "up",
      stateLabel: age.stale ? "unverified" : "current",
      detail: age.text,
      checkedAt: payload.generated_at,
    },
  ];

  if (forceUnverified) {
    return signals.map((signal) => ({ ...signal, status: "unverified", stateLabel: "unverified", detail: staleReason }));
  }
  return signals;
}

function verdictFor(payload, signals) {
  if (payload.__source === "fallback") return "Sample data only. No operational claims are verified.";
  const down = signals.filter((signal) => signal.status === "down");
  const unverified = signals.filter((signal) => signal.status === "unverified");
  const workspace = signals.find((signal) => signal.name === "Workspace");
  if (down.length) return `${down[0].name} is down${down.length > 1 ? `, with ${down.length - 1} more verified outage${down.length === 2 ? "" : "s"}` : ""}.`;
  if (unverified.length) return `${unverified.length === 1 ? "One signal is" : `${unverified.length} signals are`} unverified — ${unverified[0].detail}.`;
  if (workspace?.status === "attention") return `The workspace has ${workspace.stateLabel}; gateway and scheduler are verified up.`;
  const jobs = payload.hermes?.cron?.active_jobs ?? payload.hermes?.cron_list?.count ?? 0;
  return `Nothing needs you. Gateway up, ${jobs} routine${jobs === 1 ? "" : "s"} armed, workspace clean.`;
}

function renderChrome(payload, signals) {
  const age = ageDetails(payload.generated_at);
  const asOf = validDate(payload.generated_at);
  document.getElementById("as-of").textContent = asOf
    ? `As of ${timeText(payload.generated_at)} · ${age.text}.`
    : "As-of time unavailable · snapshot cannot be verified.";
  document.getElementById("sample-notice").hidden = payload.__source !== "fallback";
  document.getElementById("verdict-copy").textContent = verdictFor(payload, signals);
}

function renderSignals(signals) {
  document.getElementById("signal-list").innerHTML = signals.map((signal) => `
    <article class="signal-row" data-state="${esc(signal.status)}">
      <div class="signal-name-state">
        <h3>${esc(signal.name)}</h3>
        <strong>${esc(signal.stateLabel || signal.status)}</strong>
      </div>
      <p>${esc(signal.detail)}</p>
      <time datetime="${esc(signal.checkedAt || "")}">checked ${esc(timeText(signal.checkedAt))}</time>
    </article>
  `).join("");
}

const isOnce = (entry) => String(entry.schedule || "").toLowerCase().includes("once");

function renderSchedule(payload) {
  const entries = payload.hermes?.cron_list?.entries || [];
  const start = validDate(payload.generated_at);
  const end = start ? new Date(start.getTime() + 24 * 60 * 60 * 1000) : null;
  const upcoming = entries
    .map((entry) => ({ ...entry, parsedNext: validDate(entry.next_run) }))
    .filter((entry) => entry.parsedNext && (!start || entry.parsedNext >= start) && (!end || entry.parsedNext <= end))
    .sort((a, b) => a.parsedNext - b.parsedNext);
  const count = payload.hermes?.cron_list?.count ?? entries.length;
  const isPublic = payload.visibility === "public";
  document.getElementById("schedule-summary").textContent = `${count} configured · next 24 hours`;
  document.getElementById("schedule-list").innerHTML = upcoming.length
    ? upcoming.map((entry) => `
      <li>
        <time datetime="${esc(entry.next_run)}">${esc(timeText(entry.next_run))}</time>
        <span class="schedule-name">${esc(isPublic ? "Scheduled routine" : entry.name || "Unnamed routine")}${isOnce(entry) ? " · once" : ""}</span>
        ${!isPublic && entry.schedule ? `<code>${esc(entry.schedule)}</code>` : ""}
      </li>
    `).join("")
    : `<li class="empty-schedule">No scheduled runs reported in the next 24 hours.</li>`;
}

function renderColophon(payload) {
  const history = Number(payload.run_history_count);
  const historyText = Number.isFinite(history) ? `${history} run${history === 1 ? "" : "s"}` : "unavailable";
  document.getElementById("colophon").textContent = `Generated by read-only probes · no sends, no config writes · history: ${historyText}`;
}

function render(payload) {
  const signals = buildSignals(payload);
  renderChrome(payload, signals);
  renderSignals(signals);
  renderSchedule(payload);
  renderColophon(payload);
}

const SignalRoom = { ageDetails, buildSignals, normalizeProbe, verdictFor };

if (typeof module !== "undefined" && module.exports) module.exports = SignalRoom;
if (typeof document !== "undefined") loadData().then(render);
