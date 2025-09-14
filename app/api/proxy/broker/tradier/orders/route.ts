import { type NextRequest, NextResponse } from "next/server"

const API_BASE_URL = process.env.API_BASE_URL || "https://tradingassistantmcpready-production.up.railway.app"

export async function GET(request: NextRequest) {
  try {
    const apiKey = process.env.API_KEY
    const headers: Record<string, string> = { "Content-Type": "application/json" }
    if (apiKey) headers["x-api-key"] = apiKey

    const response = await fetch(`${API_BASE_URL}/broker/tradier/orders`, {
      method: "GET",
      headers,
    })

    if (!response.ok) {
      throw new Error(`Backend API error: ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Orders API error:", error)
    return NextResponse.json({ error: "Failed to fetch order history" }, { status: 500 })
  }
}
