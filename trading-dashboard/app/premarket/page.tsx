"use client";

import { useEffect, useState } from "react";
import { apiPost } from "@/src/lib/api";

type PlanCard = { horizon: string; why?: string[]; triggers?: string[] };
type Primer = { symbols: string[]; items: Record<string, PlanCard[]> };

async function fetchPrimer(): Promise<Primer> {
  try {
    const res = await fetch(`/api/proxy?path=${encodeURIComponent("/playbook/primer")}`, { cache: "no-store" });
    if (!res.ok) throw new Error("primer missing");
    return await res.json();
  } catch {
    // stub fallback
    return {
      symbols: ["SPY", "QQQ", "AAPL"],
      items: {
        SPY: [
          { horizon: "scalp", why: ["VWAP support", "ATR regime healthy"], triggers: ["break above ORH"] },
          { horizon: "intraday", why: ["EMA 9/20 up"], triggers: ["pullback to EMA20"] },
          { horizon: "swing", why: ["Range expansion"], triggers: ["close > PDH"] },
        ],
      },
    };
  }
}

export default function Page() {
  const [data, setData] = useState<Primer | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => { fetchPrimer().then(setData).catch(e=>setError(String(e))); }, []);

  const handleSize = async (symbol: string) => {
    try { await apiPost("/sizing/suggest", { symbol, side: "long", risk_R: 1, per_unit_risk: 1 }); alert("Sized (stub)"); } catch(e:any){ alert(e?.message ?? e); }
  };
  const handleAlert = async (symbol: string) => {
    try { await apiPost("/alerts/set", { symbol, timeframe:"day", condition:{type:"price_above", value: 1} }); alert("Alert created (stub)"); } catch(e:any){ alert(e?.message ?? e); }
  };

  return (
    <main className="container">
      <h1 style={{marginBottom:12}}>Premarket Playbook</h1>
      {error ? <div style={{color:'#ffb4b4'}}>Error: {error}</div> : null}
      {!data ? <div>Loading…</div> : (
        <div style={{display:"flex", flexDirection:"column", gap:12}}>
          {data.symbols.map(sym => (
            <section key={sym} className="card">
              <div style={{fontWeight:700, marginBottom:6}}>{sym}</div>
              <div style={{display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(240px,1fr))", gap:12}}>
                {(data.items[sym] || []).map((pc, i) => (
                  <div key={i} className="card" style={{margin:0}}>
                    <div style={{fontWeight:700}}>{pc.horizon.toUpperCase()}</div>
                    <ul className="small" style={{margin:"4px 0 0 16px"}}>
                      {(pc.why || []).map((w, j)=>(<li key={j}>{w}</li>))}
                    </ul>
                    <div className="small" style={{opacity:.8, marginTop:6}}>
                      {(pc.triggers || []).join(" · ")}
                    </div>
                    <div style={{display:"flex", gap:8, marginTop:8}}>
                      <button className="secondary" onClick={()=>handleSize(sym)}>Size It</button>
                      <button className="secondary" onClick={()=>handleAlert(sym)}>Create Alert</button>
                      <button className="secondary" onClick={()=>alert("Explain plan (stub)")}>Explain Plan</button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </main>
  );
}

