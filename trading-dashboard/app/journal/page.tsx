"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/src/lib/api";
import { useState } from "react";

type Entry = { id: number; symbol: string; r?: number; side?: string; notes?: string; created_at: string };

export default function JournalPage() {
  const qc = useQueryClient();
  const [symbol, setSymbol] = useState("");
  const [notes, setNotes] = useState("");

  const list = useQuery({
    queryKey: ["journal"],
    queryFn: async (): Promise<Entry[]> => {
      const res = await apiGet("/api/v1/journal/list?limit=200");
      return res?.items ?? [];
    },
  });

  const create = useMutation({
    mutationFn: async () => apiPost("/api/v1/journal/create", { symbol, notes }),
    onSuccess: () => { setSymbol(""); setNotes(""); qc.invalidateQueries({queryKey:["journal"]}); },
  });

  return (
    <main className="container">
      <h1 style={{marginBottom:12}}>Journal</h1>
      <section className="card" style={{marginBottom:12}}>
        <div style={{display:"flex", gap:8}}>
          <input className="input" placeholder="Symbol" value={symbol} onChange={e=>setSymbol(e.target.value.toUpperCase())} />
          <input className="input" placeholder="Notes" value={notes} onChange={e=>setNotes(e.target.value)} />
          <button onClick={()=> create.mutate()} disabled={!symbol || !notes}>Add</button>
        </div>
      </section>
      <section className="card">
        <table className="table">
          <thead><tr><th>Time</th><th>Symbol</th><th>Side</th><th>R</th><th>Notes</th></tr></thead>
          <tbody>
            {(list.data ?? []).map(e => (
              <tr key={e.id}><td>{new Date(e.created_at).toLocaleString()}</td><td>{e.symbol}</td><td>{e.side ?? '—'}</td><td>{e.r ?? '—'}</td><td>{e.notes ?? ''}</td></tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}

