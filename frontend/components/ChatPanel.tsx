"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { ChatResponse, Decision } from "@/lib/types";
import { DecisionBadge } from "./StatusBadge";
import { VoiceButton } from "./VoiceButton";

interface Message {
  role: "customer" | "agent";
  text: string;
  decision?: Decision;
}

export interface InjectedScenario {
  message: string;
  nonce: number;
}

export function ChatPanel({
  customerId,
  injected,
  onResult,
}: {
  customerId: string;
  injected: InjectedScenario | null;
  onResult: (r: ChatResponse) => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [tts, setTts] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function send(text: string) {
    const msg = text.trim();
    if (!msg || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "customer", text: msg }]);
    setLoading(true);
    try {
      const r = await api.chat(customerId, msg);
      setMessages((m) => [...m, { role: "agent", text: r.response, decision: r.decision }]);
      onResult(r);
      if (tts && typeof window !== "undefined" && window.speechSynthesis) {
        const u = new SpeechSynthesisUtterance(r.response);
        u.lang = "en-IN";
        window.speechSynthesis.speak(u);
      }
    } catch {
      setMessages((m) => [
        ...m,
        { role: "agent", text: "⚠️ Could not reach the backend. Is it running on :8000?" },
      ]);
    } finally {
      setLoading(false);
    }
  }

  // Auto-send when a quick demo scenario is injected from the page.
  useEffect(() => {
    if (injected) send(injected.message);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [injected?.nonce]);

  return (
    <div className="card flex h-[calc(100vh-9.5rem)] flex-col">
      {/* header */}
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse-dot" />
          <span className="text-sm font-semibold text-white">Support Chat</span>
        </div>
        <button
          onClick={() => setTts((v) => !v)}
          className={`rounded-lg border px-2.5 py-1 text-xs transition ${
            tts
              ? "border-indigo-400/50 bg-indigo-500/15 text-indigo-300"
              : "border-white/10 text-slate-400 hover:text-white"
          }`}
          title="Read agent replies aloud"
        >
          🔊 Voice reply {tts ? "on" : "off"}
        </button>
      </div>

      {/* messages */}
      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="grid h-full place-items-center text-center">
            <div className="max-w-xs text-sm text-slate-500">
              Pick a customer and describe the refund request — or use a quick demo
              scenario. The agent will verify CRM data and policy before deciding.
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <Bubble key={i} m={m} />
        ))}
        {loading && (
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-indigo-400" />
            RefundPilot is verifying policy…
          </div>
        )}
      </div>

      {/* input */}
      <div className="border-t border-white/10 px-4 py-3">
        <div className="flex items-center gap-2">
          <VoiceButton onTranscript={(t) => setInput((p) => (p ? `${p} ${t}` : t))} />
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send(input)}
            placeholder="Describe your refund request…"
            className="flex-1 rounded-xl border border-white/10 bg-ink-800 px-3.5 py-2.5 text-sm text-slate-100 outline-none transition focus:border-indigo-400/60 focus:ring-2 focus:ring-indigo-500/20"
          />
          <button
            onClick={() => send(input)}
            disabled={loading || !input.trim()}
            className="rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition hover:brightness-110 disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

function Bubble({ m }: { m: Message }) {
  const isCustomer = m.role === "customer";
  return (
    <div className={`flex animate-fade-up ${isCustomer ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-3.5 py-2.5 text-sm ${
          isCustomer
            ? "rounded-br-sm bg-indigo-500/90 text-white"
            : "rounded-bl-sm border border-white/10 bg-ink-800 text-slate-200"
        }`}
      >
        {!isCustomer && m.decision && (
          <div className="mb-1.5">
            <DecisionBadge decision={m.decision} />
          </div>
        )}
        <p className="leading-relaxed">{m.text}</p>
      </div>
    </div>
  );
}
