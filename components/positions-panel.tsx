"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { MoreHorizontal, TrendingUp, TrendingDown } from "lucide-react"
import { cn } from "@/lib/utils"

const positions = [
  {
    symbol: "AAPL",
    quantity: 100,
    avgPrice: 185.5,
    currentPrice: 187.25,
    pnl: 175.0,
    pnlPercent: 0.94,
    side: "long",
  },
  {
    symbol: "TSLA",
    quantity: 50,
    avgPrice: 245.8,
    currentPrice: 242.15,
    pnl: -182.5,
    pnlPercent: -1.49,
    side: "long",
  },
  {
    symbol: "SPY",
    quantity: 200,
    avgPrice: 443.2,
    currentPrice: 445.67,
    pnl: 494.0,
    pnlPercent: 0.56,
    side: "long",
  },
]

export function PositionsPanel() {
  const totalPnl = positions.reduce((sum, pos) => sum + pos.pnl, 0)
  const totalValue = positions.reduce((sum, pos) => sum + pos.currentPrice * pos.quantity, 0)

  return (
    <Card className="trading-card">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Open Positions
          <div className="flex items-center gap-2">
            <Badge variant={totalPnl >= 0 ? "default" : "destructive"}>
              {totalPnl >= 0 ? "+" : ""}${totalPnl.toFixed(2)}
            </Badge>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {positions.map((position) => {
            const isProfit = position.pnl >= 0
            const marketValue = position.currentPrice * position.quantity

            return (
              <div
                key={position.symbol}
                className="flex items-center justify-between p-3 rounded-lg border border-border bg-muted/20"
              >
                <div className="flex items-center gap-3">
                  <div>
                    <div className="font-semibold">{position.symbol}</div>
                    <div className="text-sm text-muted-foreground">
                      {position.quantity} shares @ ${position.avgPrice.toFixed(2)}
                    </div>
                  </div>
                </div>

                <div className="text-right">
                  <div className="metric-value">${position.currentPrice.toFixed(2)}</div>
                  <div
                    className={cn("text-sm font-medium flex items-center gap-1", isProfit ? "price-up" : "price-down")}
                  >
                    {isProfit ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                    {isProfit ? "+" : ""}${position.pnl.toFixed(2)} ({isProfit ? "+" : ""}
                    {position.pnlPercent.toFixed(2)}%)
                  </div>
                </div>

                <Button variant="ghost" size="sm">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </div>
            )
          })}

          {positions.length === 0 && <div className="text-center py-8 text-muted-foreground">No open positions</div>}
        </div>
      </CardContent>
    </Card>
  )
}
