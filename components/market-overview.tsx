"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"
import { cn } from "@/lib/utils"

const marketData = [
  { symbol: "SPY", price: 445.67, change: 2.34, changePercent: 0.53, volume: "89.2M" },
  { symbol: "QQQ", price: 378.92, change: -1.45, changePercent: -0.38, volume: "45.7M" },
  { symbol: "IWM", price: 198.45, change: 0.87, changePercent: 0.44, volume: "23.1M" },
  { symbol: "VIX", price: 16.23, change: -0.45, changePercent: -2.7, volume: "12.4M" },
]

export function MarketOverview() {
  return (
    <Card className="trading-card">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Market Overview
          <Badge variant="outline" className="text-xs">
            Live
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {marketData.map((item) => {
            const isPositive = item.change > 0
            const isNegative = item.change < 0
            const TrendIcon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus

            return (
              <div key={item.symbol} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold">{item.symbol}</span>
                  <TrendIcon
                    className={cn(
                      "h-4 w-4",
                      isPositive && "text-green-400",
                      isNegative && "text-red-400",
                      !isPositive && !isNegative && "text-muted-foreground",
                    )}
                  />
                </div>
                <div className="space-y-1">
                  <div className="metric-value">${item.price.toFixed(2)}</div>
                  <div
                    className={cn(
                      "text-sm font-medium",
                      isPositive && "price-up",
                      isNegative && "price-down",
                      !isPositive && !isNegative && "price-neutral",
                    )}
                  >
                    {isPositive ? "+" : ""}
                    {item.change.toFixed(2)} ({isPositive ? "+" : ""}
                    {item.changePercent.toFixed(2)}%)
                  </div>
                  <div className="metric-label">Vol: {item.volume}</div>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
