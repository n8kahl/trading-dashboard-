import { type NextRequest, NextResponse } from "next/server"

const API_BASE_URL = process.env.API_BASE_URL || "https://tradingassistantmcpready-production.up.railway.app"

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    const apiKey = process.env.API_KEY
    const headers: Record<string, string> = { "Content-Type": "application/json" }
    if (apiKey) headers["x-api-key"] = apiKey

    const response = await fetch(`${API_BASE_URL}/broker/tradier/order`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      throw new Error(`Backend API error: ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Order API error:", error)
    return NextResponse.json({ error: "Failed to process order" }, { status: 500 })
  }
}
