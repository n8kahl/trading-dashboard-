"use client";
import { useOrders } from "@/src/lib/store";
import { apiPost } from "@/src/lib/api";
import { useState } from "react";

export default function OrdersPage() {
  const orders = useOrders();
  const [symbol, setSymbol] = useState("SPY");

  const submit = async () => {
    await apiPost("/api/v1/broker/orders/submit", {
      symbol,
      side: "buy",
      qty: 1,
      order_type: "market",
    });
  };

  const cancel = async (id: string) => {
    await apiPost("/api/v1/broker/orders/cancel", { order_id: id });
  };

  return (
    <main className="container">
      <h1>Orders</h1>
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <input value={symbol} onChange={(e) => setSymbol(e.target.value)} className="input" />
        <button onClick={submit}>Paper Trade</button>
      </div>
      <ul>
        {orders.map((o: any) => (
          <li key={o.id}>
            {o.symbol} – {o.status}
            {o.id && (
              <button style={{ marginLeft: 8 }} onClick={() => cancel(o.id)}>
                Cancel
              </button>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
