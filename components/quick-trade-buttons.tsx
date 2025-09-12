"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, TrendingDown, Zap } from "lucide-react"
import { useTickerData } from "@/hooks/use-market-data"

interface QuickTradeButtonsProps {
  symbol: string
  onTrade?: (side: "buy" | "sell", quantity: number) => void
}

const quickSizes = [10, 25, 50, 100, 250, 500]

export function QuickTradeButtons({ symbol, onTrade }: QuickTradeButtonsProps) {
  const { data: tickerData } = useTickerData(symbol)

  const handleQuickTrade = (side: "buy" | "sell", quantity: number) => {
    if (onTrade) {
      onTrade(side, quantity)
    } else {
      // Default behavior - log the trade
      console.log(`Quick ${side} ${quantity} shares of ${symbol}`)
    }
  }

  return (
    <Card className="trading-card">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4" />
            Quick Trade - {symbol}
          </div>
          <Badge variant="outline" className="text-xs">
            ${tickerData?.price.toFixed(2) || "---"}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Buy Buttons */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium text-green-400">
            <TrendingUp className="h-4 w-4" />
            Quick Buy
          </div>
          <div className="grid grid-cols-3 gap-2">
            {quickSizes.map((size) => (
              <Button
                key={`buy-${size}`}
                variant="outline"
                size="sm"
                className="text-green-400 border-green-400/20 hover:bg-green-400/10 bg-transparent"
                onClick={() => handleQuickTrade("buy", size)}
              >
                {size}
              </Button>
            ))}
          </div>
        </div>

        {/* Sell Buttons */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium text-red-400">
            <TrendingDown className="h-4 w-4" />
            Quick Sell
          </div>
          <div className="grid grid-cols-3 gap-2">
            {quickSizes.map((size) => (
              <Button
                key={`sell-${size}`}
                variant="outline"
                size="sm"
                className="text-red-400 border-red-400/20 hover:bg-red-400/10 bg-transparent"
                onClick={() => handleQuickTrade("sell", size)}
              >
                {size}
              </Button>
            ))}
          </div>
        </div>

        {/* Market Info */}
        {tickerData && (
          <div className="pt-2 border-t border-border">
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <div className="text-muted-foreground">Bid</div>
                <div className="font-mono text-green-400">${tickerData.bid.toFixed(2)}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Ask</div>
                <div className="font-mono text-red-400">${tickerData.ask.toFixed(2)}</div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
