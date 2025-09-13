"use client";

import { useAlerts } from "@/src/lib/store";

export default function AlertsPanel() {
  const alerts = useAlerts();
  return (
    <section className="card">
      <div style={{fontWeight:600, marginBottom:6}}>Alerts</div>
      {alerts.length === 0 ? (
        <div className="small">No alerts.</div>
      ) : (
        <ul style={{display:"flex", flexDirection:"column", gap:8}}>
          {alerts.map((a, idx) => (
            <li key={idx} className="card" style={{margin:0}}>
              <div className="small" style={{opacity:.7, marginBottom:4}}>{a.level || 'info'}</div>
              <div>{a.msg}</div>
              {/* Action chips could open Coach or trigger order flows; keep simple */}
              <div style={{display:"flex", gap:8, marginTop:8}}>
                <button className="secondary" onClick={() => window.dispatchEvent(new CustomEvent('coach:prompt', { detail: `Given this alert: ${a.msg}. Propose next best action with confidence %.` }))}>Ask Coach</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

