import type { z } from "zod"

function headers() {
  const h: Record<string, string> = { "content-type": "application/json" }
  return h
}

export async function apiGet<T = unknown>(path: string, schema?: z.ZodTypeAny): Promise<T> {
  const url = `/api/proxy?path=${encodeURIComponent(path)}`
  const res = await fetch(url, { headers: headers(), cache: "no-store" })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  const data = await res.json()
  return schema ? schema.parse(data) : (data as T)
}

export async function apiPost<T = unknown>(path: string, body: unknown, schema?: z.ZodTypeAny): Promise<T> {
  const url = `/api/proxy?path=${encodeURIComponent(path)}`
  const res = await fetch(url, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  const data = await res.json()
  return schema ? schema.parse(data) : (data as T)
}
