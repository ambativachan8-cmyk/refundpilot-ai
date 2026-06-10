"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { ChatResponse, Decision, Stage } from "@/lib/types";
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

const STAGE_LABEL: Partial<Record<Stage, string>> = {
  needs_clarification: "Awaiting clarification",
  waiting_for_proof: "Waiting for proof",
  under_manual_review: "Manual review",
  warranty_support: "Warranty support",
};

const STAGE_META: Record<Stage, { label: string; eta: string; next: string }> = {
  new_request: { label: "New request", eta: "—", next: "Describe your request" },
  needs_clarification: { label: "Needs clarification", eta: "—", next: "Clarify item & condition" },
  waiting_for_proof: { label: "Waiting for proof", eta: "—", next: "Attach proof or mark unavailable" },
  proof_received: { label: "Proof received", eta: "24–48 hours", next: "Support team validation" },
  under_manual_review: { label: "Under manual review", eta: "24–48 hours", next: "Support team validation" },
  approved: { label: "Approved", eta: "3–5 business days after inspection", next: "Pickup & inspection" },
  denied: { label: "Denied", eta: "—", next: "Warranty support if defective" },
  escalated: { label: "Escalated", eta: "~24 hours", next: "Human agent review" },
  warranty_support: { label: "Warranty support", eta: "varies", next: "Warranty team validation" },
  store_credit: { label: "Store credit", eta: "—", next: "Issue store credit" },
  already_cancelled: { label: "Already cancelled", eta: "—", next: "No action needed" },
};

export function ChatPanel({
  customerId,
  injected,
  resetNonce,
  onResult,
}: {
  customerId: string;
  injected: InjectedScenario | null;
  resetNonce: number;
  onResult: (r: ChatResponse) => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [tts, setTts] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage | null>(null);
  const [proofState, setProofState] = useState<"attached" | "unavailable" | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  function resetConversation() {
    setMessages([]);
    setSessionId(null);
    setStage(null);
    setProofState(null);
  }

  async function send(
    text: string,
    fresh = false,
    proof?: { proof_attached?: boolean; proof_unavailable?: boolean },
  ) {
    const msg = text.trim();
    if (!msg || loading) return;
    setInput("");
    const useSession = fresh ? null : sessionId;
    if (fresh) {
      setSessionId(null);
      setStage(null);
      setProofState(null);
      setMessages([{ role: "customer", text: msg }]);
    } else {
      setMessages((m) => [...m, { role: "customer", text: msg }]);
    }
    if (proof?.proof_attached) setProofState("attached");
    if (proof?.proof_unavailable) setProofState("unavailable");
    setLoading(true);
    try {
      const r = await api.chat(customerId, msg, useSession, proof);
      setSessionId(r.session_id);
      setStage(r.stage);
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

  // Quick demo scenario from the page → start a fresh conversation.
  useEffect(() => {
    if (injected) send(injected.message, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [injected?.nonce]);

  // Customer change / "New conversation" → clear the thread + session.
  useEffect(() => {
    resetConversation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetNonce]);

  return (
    <div className="card flex h-[calc(100vh-9.5rem)] flex-col">
      {/* header */}
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse-dot" />
          <span className="text-sm font-semibold text-white">Support Chat</span>
          {stage && STAGE_LABEL[stage] && (
            <span className="rounded-full border border-amber-500/30 bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-300">
              {STAGE_LABEL[stage]}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {sessionId && (
            <span className="hidden font-mono text-[10px] text-slate-500 sm:inline">{sessionId}</span>
          )}
          <button
            onClick={resetConversation}
            className="rounded-lg border border-white/10 px-2.5 py-1 text-xs text-slate-400 transition hover:border-indigo-400/50 hover:text-white"
            title="Start a new conversation (new session)"
          >
            New conversation
          </button>
          <button
            onClick={() => setTts((v) => !v)}
            className={`rounded-lg border px-2.5 py-1 text-xs transition ${
              tts
                ? "border-indigo-400/50 bg-indigo-500/15 text-indigo-300"
                : "border-white/10 text-slate-400 hover:text-white"
            }`}
            title="Read agent replies aloud"
          >
            🔊 {tts ? "on" : "off"}
          </button>
        </div>
      </div>

      {/* compact case-status bar */}
      {stage && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-white/10 bg-white/[0.02] px-4 py-2 text-[11px]">
          <span className="text-slate-400">
            Status: <span className="font-medium text-slate-200">{STAGE_META[stage]?.label ?? stage}</span>
          </span>
          <span className="text-slate-400">
            Proof:{" "}
            <span className="font-medium text-slate-200">
              {proofState === "attached"
                ? "Received"
                : proofState === "unavailable"
                ? "Unavailable"
                : stage === "waiting_for_proof"
                ? "Requested"
                : "—"}
            </span>
          </span>
          <span className="text-slate-400">
            Next: <span className="font-medium text-slate-200">{STAGE_META[stage]?.next}</span>
          </span>
          <span className="text-slate-400">
            ETA: <span className="font-medium text-slate-200">{STAGE_META[stage]?.eta}</span>
          </span>
        </div>
      )}

      {/* messages */}
      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="grid h-full place-items-center text-center">
            <div className="max-w-xs text-sm text-slate-500">
              Pick a customer and describe the refund request — or use a quick demo
              scenario. The agent verifies CRM data, policy, and conversation history
              before deciding.
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

      {/* proof workflow (shown when the agent is verifying a defect claim) */}
      {(stage === "waiting_for_proof" || stage === "under_manual_review") && (
        <div className="border-t border-white/10 bg-amber-500/[0.04] px-4 py-3">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <button
              onClick={() =>
                send("I have attached photo/video proof of the issue.", false, {
                  proof_attached: true,
                })
              }
              disabled={loading}
              className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-300 transition hover:bg-emerald-500/20 disabled:opacity-40"
            >
              📎 Attach photo/video proof
            </button>
            <button
              onClick={() =>
                send(
                  "The issue is internal/software-related and cannot be shown clearly in a photo.",
                  false,
                  { proof_unavailable: true },
                )
              }
              disabled={loading}
              className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-xs font-medium text-amber-300 transition hover:bg-amber-500/20 disabled:opacity-40"
            >
              🚫 I can&apos;t show this in a photo
            </button>
            {proofState === "attached" && (
              <span className="rounded-full border border-emerald-500/30 bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-300">
                Proof attached
              </span>
            )}
            {proofState === "unavailable" && (
              <span className="rounded-full border border-amber-500/30 bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-300">
                Proof unavailable — manual review
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-500">
            For this demo, proof attachment is simulated. In production this would
            connect to a secure file-upload service.
          </p>
        </div>
      )}

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
