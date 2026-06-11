"use client";

import { useEffect, useRef, useState } from "react";

// Minimal typing for the Web Speech API (not in standard lib DOM types).
type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((e: { results: { [i: number]: { [j: number]: { transcript: string } } }; resultIndex: number }) => void) | null;
  onend: (() => void) | null;
  onerror: ((e: { error?: string }) => void) | null;
  start: () => void;
  stop: () => void;
  abort?: () => void;
};

const LISTENING_MSG = "Listening… speak now.";
const ERROR_MESSAGES: Record<string, string> = {
  "not-allowed": "Microphone permission was denied — allow mic access and try again.",
  "service-not-allowed": "Microphone permission was denied — allow mic access and try again.",
  "no-speech": "Didn't catch that — click the mic and try again.",
  "audio-capture": "No microphone found — check your audio device.",
  network: "Speech service unreachable — check your connection.",
  aborted: "",
};

export function VoiceButton({
  onTranscript,
  onStatus,
}: {
  onTranscript: (text: string) => void;
  /** Small inline status line (listening / unsupported / mic errors). */
  onStatus?: (msg: string) => void;
}) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const recRef = useRef<SpeechRecognitionLike | null>(null);
  // Latest callbacks + last status, so the recognizer is created exactly once.
  const cbRef = useRef({ onTranscript, onStatus });
  cbRef.current = { onTranscript, onStatus };
  const lastStatusRef = useRef("");

  const setStatus = (msg: string) => {
    lastStatusRef.current = msg;
    cbRef.current.onStatus?.(msg);
  };

  useEffect(() => {
    const w = window as unknown as {
      SpeechRecognition?: new () => SpeechRecognitionLike;
      webkitSpeechRecognition?: new () => SpeechRecognitionLike;
    };
    const Ctor = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!Ctor) {
      setStatus("Voice input is not supported in this browser — please type your message.");
      return;
    }
    setSupported(true);
    const rec = new Ctor();
    rec.lang = "en-IN";
    rec.interimResults = false;
    rec.continuous = false;
    rec.onresult = (e) => {
      const text = e.results[e.resultIndex][0].transcript;
      cbRef.current.onTranscript(text);
      setStatus("Transcript added — edit it if needed, then press Send.");
    };
    rec.onend = () => {
      setListening(false);
      // Clear a stale "Listening…" hint, but never wipe an error message.
      if (lastStatusRef.current === LISTENING_MSG) setStatus("");
    };
    rec.onerror = (e) => {
      setListening(false);
      const msg = ERROR_MESSAGES[e?.error ?? ""] ?? "Voice input failed — please type your message.";
      if (msg) setStatus(msg);
    };
    recRef.current = rec;
    return () => {
      try {
        rec.abort?.();
      } catch {
        /* noop */
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!supported) {
    return (
      <button
        type="button"
        disabled
        title="Voice input isn't supported in this browser. Try Chrome or Edge."
        className="grid h-10 w-10 place-items-center rounded-xl border border-white/10 bg-ink-800 text-slate-600"
      >
        <MicIcon />
      </button>
    );
  }

  const toggle = () => {
    const rec = recRef.current;
    if (!rec) return;
    if (listening) {
      rec.stop();
      setListening(false);
      setStatus("");
    } else {
      try {
        rec.start();
        setListening(true);
        setStatus(LISTENING_MSG);
      } catch {
        setListening(false);
        setStatus("Couldn't start the microphone — try again.");
      }
    }
  };

  return (
    <button
      type="button"
      onClick={toggle}
      title={listening ? "Stop listening" : "Speak your message"}
      className={`grid h-10 w-10 place-items-center rounded-xl border transition ${
        listening
          ? "border-rose-500/40 bg-rose-500/15 text-rose-300 animate-pulse-dot"
          : "border-white/10 bg-ink-800 text-slate-300 hover:border-indigo-400/50 hover:text-white"
      }`}
    >
      <MicIcon />
    </button>
  );
}

function MicIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}
