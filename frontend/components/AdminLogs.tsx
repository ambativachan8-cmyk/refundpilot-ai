"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Decision, LogEntry } from "@/lib/types";
import { DecisionBadge, StatusPill } from "./StatusBadge";

export function AdminLogs() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [session, setSession] = useState<string>("all");
  const [auto, setAuto] = useState(true);
  const [error, setError] = useState(false);

  async function load() {
    try {
      setLogs(await api.logs());
      setError(false);
    } catch {
      setError(true);
    }
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!auto) return;
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [auto]);

  const sessions = useMemo(() => {
    const s = new Set<string>();
    logs.forEach((l) => s.add(l.session_id));
    return Array.from(s);
  }, [logs]);

  const filtered = useMemo(
    () => (session === "all" ? logs : logs.filter((l) => l.session_id === session)),
    [logs, session]
  );

  const latestDecision = useMemo(() => {
    const d = filtered.find((l) => l.decision_snapshot);
    return d?.decision_snapshot as Decision | undefined;
  }, [filtered]);

  // group into sessions for the timeline, newest first
  const grouped = useMemo(() => {
    const map = new Map<string, LogEntry[]>();
    filtered.forEach((l) => {
      const arr = map.get(l.session_id) ?? [];
      arr.push(l);
      map.set(l.session_id, arr);
    });
    // entries arrive newest-first; reverse within session for chronological steps
    return Array.from(map.entries()).map(([sid, items]) => ({
      sid,
      items: [...items].reverse(),
    }));
  }, [filtered]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-white">Agent Reasoning Logs</h1>
          <p className="text-xs text-slate-400">
            Live tool-call and policy-check trace · {filtered.length} entries
            {latestDecision && (
              <>
                {" "}· latest decision <DecisionBadgeInline d={latestDecision} />
              </>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={session}
            onChange={(e) => setSession(e.target.value)}
            className="rounded-xl border border-white/10 bg-ink-800 px-3 py-2 text-xs text-slate-200 outline-none focus:border-indigo-400/60"
          >
            <option value="all">All sessions</option>
            {sessions.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <button
            onClick={() => setAuto((v) => !v)}
            className={`rounded-xl border px-3 py-2 text-xs transition ${
              auto
                ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
                : "border-white/10 text-slate-400 hover:text-white"
            }`}
          >
            {auto ? "● Live (3s)" : "Paused"}
          </button>
          <button
            onClick={load}
            className="rounded-xl border border-white/10 bg-ink-800 px-3 py-2 text-xs text-slate-200 transition hover:border-indigo-400/50 hover:text-white"
          >
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="card border-rose-500/30 p-4 text-sm text-rose-300">
          Could not reach the backend at {api.url}. Make sure it is running.
        </div>
      )}

      {grouped.length === 0 && !error && (
        <div className="card p-8 text-center text-sm text-slate-500">
          No logs yet. Run a refund request from the{" "}
          <a href="/" className="text-indigo-400 hover:underline">
            customer chat
          </a>{" "}
          to populate the trace.
        </div>
      )}

      <div className="space-y-4">
        {grouped.map(({ sid, items }) => {
          const decision = [...items].reverse().find((i) => i.decision_snapshot)
            ?.decision_snapshot as Decision | undefined;
          return (
            <div key={sid} className="card overflow-hidden">
              <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.02] px-4 py-2.5">
                <span className="font-mono text-xs text-slate-400">{sid}</span>
                {decision && <DecisionBadge decision={decision} />}
              </div>
              <div className="divide-y divide-white/5">
                {items.map((l) => (
                  <LogRow key={l.id} log={l} />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function LogRow({ log }: { log: LogEntry }) {
  return (
    <div className="flex items-start gap-3 px-4 py-2.5 text-xs">
      <span className="mt-0.5 w-14 shrink-0 font-mono text-[10px] text-slate-600">
        {log.timestamp.slice(11, 19)}
      </span>
      <div className="w-40 shrink-0">
        <div className="font-medium text-slate-200">{log.step}</div>
        <div className="font-mono text-[10px] text-indigo-400/80">{log.tool_name}</div>
      </div>
      <div className="flex-1">
        <div className="text-slate-300">{log.output_summary}</div>
        <div className="text-[11px] text-slate-500">in: {log.input_summary}</div>
      </div>
      <StatusPill status={log.status} />
    </div>
  );
}

function DecisionBadgeInline({ d }: { d: Decision }) {
  return (
    <span className="inline-block align-middle">
      <DecisionBadge decision={d} />
    </span>
  );
}
