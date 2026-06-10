"use client";

import { useEffect, useState } from "react";
import { ChatPanel, type InjectedScenario } from "@/components/ChatPanel";
import {
  CustomerSelector,
  CustomerProfile,
  OrderDetails,
} from "@/components/CustomerSelector";
import { api } from "@/lib/api";
import type { ChatResponse, Customer, Order } from "@/lib/types";

interface DemoScenario {
  label: string;
  customerId: string;
  message: string;
}

// Evaluation shortcuts only — hidden in a collapsed section, not customer-facing.
const DEMOS: DemoScenario[] = [
  {
    label: "Clean approval",
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
    message: "My ceramic dinner set arrived broken. I've attached photos of the damage.",
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
  const [selectedId, setSelectedId] = useState("CUST-001");
  const [activeCustomer, setActiveCustomer] = useState<Customer | null>(null);
  const [activeOrder, setActiveOrder] = useState<Order | null>(null);
  const [injected, setInjected] = useState<InjectedScenario | null>(null);
  const [resetNonce, setResetNonce] = useState(0);

  useEffect(() => {
    api.customers().then(setCustomers).catch(() => {});
    api.orders().then(setAllOrders).catch(() => {});
  }, []);

  useEffect(() => {
    setActiveCustomer(customers.find((x) => x.customer_id === selectedId) ?? null);
    setActiveOrder(allOrders.find((x) => x.customer_id === selectedId) ?? null);
  }, [selectedId, customers, allOrders]);

  function handleResult(r: ChatResponse) {
    if (r.customer) setActiveCustomer(r.customer);
    if (r.order) setActiveOrder(r.order);
  }

  function selectCustomer(id: string) {
    setSelectedId(id);
    setResetNonce((n) => n + 1);
  }

  function runDemo(d: DemoScenario) {
    setSelectedId(d.customerId);
    setInjected({ message: d.message, nonce: Date.now() });
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
      {/* LEFT: customer + order context */}
      <aside className="space-y-4">
        <div className="card p-4">
          <CustomerSelector
            customers={customers}
            selectedId={selectedId}
            onSelect={selectCustomer}
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

        {/* Evaluation-only shortcuts, collapsed by default (not customer-facing). */}
        <details className="card p-4 text-slate-300 [&_summary]:cursor-pointer">
          <summary className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Demo scenarios <span className="text-slate-600">(for evaluation)</span>
          </summary>
          <p className="mt-2 text-[11px] text-slate-500">
            One-click scenarios for the walkthrough. Real customers just type in the chat.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
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
        </details>
      </aside>

      {/* CENTER: wide chat */}
      <section>
        <ChatPanel
          customerId={selectedId}
          injected={injected}
          resetNonce={resetNonce}
          onResult={handleResult}
        />
      </section>
    </div>
  );
}
