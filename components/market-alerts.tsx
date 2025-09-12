"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { AlertTriangle, TrendingUp, TrendingDown, Volume2, X } from "lucide-react"
import { cn } from "@/lib/utils"

interface MarketAlert {
  id: string
  type: "price" | "volume" | "technical" | "news"
  severity: "low" | "medium" | "high"
  symbol: string
  title: string
  message: string
  timestamp: Date
  actionable: boolean
}

export function MarketAlerts() {
  const [alerts, setAlerts] = useState<MarketAlert[]>([])

  useEffect(() => {
    // Simulate incoming alerts
    const generateAlert = () => {
      const symbols = ["AAPL", "TSLA", "SPY", "QQQ", "NVDA"]
      const alertTypes = [
        {
          type: "price" as const,
          titles: ["Price Alert", "Breakout Alert", "Support/Resistance"],
          messages: [
            "broke above resistance at $185.50",
            "testing key support level at $240.00",
            "approaching 52-week high",
          ],
        },
        {
          type: "volume" as const,
          titles: ["Volume Spike", "Unusual Activity"],
          messages: ["volume 3x above average", "unusual options activity detected"],
        },
        {
          type: "technical" as const,
          titles: ["Technical Signal", "Momentum Alert"],
          messages: ["RSI oversold condition", "MACD bullish crossover", "moving average breakout"],
        },
      ]

      const symbol = symbols[Math.floor(Math.random() * symbols.length)]
      const alertType = alertTypes[Math.floor(Math.random() * alertTypes.length)]
      const title = alertType.titles[Math.floor(Math.random() * alertType.titles.length)]
      const message = alertType.messages[Math.floor(Math.random() * alertType.messages.length)]

      const alert: MarketAlert = {
        id: Date.now().toString(),
        type: alertType.type,
        severity: Math.random() > 0.7 ? "high" : Math.random() > 0.4 ? "medium" : "low",
        symbol,
        title,
        message: `${symbol} ${message}`,
        timestamp: new Date(),
        actionable: Math.random() > 0.5,
      }

      setAlerts((prev) => [alert, ...prev.slice(0, 9)]) // Keep last 10 alerts
    }

    const interval = setInterval(generateAlert, 5000 + Math.random() * 10000) // 5-15 seconds
    return () => clearInterval(interval)
  }, [])

  const dismissAlert = (id: string) => {
    setAlerts((prev) => prev.filter((alert) => alert.id !== id))
  }

  const getAlertIcon = (type: string) => {
    switch (type) {
      case "price":
        return <TrendingUp className="h-4 w-4" />
      case "volume":
        return <Volume2 className="h-4 w-4" />
      case "technical":
        return <TrendingDown className="h-4 w-4" />
      default:
        return <AlertTriangle className="h-4 w-4" />
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "high":
        return "text-red-400 border-red-400/20 bg-red-400/10"
      case "medium":
        return "text-yellow-400 border-yellow-400/20 bg-yellow-400/10"
      case "low":
        return "text-blue-400 border-blue-400/20 bg-blue-400/10"
      default:
        return "text-muted-foreground border-border bg-muted/20"
    }
  }

  return (
    <Card className="trading-card">
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            Market Alerts
          </div>
          <Badge variant="outline" className="text-xs">
            {alerts.length} Active
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2 max-h-64 overflow-auto">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={cn("flex items-start gap-2 p-2 rounded border", getSeverityColor(alert.severity))}
            >
              <div className="flex-shrink-0 mt-0.5">{getAlertIcon(alert.type)}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-xs">{alert.symbol}</span>
                    <Badge variant="outline" className="text-xs">
                      {alert.type}
                    </Badge>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-auto p-0 text-muted-foreground hover:text-foreground"
                    onClick={() => dismissAlert(alert.id)}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
                <p className="text-xs mt-1">{alert.message}</p>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-xs opacity-70">{alert.timestamp.toLocaleTimeString()}</span>
                  {alert.actionable && (
                    <Badge variant="secondary" className="text-xs">
                      Actionable
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          ))}
          {alerts.length === 0 && (
            <div className="text-center py-6 text-muted-foreground text-xs">No active alerts</div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
