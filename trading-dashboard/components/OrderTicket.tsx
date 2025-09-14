"use client";

import { useState } from "react";
import { usePrices } from "@/src/lib/store";

type Props = { symbol: string; open: boolean; onClose: ()=>void };

export default function OrderTicket({ symbol, open, onClose }: Props) {
  const [side, setSide] = useState<'buy'|'sell'>('buy');
  const [qty, setQty] = useState<string>('1');
  const [type, setType] = useState<'market'|'limit'>('market');
  const [limit, setLimit] = useState<string>('');
  const [entry, setEntry] = useState<string>('');
  const [sl, setSl] = useState<string>('');
  const [tp, setTp] = useState<string>('');
  const [preview, setPreview] = useState(true);
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [canPlace, setCanPlace] = useState(false);
  const prices = usePrices();

  if (!open) return null;

  const submit = async (overridePreview?: boolean) => {
    const q = Number(qty);
    if (!Number.isFinite(q) || q <= 0) { alert('Invalid quantity'); return; }
    if (type === 'limit' && !Number.isFinite(Number(limit))) { alert('Provide limit price'); return; }
    const e = type === 'limit' ? Number(limit) : (entry ? Number(entry) : Number(prices?.[symbol] ?? NaN));
    if (!Number.isFinite(e)) { alert('Provide entry (or limit)'); return; }
    setPending(true); setResult(null);
    try {
      const body: any = { symbol, side, quantity: q, order_type: type, preview: overridePreview ?? preview };
      if (type === 'limit') body.limit_price = Number(limit);
      if (sl) body.bracket_stop = Number(sl);
      if (tp) body.bracket_target = Number(tp);
      const res = await fetch(`/api/proxy?path=${encodeURIComponent('/broker/tradier/order')}`, {
        method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body)
      });
      const js = await res.json().catch(()=>({}));
      setResult(js);
      setCanPlace(!!(overridePreview ?? preview));
    } catch (e: any) {
      setResult({ ok: false, error: e?.message ?? String(e) });
      setCanPlace(false);
    } finally { setPending(false); }
  };

  const sizeIt = async () => {
    try {
      const e = type === 'limit' ? Number(limit) : (entry ? Number(entry) : Number(prices?.[symbol] ?? NaN));
      const s = Number(sl);
      if (!Number.isFinite(e) || !Number.isFinite(s)) { alert('Entry and Stop required for sizing'); return; }
      const sideLR = side === 'buy' ? 'long' : 'short';
      const path = '/sizing/suggest';
      const body = { symbol, side: sideLR, entry: e, stop: s };
      const resp = await fetch(`/api/proxy?path=${encodeURIComponent(path)}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
      const js = await resp.json();
      const q = Number(js?.quantity ?? js?.data?.quantity ?? js?.suggested ?? NaN);
      if (Number.isFinite(q) && q > 0) setQty(String(q));
      else alert('Sizing failed');
    } catch (e: any) {
      alert(e?.message ?? String(e));
    }
  };

  return (
    <div style={{position:'fixed', inset:0, background:'rgba(0,0,0,0.5)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:60}} onClick={onClose}>
      <div className="card" style={{minWidth:320, maxWidth:"90vw"}} onClick={e=> e.stopPropagation()}>
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
          <div style={{fontWeight:700}}>Order Ticket — {symbol}</div>
          <button className="secondary" onClick={onClose}>Close</button>
        </div>
        <div style={{display:'grid', gridTemplateColumns:'repeat(2,1fr)', gap:8, marginTop:8}}>
          <label>Side
            <select className="input" value={side} onChange={e=> setSide(e.target.value as any)}>
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>
          </label>
          <label>Qty
            <input className="input" value={qty} onChange={e=> setQty(e.target.value)} inputMode="numeric" />
          </label>
          <label>Entry price
            <input className="input" value={entry} onChange={e=> setEntry(e.target.value)} placeholder={prices?.[symbol] ? String(prices[symbol]) : '—'} inputMode="decimal" />
          </label>
          <label>Type
            <select className="input" value={type} onChange={e=> setType(e.target.value as any)}>
              <option value="market">Market</option>
              <option value="limit">Limit</option>
            </select>
          </label>
          <label>Limit
            <input className="input" value={limit} onChange={e=> setLimit(e.target.value)} placeholder="—" inputMode="decimal" />
          </label>
          <label>Stop (bracket)
            <input className="input" value={sl} onChange={e=> setSl(e.target.value)} placeholder="—" inputMode="decimal" />
          </label>
          <label>Target (bracket)
            <input className="input" value={tp} onChange={e=> setTp(e.target.value)} placeholder="—" inputMode="decimal" />
          </label>
        </div>
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginTop:8}}>
          <label className="small" style={{display:'flex', alignItems:'center', gap:6}}>
            <input type="checkbox" checked={preview} onChange={e=> setPreview(e.target.checked)} /> Preview only
          </label>
          <div style={{display:'flex', gap:8}}>
            <button className="secondary" onClick={sizeIt} disabled={pending}>Size It</button>
            <button onClick={()=>submit()} disabled={pending}>{pending? 'Submitting…' : (preview ? 'Preview' : 'Place')}</button>
            {canPlace && <button onClick={()=> submit(false)} disabled={pending}>Confirm Place</button>}
          </div>
        </div>
        <div className="small" style={{marginTop:8, whiteSpace:'pre-wrap'}}>
          {result ? JSON.stringify(result, null, 2) : ''}
        </div>
      </div>
    </div>
  );
}
