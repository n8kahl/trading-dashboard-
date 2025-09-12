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
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  return handle(res);
}

export async function apiPost(path: string, body: any) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body ?? {})
  });
  return handle(res);
}
