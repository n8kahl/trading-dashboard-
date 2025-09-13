from app.services.ta import ema, atr_1m, atr_1m_pct, anchored_vwap, obv_slope_10, cvd_approx_20
from app.services.scoring_engine import score_vwap_bounce


def make_bars(vals):
  # vals: list of tuples (o,h,l,c,v)
  out = []
  t = 0
  for o,h,l,c,v in vals:
    out.append({"t": t, "o": o, "h": h, "l": l, "c": c, "v": v})
    t += 60_000
  return out


def test_ema_basic():
  xs = [1,2,3,4,5,6,7,8,9]
  e3 = ema(xs, 3)
  assert isinstance(e3, float)
  assert 7.0 < e3 < 9.0  # rough bound


def test_atr_and_pct():
  bars = make_bars([
    (10, 11, 9, 10, 1000),
    (10, 12, 10, 11, 1000),
    (11, 12, 11, 12, 1000),
    (12, 13, 11, 12.5, 1000),
    (12.5, 13, 12, 12.8, 1000),
    (12.8, 13.5, 12.5, 13.2, 1000),
    (13.2, 13.7, 12.9, 13.4, 1000),
    (13.4, 13.9, 13.0, 13.7, 1000),
    (13.7, 14.0, 13.4, 13.9, 1000),
    (13.9, 14.1, 13.8, 14.0, 1000),
    (14.0, 14.2, 13.9, 14.1, 1000),
    (14.1, 14.3, 13.8, 14.0, 1000),
    (14.0, 14.1, 13.7, 13.9, 1000),
    (13.9, 14.0, 13.6, 13.8, 1000),
    (13.8, 14.0, 13.7, 13.9, 1000),
  ])
  a = atr_1m(bars, period=14)
  assert a is not None and a > 0
  ap = atr_1m_pct(bars, period=14)
  assert ap is not None and 0 < ap < 10


def test_anchored_vwap_basic():
  # price rises with constant volume; anchored later should be higher
  bars = make_bars([
    (10, 10.5, 9.5, 10.2, 1000),
    (10.2, 10.7, 10.0, 10.5, 1000),
    (10.5, 11.0, 10.4, 10.9, 1000),
    (10.9, 11.3, 10.8, 11.1, 1000),
  ])
  v0 = anchored_vwap(bars, 0)
  v2 = anchored_vwap(bars, 2)
  assert v0 is not None and v2 is not None
  assert v2 > v0


def test_oflow_and_scoring_positive():
  # Up bars → positive OBV slope and CVD
  bars = make_bars([
    (10, 10.5, 9.8, 10.4, 1000),
    (10.4, 10.8, 10.2, 10.6, 1200),
    (10.6, 11.0, 10.5, 10.9, 1500),
    (10.9, 11.2, 10.8, 11.0, 1500),
    (11.0, 11.3, 10.9, 11.1, 1600),
    (11.1, 11.4, 10.9, 11.3, 1700),
    (11.3, 11.5, 11.0, 11.4, 1700),
    (11.4, 11.6, 11.2, 11.5, 1800),
    (11.5, 11.7, 11.3, 11.6, 1800),
    (11.6, 11.8, 11.4, 11.7, 1800),
    (11.7, 11.9, 11.5, 11.8, 1800),
  ])
  obv = obv_slope_10(bars)
  cvd = cvd_approx_20(bars)
  assert obv is not None and obv > 0
  assert cvd is not None and cvd > 0

  # Scoring context with positive confluence
  price = bars[-1]["c"]
  vwap = (bars[-1]["c"] + bars[-1]["o"]) / 2  # rough, ensure price >= vwap
  ctx = {
    "price": price,
    "vwap": vwap,
    "bars_above_vwap": 2,
    "ema9_gt_ema20": True,
    "atr_1m_pct": 2.5,
    "dist_ema20_pct": 0.2,
    "obv_slope_10": obv,
    "cvd_approx_20": cvd,
    "divergence_5m": "bullish_confirmed",
  }
  out = score_vwap_bounce(ctx)
  assert isinstance(out.get("score"), (int, float))
  comp = out.get("components", {})
  # New components should be present and non-negative in this bullish case
  assert "atr_regime" in comp
  assert "dist_ema20" in comp
  assert "flow" in comp and comp["flow"] >= 0
  assert out["score"] >= 40
