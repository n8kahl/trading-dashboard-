"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/src/lib/api";
import { connectWS } from "@/src/lib/ws";
import { useWS, usePrices, useRisk } from "@/src/lib/store";
import { toast } from "sonner";
import NewsPanel from "@/components/NewsPanel";
import AlertsPanel from "@/components/AlertsPanel";
import NarrativeTicker from "@/components/NarrativeTicker";
import PositionCoach from "@/components/PositionCoach";
import ConfidenceCardV2 from "@/components/ConfidenceCard";
import LiveChart from "@/components/LiveChart";
import OrderTicket from "@/components/OrderTicket";

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
  const [ticketOpen, setTicketOpen] = useState(false);
  const connected = useWS();
  const prices = usePrices();
  const risk = useRisk();

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

  const analyze = useMutation({
    mutationFn: async (symbol: string) => {
      const body = { symbol, strategy_id: "auto" };
      return apiPost("/api/v1/compose-and-analyze", body);
    }
  });

  const alertMut = useMutation({
    mutationFn: (args: {symbol:string; timeframe?: 'minute'|'day'; type: 'price_above'|'price_below'; value:number; threshold_pct?: number}) =>
      apiPost("/api/v1/alerts/set", {
        symbol: args.symbol,
        timeframe: args.timeframe || 'minute',
        condition: { type: args.type, value: args.value, threshold_pct: args.threshold_pct },
      })
  });

  const setInput = (k: string, field: "entry"|"stop", v: string) =>
    setInputs(prev => ({ ...prev, [k]: { ...(prev[k] ?? {entry:"", stop:""}), [field]: v } }));

  const getInput = (k: string) => inputs[k] ?? { entry: "", stop: "" };

  useEffect(() => {
    connectWS();
  }, []);

  return (
    <main className="container">
      <h1 style={{marginBottom:12}}>Trading Assistant Dashboard</h1>

      <div className="small" style={{marginBottom:8, display:"flex", gap:12, alignItems:"center", flexWrap:"wrap"}}>
        <span>WS: {connected ? "Connected" : "Disconnected"}</span>
        <span>Price {ticker}: {prices?.[ticker] !== undefined ? Number(prices[ticker]).toFixed(2) : "—"}</span>
        {risk ? (
          <span>
            Risk — daily R: {Number(risk?.daily_r ?? 0).toFixed(2)} · positions: {risk?.concurrent ?? 0}
            {risk?.breach_daily_r ? " · DAILY BREACH" : ""}
            {risk?.breach_concurrent ? " · CONCURRENT BREACH" : ""}
          </span>
        ) : null}
      </div>

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
              const line2 = `spread ${c.spread_pct !== undefined ? smallNum(c.spread_pct*100,2) + '%' : '—'} · OI ${c.open_interest ?? "—"} · Vol ${c.volume ?? "—"}`;

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
                      if(!entry || !stop){ toast("Enter entry & stop first"); return; }
                      plan.mutate({ symbol: ticker, side: side==="call" ? "long" : "short", entry: Number(entry), stop: Number(stop) });
                    }}>Build Plan</button>

                    <button className="secondary" onClick={()=>{
                      if(!entry || !stop){ toast("Enter entry & stop first"); return; }
                      const per_unit_risk = Math.abs(Number(entry) - Number(stop));
                      sizing.mutate({ symbol: ticker, side: side==="call" ? "long" : "short", risk_R: 1, per_unit_risk });
                    }}>Size It</button>

                    <InlineAlertCreator
                      symbol={ticker}
                      entry={entry}
                      stop={stop}
                      onCreate={(type, thresholdPct, level)=>{
                        if(!entry){ toast("Enter an entry first"); return; }
                        alertMut.mutate({ symbol: ticker, type, value: level, threshold_pct: thresholdPct });
                      }}
                    />
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

          <ConfidencePanel ticker={ticker} analyze={analyze} />
        </div>
      </section>

      <div style={{display:"grid", gridTemplateColumns:"2fr 1fr", gap:12, marginTop:12}}>
        <div style={{display:"flex", flexDirection:"column", gap:12}}>
          <LiveChart symbol={ticker} />
        </div>
        <div style={{display:"flex", flexDirection:"column", gap:12}}>
          {process.env.NEXT_PUBLIC_DISABLE_NARRATOR === '1' ? null : <NarrativeTicker symbol={ticker} />}
          {process.env.NEXT_PUBLIC_DISABLE_NARRATOR === '1' ? null : <PositionCoach symbol={ticker} />}
          <NewsPanel symbols={(wl.data?.symbols ?? [ticker]).slice(0,7)} />
          <AlertsPanel />
        </div>
      </div>

      {/* Sticky mobile action bar */}
      <div style={{position:"fixed", left:0, right:0, bottom:8, display:"flex", gap:8, justifyContent:"center"}}
        className="mobile-only">
        <div className="card" style={{display:"flex", gap:8, padding:8}}>
          <button className="secondary" onClick={()=>setTicketOpen(true)}>Buy</button>
          <button className="secondary" onClick={()=>setTicketOpen(true)}>Sell</button>
          <button className="secondary" onClick={()=>alert("Alert preset (stub)")}>Alert</button>
          <button className="secondary" onClick={()=>alert("Ask Coach (stub)")}>Coach</button>
        </div>
      </div>
      <OrderTicket symbol={ticker} open={ticketOpen} onClose={()=> setTicketOpen(false)} />
    </main>
  );
}

