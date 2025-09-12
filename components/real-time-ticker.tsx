"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"
import { cn } from "@/lib/utils"
import { useMarketData } from "@/hooks/use-market-data"
import { useEffect, useState } from "react"

interface RealTimeTickerProps {
  symbols: string[]
  className?: string
}

export function RealTimeTicker({ symbols, className }: RealTimeTickerProps) {
  const { data, isConnected } = useMarketData(symbols)
  const [flashingSymbols, setFlashingSymbols] = useState<Set<string>>(new Set())

  // Flash effect when price changes
  useEffect(() => {
    const newFlashing = new Set<string>()
    Object.keys(data).forEach((symbol) => {
      newFlashing.add(symbol)
    })
    setFlashingSymbols(newFlashing)

    const timer = setTimeout(() => {
      setFlashingSymbols(new Set())
    }, 200)

    return () => clearTimeout(timer)
  }, [data])

  return (
    <Card className={cn("trading-card", className)}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Live Market Data</h3>
          <Badge variant={isConnected ? "default" : "destructive"} className="text-xs">
            {isConnected ? "Live" : "Disconnected"}
          </Badge>
        </div>

        <div className="space-y-3">
          {symbols.map((symbol) => {
            const item = data[symbol]
            if (!item) return null

            const isPositive = item.change > 0
            const isNegative = item.change < 0
            const TrendIcon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus
            const isFlashing = flashingSymbols.has(symbol)

            return (
              <div
                key={symbol}
                className={cn(
                  "flex items-center justify-between p-2 rounded transition-colors",
                  isFlashing && "bg-accent/20",
                )}
              >
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm">{symbol}</span>
                  <TrendIcon
                    className={cn(
                      "h-3 w-3",
                      isPositive && "text-green-400",
                      isNegative && "text-red-400",
                      !isPositive && !isNegative && "text-muted-foreground",
                    )}
                  />
                </div>

                <div className="text-right">
                  <div className="font-mono text-sm font-semibold">${item.price.toFixed(2)}</div>
                  <div
                    className={cn(
                      "text-xs",
                      isPositive && "price-up",
                      isNegative && "price-down",
                      !isPositive && !isNegative && "price-neutral",
                    )}
                  >
                    {isPositive ? "+" : ""}
                    {item.change.toFixed(2)} ({isPositive ? "+" : ""}
                    {item.changePercent.toFixed(2)}%)
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
