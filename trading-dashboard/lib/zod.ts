import { z } from "zod";

export const HealthZ = z.object({ ok: z.boolean().optional(), status: z.string().optional() });
export const ReadyZ  = z.object({ ok: z.boolean().optional(), ready: z.boolean() });

export const WatchlistZ = z.object({
  ok: z.boolean(),
  symbols: z.array(z.string())
});

export const OptionsPickItemZ = z.object({
  symbol: z.string(),
  expiration: z.string().optional(),
  strike: z.number().optional(),
  option_type: z.string().optional(),
  delta: z.number().nullable().optional(),
  bid: z.number().nullable().optional(),
  ask: z.number().nullable().optional(),
  mark: z.number().nullable().optional(),
  spread_pct: z.number().nullable().optional(),
  open_interest: z.number().nullable().optional(),
  volume: z.number().nullable().optional(),
  score: z.number().nullable().optional(),
  dte: z.number().nullable().optional()
});

export const OptionsPicksZ = z.object({
  ok: z.boolean(),
  env: z.string().optional(),
  note: z.string().optional(),
  count_considered: z.number().optional(),
  picks: z.array(OptionsPickItemZ).default([])
});
