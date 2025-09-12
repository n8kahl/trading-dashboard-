"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/src/lib/api";

type WatchlistResp = { ok: boolean; symbols: string[] };
type Pick = {
  symbol: string;
  expiration: string;
  strike: number;
  option_type: "call"|"put";
  delta?: number;
  bid?: number; ask?: number; mark?: number;
  spread_pct?: number;
  open_interest?: number; volume?: number;
  dte?: number; score?: number;
};

function smallNum(n?: number, d: number = 3) {
  if (n === undefined || n === null || Number.isNaN(n)) return "—";
  return Number(n).toFixed(d);
}

export default function Page() {
  const [side, setSide] = useState<"call"|"put">("call");
  const [ticker, setTicker] = useState("SPY");

  // per-contract inputs: { [contractSymbol]: {entry, stop} }
  const [inputs, setInputs] = useState<Record<string, {entry:string; stop:string}>>({});

  const wl = useQuery({
    queryKey: ["watchlist"],
    queryFn: async (): Promise<WatchlistResp> => apiGet("/api/v1/screener/watchlist/get")
  });

  const picks = useQuery({
    queryKey: ["picks", ticker, side],
    queryFn: async () => {
      const body = { symbol: ticker, side: side === "call" ? "long_call" : "long_put", horizon: "intra", n: 5 };
      const res = await apiPost("/api/v1/options/pick", body);
      // Normalize to array
      return Array.isArray(res?.picks) ? (res.picks as Pick[]) : [];
    },
    refetchOnWindowFocus: false
  });

  const plan = useMutation({
    mutationFn: (args: {symbol:string; side:"long"|"short"; entry:number; stop:number}) =>
      apiPost("/api/v1/plan/validate", args)
  });

  const sizing = useMutation({
    mutationFn: (args: {symbol:string; side:"long"|"short"; risk_R:number; per_unit_risk:number}) =>
      apiPost("/api/v1/sizing/suggest", args)
  });

  const alertMut = useMutation({
    mutationFn: (args: {symbol:string; level:number; note?:string}) =>
      apiPost("/api/v1/alerts/set", args)
  });

  const setInput = (k: string, field: "entry"|"stop", v: string) =>
    setInputs(prev => ({ ...prev, [k]: { ...(prev[k] ?? {entry:"", stop:""}), [field]: v } }));

  const getInput = (k: string) => inputs[k] ?? { entry: "", stop: "" };

  return (
    <main className="container">
      <h1 style={{marginBottom:12}}>Trading Assistant Dashboard</h1>

      <section className="card" style={{marginBottom:12}}>
        <div style={{fontWeight:600, marginBottom:6}}>Watchlist</div>
        <div style={{display:"flex", gap:8, flexWrap:"wrap"}}>
          {(wl.data?.symbols ?? ["SPY","QQQ","AAPL","NVDA","MSFT","TSLA","META","AMZN"]).map(sym=>(
            <button key={sym}
              className={ticker===sym ? "" : "secondary"}
              onClick={()=> setTicker(sym)}
            >{sym}</button>
          ))}
        </div>
      </section>

      <section className="card" style={{marginBottom:12}}>
        <div style={{fontWeight:600, marginBottom:6}}>Side</div>
        <div style={{display:"flex", gap:8}}>
          <button className={side==="call" ? "" : "secondary"} onClick={()=> setSide("call")}>Calls</button>
          <button className={side==="put"  ? "" : "secondary"} onClick={()=> setSide("put")}>Puts</button>
        </div>
      </section>

      <section className="card">
        <div style={{display:"flex", justifyContent:"space-between", alignItems:"center"}}>
          <div style={{fontWeight:600}}> {ticker} — Top 5 {side==="call"?"Calls":"Puts"} (closest to ATM)</div>
          <div className="small" style={{opacity:.75}}>
            {picks.isFetching ? "loading…" : ""}
          </div>
        </div>

        {picks.isError ? (
          <div style={{marginTop:8, color:"#ffb4b4"}}>Error: {String(picks.error)}</div>
        ) : (
          <div style={{display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(320px,1fr))", gap:12, marginTop:10}}>
            {(picks.data ?? []).map((c: Pick) => {
              const k = c.symbol; // contract symbol as key
              const { entry, stop } = getInput(k);
              const line1 = `Δ ${smallNum(c.delta,2)} · bid ${smallNum(c.bid)} / ask ${smallNum(c.ask)} · mark ${smallNum(c.mark)}`;
              const line2 = `spread ${smallNum(c.spread_pct*100,2)}% · OI ${c.open_interest ?? "—"} · Vol ${c.volume ?? "—"}`;

              return (
                <div key={k} className="card" style={{margin:0}}>
                  <div style={{display:"flex", justifyContent:"space-between", gap:8, marginBottom:4}}>
                    <div style={{fontWeight:700}}>{k}</div>
                    <div className="small" style={{opacity:.75}}>{c.expiration} · {c.option_type.toUpperCase()} · {c.strike}</div>
                  </div>
                  <div className="small" style={{opacity:.9}}>{line1}</div>
                  <div className="small" style={{opacity:.6, marginBottom:8}}>{line2}</div>

                  <div style={{display:"flex", gap:8, marginBottom:8}}>
                    <input
                      placeholder="Entry (e.g., 231.20)"
                      value={entry}
                      onChange={(e)=> setInput(k,"entry", e.target.value)}
                      className="input"
                      inputMode="decimal"
                    />
                    <input
                      placeholder="Stop (e.g., 230.10)"
                      value={stop}
                      onChange={(e)=> setInput(k,"stop", e.target.value)}
                      className="input"
                      inputMode="decimal"
                    />
                  </div>

                  <div style={{display:"flex", gap:8, flexWrap:"wrap"}}>
                    <button onClick={()=>{
                      if(!entry || !stop){ window.alert("Enter entry & stop first"); return; }
                      plan.mutate({ symbol: ticker, side: side==="call" ? "long" : "short", entry: Number(entry), stop: Number(stop) });
                    }}>Build Plan</button>

                    <button className="secondary" onClick={()=>{
                      if(!entry || !stop){ window.alert("Enter entry & stop first"); return; }
                      const per_unit_risk = Math.abs(Number(entry) - Number(stop));
                      sizing.mutate({ symbol: ticker, side: side==="call" ? "long" : "short", risk_R: 1, per_unit_risk });
                    }}>Size It</button>

                    <button className="secondary" onClick={()=>{
                      // simple price alert at the entry level
                      if(!entry){ window.alert("Enter an entry to set an alert level"); return; }
                      alertMut.mutate({ symbol: ticker, level: Number(entry), note: `Alert near plan entry for ${ticker}` });
                    }}>Set Alert</button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div style={{display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(320px,1fr))", gap:12, marginTop:12}}>
          <div className="card" style={{flex:"1 1 320px"}}>
            <div style={{fontWeight:600, marginBottom:6}}>Plan Result</div>
            <div className="small">
              {plan.isPending ? "Working…" :
               plan.isError ? String(plan.error) :
               plan.data ? JSON.stringify(plan.data, null, 2) : "—"}
            </div>
          </div>

          <div className="card" style={{flex:"1 1 320px"}}>
            <div style={{fontWeight:600, marginBottom:6}}>Sizing Result</div>
            <div className="small">
              {sizing.isPending ? "Working…" :
               sizing.isError ? String(sizing.error) :
               sizing.data ? JSON.stringify(sizing.data, null, 2) : "—"}
            </div>
          </div>

          <div className="card" style={{flex:"1 1 320px"}}>
            <div style={{fontWeight:600, marginBottom:6}}>Alert Result</div>
            <div className="small">
              {alertMut.isPending ? "Working…" :
               alertMut.isError ? String(alertMut.error) :
               alertMut.data ? "✓ Alert set" : "—"}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
