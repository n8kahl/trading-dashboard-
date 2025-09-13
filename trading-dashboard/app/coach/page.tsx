"use client";

import { useState } from "react";
import { apiPost } from "@/src/lib/api";

type Msg = { role: "user"|"assistant"|"system"|"tool"; content: string; tool_call_id?: string; name?: string };

export default function CoachPage() {
  const [messages, setMessages] = useState<Msg[]>([
    { role: "system", content: "Coach me on intraday opportunities; be concise and risk-aware." },
  ]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);

  const send = async () => {
    const text = input.trim();
    if (!text || pending) return;
    const next = [...messages, { role: "user", content: text } as Msg];
    setMessages(next);
    setInput("");
    setPending(true);
    try {
      const resp = await apiPost("/api/v1/coach/chat", { messages: next });
      const content = (resp?.content ?? "").toString();
      setMessages([...next, { role: "assistant", content }]);
    } catch (e: any) {
      setMessages([...next, { role: "assistant", content: `Error: ${e?.message ?? e}` }]);
    } finally {
      setPending(false);
    }
  };

  return (
    <main className="container">
      <h1 style={{ marginBottom: 12 }}>AI Coach</h1>
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, minHeight: 240 }}>
          {messages.filter(m => m.role !== "system").map((m, i) => (
            <div key={i} className="card" style={{ margin: 0, background: m.role === "user" ? "#1e1e1e" : "#141414" }}>
              <div className="small" style={{ opacity: .7, marginBottom: 4 }}>{m.role}</div>
              <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
            </div>
          ))}
          {pending && <div className="small">Thinking…</div>}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            className="input"
            placeholder="Ask the coach (e.g., Best scalp setups right now?)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") send(); }}
          />
          <button onClick={send} disabled={pending}>Send</button>
        </div>
      </div>
    </main>
  );
}

