"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { PolicyResponse } from "@/lib/types";

export default function PolicyPage() {
  const [policy, setPolicy] = useState<PolicyResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.policy().then(setPolicy).catch(() => setError(true));
  }, []);

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div>
        <h1 className="text-lg font-semibold text-white">Refund Policy</h1>
        <p className="text-sm text-slate-400">
          The strict policy the agent is grounded in. The deterministic policy engine
          decides every refund from these rules — the LLM never overrides them.
        </p>
      </div>

      {error && (
        <div className="card border-rose-500/30 p-4 text-sm text-rose-300">
          Could not reach the backend at {api.url}. Make sure it is running.
        </div>
      )}

      <div className="card p-5">
        <ol className="space-y-2.5">
          {(policy?.rules ?? []).map((r, i) => (
            <li key={i} className="flex gap-3 text-sm text-slate-300">
              <span className="select-none font-mono text-xs text-indigo-400">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span>{r}</span>
            </li>
          ))}
        </ol>
        {!policy && !error && (
          <p className="text-sm text-slate-500">Loading policy…</p>
        )}
      </div>

      <p className="text-xs text-slate-500">
        Source: <code className="text-slate-400">backend/app/data/refund_policy.md</code>
      </p>
    </div>
  );
}
