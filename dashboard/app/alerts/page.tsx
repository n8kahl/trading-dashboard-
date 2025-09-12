"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/src/lib/api";

type AlertsList = { status: string; data: { alerts: Array<Record<string, any>> } };

export default function AlertsPage() {
  const qc = useQueryClient();
  const [form, setForm] = useState<{ symbol: string; price: string }>({ symbol: "", price: "" });

  const list = useQuery({
    queryKey: ["alerts"],
    queryFn: () => apiGet<AlertsList>("/api/v1/alerts/list"),
  });

  const create = useMutation({
    mutationFn: async () => {
      const priceNum = Number(form.price);
      if (!form.symbol || Number.isNaN(priceNum)) throw new Error("Enter symbol and numeric price");
      await apiPost("/api/v1/alerts/set", { symbol: form.symbol, level: priceNum, note: "dashboard" });
    },
    onSuccess: () => {
      setForm({ symbol: "", price: "" });
      qc.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  return (
    <main style={{ padding: 20, fontFamily: "system-ui, sans-serif" }}>
      <h1>Alerts</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <input
          value={form.symbol}
          onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })}
          placeholder="Symbol"
        />
        <input
          value={form.price}
          onChange={(e) => setForm({ ...form, price: e.target.value })}
          placeholder="Price"
          inputMode="decimal"
        />
        <button onClick={() => create.mutate()} disabled={create.isPending}>
          {create.isPending ? "Creating…" : "Create"}
        </button>
      </div>

      {list.isPending && <div>Loading alerts…</div>}
      {list.error && <div style={{ color: "crimson" }}>Error: {(list.error as Error).message}</div>}
      {list.data?.data?.alerts?.length ? (
        <ul>
          {list.data.data.alerts.map((a, i) => (
            <li key={i}><code>{JSON.stringify(a)}</code></li>
          ))}
        </ul>
      ) : list.isSuccess ? (
        <div>No alerts yet.</div>
      ) : null}
    </main>
  );
}
