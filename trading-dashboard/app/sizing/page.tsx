"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiPost } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function Page() {
  const [symbol, setSymbol] = useState("AAPL");
  const [side, setSide] = useState("long");
  const [riskR, setRiskR] = useState<number | string>("1");

  const m = useMutation({
    mutationFn: () => apiPost("/api/v1/sizing/suggest", {
      symbol, side, risk_R: Number(riskR)
    })
  });

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">Sizing Suggest</h1>
      <div className="flex gap-2">
        <Input className="w-28" value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} />
        <Input className="w-28" value={side} onChange={e => setSide(e.target.value)} />
        <Input className="w-28" value={riskR} onChange={e => setRiskR(e.target.value)} />
        <Button onClick={() => m.mutate()} disabled={m.isPending}>Suggest</Button>
      </div>
      <pre className="text-xs bg-muted p-3 rounded">{m.isSuccess ? JSON.stringify(m.data, null, 2) : m.isPending ? "..." : ""}</pre>
    </div>
  );
}
