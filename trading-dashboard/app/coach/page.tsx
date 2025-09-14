"use client";

import { useState } from "react";
import { apiPost } from "@/src/lib/api";
import ConfidenceCard from "@/components/ConfidenceCard";

type Msg = { role: "user"|"assistant"|"system"|"tool"; content: string; tool_call_id?: string; name?: string };

export default function CoachPage() {
  const [messages, setMessages] = useState<Msg[]>([
    { role: "system", content: "Coach me on intraday opportunities; be concise and risk-aware." },
  ]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [symbol, setSymbol] = useState("SPY");
  const [analysis, setAnalysis] = useState<any|null>(null);

  const analyze = async () => {
    try {
      const res = await apiPost("/api/v1/compose-and-analyze", { symbol, strategy_id: "auto" });
      setAnalysis(res?.analysis || null);
    } catch (e) { setAnalysis(null); }
  };

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
      <section className="card" style={{marginBottom:12}}>
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
          <div style={{fontWeight:600}}>Context</div>
          <div style={{display:'flex', gap:8}}>
            <input className="input" style={{width:120}} value={symbol} onChange={(e)=> setSymbol(e.target.value.toUpperCase())} />
            <button className="secondary" onClick={analyze}>Analyze</button>
          </div>
        </div>
        {analysis ? (
          <div style={{marginTop:8}}>
            <ConfidenceCard
              score={Number(analysis?.score ?? 0)}
              band={String(analysis?.band ?? 'mixed')}
              components={{
                ATR: Number(analysis?.components?.atr_regime ?? 0),
                VWAP: Number(analysis?.components?.vwap_posture ?? analysis?.components?.vwap_support ?? 0),
                EMAs: Number(analysis?.components?.ema_stack ?? 0),
                Flow: Number((analysis?.components?.flow ?? 0) + (analysis?.components?.momentum_hint ?? 0)),
                Liquidity: Number(analysis?.components?.liquidity ?? 0),
                Vol: Number(analysis?.components?.vol_context ?? 0),
              }}
            />
          </div>
        ) : <div className="small" style={{opacity:.7, marginTop:6}}>Analyze a symbol to view confidence and signals.</div>}
      </section>
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
