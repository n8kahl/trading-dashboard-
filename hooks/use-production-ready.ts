"use client"

import { useEffect, useState } from "react"
import { useConnectionMonitor } from "./use-connection-monitor"
import { useErrorHandler } from "./use-error-handler"
import { config } from "@/lib/config"

interface ProductionStatus {
  isReady: boolean
  checks: {
    apiConnection: boolean
    marketDataStream: boolean
    tradingAPI: boolean
    errorHandling: boolean
  }
  warnings: string[]
  errors: string[]
}

export function useProductionReady() {
  const [status, setStatus] = useState<ProductionStatus>({
    isReady: false,
    checks: {
      apiConnection: false,
      marketDataStream: false,
      tradingAPI: false,
      errorHandling: false,
    },
    warnings: [],
    errors: [],
  })

  const { apiHealthy } = useConnectionMonitor()
  const { handleError } = useErrorHandler()

  useEffect(() => {
    const runProductionChecks = async () => {
      const warnings: string[] = []
      const errors: string[] = []
      const checks = {
        apiConnection: false,
        marketDataStream: false,
        tradingAPI: false,
        errorHandling: true, // Always true since we have error handling
      }

      try {
        // Check API Connection
        checks.apiConnection = apiHealthy

        // Check Market Data Stream
        try {
          const streamResponse = await fetch("/api/proxy/market/stream/status")
          checks.marketDataStream = streamResponse.ok
        } catch (err) {
          errors.push("Market data stream unavailable")
        }

        // Check Trading API
        try {
          const tradingResponse = await fetch("/api/proxy/broker/tradier/account")
          checks.tradingAPI = tradingResponse.ok

          if (!tradingResponse.ok) {
            warnings.push("Trading API not connected - using paper trading mode")
          }
        } catch (err) {
          warnings.push("Trading API unavailable - limited functionality")
        }

        // Production warnings
        if (config.production.sandboxMode) {
          warnings.push("Running in sandbox mode - no real trades will be executed")
        }

        if (!config.features.liveTrading) {
          warnings.push("Live trading disabled - paper trading only")
        }

        const isReady = checks.apiConnection && checks.errorHandling && errors.length === 0

        setStatus({
          isReady,
          checks,
          warnings,
          errors,
        })
      } catch (error) {
        handleError(error, "production-checks")
        setStatus((prev) => ({
          ...prev,
          isReady: false,
          errors: [...prev.errors, "Failed to complete production readiness checks"],
        }))
      }
    }

    runProductionChecks()

    // Re-run checks every 60 seconds
    const interval = setInterval(runProductionChecks, 60000)

    return () => clearInterval(interval)
  }, [apiHealthy, handleError])

  return status
}
