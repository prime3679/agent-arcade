const test = require("node:test");
const assert = require("node:assert/strict");
const { ageDetails, buildSignals, normalizeProbe, scheduleTimeText, verdictFor } = require("../app/app.js");

const generatedAt = "2026-08-10T12:00:00Z";
const currentPayload = {
  generated_at: generatedAt,
  __source: "snapshot",
  hermes: {
    gateway: { status: "up", reason: "gateway supervision confirmed", checked_at: generatedAt },
    cron: { status: "up", reason: "scheduler activity confirmed", checked_at: generatedAt, active_jobs: 2 },
    cron_list: { count: 2, entries: [] },
  },
  repo: { clean: true, changed_files: 0, checked_at: generatedAt },
};

test("legacy false values normalize to unverified, never down", () => {
  assert.equal(normalizeProbe({ running: false }, "gateway").status, "unverified");
});

test("a stale snapshot is detected after twelve hours", () => {
  assert.equal(ageDetails(generatedAt, new Date("2026-08-11T00:00:01Z")).stale, true);
  assert.equal(ageDetails(generatedAt, new Date("2026-08-10T23:59:59Z")).stale, false);
});

test("stale data degrades every signal to unverified", () => {
  const payload = { ...currentPayload, generated_at: "2020-01-01T00:00:00Z" };
  const signals = buildSignals(payload);
  assert.equal(signals.length, 4);
  assert.ok(signals.every((signal) => signal.status === "unverified"));
  assert.match(verdictFor(payload, signals), /signals are unverified/);
});

test("verified down is reserved for an explicit down status", () => {
  const payload = {
    ...currentPayload,
    generated_at: new Date().toISOString(),
    hermes: { ...currentPayload.hermes, gateway: { status: "down", reason: "gateway explicitly reported unavailable" } },
  };
  const signals = buildSignals(payload);
  assert.equal(signals[0].status, "down");
  assert.equal(verdictFor(payload, signals), "Gateway is down.");
});

test("public workspace detail never renders a branch", () => {
  const payload = { ...currentPayload, visibility: "public", repo: { ...currentPayload.repo, branch: "codex/signal-room" } };
  const workspace = buildSignals(payload).find((signal) => signal.name === "Workspace");
  assert.equal(workspace.detail, "working tree");
});

test("next-calendar-day schedule times are marked tomorrow", () => {
  assert.doesNotMatch(scheduleTimeText("2026-08-10T21:00:00-04:00", "2026-08-10T17:00:00-04:00"), /tomorrow/);
  assert.match(scheduleTimeText("2026-08-11T08:00:00-04:00", "2026-08-10T17:00:00-04:00"), / · tomorrow$/);
});
