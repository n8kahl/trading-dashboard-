import { type NextRequest, NextResponse } from "next/server"

const API_BASE_URL = process.env.API_BASE_URL || "https://tradingassistantmcpready-production.up.railway.app"

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const symbol = searchParams.get("symbol")

    if (!symbol) {
      return NextResponse.json({ error: "Symbol parameter required" }, { status: 400 })
    }

    const response = await fetch(`${API_BASE_URL}/market/stream/snapshot?symbol=${symbol}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    })

    if (!response.ok) {
      throw new Error(`Backend API error: ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Snapshot API error:", error)
    return NextResponse.json({ error: "Failed to get market snapshot" }, { status: 500 })
  }
}
