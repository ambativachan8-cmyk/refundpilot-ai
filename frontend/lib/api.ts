import type {
  ChatResponse,
  Customer,
  LogEntry,
  Order,
  PolicyResponse,
} from "./types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  url: API_URL,

  health: () => getJSON<Record<string, unknown>>("/health"),
  customers: () => getJSON<Customer[]>("/customers"),
  orders: () => getJSON<Order[]>("/orders"),
  policy: () => getJSON<PolicyResponse>("/policy"),
  logs: () => getJSON<LogEntry[]>("/admin/logs"),

  async chat(
    customer_id: string,
    message: string,
    session_id?: string | null,
  ): Promise<ChatResponse> {
    const res = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customer_id, message, session_id: session_id ?? null }),
    });
    if (!res.ok) throw new Error(`chat -> ${res.status}`);
    return res.json() as Promise<ChatResponse>;
  },
};
