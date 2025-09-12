"use client"

import { useState, useEffect, useCallback } from "react"
import { useWebSocket } from "./use-websocket"

interface MarketData {
  symbol: string
  price: number
  change: number
  changePercent: number
  volume: number
  high: number
  low: number
  open: number
  timestamp: number
  realtime: boolean
}

interface MarketDataState {
  [symbol: string]: MarketData
}

export function useLiveMarketData(symbols: string[] = []) {
  const [marketData, setMarketData] = useState<MarketDataState>({})
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { isConnected, sendMessage, connectionStatus } = useWebSocket(
    `wss://${process.env.NEXT_PUBLIC_API_BASE_URL || "tradingassistantmcpready-production.up.railway.app"}/ws/market`,
    {
      onMessage: (message) => {
        if (message.data.type === "market_data") {
          const data = message.data.payload
          setMarketData((prev) => ({
            ...prev,
            [data.symbol]: {
              ...data,
              realtime: true,
              timestamp: Date.now(),
            },
          }))
        }
      },
      onConnect: () => {
        setError(null)
        console.log("[v0] Market data stream connected")
      },
      onError: () => {
        setError("Failed to connect to market data stream")
      },
    },
  )

  const startStreaming = useCallback(
    async (symbolsToStream: string[]) => {
      try {
        const response = await fetch("/api/proxy/market/stream/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ symbols: symbolsToStream }),
        })

        if (!response.ok) {
          throw new Error("Failed to start market data stream")
        }

        if (isConnected) {
          sendMessage({
            action: "subscribe",
            symbols: symbolsToStream,
          })
        }

        setIsStreaming(true)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error")
        console.error("[v0] Failed to start streaming:", err)
      }
    },
    [isConnected, sendMessage],
  )

  const stopStreaming = useCallback(async () => {
    try {
      await fetch("/api/proxy/market/stream/stop", { method: "POST" })

      if (isConnected) {
        sendMessage({ action: "unsubscribe_all" })
      }

      setIsStreaming(false)
    } catch (err) {
      console.error("[v0] Failed to stop streaming:", err)
    }
  }, [isConnected, sendMessage])

  const getSnapshot = useCallback(async (symbol: string) => {
    try {
      const response = await fetch(`/api/proxy/market/stream/snapshot?symbol=${symbol}`)
      if (response.ok) {
        const data = await response.json()
        setMarketData((prev) => ({
          ...prev,
          [symbol]: {
            ...data,
            realtime: data.realtime || false,
            timestamp: Date.now(),
          },
        }))
        return data
      }
    } catch (err) {
      console.error("[v0] Failed to get snapshot:", err)
    }
  }, [])

  useEffect(() => {
    if (symbols.length > 0 && isConnected && !isStreaming) {
      startStreaming(symbols)
    }
  }, [symbols, isConnected, isStreaming, startStreaming])

  return {
    marketData,
    isStreaming,
    isConnected: connectionStatus === "connected",
    connectionStatus,
    error,
    startStreaming,
    stopStreaming,
    getSnapshot,
  }
}
