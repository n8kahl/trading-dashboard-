"use client";

import EdgeRing from "@/components/EdgeRing";

type Props = {
  score: number;
  band: "favorable" | "mixed" | "unfavorable" | string;
  components?: Partial<Record<"ATR"|"VWAP"|"EMAs"|"Flow"|"Liquidity"|"Vol", number>>;
};

function bandColor(b: string) {
  return b === "favorable" ? "#46d37e" : b === "mixed" ? "#e8b44c" : "#f26666";
}

export default function ConfidenceCard({ score, band, components={} }: Props) {
  const slices = [
    { key: "ATR", value: Math.max(0, components.ATR ?? 10), color: "#7dd3fc" },
    { key: "VWAP", value: Math.max(0, components.VWAP ?? 10), color: "#60a5fa" },
    { key: "EMAs", value: Math.max(0, components.EMAs ?? 10), color: "#34d399" },
    { key: "Flow", value: Math.max(0, components.Flow ?? 10), color: "#f472b6" },
    { key: "Liquidity", value: Math.max(0, components.Liquidity ?? 10), color: "#fbbf24" },
    { key: "Vol", value: Math.max(0, components.Vol ?? 10), color: "#a78bfa" },
  ];
  const ring = <EdgeRing size={120} stroke={10} slices={slices} />;
  return (
    <section className="card" style={{display:"flex", gap:12, alignItems:"center"}}>
      <div style={{position:"relative"}}>
        {ring}
        <div style={{position:"absolute", left:0, top:0, width:120, height:120, display:"flex", alignItems:"center", justifyContent:"center", flexDirection:"column"}}>
          <div style={{fontSize:22, fontWeight:800}}>{Math.round(score)}</div>
          <div className="small" style={{color:bandColor(band)}}>{String(band).toUpperCase()}</div>
        </div>
      </div>
      <div style={{display:"grid", gridTemplateColumns:"repeat(3,auto)", gap:"6px 12px", alignItems:"center"}}>
        {slices.map(s=> (
          <>
            <span key={`${s.key}-k`} className="small" style={{opacity:.8}}>{s.key}</span>
            <div key={`${s.key}-bar`} style={{width:80, height:6, background:"#1f2937", borderRadius:6, overflow:"hidden"}}>
              <div style={{width:`${Math.min(100, (s.value/20)*100)}%`, height:"100%", background:s.color}} />
            </div>
            <span key={`${s.key}-v`} className="small" style={{opacity:.6}}>{Math.round(s.value)}</span>
          </>
        ))}
      </div>
    </section>
  );
}

