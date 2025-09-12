import type { z } from "zod"

export async function apiFetch<T>(path: string, schema: z.ZodType<T>, options: RequestInit = {}): Promise<T> {
  const url = `/api/proxy?path=${encodeURIComponent(path)}`

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  }

  const res = await fetch(url, {
    ...options,
    headers,
    cache: "no-store", // Ensure fresh data for trading
  })

  if (!res.ok) {
    throw new Error(`API request failed: ${res.status} ${res.statusText}`)
  }

  const json = await res.json()
  return schema.parse(json)
}

export async function apiGet<T>(path: string, schema: z.ZodType<T>): Promise<T> {
  return apiFetch(path, schema, { method: "GET" })
}

export async function apiPost<T>(path: string, body: unknown, schema: z.ZodType<T>): Promise<T> {
  return apiFetch(path, schema, { method: "POST", body: JSON.stringify(body) })
}
