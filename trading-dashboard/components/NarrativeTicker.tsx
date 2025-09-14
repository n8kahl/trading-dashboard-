"use client";

import { useMemo } from "react";
import { useEventSource } from "@/src/lib/useEventSource";

type Props = { symbol: string };

function timeAgo(ms?: number) {
  if (!ms) return "now";
  const s = Math.max(0, Math.floor((Date.now() - ms) / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60); if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60); return `${h}h ago`;
}

function BandChip({ band }: { band?: string }) {
  const color = band === "favorable" ? "#46d37e" : band === "mixed" ? "#e8b44c" : "#f26666";
  return <span style={{border:`1px solid ${color}`, color, padding:"1px 6px", borderRadius:10, fontSize:12}}>{band || "—"}</span>;
}

export default function NarrativeTicker({ symbol }: Props) {
  const url = useMemo(() => `/api/proxy?path=/coach/stream&symbol=${encodeURIComponent(symbol)}`, [symbol]);
  const { status, messages } = useEventSource(url, [url]);

  return (
    <section className="card" style={{minHeight:120}}>
      <div style={{display:"flex", justifyContent:"space-between", alignItems:"center"}}>
        <div style={{fontWeight:600}}>Trade Narrator — {symbol}</div>
        <div className="small" style={{opacity:.8}}>{status === "open" ? "Live" : status === "connecting" ? "Connecting…" : "Idle"}</div>
      </div>

      <div style={{display:"flex", flexDirection:"column", gap:8, marginTop:8}}>
        {messages.length === 0 ? (
          <div className="small" style={{opacity:.7}}>Waiting for guidance…</div>
        ) : messages.map((m: any, i: number) => {
          const g = (m?.guidance) || {};
          const lev = g?.stops || {};
          const why: string[] = (Array.isArray(g?.why) ? g.why : []).slice(0, 3);
          const horiz = g?.horizon || "intra";
          return (
            <div key={i} className="card" style={{margin:0}}>
              <div style={{display:"flex", justifyContent:"space-between", alignItems:"center", gap:8}}>
                <div className="small" style={{display:"flex", alignItems:"center", gap:8}}>
                  <span style={{fontWeight:700}}>[{horiz.toUpperCase()}]</span>
                  <BandChip band={g?.band} />
                </div>
                <div className="small" style={{opacity:.7}}>{timeAgo(m?.t_ms)}</div>
              </div>
              <div style={{fontWeight:700, marginTop:4}}>{g?.action || "—"}</div>
              {why.length ? (
                <ul className="small" style={{margin:"4px 0 0 16px"}}>
                  {why.map((w, j)=> <li key={j}>{w}</li>)}
                </ul>
              ) : null}
              <div className="small" style={{display:"flex", gap:12, marginTop:6, opacity:.85}}>
                {lev?.sl !== undefined ? <span>SL {lev.sl}</span> : null}
                {lev?.tp1 !== undefined ? <span>TP1 {lev.tp1}</span> : null}
                {lev?.tp2 !== undefined ? <span>TP2 {lev.tp2}</span> : null}
              </div>
              {g?.risk_notes ? <div className="small" style={{textAlign:"right", opacity:.75, marginTop:4}}>{g.risk_notes}</div> : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}

