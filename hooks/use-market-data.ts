"use client"

import { useState, useEffect } from "react"
import { useLiveMarketData } from "./use-live-market-data"

export interface MarketDataPoint {
  symbol: string
  price: number
  change: number
  changePercent: number
  volume: string
  timestamp: number
  realtime?: boolean
}

export interface TickerData {
  symbol: string
  price: number
  bid: number
  ask: number
  volume: number
  high: number
  low: number
  open: number
  previousClose: number
  timestamp: number
  realtime?: boolean
}

export function useMarketData(symbols: string[] = []) {
  const [data, setData] = useState<Record<string, MarketDataPoint>>({})
  const [error, setError] = useState<string | null>(null)

  const { marketData, isConnected, error: streamError, getSnapshot } = useLiveMarketData(symbols)

  useEffect(() => {
    const convertedData: Record<string, MarketDataPoint> = {}

    Object.entries(marketData).forEach(([symbol, liveData]) => {
      convertedData[symbol] = {
        symbol: liveData.symbol,
        price: liveData.price,
        change: liveData.change,
        changePercent: liveData.changePercent,
        volume: `${(liveData.volume / 1000000).toFixed(1)}M`,
        timestamp: liveData.timestamp,
        realtime: liveData.realtime,
      }
    })

    setData(convertedData)
  }, [marketData])

  useEffect(() => {
    if (streamError) {
      setError(streamError)
    }
  }, [streamError])

  useEffect(() => {
    symbols.forEach(async (symbol) => {
      if (!marketData[symbol]) {
        try {
          await getSnapshot(symbol)
        } catch (err) {
          console.error(`[v0] Failed to get snapshot for ${symbol}:`, err)
        }
      }
    })
  }, [symbols, marketData, getSnapshot])

  return { data, isConnected, error }
}

export function useTickerData(symbol: string) {
  const [data, setData] = useState<TickerData | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const { marketData, getSnapshot } = useLiveMarketData([symbol])

  useEffect(() => {
    if (!symbol) return

    const fetchTickerData = async () => {
      try {
        const response = await fetch(`/api/proxy/market/ticker/${symbol}`)
        if (response.ok) {
          const tickerData = await response.json()
          setData({
            symbol: tickerData.symbol,
            price: tickerData.price || tickerData.last || 0,
            bid: tickerData.bid || tickerData.price - 0.05,
            ask: tickerData.ask || tickerData.price + 0.05,
            volume: tickerData.volume || 0,
            high: tickerData.high || tickerData.price,
            low: tickerData.low || tickerData.price,
            open: tickerData.open || tickerData.price,
            previousClose: tickerData.prevclose || tickerData.price,
            timestamp: Date.now(),
            realtime: tickerData.realtime || false,
          })
        } else {
          await getSnapshot(symbol)
        }
      } catch (err) {
        console.error(`[v0] Failed to fetch ticker data for ${symbol}:`, err)
        const liveData = marketData[symbol]
        if (liveData) {
          setData({
            symbol: liveData.symbol,
            price: liveData.price,
            bid: liveData.price - 0.05,
            ask: liveData.price + 0.05,
            volume: liveData.volume,
            high: liveData.high,
            low: liveData.low,
            open: liveData.open,
            previousClose: liveData.price,
            timestamp: liveData.timestamp,
            realtime: liveData.realtime,
          })
        }
      } finally {
        setIsLoading(false)
      }
    }

    fetchTickerData()
  }, [symbol, marketData, getSnapshot])

  useEffect(() => {
    const liveData = marketData[symbol]
    if (liveData && data) {
      setData((prev) =>
        prev
          ? {
              ...prev,
              price: liveData.price,
              bid: liveData.price - 0.05,
              ask: liveData.price + 0.05,
              timestamp: liveData.timestamp,
              realtime: liveData.realtime,
            }
          : null,
      )
    }
  }, [marketData, symbol, data])

  return { data, isLoading }
}
