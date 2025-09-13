"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/src/lib/api";

type Signal = {
  id: string;
  symbol: string;
  time: string;
  strategy?: string;
  gates?: Record<string, boolean>;
  pr_win?: number;
  expected_r?: number;
  actionability?: string;
};

type Position = {
  id: string;
  symbol: string;
  side: string;
  avg_price: number;
  qty: number;
  unrealized_r?: number;
  timer_sec?: number;
  risk_state?: string;
};

export default function AdminPage() {
  const signals = useQuery({
    queryKey: ["signals"],
    queryFn: async () => {
      const res = await apiGet("/api/v1/admin/signals");
      // API sometimes returns {ok, items: [...]}
      // or just an array. Normalize to array.
      if (Array.isArray(res)) return res as Signal[];
      if (res?.items && Array.isArray(res.items)) return res.items as Signal[];
      return [];
    },
  });

  const positions = useQuery({
    queryKey: ["positions"],
    queryFn: async () => {
      const res = await apiGet("/api/v1/admin/positions");
      if (Array.isArray(res)) return res as Position[];
      if (res?.items && Array.isArray(res.items)) return res.items as Position[];
      return [];
    },
  });

  const calib = useQuery({
    queryKey: ["calib"],
    queryFn: async () => apiGet("/api/v1/admin/diag/calibration?strategy=vwap_bounce&period=30d"),
  });

  return (
    <main className="container">
      <h1 style={{marginBottom:12}}>Admin</h1>

      <section className="card" style={{marginBottom:16}}>
        <h2 style={{margin:"0 0 8px"}}>Signals</h2>
        {signals.isPending ? "Loading…" : signals.isError ? String(signals.error) : (
          <table className="table">
            <thead>
              <tr><th>Time</th><th>Symbol</th><th>Strategy</th><th>P(win)</th><th>E[R]</th><th>Action</th></tr>
            </thead>
            <tbody>
              {(signals.data ?? []).map((s: Signal) => (
                <tr key={s.id}>
                  <td>{new Date(s.time).toLocaleString()}</td>
                  <td>{s.symbol}</td>
                  <td>{s.strategy ?? "—"}</td>
                  <td>{s.pr_win?.toFixed?.(2) ?? "—"}</td>
                  <td>{s.expected_r?.toFixed?.(2) ?? "—"}</td>
                  <td>{s.actionability ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="card" style={{marginBottom:16}}>
        <h2 style={{margin:"0 0 8px"}}>Positions</h2>
        {positions.isPending ? "Loading…" : positions.isError ? String(positions.error) : (
          <table className="table">
            <thead>
              <tr><th>Symbol</th><th>Side</th><th>Avg</th><th>Qty</th><th>U/R</th><th>Risk</th></tr>
            </thead>
            <tbody>
              {(positions.data ?? []).map((p: Position) => (
                <tr key={p.id}>
                  <td>{p.symbol}</td>
                  <td>{p.side}</td>
                  <td>{p.avg_price}</td>
                  <td>{p.qty}</td>
                  <td>{p.unrealized_r ?? "—"}</td>
                  <td>{p.risk_state ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="card">
        <h2 style={{margin:"0 0 8px"}}>Calibration (vwap_bounce • 30d)</h2>
        <pre className="small" style={{whiteSpace:"pre-wrap"}}>
          {calib.isPending ? "Loading…" : calib.isError ? String(calib.error) : JSON.stringify(calib.data, null, 2)}
        </pre>
      </section>
    </main>
  );
}
