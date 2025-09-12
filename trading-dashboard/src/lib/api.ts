export async function apiGet<T>(path: string, schema?: { parse: (x: any) => T }): Promise<T> {
  const url = `/api/proxy?path=${encodeURIComponent(path)}`
  const response = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
    cache: "no-store",
  })

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`)
  }

  const j = await response.json()
  return schema ? schema.parse(j) : j
}

export async function apiPost<T>(path: string, body: any, schema?: { parse: (x: any) => T }): Promise<T> {
  const url = `/api/proxy?path=${encodeURIComponent(path)}`
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`)
  }

  const j = await response.json()
  return schema ? schema.parse(j) : j
}
