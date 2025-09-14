"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/src/lib/api";
import { useState, useEffect } from "react";

type Settings = {
  risk_daily_r?: number|null;
  risk_per_trade_r?: number|null;
  risk_max_concurrent?: number|null;
  rr_default?: string|null;
  auto_execute_sandbox?: boolean;
  top_symbols?: string|null;
  discord_webhook_url?: string|null;
  discord_alerts_enabled?: boolean;
  discord_alert_types?: string|null;
};

export default function SettingsPage() {

  const { data, isLoading, error } = useQuery({
    queryKey: ["settings"],
    queryFn: async (): Promise<Settings> => (await apiGet("/api/v1/settings/get")).settings,
  });
  const [local, setLocal] = useState<Settings | null>(null);

  useEffect(() => { if (data) setLocal(data); }, [data]);

  const save = useMutation({
    mutationFn: async () => apiPost("/api/v1/settings/set", local),
  });

  const sendTest = useMutation({
    mutationFn: async () => {
      const url = local?.discord_webhook_url || "";
      // very light validation
      if (!/^https:\/\/discord\.com\//.test(url) && !/^https:\/\/discordapp\.com\//.test(url)) {
        throw new Error("Invalid Discord webhook URL");
      }
      const res = await fetch(`/api/proxy?path=${encodeURIComponent('/settings/discord/test')}`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const js = await res.json();
      if (!js?.ok) throw new Error(js?.error || 'Test failed');
      return js;
    }
  });

  return (
    <main className="container">
      <h1 style={{marginBottom:12}}>Admin Settings</h1>

  {isLoading ? "Loading…" : error ? String(error) : (
        <section className="card" style={{display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(280px,1fr))", gap:12}}>
          <label>Daily loss cap (R)
            <input className="input" value={local?.risk_daily_r ?? ''} onChange={e=>setLocal(v=>({...v!, risk_daily_r: e.target.value?Number(e.target.value):null}))} />
          </label>
          <label>Per-trade max R
            <input className="input" value={local?.risk_per_trade_r ?? ''} onChange={e=>setLocal(v=>({...v!, risk_per_trade_r: e.target.value?Number(e.target.value):null}))} />
          </label>
          <label>Max concurrent positions
            <input className="input" value={local?.risk_max_concurrent ?? ''} onChange={e=>setLocal(v=>({...v!, risk_max_concurrent: e.target.value?Number(e.target.value):null}))} />
          </label>
          <label>Default R:R
            <input className="input" placeholder="1:5" value={local?.rr_default ?? ''} onChange={e=>setLocal(v=>({...v!, rr_default: e.target.value}))} />
          </label>
          <label style={{gridColumn:"1 / -1"}}>Top symbols (comma-separated)
            <input className="input" value={local?.top_symbols ?? ''} onChange={e=>setLocal(v=>({...v!, top_symbols: e.target.value}))} />
          </label>
          <label>
            <input type="checkbox" checked={!!local?.auto_execute_sandbox} onChange={e=>setLocal(v=>({...v!, auto_execute_sandbox: e.target.checked}))} />
            {' '}Allow auto-execute in Sandbox
          </label>
          <div style={{gridColumn:"1 / -1", marginTop:8, opacity:.8, fontWeight:600}}>Discord Alerts</div>
          <label style={{gridColumn:"1 / -1"}}>Webhook URL
            <input className="input" placeholder="https://discord.com/api/webhooks/..." value={local?.discord_webhook_url ?? ''} onChange={e=>setLocal(v=>({...v!, discord_webhook_url: e.target.value}))} />
          </label>
          <label>
            <input type="checkbox" checked={!!local?.discord_alerts_enabled} onChange={e=>setLocal(v=>({...v!, discord_alerts_enabled: e.target.checked}))} />
            {' '}Enable Discord forwarding
          </label>
          <label style={{gridColumn:"1 / -1"}}>Alert types (comma-separated)
            <input className="input" placeholder="price_above,price_below,risk" value={local?.discord_alert_types ?? ''} onChange={e=>setLocal(v=>({...v!, discord_alert_types: e.target.value}))} />
          </label>
          <div style={{gridColumn:"1 / span 2", display:'flex', gap:8}}>
            <button onClick={()=> save.mutate()} disabled={!local || save.isPending}>{save.isPending?"Saving…":"Save Settings"}</button>
            <button className="secondary" onClick={()=> sendTest.mutate()} disabled={sendTest.isPending}>Send test Discord</button>
          </div>
        </section>
      )}
    </main>
  );
}
