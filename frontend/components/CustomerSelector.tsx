"use client";

import type { Customer, Order } from "@/lib/types";

export function CustomerSelector({
  customers,
  selectedId,
  onSelect,
}: {
  customers: Customer[];
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-slate-400">
        Customer
      </label>
      <select
        value={selectedId}
        onChange={(e) => onSelect(e.target.value)}
        className="w-full rounded-xl border border-white/10 bg-ink-800 px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-indigo-400/60 focus:ring-2 focus:ring-indigo-500/20"
      >
        {customers.map((c) => (
          <option key={c.customer_id} value={c.customer_id}>
            {c.customer_id} — {c.name}
          </option>
        ))}
      </select>
    </div>
  );
}

const TIER_STYLE: Record<string, string> = {
  premium: "bg-violet-500/15 text-violet-300 border-violet-500/30",
  plus: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30",
  standard: "bg-slate-500/15 text-slate-300 border-slate-500/30",
};

export function CustomerProfile({ customer }: { customer: Customer | null }) {
  if (!customer) return null;
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold text-white">{customer.name}</div>
          <div className="text-xs text-slate-400">{customer.email}</div>
        </div>
        <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium capitalize ${TIER_STYLE[customer.tier] ?? TIER_STYLE.standard}`}>
          {customer.tier}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <Stat label="Refunds (90d)" value={String(customer.refund_count_90d)} />
        <Stat
          label="Risk flag"
          value={customer.risk_flag ? "Flagged" : "Clear"}
          danger={customer.risk_flag}
        />
      </div>
      <p className="rounded-lg bg-white/[0.03] px-3 py-2 text-xs italic text-slate-400">
        {customer.notes}
      </p>
    </div>
  );
}

export function OrderDetails({ order }: { order: Order | null }) {
  if (!order) return null;
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-white">{order.product_name}</div>
        <div className="text-sm font-semibold text-indigo-300">
          ₹{order.price.toLocaleString("en-IN")}
        </div>
      </div>
      <div className="text-[11px] text-slate-500">
        {order.order_id} · {order.category}
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <Stat label="Delivered" value={`${order.delivered_days_ago}d ago`} />
        <Stat label="Status" value={order.status} />
        <Stat label="Condition" value={order.condition_claimed} />
        <Stat label="Country" value={order.country} />
        <Stat label="Final sale" value={order.final_sale ? "Yes" : "No"} danger={order.final_sale} />
        <Stat label="Photo proof" value={order.photo_proof_available ? "Yes" : "No"} />
      </div>
    </div>
  );
}

function Stat({ label, value, danger }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className="rounded-lg bg-white/[0.03] px-2.5 py-1.5">
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`text-xs font-medium capitalize ${danger ? "text-rose-300" : "text-slate-200"}`}>
        {value}
      </div>
    </div>
  );
}
