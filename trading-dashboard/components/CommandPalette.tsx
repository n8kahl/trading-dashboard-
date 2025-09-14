"use client";

import { useEffect, useState } from "react";
import { useHotkeys } from "@/src/lib/useHotkeys";

type Props = { onClose?: ()=>void };

export default function CommandPalette({ onClose }: Props) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      const meta = e.metaKey || e.ctrlKey; if (meta && e.key.toLowerCase() === "k") { e.preventDefault(); setOpen(v=>!v); }
    };
    window.addEventListener("keydown", on); return () => window.removeEventListener("keydown", on);
  }, []);
  useHotkeys({
    "b": ()=> console.log("Open buy ticket"),
    "s": ()=> console.log("Sell/Close"),
    "a": ()=> console.log("Create alert preset"),
    "c": ()=> console.log("Re-analyze")
  });

  if (!open) return null;
  return (
    <div style={{position:"fixed", inset:0, background:"rgba(0,0,0,0.4)", display:"flex", alignItems:"flex-start", justifyContent:"center", paddingTop:80, zIndex:50}} onClick={()=>{ setOpen(false); onClose?.(); }}>
      <div className="card" style={{width:"min(720px,90vw)"}} onClick={(e)=> e.stopPropagation()}>
        <input autoFocus placeholder="Type a command…" className="input" value={q} onChange={(e)=> setQ(e.target.value)} />
        <div className="small" style={{opacity:.7, marginTop:6}}>Try: buy ticket (b), sell/close (s), set alert (a), reanalyze (c)</div>
      </div>
    </div>
  );
}

