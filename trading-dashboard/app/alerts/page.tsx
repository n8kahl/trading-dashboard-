"use client";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useState } from "react";

export default function Page() {
  const list = useQuery({ queryKey: ["alerts"], queryFn: () => apiGet("/api/v1/alerts/list") });
  const [symbol, setSymbol] = useState("AAPL");
  const [level, setLevel] = useState("230");
  const create = useMutation({
    mutationFn: () => apiPost("/api/v1/alerts/set", { symbol, level: Number(level) })
  });

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">Alerts</h1>
      <div className="flex gap-2">
        <Input className="w-28" value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())}/>
        <Input className="w-28" value={level} onChange={e => setLevel(e.target.value)}/>
        <Button onClick={() => create.mutate()}>Create</Button>
      </div>
      <pre className="text-xs bg-muted p-3 rounded">{JSON.stringify(list.data, null, 2)}</pre>
    </div>
  );
}
