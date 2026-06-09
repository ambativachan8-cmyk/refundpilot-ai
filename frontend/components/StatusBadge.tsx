import type { CheckStatus, Decision } from "@/lib/types";

const DECISION_STYLES: Record<Decision, { label: string; cls: string; dot: string }> = {
  approved: { label: "Approved", cls: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30", dot: "bg-emerald-400" },
  denied: { label: "Denied", cls: "bg-rose-500/15 text-rose-300 border-rose-500/30", dot: "bg-rose-400" },
  escalated: { label: "Escalated", cls: "bg-amber-500/15 text-amber-300 border-amber-500/30", dot: "bg-amber-400" },
  store_credit: { label: "Store Credit", cls: "bg-sky-500/15 text-sky-300 border-sky-500/30", dot: "bg-sky-400" },
  warranty_support: { label: "Warranty Support", cls: "bg-violet-500/15 text-violet-300 border-violet-500/30", dot: "bg-violet-400" },
  already_cancelled: { label: "Already Cancelled", cls: "bg-slate-500/15 text-slate-300 border-slate-500/30", dot: "bg-slate-400" },
};

export function DecisionBadge({ decision }: { decision: Decision }) {
  const s = DECISION_STYLES[decision] ?? DECISION_STYLES.escalated;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${s.cls}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}

const STATUS_STYLES: Record<CheckStatus, string> = {
  success: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  warning: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  failed: "bg-rose-500/15 text-rose-300 border-rose-500/30",
};

export function StatusPill({ status }: { status: CheckStatus }) {
  return (
    <span className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${STATUS_STYLES[status]}`}>
      {status}
    </span>
  );
}
