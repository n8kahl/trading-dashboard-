import { type NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const path = searchParams.get("path")

  if (!path) {
    return NextResponse.json({ error: "Path parameter required" }, { status: 400 })
  }

  try {
    // Use server-side environment variables (not exposed to client)
    const baseUrl = process.env.API_BASE_URL || "https://tradingassistantmcpready-production.up.railway.app"
    const apiKey = process.env.API_KEY

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    }

    if (apiKey) {
      headers["x-api-key"] = apiKey
    }

    const response = await fetch(`${baseUrl}${path}`, {
      method: "GET",
      headers,
    })

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("API proxy error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const path = searchParams.get("path")

  if (!path) {
    return NextResponse.json({ error: "Path parameter required" }, { status: 400 })
  }

  try {
    const body = await request.json()
    const baseUrl = process.env.API_BASE_URL || "https://tradingassistantmcpready-production.up.railway.app"
    const apiKey = process.env.API_KEY

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    }

    if (apiKey) {
      headers["x-api-key"] = apiKey
    }

    const response = await fetch(`${baseUrl}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("API proxy error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
