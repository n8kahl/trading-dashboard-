const $ = (id) => document.getElementById(id);
// Same-origin calls to your FastAPI
const BASE = ""; // keep blank when UI is served by same app

async function getJSON(path) {
  const r = await fetch(`${BASE}${path}`);
  return r.json();
}
async function postJSON(path, body) {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body || {})
  });
  return r.json();
}
async function postForm(path, data) {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: {"Content-Type": "application/x-www-form-urlencoded"},
    body: new URLSearchParams(data)
  });
  return r.json();
}

function pretty(el, obj) {
  el.textContent = JSON.stringify(obj, null, 2);
}

// --- Health & env ---
(async () => {
  try {
    const h = await getJSON("/api/v1/diag/health");
    const e = await getJSON("/api/v1/broker/envcheck");
    $.healthBadge.textContent = h.ok ? "healthy" : "unhealthy";
    $.healthBadge.className = "text-sm px-2 py-1 rounded " + (h.ok ? "bg-emerald-700" : "bg-rose-700");
    pretty($.env, e);
  } catch (err) {
    $.healthBadge.textContent = "error";
  }
})();

// --- Stream controls ---
async function refreshStream() {
  const s = await getJSON("/api/v1/market/stream/status");
  pretty($.streamStatus, s);
}
async function refreshSnapshot() {
  const s = await getJSON("/api/v1/market/stream/snapshot");
  pretty($.snapshot, s);
}
$.startStream.onclick = async () => {
  const input = $.streamSymbols.value.trim();
  const symbols = input ? input.split(",").map(s => s.trim().toUpperCase()).filter(Boolean) : ["SPY","QQQ","I:SPX"];
  const res = await postJSON("/api/v1/market/stream/start", { symbols });
  await refreshStream();
  if (res.status !== "ok") alert("Stream start error: " + JSON.stringify(res));
};
$.stopStream.onclick = async () => {
  await postJSON("/api/v1/market/stream/stop", {});
  await refreshStream();
};
// keep status refresh
setInterval(() => { refreshStream(); }, 5000);

// --- Alerts ---
$.setAlert.onclick = async () => {
  const symbol = $.alertSymbol.value.trim().toUpperCase();
  const level = parseFloat($.alertLevel.value);
  const note = $.alertNote.value.trim();
  if (!symbol || Number.isNaN(level)) return alert("Enter symbol and numeric level");
  const res = await postJSON("/api/v1/alerts/set", { symbol, level, note });
  pretty($.alertsList, res);
};
$.listAlerts.onclick = async () => {
  const res = await getJSON("/api/v1/alerts/list");
  pretty($.alertsList, res);
};

// --- Equity order ---
$.eqSubmit.onclick = async () => {
  const symbol = $.eqSymbol.value.trim().toUpperCase();
  const side = $.eqSide.value;
  const quantity = parseInt($.eqQty.value || "1", 10);
  const type = $.eqType.value;
  const duration = $.eqDur.value;
  const priceStr = $.eqPrice.value.trim();
  const data = { class: "equity", symbol, side, quantity, type, duration };
  if (priceStr) data.price = priceStr;
  const res = await postForm("/api/v1/broker/orders/submit", data);
  pretty($.eqResp, res);
};

// --- Option order ---
$.opSubmit.onclick = async () => {
  const root = $.opRoot.value.trim().toUpperCase();
  const occ = $.opOcc.value.trim().toUpperCase();
  const side = $.opSide.value;
  const quantity = parseInt($.opQty.value || "1", 10);
  const type = $.opType.value;
  const duration = $.opDur.value;
  if (!root || !occ) return alert("Enter root symbol and OCC option symbol");
  const data = { class: "option", symbol: root, option_symbol: occ, side, quantity, type, duration };
  const priceStr = $.opPrice.value.trim();
  if (priceStr) data.price = priceStr;
  const res = await postForm("/api/v1/broker/orders/submit", data);
  pretty($.opResp, res);
};

// --- Account ---
$.btnPositions.onclick = async () => {
  const res = await getJSON("/api/v1/broker/positions");
  pretty($.accountOut, res);
};
$.btnOrders.onclick = async () => {
  // your backend exposes /api/v1/broker/tradier/account (but not raw orders list),
  // so we call that for now; extend later if you add an orders list endpoint.
  const res = await getJSON("/api/v1/broker/tradier/account");
  pretty($.accountOut, res);
};


// ===== Live UX upgrades =====
const DEFAULT_SYMBOLS = ["SPY","QQQ","I:SPX"];
let tapeBuf = []; const TAPE_MAX = 50;

function isMarketHours() {
  const now = new Date();
  const h = now.getUTCHours(), m = now.getUTCMinutes();
  const minutes = h*60 + m;
  return minutes >= 13*60+30 && minutes <= 20*60;
}
function renderTape(snap) {
  const el = document.getElementById("tape"); if (!el) return;
  const rows = [];
  const data = snap?.data || snap || {};
  Object.entries(data).forEach(([sym, d])=>{
    if (!d) return;
    const last = d.last ?? d.price ?? d.close ?? null;
    const bid  = d.bid ?? null;
    const ask  = d.ask ?? null;
    const ts   = d.ts ?? d.time ?? new Date().toISOString();
    if (last==null && bid==null && ask==null) return;
    rows.push({ts, sym, last, bid, ask});
  });
  rows.sort((a,b)=> a.ts > b.ts ? 1 : -1).forEach(r=>{
    tapeBuf.push(r); if (tapeBuf.length > TAPE_MAX) tapeBuf.shift();
  });
  const html = [...tapeBuf].reverse().map(r =>
    `<div class="flex gap-3"><span class="text-slate-500">${r.ts}</span><b>${r.sym}</b>`
    + `<span>last:${r.last ?? "-"}</span><span>bid:${r.bid ?? "-"}</span><span>ask:${r.ask ?? "-"}</span></div>`
  ).join("");
  el.innerHTML = html || '<div class="text-slate-500">No ticks yet (after-hours is normal).</div>';
}
async function ensureStreamStarted() {
  try {
    const stat = await getJSON("/api/v1/market/stream/status");
    const watching = stat?.data?.watching ?? [];
    if (!stat?.data?.connected || watching.length===0) {
      const input = document.getElementById("streamSymbols")?.value?.trim();
      const symbols = input ? input.split(",").map(s => s.trim().toUpperCase()).filter(Boolean) : DEFAULT_SYMBOLS;
      await postJSON("/api/v1/market/stream/start", { symbols });
    }
  } catch {}
}
async function refreshSnapshotFast() {
  try {
    const snap = await getJSON("/api/v1/market/stream/snapshot");
    pretty(document.getElementById("snapshot"), snap);
    renderTape(snap);
  } catch {}
}
async function refreshAccountPassive() {
  if (!isMarketHours()) return;
  try {
    const pos = await getJSON("/api/v1/broker/positions");
    const acct = await getJSON("/api/v1/broker/tradier/account");
    pretty(document.getElementById("accountOut"), { positions: pos, account: acct });
  } catch {}
}
// boot
(async () => {
  try { await ensureStreamStarted(); await refreshStream(); await refreshSnapshotFast(); } catch {}
})();
setInterval(refreshSnapshotFast, 2000);
setInterval(refreshAccountPassive, 10000);
