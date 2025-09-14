'use client';

import { useQuery } from '@tanstack/react-query';
import { apiGet, apiPost } from '@/src/lib/api';
import { z } from 'zod';

const WatchlistZ = z.object({
  ok: z.boolean().optional(),
  symbols: z.array(z.string()).default([]),
});

const OptionsPickRespZ = z.object({
  ok: z.boolean().optional(),
  env: z.string().optional(),
  note: z.string().optional(),
  count_considered: z.number().optional(),
  picks: z.array(z.object({
    symbol: z.string(),
    expiration: z.string(),
    strike: z.number(),
    option_type: z.enum(['call','put']).optional(),
    delta: z.number().nullable().optional(),
    bid: z.number().nullable().optional(),
    ask: z.number().nullable().optional(),
    mark: z.number().nullable().optional(),
    spread_pct: z.number().nullable().optional(),
    open_interest: z.number().nullable().optional(),
    volume: z.number().nullable().optional(),
    score: z.number().nullable().optional(),
    dte: z.number().nullable().optional(),
  })).default([]),
});

export default function ClientDashboard() {
  const wl = useQuery({
    queryKey: ['watchlist'],
  queryFn: async () => WatchlistZ.parse(await apiGet('/api/v1/screener/watchlist/get')),
  });

  const picks = useQuery({
    queryKey: ['picks','SPY','long_call','intra'],
    queryFn: async () =>
      OptionsPickRespZ.parse(
        await apiPost('/api/v1/options/pick', { symbol: 'SPY', side: 'long_call', horizon: 'intra', n: 5 })
      ),
  });

  return (
    <main style={{maxWidth:960, margin:'32px auto', padding:'0 16px', lineHeight:1.45}}>
      <h1>Trading Assistant Dashboard</h1>
      <p style={{opacity:.75}}>API: {process.env.NEXT_PUBLIC_API_BASE}</p>

      <section style={{marginTop:24}}>
        <h2>Watchlist</h2>
        {wl.isLoading && <div>Loading watchlist…</div>}
        {wl.error && <div style={{color:'crimson'}}>Watchlist error: {(wl.error as Error).message}</div>}
        {wl.data?.symbols?.length ? (
          <ul>{wl.data.symbols.map(s => <li key={s}>{s}</li>)}</ul>
        ) : <div>No symbols.</div>}
      </section>

      <section style={{marginTop:24}}>
        <h2>SPY Picks (long_call · intra)</h2>
        {picks.isLoading && <div>Loading picks…</div>}
        {picks.error && <div style={{color:'crimson'}}>Picks error: {(picks.error as Error).message}</div>}
        {picks.data?.picks?.length ? (
          <ol>
            {picks.data.picks.slice(0,5).map(p => (
              <li key={p.symbol}>
                {p.symbol} — {p.option_type?.toUpperCase?.()} — {p.strike} @ {p.expiration}
                {' '}mark: {p.mark ?? '—'} (bid {p.bid ?? '—'} / ask {p.ask ?? '—'})
              </li>
            ))}
          </ol>
        ) : <div>No picks available.</div>}
        {picks.data?.note && <div style={{opacity:.7, marginTop:8}}>note: {picks.data.note}</div>}
      </section>
    </main>
  );
}
