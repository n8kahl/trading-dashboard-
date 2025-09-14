from __future__ import annotations

from fastapi import APIRouter, Query, Response
from html import escape

router = APIRouter(prefix="/charts", tags=["charts"])


@router.get("/proposal")
async def chart_proposal(
    symbol: str,
    interval: str = Query("1m"),
    lookback: int = 390,
    overlays: str = Query("vwap,ema20,ema50"),
    entry: float | None = None,
    sl: float | None = None,
    tp1: float | None = None,
    tp2: float | None = None,
    theme: str = Query("dark"),
    width: int = 1200,
    height: int = 650,
) -> Response:
    sym = escape((symbol or "").upper())
    interval = escape(interval)
    overlays = escape(overlays)
    theme = "dark" if (theme or "").lower() == "dark" else "light"
    width = max(640, min(1920, int(width)))
    height = max(360, min(1080, int(height)))

    # Build HTML with Lightweight Charts pulling data from /api/v1/market/bars
    html = f"""
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>
  <title>{sym} – Proposal</title>
  <script src=\"https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js\"></script>
  <style>
    html, body {{ margin: 0; padding: 0; background: {('#0d1117' if theme=='dark' else '#ffffff')}; }}
    #wrap {{ width: {width}px; height: {height}px; margin: 0 auto; }}
    #chart {{ width: 100%; height: 100%; }}
    .legend {{ position:absolute; left:8px; top:8px; color:{('#c9d1d9' if theme=='dark' else '#111')}; font: 12px/1.4 -apple-system,Segoe UI,Arial; background: transparent; }}
  </style>
</head>
<body>
  <div id=\"wrap\">
    <div id=\"chart\"></div>
    <div class=\"legend\" id=\"legend\">{sym} {interval} · overlays: {overlays}</div>
  </div>
  <script>
    const params = new URLSearchParams({{ symbol: '{sym}', interval: '{interval}', lookback: '{lookback}' }});
    const url = `/api/v1/market/bars?` + params.toString();
    const theme = '{theme}';
    const want = (name) => '{overlays}'.split(',').map(s => s.trim().toLowerCase()).includes(name);

    function ema(values, period) {{
      const k = 2/(period+1);
      let e = values[0];
      const out = [];
      for (let i=0;i<values.length;i++) {{
        e = values[i]*k + e*(1-k);
        out.push(e);
      }}
      return out;
    }}

    function computeVWAP(bars) {{
      let cumPV = 0; let cumV = 0; const out = [];
      for (const b of bars) {{
        const tp = (b.h + b.l + b.c)/3.0;
        const v = b.v || 0;
        cumPV += tp * v;
        cumV += v;
        const vwap = cumV>0 ? (cumPV/cumV) : tp;
        out.push({{ time: Math.floor(b.t/1000), value: vwap }});
      }}
      return out;
    }}

    async function main() {{
      const el = document.getElementById('chart');
      const chart = LightweightCharts.createChart(el, {{
        autoSize: true,
        layout: {{ background: {{ type: 'Solid', color: '{('#0d1117' if theme=='dark' else '#ffffff')}' }}, textColor: '{('#c9d1d9' if theme=='dark' else '#111')}' }},
        rightPriceScale: {{ borderVisible: false }},
        timeScale: {{ borderVisible: false, timeVisible: true, secondsVisible: false }},
        grid: {{ vertLines: {{ color: '{('#161b22' if theme=='dark' else '#eee')}' }}, horzLines: {{ color: '{('#161b22' if theme=='dark' else '#eee')}' }} }},
        crosshair: {{ mode: 1 }}
      }});

      const candleSeries = chart.addCandlestickSeries({{
        upColor: '#22c55e', downColor: '#ef4444', borderVisible: false, wickUpColor: '#22c55e', wickDownColor: '#ef4444'
      }});

      const resp = await fetch(url);
      const j = await resp.json();
      if (!j.ok) {{
        el.innerHTML = '<div style="color:#f00;padding:16px">Failed to load bars: '+(j.error||'unknown')+'</div>';
        return;
      }}
      const bars = j.bars || [];
      const data = bars.map(b => ({{ time: Math.floor(b.t/1000), open: b.o, high: b.h, low: b.l, close: b.c }}));
      candleSeries.setData(data);

      if (want('vwap')) {{
        const vwapSeries = chart.addLineSeries({{ color: '#60a5fa', lineWidth: 2 }});
        vwapSeries.setData(computeVWAP(bars));
      }}

      const closes = bars.map(b => b.c);
      function overlayEMA(period, color) {{
        const arr = ema(closes, period);
        const line = chart.addLineSeries({{ color, lineWidth: 1 }});
        const arrData = bars.map((b, i) => ({{ time: Math.floor(b.t/1000), value: arr[i] }}));
        line.setData(arrData);
      }}
      if (want('ema20')) overlayEMA(20, '#f59e0b');
      if (want('ema50')) overlayEMA(50, '#a855f7');

      // Price lines for proposed trade
      const p = (x) => (x===null || x===undefined || isNaN(x)) ? null : Number(x);
      const entry = p({entry});
      const sl = p({sl});
      const tp1 = p({tp1});
      const tp2 = p({tp2});
      function priceLine(value, title, color) {{
        if (value===null) return;
        candleSeries.createPriceLine({{ price: value, color, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title }});
      }}
      priceLine(entry, 'ENTRY', '#16a34a');
      priceLine(sl, 'STOP', '#ef4444');
      priceLine(tp1, 'TP1', '#60a5fa');
      priceLine(tp2, 'TP2', '#60a5fa');
    }}
    main();
  </script>
</body>
</html>
    """
    return Response(content=html, media_type="text/html; charset=utf-8")

