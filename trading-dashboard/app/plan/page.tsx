"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiPost } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function Page() {
  const [symbol, setSymbol] = useState("AAPL");
  const [side, setSide] = useState("long");
  const [entry, setEntry] = useState<number | string>("");
  const [stop, setStop] = useState<number | string>("");

  const m = useMutation({
    mutationFn: () => apiPost("/api/v1/plan/validate", {
      symbol, side, entry: Number(entry), stop: Number(stop)
    })
  });

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">Plan Validate</h1>
      <div className="flex gap-2">
        <Input className="w-28" value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} />
        <Input className="w-28" value={side} onChange={e => setSide(e.target.value)} />
        <Input className="w-28" placeholder="Entry" value={entry} onChange={e => setEntry(e.target.value)} />
        <Input className="w-28" placeholder="Stop" value={stop} onChange={e => setStop(e.target.value)} />
        <Button onClick={() => m.mutate()} disabled={m.isPending}>Validate</Button>
      </div>
      <pre className="text-xs bg-muted p-3 rounded">{m.isSuccess ? JSON.stringify(m.data, null, 2) : m.isPending ? "..." : ""}</pre>
    </div>
  );
}
