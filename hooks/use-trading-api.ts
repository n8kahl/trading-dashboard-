"use client"

import { useState, useCallback } from "react"

interface OrderRequest {
  symbol: string
  side: "buy" | "sell"
  quantity: number
  orderType: "market" | "limit" | "stop"
  price?: number
  stopPrice?: number
  timeInForce?: string
  preview?: boolean
}

interface OrderResponse {
  ok: boolean
  orderId?: string
  preview?: any
  error?: string
}

export function useTradingAPI() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const placeOrder = useCallback(async (order: OrderRequest): Promise<OrderResponse> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/proxy?path=${encodeURIComponent("/v1/broker/tradier/order")}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(order),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const result = await response.json()
      return result
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error occurred"
      setError(errorMessage)
      return { ok: false, error: errorMessage }
    } finally {
      setIsLoading(false)
    }
  }, [])

  const getAccountInfo = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/proxy?path=${encodeURIComponent("/v1/broker/tradier/account")}`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      return await response.json()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error occurred"
      setError(errorMessage)
      return null
    } finally {
      setIsLoading(false)
    }
  }, [])

  const getAssistantActions = useCallback(async () => {
    try {
      const response = await fetch(`/api/proxy?path=${encodeURIComponent("/assistant/actions")}`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      return await response.json()
    } catch (err) {
      console.error("Failed to fetch assistant actions:", err)
      return { ok: false, actions: [] }
    }
  }, [])

  const executeAssistantAction = useCallback(async (op: string, args: any) => {
    try {
      const response = await fetch(`/api/proxy?path=${encodeURIComponent("/assistant/exec")}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ op, args }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      return await response.json()
    } catch (err) {
      console.error("Failed to execute assistant action:", err)
      return { ok: false, error: err instanceof Error ? err.message : "Unknown error" }
    }
  }, [])

  return {
    placeOrder,
    getAccountInfo,
    getAssistantActions,
    executeAssistantAction,
    isLoading,
    error,
  }
}
