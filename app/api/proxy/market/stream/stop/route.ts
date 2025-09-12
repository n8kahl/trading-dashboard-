import { type NextRequest, NextResponse } from "next/server"

const API_BASE_URL = process.env.API_BASE_URL || "https://tradingassistantmcpready-production.up.railway.app"

export async function POST(request: NextRequest) {
  try {
    const response = await fetch(`${API_BASE_URL}/market/stream/stop`, {
      method: "POST",
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
    console.error("Stream stop API error:", error)
    return NextResponse.json({ error: "Failed to stop market stream" }, { status: 500 })
  }
}
