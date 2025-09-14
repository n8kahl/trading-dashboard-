"use client";

import { useEffect, useRef } from "react";
import { createChart, ISeriesApi, UTCTimestamp } from "lightweight-charts";

type Bar = { t: number; o: number; h: number; l: number; c: number; v: number };
type Props = { symbol: string };

function toLw(bar: Bar) {
  return { time: (bar.t/1000) as UTCTimestamp, open: bar.o, high: bar.h, low: bar.l, close: bar.c };
}

export default function LiveChart({ symbol }: Props) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, { width: ref.current.clientWidth, height: 280, layout: { textColor: '#ddd', background: { type: 'solid', color: '#0b0b0b' }}, grid: { vertLines: { color: '#111' }, horzLines: { color: '#111' }}});
    const candle = chart.addCandlestickSeries({});
    const ema9: ISeriesApi<'Line'> = chart.addLineSeries({ color: '#22d3ee', lineWidth: 1 });
    const ema20: ISeriesApi<'Line'> = chart.addLineSeries({ color: '#a3e635', lineWidth: 1 });

    let cleanup = () => { chart.remove(); };

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
      } catch {}
    })();

    const onResize = () => {
      if (ref.current) chart.applyOptions({ width: ref.current.clientWidth });
    };
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); cleanup(); };
  }, [symbol]);

  return (
    <section className="card">
      <div style={{fontWeight:600, marginBottom:6}}>Live Chart — {symbol}</div>
      <div ref={ref} />
    </section>
  );
}

