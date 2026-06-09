"use client";

import { useEffect, useState } from "react";
import { ChatPanel, type InjectedScenario } from "@/components/ChatPanel";
import {
  CustomerSelector,
  CustomerProfile,
  OrderDetails,
} from "@/components/CustomerSelector";
import { PolicyHighlights, PolicyChecks } from "@/components/PolicyCard";
import { api } from "@/lib/api";
import type {
  ChatResponse,
  Customer,
  Order,
  PolicyCheck,
} from "@/lib/types";

interface DemoScenario {
  label: string;
  customerId: string;
  message: string;
}

const DEMOS: DemoScenario[] = [
  {
    label: "Eligible refund",
    customerId: "CUST-001",
    message:
      "Hi, I want to return my headphones. They were delivered 5 days ago and I haven't used them.",
  },
  {
    label: "Policy violation",
    customerId: "CUST-002",
    message:
      "I bought a smartwatch 45 days ago. I used it for a month but now I want a full refund.",
  },
  {
    label: "Damaged item",
    customerId: "CUST-005",
    message:
      "My ceramic dinner set arrived broken. I've uploaded photos showing the damage.",
  },
  {
    label: "High-value escalation",
    customerId: "CUST-008",
    message: "I'd like to return the laptop I ordered. It's unused.",
  },
];

export default function Home() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [allOrders, setAllOrders] = useState<Order[]>([]);
  const [rules, setRules] = useState<string[]>([]);
  const [selectedId, setSelectedId] = useState("CUST-001");
  const [activeCustomer, setActiveCustomer] = useState<Customer | null>(null);
  const [activeOrder, setActiveOrder] = useState<Order | null>(null);
  const [checks, setChecks] = useState<PolicyCheck[]>([]);
  const [injected, setInjected] = useState<InjectedScenario | null>(null);

  useEffect(() => {
    api.customers().then(setCustomers).catch(() => {});
    api.orders().then(setAllOrders).catch(() => {});
    api.policy().then((p) => setRules(p.rules)).catch(() => {});
  }, []);

  // When customer changes (manually), preview their first order in the side panel.
  useEffect(() => {
    const c = customers.find((x) => x.customer_id === selectedId) ?? null;
    setActiveCustomer(c);
    const o = allOrders.find((x) => x.customer_id === selectedId) ?? null;
    setActiveOrder(o);
  }, [selectedId, customers, allOrders]);

  function handleResult(r: ChatResponse) {
    if (r.customer) setActiveCustomer(r.customer);
    if (r.order) setActiveOrder(r.order);
    setChecks(r.policy_checks);
  }

  function runDemo(d: DemoScenario) {
    setSelectedId(d.customerId);
    setInjected({ message: d.message, nonce: Date.now() });
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[300px_1fr_330px]">
      {/* LEFT: customer + order */}
      <aside className="space-y-4">
        <div className="card p-4">
          <CustomerSelector
            customers={customers}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
          <div className="mt-4">
            <CustomerProfile customer={activeCustomer} />
          </div>
        </div>
        <div className="card p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Order
          </h3>
          <OrderDetails order={activeOrder} />
        </div>
      </aside>

      {/* CENTER: demos + chat */}
      <section className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {DEMOS.map((d) => (
            <button
              key={d.label}
              onClick={() => runDemo(d)}
              className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-indigo-400/50 hover:text-white"
            >
              {d.label}
            </button>
          ))}
        </div>
        <ChatPanel
          customerId={selectedId}
          injected={injected}
          onResult={handleResult}
        />
      </section>

      {/* RIGHT: policy */}
      <aside className="space-y-4">
        <div className="card p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Policy Highlights
          </h3>
          <PolicyHighlights rules={rules} />
        </div>
        <div className="card p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Live Policy Checks
          </h3>
          {checks.length ? (
            <PolicyChecks checks={checks} />
          ) : (
            <p className="text-xs text-slate-500">
              Checks from the most recent decision will appear here.
            </p>
          )}
        </div>
      </aside>
    </div>
  );
}
