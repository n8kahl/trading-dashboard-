"use client";

import { useMemo } from "react";
import { useEventSource } from "@/src/lib/useEventSource";

type Props = { symbol: string; positionId?: string | null };

export default function PositionCoach({ symbol, positionId }: Props) {
  const url = useMemo(() => `/api/proxy?path=/coach/stream&symbol=${encodeURIComponent(symbol)}${positionId?`&position_id=${encodeURIComponent(positionId)}`:""}`,[symbol, positionId]);
  const { status, messages } = useEventSource(url, [url]);
  const head = messages[0] || {};
  const g = (head?.guidance) || {};
  const next = Array.isArray(g?.if_then) && g.if_then.length ? (g.if_then[0] || {}) : {};
  const unless = g?.risk_notes || g?.unless || "—";

  const disabled = false; // TODO: bound to risk breach from store

  return (
    <section className="card" style={{minHeight:100}}>
      <div style={{display:"flex", justifyContent:"space-between", alignItems:"center"}}>
        <div style={{fontWeight:600}}>Position Coach — {symbol}</div>
        <div className="small" style={{opacity:.8}}>{status === "open" ? "Live" : status === "connecting" ? "Connecting…" : "Idle"}</div>
      </div>
      <div style={{display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(220px,1fr))", gap:12, marginTop:8}}>
        <div className="card" style={{margin:0}}>
          <div style={{fontWeight:700, marginBottom:6}}>NOW</div>
          <div className="small">{g?.action || "—"}</div>
        </div>
        <div className="card" style={{margin:0}}>
          <div style={{fontWeight:700, marginBottom:6}}>NEXT</div>
          <div className="small">{next?.then || next?.action || "—"}</div>
        </div>
        <div className="card" style={{margin:0}}>
          <div style={{fontWeight:700, marginBottom:6}}>UNLESS</div>
          <div className="small">{unless}</div>
        </div>
      </div>
      <div style={{display:"flex", gap:8, marginTop:10, flexWrap:"wrap"}}>
        <button className="secondary" disabled={disabled} onClick={()=>console.log("Trim clicked")}>Trim</button>
        <button className="secondary" disabled={disabled} onClick={()=>console.log("Move Stop to VWAP")}>Move Stop → VWAP</button>
        <button className="secondary" disabled={disabled} onClick={()=>console.log("Close position")}>Close</button>
      </div>
    </section>
  );
}

