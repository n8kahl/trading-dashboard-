"use client";

import { useState } from "react";
import { apiPost } from "@/src/lib/api";

export default function AskCoachWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [reply, setReply] = useState("");

  const send = async () => {
    const text = input.trim(); if (!text) return;
    setPending(true); setReply("");
    try {
      const resp = await apiPost("/api/v1/coach/chat", { messages: [{ role: 'user', content: text }] });
      setReply((resp?.content || '').toString());
    } catch (e: any) {
      setReply(`Error: ${e?.message ?? e}`);
    } finally { setPending(false); }
  };

  return (
    <div style={{position:'fixed', right:12, bottom:12, zIndex:55}}>
      {!open ? (
        <button className="secondary" onClick={()=> setOpen(true)}>Ask Coach</button>
      ) : (
        <div className="card" style={{width:320}}>
          <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
            <div style={{fontWeight:700}}>Ask Coach</div>
            <button className="secondary" onClick={()=> setOpen(false)}>Close</button>
          </div>
          <div className="small" style={{whiteSpace:'pre-wrap', minHeight:80, marginTop:6}}>{reply || '—'}</div>
          <div style={{display:'flex', gap:6, marginTop:6}}>
            <input className="input" value={input} onChange={e=> setInput(e.target.value)} placeholder="e.g., What about SPY scalp?" onKeyDown={e=> { if(e.key==='Enter') send(); }} />
            <button onClick={send} disabled={pending}>{pending? '...' : 'Send'}</button>
          </div>
        </div>
      )}
    </div>
  );
}

