"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiPost } from "@/lib/api";
import { OptionsPicksZ } from "@/lib/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function Page() {
  const [symbol, setSymbol] = useState("SPY");
  const [side, setSide] = useState("long_call");
  const [horizon, setHorizon] = useState("intra");
  const [n, setN] = useState(5);

  const m = useMutation({
    mutationFn: () => apiPost("/api/v1/options/pick", { symbol, side, horizon, n }, OptionsPicksZ)
  });

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Options Picker</h1>
      <div className="flex gap-2">
        <Input className="w-28" value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} placeholder="Symbol" />
        <Select value={side} onValueChange={setSide}>
          <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="long_call">long_call</SelectItem>
            <SelectItem value="long_put">long_put</SelectItem>
            <SelectItem value="short_call">short_call</SelectItem>
            <SelectItem value="short_put">short_put</SelectItem>
          </SelectContent>
        </Select>
        <Select value={horizon} onValueChange={setHorizon}>
          <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="intra">intra</SelectItem>
            <SelectItem value="day">day</SelectItem>
            <SelectItem value="week">week</SelectItem>
          </SelectContent>
        </Select>
        <Input type="number" className="w-20" value={n} onChange={e => setN(parseInt(e.target.value || "1"))} />
        <Button onClick={() => m.mutate()} disabled={m.isPending}>Fetch</Button>
      </div>
      <div>
        {m.isPending ? "Loading..." : m.data?.picks?.length ? (
          <ul className="text-sm space-y-1">
            {m.data.picks.slice(0, 20).map((p, i) => (
              <li key={i}>{p.symbol} · strike {p.strike ?? "?"} · mark {p.mark ?? "?"} · spread {(p.spread_pct ?? 0)*100}%</li>
            ))}
          </ul>
        ) : m.isSuccess ? "No picks." : null}
      </div>
    </div>
  );
}