// --- UI subcomponents ---

function bandMeta(score?: number): { label: string; color: string } {
  const s = typeof score === 'number' ? score : -1;
  if (s >= 70) return { label: 'Favorable', color: '#16a34a' };
  if (s >= 50) return { label: 'Mixed', color: '#eab308' };
  if (s >= 0) return { label: 'Unfavorable', color: '#ef4444' };
  return { label: '—', color: '#64748b' };
}

function ConfidencePanel({ ticker, analyze }: { ticker: string; analyze: any }) {
  const data = analyze?.data;
  const analysis = data?.analysis || null;
  const score: number | undefined = analysis?.score;
  const meta = bandMeta(score);
  const comps: Record<string, number> = analysis?.components || {};
  const rationale: string | undefined = analysis?.rationale;
  const freshness = data?.context?.data_freshness_sec;

  return (
    <div className="card" style={{flex:"1 1 320px"}}>
      <div style={{display:"flex", justifyContent:"space-between", alignItems:"center"}}>
        <div style={{fontWeight:600, marginBottom:6}}>Confidence & Analysis</div>
        <button className="secondary" onClick={() => analyze.mutate(ticker)} disabled={analyze.isPending}>Analyze</button>
      </div>
      <div className="small" style={{marginTop:6}}>
        {analyze.isPending ? "Analyzing…" : analyze.isError ? String(analyze.error) : analysis ? (
          <>
            <div style={{marginBottom:8}}>
              <ConfidenceCardV2
                score={score ?? 0}
                band={meta.label.toLowerCase()}
                components={{
                  ATR: Number(comps.atr_regime ?? 0),
                  VWAP: Number(comps.vwap_posture ?? comps.vwap_support ?? 0),
                  EMAs: Number(comps.ema_stack ?? 0),
                  Flow: Number((comps.flow ?? 0) + (comps.momentum_hint ?? 0)),
                  Liquidity: Number(comps.liquidity ?? 0),
                  Vol: Number(comps.vol_context ?? 0),
                }}
              />
            </div>
            <div style={{display:"flex", alignItems:"center", gap:10, marginBottom:8}}>
              <div style={{display:"inline-flex", alignItems:"center", gap:8, background:"rgba(255,255,255,0.04)", border:"1px solid var(--border)", borderRadius:12, padding:"6px 10px"}}>
                <div style={{fontSize:"1.2rem", fontWeight:800}}>{Math.round(score ?? 0)}</div>
                <div style={{color: meta.color, fontWeight:700}}>{meta.label}</div>
              </div>
              <div style={{opacity:.75}}>freshness: {freshness !== undefined ? `${freshness}s` : '—'}</div>
            </div>

            <div className="chiprow" style={{marginBottom:8}}>
              {Object.keys(comps).length ? (
                Object.entries(comps).map(([k,v]) => (
                  <span key={k} className="chip" title={k}>

                      {k.replace(/_/g,' ')}: {(v as number) >= 0 ? `+${v}` : v}

                  </span>
                ))
              ) : (
                <span className="small">No components available.</span>
              )}
            </div>

            {rationale ? (<div className="small" style={{whiteSpace:'pre-wrap'}}>{rationale}</div>) : null}
          </>
        ) : "—"}
      </div>
    </div>
  );
}

function InlineAlertCreator({ symbol, entry, stop, onCreate }:{ symbol: string; entry: string; stop: string; onCreate: (type: 'price_above'|'price_below', thresholdPct: number|undefined, level: number)=>void }) {
  const [atype, setAtype] = useState<'price_above'|'price_below'>('price_above');
  const [thresh, setThresh] = useState<string>(""); // % optional

  const computeLevel = () => {
    const e = Number(entry);
    const s = Number(stop);
    if (!entry || !stop || Number.isNaN(e) || Number.isNaN(s)) return NaN;
    const perR = Math.abs(e - s);
    const pct = Number(thresh);
    if (!Number.isNaN(pct) && pct > 0) {
      const offs = (e * pct) / 100;
      return atype === 'price_above' ? e + offs : e - offs;
    }
    return atype === 'price_above' ? e + perR : e - perR;
  };

  const level = computeLevel();

  return (
    <div style={{display:'inline-flex', gap:8, alignItems:'center', flexWrap:'wrap'}}>
      <select value={atype} onChange={(e)=> setAtype(e.target.value as any)}>
        <option value="price_above">Alert above</option>
        <option value="price_below">Alert below</option>
      </select>
      <input className="input" placeholder="threshold % (opt)" style={{width:120}}
        value={thresh} onChange={(e)=> setThresh(e.target.value)} inputMode="decimal" />
      <button className="secondary" onClick={()=>{
        if (!entry) { toast("Enter an entry first"); return; }
        const lvl = computeLevel();
        if (!Number.isFinite(lvl)) { toast("Provide stop or threshold %"); return; }
        const pct = thresh ? Number(thresh) : undefined;
        onCreate(atype, pct, Number(lvl.toFixed(4)));
      }}>Set Alert {Number.isFinite(level) ? `@ ${level.toFixed(2)}` : ''}</button>
    </div>
  );
}
