"use client";
import { useRisk } from "@/src/lib/store";

export default function RiskPage() {
  const risk = useRisk() || {};
  return (
    <main className="container">
      <h1>Risk</h1>
      <pre>{JSON.stringify(risk, null, 2)}</pre>
    </main>
  );
}
