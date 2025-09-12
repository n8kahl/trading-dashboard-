"use client"

import { useState, useEffect, useCallback, useRef } from "react"

interface ConnectionState {
  isOnline: boolean
  apiHealthy: boolean
  lastCheck: number
  retryCount: number
}

export function useConnectionMonitor() {
  const [connectionState, setConnectionState] = useState<ConnectionState>({
    isOnline: navigator.onLine,
    apiHealthy: false,
    lastCheck: 0,
    retryCount: 0,
  })

  const healthCheckInterval = useRef<ReturnType<typeof setInterval> | null>(null)
  const retryTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  const checkApiHealth = useCallback(async () => {
    try {
      const controller = new AbortController()
      const timeoutId: ReturnType<typeof setTimeout> = setTimeout(
        () => controller.abort(),
        5000,
      ) // 5 second timeout

      const response = await fetch("/api/proxy/health", {
        method: "GET",
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      const isHealthy = response.ok
      setConnectionState((prev) => ({
        ...prev,
        apiHealthy: isHealthy,
        lastCheck: Date.now(),
        retryCount: isHealthy ? 0 : prev.retryCount + 1,
      }))

      return isHealthy
    } catch (error) {
      console.error("[v0] API health check failed:", error)
      setConnectionState((prev) => ({
        ...prev,
        apiHealthy: false,
        lastCheck: Date.now(),
        retryCount: prev.retryCount + 1,
      }))
      return false
    }
  }, [])

  const startHealthChecks = useCallback(() => {
    // Initial check
    checkApiHealth()

    // Regular health checks every 30 seconds
    healthCheckInterval.current = setInterval(checkApiHealth, 30000)
  }, [checkApiHealth])

  const stopHealthChecks = useCallback(() => {
    if (healthCheckInterval.current) {
      clearInterval(healthCheckInterval.current)
      healthCheckInterval.current = null
    }
    if (retryTimeout.current) {
      clearTimeout(retryTimeout.current)
      retryTimeout.current = null
    }
  }, [])

  const retryConnection = useCallback(() => {
    if (connectionState.retryCount < 5) {
      const delay = Math.min(1000 * Math.pow(2, connectionState.retryCount), 30000) // Exponential backoff, max 30s

      retryTimeout.current = setTimeout(() => {
        checkApiHealth()
      }, delay)
    }
  }, [connectionState.retryCount, checkApiHealth])

  // Monitor online/offline status
  useEffect(() => {
    const handleOnline = () => {
      setConnectionState((prev) => ({ ...prev, isOnline: true }))
      checkApiHealth()
    }

    const handleOffline = () => {
      setConnectionState((prev) => ({ ...prev, isOnline: false, apiHealthy: false }))
    }

    window.addEventListener("online", handleOnline)
    window.addEventListener("offline", handleOffline)

    return () => {
      window.removeEventListener("online", handleOnline)
      window.removeEventListener("offline", handleOffline)
    }
  }, [checkApiHealth])

  // Start health checks on mount
  useEffect(() => {
    startHealthChecks()
    return stopHealthChecks
  }, [startHealthChecks, stopHealthChecks])

  // Auto-retry on failures
  useEffect(() => {
    if (!connectionState.apiHealthy && connectionState.isOnline && connectionState.retryCount > 0) {
      retryConnection()
    }
  }, [connectionState.apiHealthy, connectionState.isOnline, connectionState.retryCount, retryConnection])

  return {
    ...connectionState,
    checkApiHealth,
    retryConnection,
  }
}
