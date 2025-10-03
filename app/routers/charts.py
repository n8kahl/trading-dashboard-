from __future__ import annotations

from fastapi import APIRouter, Query, Response
from html import escape

router = APIRouter(prefix="/charts", tags=["charts"])


@router.get("/proposal")
async def chart_proposal(
    symbol: str,
    interval: str = Query("1m"),
    lookback: int = 390,
    overlays: str = Query("vwap,ema20,ema50,pivots"),
    entry: float | None = None,
    sl: float | None = None,
    tp1: float | None = None,
    tp2: float | None = None,
    entry_time: int | None = None,
    direction: str = Query("long"),
    confluence: str = Query(""),
    em_abs: float | None = None,
    em_rel: float | None = None,
    anchor: str = Query("entry"),
    hit_tp1: float | None = None,
    hit_tp2: float | None = None,
    theme: str = Query("dark"),
    plan: str = Query(""),
    state: str = Query(""),
    width: int = 1200,
    height: int = 650,
) -> Response:
    sym = escape((symbol or "").upper())
    interval = escape(interval)
    overlays = escape(overlays)
    theme = "dark" if (theme or "").lower() == "dark" else "light"
    width = max(640, min(1920, int(width)))
    height = max(360, min(1080, int(height)))

    # Build HTML with a template to avoid f-string brace conflicts
    from string import Template
    bg = '#0d1117' if theme == 'dark' else '#ffffff'
    text = '#c9d1d9' if theme == 'dark' else '#111'
    grid = '#161b22' if theme == 'dark' else '#eee'
    border = '#30363d' if theme == 'dark' else '#ddd'
    badge_bg = '#161b22' if theme == 'dark' else '#f8f8f8'
    dir_js = escape((direction or '').lower())
    tpl = Template("""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>${SYM} – Proposal</title>
  <script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    html, body { margin: 0; padding: 0; background: ${BG}; height: 100%; width: 100%; }
    #wrap { width: min(100vw, ${WIDTH}px); height: min(100vh, ${HEIGHT}px); margin: 0 auto; }
    #chart { width: 100%; height: 100%; display: block; }
    .legend { position:absolute; left:8px; top:8px; color:${TEXT}; font: 12px/1.4 -apple-system,Segoe UI,Arial; background: transparent; }
    .symbol { position:absolute; left:8px; top:26px; color:${TEXT}; font: 14px/1.4 -apple-system,Segoe UI,Arial; opacity: 0.9; }
    .panel { position:absolute; left:8px; bottom:8px; max-width:min(460px, 95vw); padding:10px 12px; border-radius:8px; background:${BADGE_BG}; color:${TEXT}; border:1px solid ${BORDER}; font: 12px/1.5 -apple-system,Segoe UI,Arial; }
    .panel h4 { margin: 0 0 6px 0; font-size: 13px; }
    .panel ul { margin: 6px 0 0; padding-left: 18px; }
    .panel li { margin: 3px 0; }
    .badges { position:absolute; right:8px; top:8px; display:flex; gap:6px; flex-wrap:wrap; max-width:50%; }
    .badge { padding:2px 6px; border-radius:10px; font-size:11px; border:1px solid ${BORDER}; color:${TEXT}; background:${BADGE_BG}; }
    .tools { position:absolute; right:8px; top:44px; display:flex; align-items:center; gap:6px; background:${BADGE_BG}; border:1px solid ${BORDER}; border-radius:8px; padding:6px 8px; }
    .tools label { font-size:11px; color:${TEXT}; margin-right:2px; }
    .tools select, .tools button { font-size:11px; padding:3px 6px; border-radius:6px; border:1px solid ${BORDER}; background:${BG}; color:${TEXT}; }
  </style>
</head>
<body>
    <div id="wrap">
      <div id="chart"></div>
      <div class="legend" id="legend">${SYM} ${INTERVAL} · overlays: ${OVERLAYS}</div>
      <div class="symbol" id="symbolTag">${SYM}</div>
      <div class="badges" id="badges"></div>
      <div class="tools" id="tools">
      <label for="selInterval">Timeframe</label>
      <select id="selInterval">
        <option value="1m">1m</option>
        <option value="5m">5m</option>
        <option value="1d">1d</option>
      </select>
      <button id="btnFit">Fit</button>
      <button id="btnRefresh">Refresh</button>
    </div>
    <div class="panel" id="planPanel" style="display:none"></div>
  </div>
  <script>
    const params = new URLSearchParams({ symbol: '${SYM}', interval: '${INTERVAL}', lookback: '${LOOKBACK}' });
    const apiBase = (window.location && window.location.origin) || '';
    const url = apiBase + '/api/v1/market/bars?' + params.toString();
    const levelsUrl = apiBase + '/api/v1/market/levels?symbol=${SYM}';
    const theme = '${THEME}';
    const dir = '${DIR}' === 'long' ? 'long' : 'short';
    const want = (name) => '${OVERLAYS}'.split(',').map(s => s.trim().toLowerCase()).includes(name);
    const confluence = '${CONFLUENCE}'.split(',').map(s => s.trim()).filter(Boolean);
    const emAbs = ${EM_ABS};
    const emRel = ${EM_REL};
    const anchor = '${ANCHOR}'.toLowerCase() === 'last' ? 'last' : 'entry';
    const hit1 = ${HIT1};
    const hit2 = ${HIT2};
    const planRaw = `${PLAN}`;
    const prettyOverlays = () => '${OVERLAYS}'.split(',').map(s => s.trim().toLowerCase()).map(s => {
      if (s === 'vwap') return 'VWAP';
      if (s.startsWith('ema')) return s.toUpperCase();
      if (s === 'pivots' || s === 'levels') return 'Pivots';
      return s;
    }).join(' + ');

    function ema(values, period) {
      const k = 2/(period+1);
      let e = values[0];
      const out = [];
      for (let i=0;i<values.length;i++) {
        e = values[i]*k + e*(1-k);
        out.push(e);
      }
      return out;
    }

    function computeVWAP(bars) {
      let cumPV = 0; let cumV = 0; const out = [];
      for (const b of bars) {
        const tp = (b.h + b.l + b.c)/3.0;
        const v = b.v || 0;
        cumPV += tp * v;
        cumV += v;
        const vwap = cumV>0 ? (cumPV/cumV) : tp;
        out.push({ time: Math.floor(b.t/1000), value: vwap });
      }
      return out;
    }

    let chart = null;
    async function main() {
      const el = document.getElementById('chart');
      if (typeof LightweightCharts === 'undefined') {
        el.innerHTML = '<div style="color:#f00;padding:16px">Chart library failed to load. Please allow CDN scripts or try again.</div>';
        return;
      }
      chart = LightweightCharts.createChart(el, {
        autoSize: true,
        layout: { background: { type: 'Solid', color: '${BG}' }, textColor: '${TEXT}' },
        rightPriceScale: { borderVisible: false },
        timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
        grid: { vertLines: { color: '${GRID}' }, horzLines: { color: '${GRID}' } },
        crosshair: { mode: 1 }
      });

      const candleSeries = chart.addCandlestickSeries({
        upColor: '#22c55e', downColor: '#ef4444', borderVisible: false, wickUpColor: '#22c55e', wickDownColor: '#ef4444'
      });

      async function fetchBars(intv) {
        const p = new URLSearchParams({ symbol: '${SYM}', interval: intv, lookback: '${LOOKBACK}' });
        const u = apiBase + '/api/v1/market/bars?' + p.toString();
        try {
          const r = await fetch(u);
          const jj = await r.json();
          if (jj && jj.ok && Array.isArray(jj.bars) && jj.bars.length) return jj.bars;
        } catch (e) {}
        return [];
      }
      let bars = await fetchBars('${INTERVAL}');
      if (!bars.length && '${INTERVAL}' === '1m') bars = await fetchBars('5m');
      if (!bars.length) bars = await fetchBars('1d');
      if (!bars.length) {
        el.innerHTML = '<div style="color:${TEXT};padding:16px">No bars available. Try later or a different interval.</div>';
        return;
      }
      const data = bars.map(b => ({ time: Math.floor(b.t/1000), open: b.o, high: b.h, low: b.l, close: b.c }));
      candleSeries.setData(data);
      // Fit content to visible range for readability
      try { chart.timeScale().fitContent(); } catch (e) {}

      if (want('vwap')) {
        const vwapSeries = chart.addLineSeries({ color: '#60a5fa', lineWidth: 2 });
        vwapSeries.setData(computeVWAP(bars));
      }

      const closes = bars.map(b => b.c);
      function overlayEMA(period, color) {
        const arr = ema(closes, period);
        const line = chart.addLineSeries({ color, lineWidth: 1 });
        const arrData = bars.map((b, i) => ({ time: Math.floor(b.t/1000), value: arr[i] }));
        line.setData(arrData);
      }
      if (want('ema20')) overlayEMA(20, '#f59e0b');
      if (want('ema50')) overlayEMA(50, '#a855f7');

      const p = (x) => (x===null || x===undefined || isNaN(x)) ? null : Number(x);
      const entry = p(${ENTRY});
      const sl = p(${SL});
      const tp1 = p(${TP1});
      const tp2 = p(${TP2});
      const entryTime = ${ENTRY_TIME};
      function priceLine(value, title, color) {
        if (value===null) return;
        candleSeries.createPriceLine({ price: value, color, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title });
      }
      priceLine(entry, 'Entry', '#16a34a');
      priceLine(sl, 'Stop Loss', '#ef4444');
      priceLine(tp1, 'Target 1', '#60a5fa');
      priceLine(tp2, 'Target 2', '#60a5fa');

      if (entryTime) {
        const marker = {
          time: Math.floor(entryTime/1000),
          position: (dir === 'long' ? 'belowBar' : 'aboveBar'),
          color: (dir === 'long' ? '#16a34a' : '#ef4444'),
          shape: (dir === 'long' ? 'arrowUp' : 'arrowDown'),
          text: 'Entry'
        };
        candleSeries.setMarkers([marker]);
      }

      if (emAbs !== null && !isNaN(emAbs)) {
        let base = null;
        if (anchor === 'entry' && entry !== null) base = entry;
        if ((base === null || base === undefined) && data && data.length) {
          base = data[data.length - 1].close;
        }
        if (base !== null && base !== undefined) {
          const hi = Number(base) + Number(emAbs);
          const lo = Number(base) - Number(emAbs);
          priceLine(hi, 'EM Upper', '#7c3aed');
          priceLine(lo, 'EM Lower', '#7c3aed');
      }
    }

      if (want('pivots') || want('levels')) {
        try {
          const levResp = await fetch(levelsUrl);
          const L = await levResp.json();
          if (L.ok && L.pivots) {
            const colors = { P: '#999', R1: '#f59e0b', R2: '#f59e0b', S1: '#3b82f6', S2: '#3b82f6' };
            const labels = { P: 'Pivot (P)', R1: 'Resistance 1', R2: 'Resistance 2', S1: 'Support 1', S2: 'Support 2' };
            for (const k of Object.keys(L.pivots)) {
              const val = L.pivots[k];
              if (val!==null && val!==undefined) {
                candleSeries.createPriceLine({ price: Number(val), color: colors[k]||'#888', lineWidth: 1, lineStyle: 0, axisLabelVisible: true, title: labels[k] || k });
              }
            }
          }
        } catch (e) {}
      }

      const badges = document.getElementById('badges');
      const addBadge = (label) => {
        const b = document.createElement('span');
        b.className = 'badge';
        b.textContent = label;
        badges.appendChild(b);
      };
      if (confluence && confluence.length) {
        for (const name of confluence) addBadge(name);
      }
      if (emAbs !== null && !isNaN(emAbs)) addBadge('EM ± ' + Number(emAbs).toFixed(2));
      if (emRel !== null && !isNaN(emRel)) addBadge('EM ' + (Number(emRel)*100).toFixed(1) + '%');
      if ('${STATE}'.length) addBadge('${STATE}');
      const pctFmt = (x) => (x==null || isNaN(x)) ? null : (x > 1.5 ? Number(x) : Number(x)*100);
      const h1 = pctFmt(hit1); const h2 = pctFmt(hit2);
      if (h1 !== null) addBadge('P(TP1) ~ ' + h1.toFixed(0) + '%');
      if (h2 !== null) addBadge('P(TP2) ~ ' + h2.toFixed(0) + '%');
      // Make legend text more intuitive
      try { document.getElementById('legend').textContent = '${SYM} ${INTERVAL} • ' + prettyOverlays(); } catch (e) {}

      // Tools: initialize states and handlers (Timeframe, Fit, Refresh)
      const on = (id, fn) => { const el=document.getElementById(id); if (el) el.onclick = fn; };
      const iv = document.getElementById('selInterval'); if (iv) iv.value='${INTERVAL}';
      on('btnRefresh', ()=>location.reload());
      on('btnFit', ()=>{ try { chart.timeScale().fitContent(); } catch(e){} });
      if (iv) iv.onchange = () => {
        const params = new URLSearchParams(location.search);
        const itv = iv.value;
        params.set('interval', itv);
        if (!params.get('lookback')) {
          params.set('lookback', itv==='1d'? '180' : itv==='5m'? '300' : '390');
        }
        location.search = params.toString();
      };

      // Strategy plan panel for beginners (auto text if not provided)
      const panel = document.getElementById('planPanel');
      if (panel) {
        const items = (planRaw||'').split('|').map(s=>s.trim()).filter(Boolean);
        const last = data[data.length-1].close;
        const vwapArr = computeVWAP(bars); const vwapLast = (vwapArr.slice(-1)[0]||{}).value;
        const state = (vwapLast!=null && !isNaN(vwapLast)) ? (last>=vwapLast ? 'Price is above VWAP (bullish bias)' : 'Price is below VWAP (bearish bias)') : 'VWAP unavailable';
        let html = '<h4>Strategy Plan</h4>';
        html += '<div>'+state+'. Use VWAP and Pivots as context (P/R/S lines).</div>';
        const list = items.length? items : (function(){
          const b=[];
          if (dir==='long') { b.push('Step 1 — Confirmation: wait for a clean break and 1–2 candles to hold above Entry.'); b.push('Step 2 — Entry: buy on a quick retest that holds (avoid chasing).'); }
          else { b.push('Step 1 — Confirmation: wait for a clean break and 1–2 candles to hold below Entry.'); b.push('Step 2 — Entry: short on a quick retest that fails (avoid chasing).'); }
          b.push('Risk — Stop Loss at the red line; exit quickly if hit.');
          b.push('Targets — Take partial at Target 1 (~0.25×EM); consider runner to Target 2 (~0.50×EM).');
          if (h1!=null) b.push('Approx P(Target 1) ~ '+h1.toFixed(0)+'% (touch probability).');
          if (h2!=null) b.push('Approx P(Target 2) ~ '+h2.toFixed(0)+'% (touch probability).');
          b.push('Skip/Size Down — if spreads widen, quotes unstable, or liquidity is light.');
          return b;
        })();
        html += '<ul>' + list.map(s=>'<li>'+s.replace(/</g,'&lt;').replace(/>/g,'&gt;')+'</li>').join('') + '</ul>';
        panel.innerHTML = html; panel.style.display='block';
      }
    }
    (function bootstrap(){
      if (typeof LightweightCharts !== 'undefined') { main(); return; }
      try {
        const alt = 'https://cdn.jsdelivr.net/npm/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js';
        const s = document.createElement('script');
        s.src = alt; s.async = true; s.onload = () => main();
        s.onerror = () => { try { document.getElementById('chart').innerHTML = '<div style="color:#f00;padding:16px">Chart library failed to load from both CDNs.</div>'; } catch(e) {} };
        document.head.appendChild(s);
      } catch (e) { try { document.getElementById('chart').innerHTML = '<div style="color:#f00;padding:16px">Chart library failed to load. Please try again.</div>'; } catch(_) {} }
    })();
  </script>
</body>
</html>
""")
    html = tpl.substitute({
        'SYM': sym,
        'INTERVAL': interval,
        'LOOKBACK': str(lookback),
        'OVERLAYS': overlays,
        'THEME': theme,
        'DIR': dir_js,
        'CONFLUENCE': escape(confluence),
        'EM_ABS': 'null' if em_abs is None else str(em_abs),
        'EM_REL': 'null' if em_rel is None else str(em_rel),
        'ANCHOR': anchor,
        'HIT1': 'null' if hit_tp1 is None else str(hit_tp1),
        'HIT2': 'null' if hit_tp2 is None else str(hit_tp2),
        'BG': bg,
        'TEXT': text,
        'GRID': grid,
        'BORDER': border,
        'BADGE_BG': badge_bg,
        'WIDTH': str(width),
        'HEIGHT': str(height),
        'PLAN': escape(plan),
        'ENTRY': 'null' if entry is None else str(entry),
        'SL': 'null' if sl is None else str(sl),
        'TP1': 'null' if tp1 is None else str(tp1),
        'TP2': 'null' if tp2 is None else str(tp2),
        'ENTRY_TIME': 'null' if entry_time is None else str(int(entry_time)),
    })
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/tradingview")
async def tradingview_chart(
    symbol: str,
    interval: str = Query("15"),
    entry: float | None = None,
    sl: float | None = None,
    tp1: float | None = None,
    tp2: float | None = None,
    theme: str = Query("dark"),
    note: str = Query(""),
) -> Response:
    sym = (symbol or "").upper().strip()
    if not sym:
        return Response(content="Symbol required", media_type="text/plain", status_code=400)

    def _num(val: float | None) -> str:
        if val is None:
            return "null"
        try:
            return repr(round(float(val), 4))
        except Exception:
            return "null"

    theme_key = "dark" if (theme or "").lower() == "dark" else "light"
    note_html = escape(note)
    bg_overlay = "#111827cc" if theme_key == "dark" else "#ffffffd9"
    text_color = "#f9fafb" if theme_key == "dark" else "#111827"
    html = f"""<!doctype html>
<html>
  <head>
    <meta charset='utf-8'/>
    <meta name='viewport' content='width=device-width, initial-scale=1'/>
    <title>{sym} Play – TradingView</title>
    <script type='text/javascript' src='https://s3.tradingview.com/tv.js'></script>
    <style>
      html, body {{ margin:0; padding:0; height:100%; background:{'#0d1117' if theme_key == 'dark' else '#ffffff'}; }}
      #tv_chart {{ width:100%; height:100%; position:absolute; inset:0; }}
      #note {{ position:absolute; left:12px; top:12px; background:{bg_overlay}; color:{text_color}; padding:10px 12px; border-radius:8px; font:13px/1.45 -apple-system,Segoe UI,Roboto; max-width:min(360px, 90vw); box-shadow:0 8px 16px rgba(15,23,42,0.3); }}
    </style>
  </head>
  <body>
    <div id='tv_chart'></div>
    {"" if not note_html else f"<div id='note'>{note_html}</div>"}
    <script>
      const widget = new TradingView.widget({{
        symbol: "{escape(sym)}",
        interval: "{escape(interval)}",
        timezone: "exchange",
        theme: "{theme_key}",
        style: "1",
        locale: "en",
        container_id: "tv_chart",
        autosize: true,
        hide_side_toolbar: false,
        hide_legend: false,
        save_image: false,
        allow_symbol_change: true,
        studies: [],
      }});

      widget.onChartReady(function() {{
        const chart = widget.activeChart();
        const lines = [
          {{ price: {_num(entry)}, text: 'Entry', color: '#22c55e', lineWidth: 2 }},
          {{ price: {_num(sl)}, text: 'Stop', color: '#ef4444', lineWidth: 2 }},
          {{ price: {_num(tp1)}, text: 'TP1', color: '#2563eb', lineWidth: 2 }},
          {{ price: {_num(tp2)}, text: 'TP2', color: '#2563eb', lineWidth: 2, lineStyle: 2 }}
        ];
        lines.forEach(cfg => {{
          if (cfg.price === null) return;
          const line = chart.createHorizontalLine({{
            price: cfg.price,
            text: cfg.text,
            color: cfg.color,
            lineWidth: cfg.lineWidth || 1,
            lineStyle: cfg.lineStyle || 0,
          }});
          if (line && cfg.text) {{
            line.setText(cfg.text);
          }}
        }});
      }});
    </script>
  </body>
</html>"""
    return Response(content=html, media_type="text/html; charset=utf-8")
