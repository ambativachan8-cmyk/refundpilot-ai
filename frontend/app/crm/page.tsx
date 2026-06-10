"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Customer, Order } from "@/lib/types";

export default function CrmPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [q, setQ] = useState("");
  const [error, setError] = useState(false);

  useEffect(() => {
    api.customers().then(setCustomers).catch(() => setError(true));
    api.orders().then(setOrders).catch(() => setError(true));
  }, []);

  // Primary order per customer (first one).
  const primaryOrder = useMemo(() => {
    const m = new Map<string, Order>();
    orders.forEach((o) => {
      if (!m.has(o.customer_id)) m.set(o.customer_id, o);
    });
    return m;
  }, [orders]);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return customers;
    return customers.filter((c) => {
      const o = primaryOrder.get(c.customer_id);
      return (
        c.customer_id.toLowerCase().includes(s) ||
        c.name.toLowerCase().includes(s) ||
        (o?.product_name.toLowerCase().includes(s) ?? false) ||
        (o?.scenario_label?.toLowerCase().includes(s) ?? false)
      );
    });
  }, [customers, primaryOrder, q]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-white">Mock CRM — 15 customer profiles</h1>
          <p className="text-sm text-slate-400">
            Synthetic but realistic data covering the 15 refund-policy scenarios. No real
            or scraped customer data is used.
          </p>
        </div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search customer, product, scenario…"
          className="w-64 rounded-xl border border-white/10 bg-ink-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-indigo-400/60"
        />
      </div>

      {error && (
        <div className="card border-rose-500/30 p-4 text-sm text-rose-300">
          Could not reach the backend at {api.url}. Make sure it is running.
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map((c) => {
          const o = primaryOrder.get(c.customer_id);
          return (
            <div key={c.customer_id} className="card p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-white">{c.name}</div>
                  <div className="font-mono text-[11px] text-slate-500">{c.customer_id}</div>
                </div>
                <span className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] capitalize text-slate-300">
                  {c.tier}
                </span>
              </div>

              {o && (
                <div className="mt-3 rounded-lg bg-white/[0.03] px-3 py-2 text-xs text-slate-300">
                  <div className="font-medium text-slate-200">
                    {o.product_name}{" "}
                    <span className="text-slate-500">· ₹{o.price.toLocaleString("en-IN")}</span>
                  </div>
                  <div className="mt-0.5 text-[11px] text-slate-500">
                    {o.category} · delivered {o.delivered_days_ago}d ago · {o.condition_claimed}
                    {o.final_sale ? " · final sale" : ""}
                    {o.country !== "India" ? ` · ${o.country}` : ""}
                  </div>
                </div>
              )}

              {o?.scenario_label && (
                <div className="mt-3 flex items-center justify-between gap-2">
                  <span className="text-[11px] text-slate-400">{o.scenario_label}</span>
                  <span className="shrink-0 rounded-md border border-indigo-500/30 bg-indigo-500/10 px-1.5 py-0.5 text-[10px] font-medium uppercase text-indigo-300">
                    {o.expected_decision}
                  </span>
                </div>
              )}

              <p className="mt-2 text-[11px] italic text-slate-500">{c.notes}</p>
            </div>
          );
        })}
      </div>

      <p className="text-xs text-slate-500">
        <code className="text-slate-400">expected_decision</code> documents the intended
        outcome for evaluators — the agent never reads it; the policy engine decides
        independently.
      </p>
    </div>
  );
}
