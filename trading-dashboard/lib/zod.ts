import { z } from 'zod';

export const HealthSchema = z.object({ status: z.string() });
export const ReadySchema = z.object({ status: z.string() });

export const WatchlistItemSchema = z.object({
  symbol: z.string(),
  last: z.number().nullish(),
});
export const WatchlistSchema = z.array(WatchlistItemSchema);

export const RankedPickSchema = z.object({
  symbol: z.string(),
  score: z.number(),
});
export const RankedPicksSchema = z.array(RankedPickSchema);

export const OptionContractSchema = z.object({
  symbol: z.string(),
  expiry: z.string(),
  strike: z.number(),
  type: z.string(),
  delta: z.number().optional(),
  gamma: z.number().optional(),
  theta: z.number().optional(),
  vega: z.number().optional(),
});
export const OptionContractsSchema = z.array(OptionContractSchema);

export const PlanResponseSchema = z.object({
  targets: z.array(z.number()),
  per_unit_risk: z.number(),
  notes: z.string().optional(),
});

export const SizingResponseSchema = z.object({
  qty: z.number(),
  expected_R: z.number(),
});

export const AlertSchema = z.object({ id: z.string(), symbol: z.string(), price: z.number() });
export const AlertsSchema = z.array(AlertSchema);

export const SignalSchema = z.object({ id: z.string(), symbol: z.string(), strength: z.number() });
export const SignalsSchema = z.array(SignalSchema);

export const PositionSchema = z.object({ symbol: z.string(), qty: z.number(), basis: z.number() });
export const PositionsSchema = z.array(PositionSchema);
