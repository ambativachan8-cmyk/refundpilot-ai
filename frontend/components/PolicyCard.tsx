"use client";

import type { PolicyCheck } from "@/lib/types";
import { StatusPill } from "./StatusBadge";

export function PolicyHighlights({ rules }: { rules: string[] }) {
  if (!rules.length) return null;
  return (
    <ul className="space-y-1.5 text-xs text-slate-400">
      {rules.slice(0, 6).map((r, i) => (
        <li key={i} className="flex gap-2">
          <span className="mt-0.5 text-indigo-400">•</span>
          <span>{r}</span>
        </li>
      ))}
    </ul>
  );
}

export function PolicyChecks({ checks }: { checks: PolicyCheck[] }) {
  if (!checks.length) return null;
  return (
    <div className="space-y-1.5">
      {checks.map((c, i) => (
        <div
          key={i}
          className="flex items-start justify-between gap-3 rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2"
        >
          <div>
            <div className="text-xs font-medium text-slate-200">{c.rule}</div>
            <div className="text-[11px] text-slate-500">{c.detail}</div>
          </div>
          <StatusPill status={c.status} />
        </div>
      ))}
    </div>
  );
}
