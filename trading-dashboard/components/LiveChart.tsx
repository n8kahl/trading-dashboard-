"use client";

import { useEffect, useRef } from "react";
import { createChart, ISeriesApi, UTCTimestamp } from "lightweight-charts";
import { usePrices } from "@/src/lib/store";

type Bar = { t: number; o: number; h: number; l: number; c: number; v: number };
type Levels = { entry?: number; stop?: number; tp1?: number; tp2?: number };
type Props = { symbol: string; levels?: Levels };

function toLw(bar: Bar) {
  return { time: (bar.t/1000) as UTCTimestamp, open: bar.o, high: bar.h, low: bar.l, close: bar.c };
}

export default function LiveChart({ symbol, levels }: Props) {
  const ref = useRef<HTMLDivElement | null>(null);
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const levelLinesRef = useRef<any[]>([]);
  const vwapRef = useRef<ISeriesApi<'Line'> | null>(null);
  const priceLineRef = useRef<any | null>(null);
  const prices = usePrices();

  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, { width: ref.current.clientWidth, height: 280, layout: { textColor: '#ddd', background: { color: '#0b0b0b' }}, grid: { vertLines: { color: '#111' }, horzLines: { color: '#111' }}});
    const candle = chart.addCandlestickSeries({});
    candleRef.current = candle;
    const ema9: ISeriesApi<'Line'> = chart.addLineSeries({ color: '#22d3ee', lineWidth: 1 });
    const ema20: ISeriesApi<'Line'> = chart.addLineSeries({ color: '#a3e635', lineWidth: 1 });
    const vwap = chart.addLineSeries({ color: '#60a5fa', lineWidth: 1 });
    vwapRef.current = vwap;

    const cleanup = () => { chart.remove(); };

    (async () => {
      try {
        const path = `/market/bars?symbol=${encodeURIComponent(symbol)}&tf=1m`;
        const res = await fetch(`/api/proxy?path=${encodeURIComponent(path)}`, { cache: 'no-store' });
        const js = await res.json();
        const items: Bar[] = Array.isArray(js?.items) ? js.items : [];
        candle.setData(items.map(toLw));
        // compute EMAs on close
        const closes = items.map(b=> b.c);
        const ema = (w: number) => {
          const out: { time: UTCTimestamp, value: number }[] = [];
          const k = 2 / (w+1);
          let e = 0;
          for (let i=0;i<closes.length;i++) {
            const x = closes[i];
            if (i < w) {
              e += x;
              out.push({ time: (items[i].t/1000) as UTCTimestamp, value: NaN });
              if (i===w-1) e/=w;
              continue;
            }
            e = x*k + e*(1-k);
            out.push({ time: (items[i].t/1000) as UTCTimestamp, value: e });
          }
          return out;
        };
        ema9.setData(ema(9));
        ema20.setData(ema(20));
        // simple anchored VWAP across series
        const vwapData: { time: UTCTimestamp, value: number }[] = [];
        let pv = 0, vol = 0;
        for (const b of items) {
          const price = (b.o + b.h + b.l + b.c) / 4;
          pv += price * (b.v || 0);
          vol += (b.v || 0);
          const val = vol > 0 ? pv / vol : NaN;
          vwapData.push({ time: (b.t/1000) as UTCTimestamp, value: val });
        }
        vwap.setData(vwapData);
      } catch {}
    })();

    const onResize = () => {
      if (ref.current) chart.applyOptions({ width: ref.current.clientWidth });
    };
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); cleanup(); };
  }, [symbol]);

  // Update or render horizontal lines for levels
  useEffect(() => {
    // Clear existing level lines
    if (candleRef.current && levelLinesRef.current.length) {
      for (const line of levelLinesRef.current) {
        try { candleRef.current.removePriceLine(line); } catch {}
      }
      levelLinesRef.current = [];
    }
    if (!candleRef.current || !levels) return;
    const addLine = (price?: number, color?: string, title?: string) => {
      if (price === undefined || price === null || !Number.isFinite(price)) return;
      try {
        const line = candleRef.current!.createPriceLine({ price, color: color || '#94a3b8', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title });
        levelLinesRef.current.push(line);
      } catch {}
    };
    addLine(levels.entry, '#60a5fa', 'Entry');
    addLine(levels.stop, '#f87171', 'Stop');
    addLine(levels.tp1, '#a7f3d0', 'TP1');
    addLine(levels.tp2, '#34d399', 'TP2');
  }, [levels]);

  // Live price line updates
  useEffect(() => {
    const last = prices?.[symbol];
    if (!candleRef.current || last === undefined) return;
    try {
      if (priceLineRef.current) {
        candleRef.current.removePriceLine(priceLineRef.current);
        priceLineRef.current = null;
      }
      priceLineRef.current = candleRef.current.createPriceLine({ price: Number(last), color: '#f59e0b', lineWidth: 1, lineStyle: 0, axisLabelVisible: true, title: 'Last' });
    } catch {}
  }, [prices, symbol]);

  return (
    <section className="card">
      <div style={{fontWeight:600, marginBottom:6}}>Live Chart — {symbol}</div>
      <div ref={ref} />
    </section>
  );
}
