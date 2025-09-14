const BASE = process.env.NEXT_PUBLIC_API_BASE || "";

async function handle(res: Response) {
  if (!res.ok) {
    const text = await res.text().catch(()=>"");
    try { throw new Error(text || `HTTP ${res.status}`); }
    catch { throw new Error(`HTTP ${res.status}`); }
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

export async function apiGet(path: string) {
  // Use local proxy to avoid cross-origin CORS issues in the browser.
  const proxied = `/api/proxy?path=${encodeURIComponent(path)}`;
  const res = await fetch(proxied, { cache: "no-store" });
  return handle(res);
}

export async function apiPost(path: string, body: any) {
  const proxied = `/api/proxy?path=${encodeURIComponent(path)}`;
  const res = await fetch(proxied, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body ?? {})
  });
  return handle(res);
}
