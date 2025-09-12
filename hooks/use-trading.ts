"use client"

import { useState, useCallback } from "react"

interface Account {
  account_number: string
  day_trader: boolean
  option_level: number
  status: string
  type: string
  last_update_date: string
}

interface Balance {
  option_buying_power: number
  stock_buying_power: number
  stock_short_value: number
  total_equity: number
  total_cash: number
  market_value: number
  day_trade_buying_power: number
}

interface Position {
  cost_basis: number
  date_acquired: string
  id: number
  quantity: number
  symbol: string
  instrument: {
    underlying_symbol: string
    option_type?: string
    strike?: number
    expiration_date?: string
  }
}

interface OrderRequest {
  account_id: string
  class: "equity" | "option"
  symbol: string
  side: "buy" | "sell" | "buy_to_open" | "sell_to_open" | "buy_to_close" | "sell_to_close"
  quantity: number
  type: "market" | "limit" | "stop" | "stop_limit"
  duration: "day" | "gtc" | "pre" | "post"
  price?: number
  stop?: number
  option_symbol?: string
  preview?: boolean
}

interface OrderResponse {
  id?: string
  status: string
  errors?: string[]
  order?: {
    id: string
    status: string
    symbol: string
    side: string
    quantity: number
    price?: number
    time_in_force: string
    type: string
  }
  cost?: number
  fees?: number
  margin_change?: number
  request_date?: string
  extended_hours?: boolean
  class?: string
  strategy?: string
}

export function useTrading() {
  const [account, setAccount] = useState<Account | null>(null)
  const [balance, setBalance] = useState<Balance | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchAccount = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch("/api/proxy/broker/tradier/account")
      if (!response.ok) {
        throw new Error("Failed to fetch account information")
      }
      const data = await response.json()
      setAccount(data.account)
      setBalance(data.balances)
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error"
      setError(errorMessage)
      console.error("[v0] Failed to fetch account:", err)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchPositions = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch("/api/proxy/broker/tradier/positions")
      if (!response.ok) {
        throw new Error("Failed to fetch positions")
      }
      const data = await response.json()
      setPositions(data.positions || [])
      return data.positions || []
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error"
      setError(errorMessage)
      console.error("[v0] Failed to fetch positions:", err)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const previewOrder = useCallback(async (orderRequest: OrderRequest): Promise<OrderResponse> => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch("/api/proxy/broker/tradier/order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...orderRequest, preview: true }),
      })

      if (!response.ok) {
        throw new Error("Failed to preview order")
      }

      const data = await response.json()
      console.log("[v0] Order preview:", data)
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error"
      setError(errorMessage)
      console.error("[v0] Failed to preview order:", err)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const placeOrder = useCallback(async (orderRequest: OrderRequest): Promise<OrderResponse> => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch("/api/proxy/broker/tradier/order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...orderRequest, preview: false }),
      })

      if (!response.ok) {
        throw new Error("Failed to place order")
      }

      const data = await response.json()
      console.log("[v0] Order placed:", data)

      // Log the trade
      await fetch("/api/proxy/trades", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: orderRequest.symbol,
          side: orderRequest.side,
          quantity: orderRequest.quantity,
          price: orderRequest.price,
          order_type: orderRequest.type,
          status: data.status,
          order_id: data.id,
          timestamp: new Date().toISOString(),
        }),
      })

      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error"
      setError(errorMessage)
      console.error("[v0] Failed to place order:", err)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const getOrderHistory = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch("/api/proxy/broker/tradier/orders")
      if (!response.ok) {
        throw new Error("Failed to fetch order history")
      }
      const data = await response.json()
      return data.orders || []
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error"
      setError(errorMessage)
      console.error("[v0] Failed to fetch order history:", err)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    account,
    balance,
    positions,
    loading,
    error,
    fetchAccount,
    fetchPositions,
    previewOrder,
    placeOrder,
    getOrderHistory,
  }
}
