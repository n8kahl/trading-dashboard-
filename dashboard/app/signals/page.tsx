"use client";
import { useEffect, useState } from "react";
import { apiGet } from "@/src/lib/api";

export default function SignalsPage() {
  const [signals, setSignals] = useState<any[]>([]);
  useEffect(() => {
    const fetchSignals = async () => {
      try {
        const r = await apiGet("/api/v1/admin/signals");
        setSignals(r.items || []);
      } catch {
        /* ignore */
      }
    };
    fetchSignals();
    const t = setInterval(fetchSignals, 20000);
    return () => clearInterval(t);
  }, []);

  return (
    <main className="container">
      <h1>Signals</h1>
      <ul>
        {signals.map((s: any, i) => (
          <li key={i}>{JSON.stringify(s)}</li>
        ))}
      </ul>
    </main>
  );
}
