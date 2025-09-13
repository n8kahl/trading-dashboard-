"use client";

import { useEffect, useState } from "react";
import { coachChat, CoachMsg } from "@/src/lib/coach";

type Props = { symbols: string[] };

export default function NewsPanel({ symbols }: Props) {
  const [text, setText] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const fetchNews = async () => {
    setLoading(true);
    try {
      const sys: CoachMsg = { role: "system", content: "You browse the web and return concise trading-relevant news, upcoming earnings, and economic events. Always include confidence % per item." };
      const user: CoachMsg = { role: "user", content: `For ${symbols.join(", ")}, summarize: (1) top headlines that can move price now, (2) next 7 days earnings for any of them, (3) today's/tomorrow's key econ prints. For each item: symbol(s), why it matters in 1 line, confidence %.` };
      const resp = await coachChat([sys, user]);
      setText(resp?.content || "");
    } catch (e: any) {
      setText(`Error: ${e?.message ?? e}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchNews(); /* eslint-disable-next-line */ }, [symbols.join(",")]);

  return (
    <section className="card">
      <div style={{display:"flex", justifyContent:"space-between", alignItems:"center"}}>
        <div style={{fontWeight:600}}>News & Events</div>
        <button className="secondary" onClick={fetchNews} disabled={loading}>{loading?"Refreshing…":"Refresh"}</button>
      </div>
      <div className="small" style={{whiteSpace:"pre-wrap", marginTop:8}}>{text || "—"}</div>
    </section>
  );
}

