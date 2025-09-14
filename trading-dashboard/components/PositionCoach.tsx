"use client";

import { useMemo } from "react";
import { useEventSource } from "@/src/lib/useEventSource";
import { useRisk, usePositions } from "@/src/lib/store";

type Props = { symbol: string; positionId?: string | null };

export default function PositionCoach({ symbol, positionId }: Props) {
  const url = useMemo(() => `/api/proxy?path=/coach/stream&symbol=${encodeURIComponent(symbol)}${positionId?`&position_id=${encodeURIComponent(positionId)}`:""}`,[symbol, positionId]);
  const { status, messages } = useEventSource(url, [url]);
  const head = messages[0] || {};
  const g = (head?.guidance) || {};
  const next = Array.isArray(g?.if_then) && g.if_then.length ? (g.if_then[0] || {}) : {};
  const unless = g?.risk_notes || g?.unless || "—";

  const risk = useRisk();
  const positions = usePositions();
  const disabled = !!(risk?.breach_daily_r || risk?.breach_concurrent);

  const postJson = async (path: string, body: any) => {
    const res = await fetch(`/api/proxy?path=${encodeURIComponent(path)}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json().catch(()=> ({}));
  };

  const onTrim = async () => {
    const qtyStr = window.prompt("Trim quantity (shares)", "1");
    const qty = qtyStr ? Number(qtyStr) : NaN;
    if (!Number.isFinite(qty) || qty <= 0) return;
    try { await postJson("/broker/tradier/order", { symbol, side: "sell", quantity: qty, order_type: "market", preview: true }); alert("Trim preview sent"); } catch(e:any){ alert(e?.message ?? String(e)); }
  };
  const onMoveStopToVWAP = async () => {
    const pos = (positions || []).find((p:any)=> (p.symbol||'').toUpperCase()===symbol.toUpperCase());
    let qty = Math.abs(Number(pos?.qty ?? 0)) || NaN;
    let side: 'long'|'short' = (Number(pos?.qty ?? 0) >= 0 ? 'long' : 'short');
    if (!Number.isFinite(qty) || qty<=0) {
      const s = window.prompt('Position side (long/short)', 'long');
      if (!s) return;
      side = (s.toLowerCase()==='short' ? 'short' : 'long');
      const q = window.prompt('Quantity to protect (shares)', '1');
      qty = q ? Number(q) : NaN;
    }
    if (!Number.isFinite(qty) || qty<=0) return;
    try { const res = await postJson('/broker/tradier/move_stop', { symbol, side, quantity: qty, preview: true }); alert(`Stop preview at VWAP: ${res?.computed?.stop_price ?? ''}`); } catch(e:any){ alert(e?.message ?? String(e)); }
  };

  const onTakeProfitTp1 = async () => {
    const tp1 = g?.stops?.tp1 ?? g?.tp1;
    if (tp1 === undefined || tp1 === null) { alert('No TP1 available'); return; }
    const pos = (positions || []).find((p:any)=> (p.symbol||'').toUpperCase()===symbol.toUpperCase());
    let qty = Math.floor((Math.abs(Number(pos?.qty ?? 0)) || 0)/2) || 1;
    const q = window.prompt('Take profit quantity', String(qty));
    qty = q ? Number(q) : NaN;
    if (!Number.isFinite(qty) || qty<=0) return;
    const side = (Number(pos?.qty ?? 0) >= 0 ? 'sell' : 'buy');
    try { await postJson('/broker/tradier/order', { symbol, side, quantity: qty, order_type: 'limit', limit_price: Number(tp1), preview: true }); alert('TP1 preview sent'); } catch(e:any){ alert(e?.message ?? String(e)); }
  };
  const onClose = async () => {
    const qtyStr = window.prompt("Close quantity (shares)", "1");
    const qty = qtyStr ? Number(qtyStr) : NaN;
    if (!Number.isFinite(qty) || qty <= 0) return;
    try { await postJson("/broker/tradier/order", { symbol, side: "sell", quantity: qty, order_type: "market", preview: true }); alert("Close preview sent"); } catch(e:any){ alert(e?.message ?? String(e)); }
  };

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
        <button className="secondary" disabled={disabled} onClick={onTrim}>Trim</button>
        <button className="secondary" disabled={disabled} onClick={onMoveStopToVWAP}>Move Stop → VWAP</button>
        <button className="secondary" disabled={disabled} onClick={onTakeProfitTp1}>TP1</button>
        <button className="secondary" disabled={disabled} onClick={onClose}>Close</button>
      </div>
    </section>
  );
}
