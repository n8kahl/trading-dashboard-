"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/src/lib/api";

type AlertItem = {
  id: number;
  symbol: string;
  timeframe?: "minute" | "day";
  condition: { type: "price_above" | "price_below"; value: number; threshold_pct?: number };
  expires_at?: string | null;
  is_active?: boolean;
  created_at?: string | null;
};

type AlertsListResp = { ok: boolean; items: AlertItem[] };

export default function AlertsPage() {
  const qc = useQueryClient();
  const [form, setForm] = useState<{
    symbol: string;
    type: "price_above" | "price_below";
    timeframe: "minute" | "day";
    level: string; // numeric input as string
    threshold_pct: string; // optional
    expires_at: string; // ISO string, optional
  }>({ symbol: "SPY", type: "price_above", timeframe: "minute", level: "", threshold_pct: "", expires_at: "" });

  const list = useQuery<AlertsListResp>({
    queryKey: ["alerts"],
    queryFn: () => apiGet("/api/v1/alerts/list"),
  });

  const create = useMutation({
    mutationFn: async () => {
      const value = Number(form.level);
      const pct = form.threshold_pct ? Number(form.threshold_pct) : undefined;
      if (!form.symbol || Number.isNaN(value)) throw new Error("Enter symbol and numeric level");
      await apiPost("/api/v1/alerts/set", {
        symbol: form.symbol.toUpperCase(),
        timeframe: form.timeframe,
        condition: { type: form.type, value, threshold_pct: pct },
        expires_at: form.expires_at || undefined,
      });
    },
    onSuccess: () => {
      setForm((f) => ({ ...f, level: "", threshold_pct: "", expires_at: "" }));
      qc.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  const del = useMutation({
    mutationFn: async (id: number) => apiPost(`/api/v1/alerts/delete/${id}`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  return (
    <main className="container">
      <h1 style={{ marginBottom: 12 }}>Alerts</h1>

      <section className="card" style={{ marginBottom: 12 }}>
        <div style={{ fontWeight: 600, marginBottom: 6 }}>Create Alert</div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <input
            value={form.symbol}
            onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })}
            placeholder="Symbol"
            className="input"
            style={{ width: 100 }}
          />
          <select className="input" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value as any })} style={{ width: 160 }}>
            <option value="price_above">Price above</option>
            <option value="price_below">Price below</option>
          </select>
          <select className="input" value={form.timeframe} onChange={(e) => setForm({ ...form, timeframe: e.target.value as any })} style={{ width: 120 }}>
            <option value="minute">Minute</option>
            <option value="day">Day</option>
          </select>
          <input
            value={form.level}
            onChange={(e) => setForm({ ...form, level: e.target.value })}
            placeholder="Level (price)"
            className="input"
            inputMode="decimal"
            style={{ width: 140 }}
          />
          <input
            value={form.threshold_pct}
            onChange={(e) => setForm({ ...form, threshold_pct: e.target.value })}
            placeholder="Threshold % (opt)"
            className="input"
            inputMode="decimal"
            style={{ width: 160 }}
          />
          <input
            value={form.expires_at}
            onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
            placeholder="Expiry ISO (opt)"
            className="input"
            style={{ width: 200 }}
          />
          <button onClick={() => create.mutate()} disabled={create.isPending}>{create.isPending ? "Creating…" : "Create"}</button>
        </div>
        <div className="small" style={{ marginTop: 6, opacity: 0.75 }}>
          Tip: Use threshold % to account for minor overshoots; leave blank to default to exact level.
        </div>
      </section>

      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontWeight: 600 }}>Active Alerts</div>
          {list.isFetching ? <div className="small" style={{ opacity: 0.75 }}>Refreshing…</div> : null}
        </div>
        {list.isPending && <div className="small">Loading alerts…</div>}
        {list.error && <div className="small" style={{ color: "#ffb4b4" }}>Error: {(list.error as Error).message}</div>}
        {list.data?.items?.length ? (
          <table className="table" style={{ marginTop: 8 }}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Symbol</th>
                <th>Timeframe</th>
                <th>Type</th>
                <th>Level</th>
                <th>Thresh %</th>
                <th>Expires</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {list.data.items.map((a) => (
                <tr key={a.id}>
                  <td>{a.id}</td>
                  <td>{a.symbol}</td>
                  <td>{a.timeframe ?? "—"}</td>
                  <td>{a.condition?.type ?? "—"}</td>
                  <td>{a.condition?.value ?? "—"}</td>
                  <td>{a.condition?.threshold_pct ?? "—"}</td>
                  <td>{a.expires_at ?? "—"}</td>
                  <td>{a.created_at ?? "—"}</td>
                  <td><button className="secondary" onClick={() => del.mutate(a.id)} disabled={del.isPending}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : list.isSuccess ? (
          <div className="small" style={{ marginTop: 8 }}>No alerts yet.</div>
        ) : null}
      </section>

      <div className="small" style={{ marginTop: 8, opacity: 0.75 }}>
        Discord forwarding can be enabled in Settings when a webhook is configured and types are allowed.
      </div>
    </main>
  );
}
