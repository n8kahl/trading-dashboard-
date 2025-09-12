"use client"

import { useEffect, useRef, useState, useCallback } from "react"

interface WebSocketMessage {
  type: string
  data: any
  timestamp: number
}

interface WebSocketError {
  message: string
  error?: unknown
  event: Event | ErrorEvent
}

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void
  onError?: (error: WebSocketError) => void
  onConnect?: () => void
  onDisconnect?: () => void
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

export function useWebSocket(url: string, options: UseWebSocketOptions = {}) {
  const [isConnected, setIsConnected] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<"connecting" | "connected" | "disconnected" | "error">(
    "disconnected",
  )
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)

  const ws = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { onMessage, onError, onConnect, onDisconnect, reconnectInterval = 3000, maxReconnectAttempts = 5 } = options

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return

    setConnectionStatus("connecting")

    try {
      ws.current = new WebSocket(url)

      ws.current.onopen = () => {
        console.log("[v0] WebSocket connected")
        setIsConnected(true)
        setConnectionStatus("connected")
        reconnectAttempts.current = 0
        onConnect?.()
      }

      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = {
            type: "message",
            data: JSON.parse(event.data),
            timestamp: Date.now(),
          }
          setLastMessage(message)
          onMessage?.(message)
        } catch (error) {
          console.error("[v0] Failed to parse WebSocket message:", error)
        }
      }

      ws.current.onclose = () => {
        console.log("[v0] WebSocket disconnected")
        setIsConnected(false)
        setConnectionStatus("disconnected")
        onDisconnect?.()

        // Attempt reconnection
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++
          console.log(`[v0] Reconnecting... Attempt ${reconnectAttempts.current}/${maxReconnectAttempts}`)
          reconnectTimer.current = setTimeout(connect, reconnectInterval)
        }
      }

      ws.current.onerror = (event: Event | ErrorEvent) => {
        const errorInfo: WebSocketError =
          event instanceof ErrorEvent
            ? {
                message: event.message,
                error: event.error,
                event,
              }
            : {
                message: "WebSocket encountered an error",
                event,
              }

        console.error("[v0] WebSocket error:", errorInfo.message, errorInfo.error)
        setConnectionStatus("error")
        onError?.(errorInfo)
      }
    } catch (error) {
      console.error("[v0] Failed to create WebSocket connection:", error)
      setConnectionStatus("error")
    }
  }, [url, onMessage, onError, onConnect, onDisconnect, reconnectInterval, maxReconnectAttempts])

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
      reconnectTimer.current = null
    }

    if (ws.current) {
      ws.current.close()
      ws.current = null
    }

    setIsConnected(false)
    setConnectionStatus("disconnected")
  }, [])

  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message))
      return true
    }
    console.warn("[v0] WebSocket not connected, message not sent")
    return false
  }, [])

  useEffect(() => {
    connect()

    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    isConnected,
    connectionStatus,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
  }
}
