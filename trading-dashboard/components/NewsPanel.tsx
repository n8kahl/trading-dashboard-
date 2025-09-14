"use client";

import { useEffect, useState } from "react";

type Item = { symbol: string; title: string; url?: string; source?: string; published_at?: string };
type Props = { symbols: string[] };

function timeAgo(iso?: string) {
  if (!iso) return "";
  const t = Date.parse(iso); if (Number.isNaN(t)) return "";
  const s = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s/60); if (m < 60) return `${m}m`;
  const h = Math.floor(m/60); return `${h}h`;
}

export default function NewsPanel({ symbols }: Props) {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");

  const fetchNews = async () => {
    setLoading(true); setError("");
    try {
      const path = `/news?symbols=${encodeURIComponent(symbols.join(","))}&limit=8`;
      const res = await fetch(`/api/proxy?path=${encodeURIComponent(path)}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const js = await res.json();
      setItems(Array.isArray(js?.items) ? js.items as Item[] : []);
    } catch (e: any) {
      setError(e?.message ?? String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchNews(); /* eslint-disable-next-line */ }, [symbols.join(",")]);

  return (
    <section className="card">
      <div style={{display:"flex", justifyContent:"space-between", alignItems:"center"}}>
        <div style={{fontWeight:600}}>Real News</div>
        <button className="secondary" onClick={fetchNews} disabled={loading}>{loading?"Refreshing…":"Refresh"}</button>
      </div>
      {error ? <div className="small" style={{color:'#ffb4b4', marginTop:6}}>Error: {error}</div> : null}
      <div style={{display:"flex", flexDirection:"column", gap:6, marginTop:8}}>
        {items.length === 0 ? <div className="small" style={{opacity:.7}}>{loading?"Loading…":"No headlines"}</div> :
          items.map((it, i) => (
            <div key={i} className="small" style={{display:"flex", gap:8, alignItems:"baseline"}}>
              <span style={{opacity:.7, minWidth:40}}>[{it.symbol}]</span>
              <a href={it.url} target="_blank" rel="noreferrer" style={{color:"#ddd"}}>{it.title}</a>
              <span style={{opacity:.6, marginLeft:"auto"}}>{it.source ? `(${it.source}) `: ""}{timeAgo(it.published_at)}</span>
            </div>
          ))}
      </div>
    </section>
  );
}
