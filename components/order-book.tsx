"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { useEffect, useState } from "react"

interface OrderBookEntry {
  price: number
  size: number
  orders: number
  total: number
}

interface OrderBookProps {
  symbol: string
}

export function OrderBook({ symbol }: OrderBookProps) {
  const [bids, setBids] = useState<OrderBookEntry[]>([])
  const [asks, setAsks] = useState<OrderBookEntry[]>([])
  const [lastPrice, setLastPrice] = useState(187.25)
  const [spread, setSpread] = useState(0)

  useEffect(() => {
    const generateOrderBook = () => {
      const basePrice = 187.25
      const newBids: OrderBookEntry[] = []
      const newAsks: OrderBookEntry[] = []
      let bidTotal = 0
      let askTotal = 0

      // Generate bids (descending from highest to lowest)
      for (let i = 0; i < 15; i++) {
        const size = Math.floor(Math.random() * 500) + 100
        bidTotal += size
        newBids.push({
          price: basePrice - (i + 1) * 0.01,
          size,
          orders: Math.floor(Math.random() * 5) + 1,
          total: bidTotal,
        })
      }

      // Generate asks (ascending from lowest to highest)
      for (let i = 0; i < 15; i++) {
        const size = Math.floor(Math.random() * 500) + 100
        askTotal += size
        newAsks.push({
          price: basePrice + (i + 1) * 0.01,
          size,
          orders: Math.floor(Math.random() * 5) + 1,
          total: askTotal,
        })
      }

      setBids(newBids)
      setAsks(newAsks)
      setSpread(newAsks[0]?.price - newBids[0]?.price || 0)
      setLastPrice(basePrice + (Math.random() - 0.5) * 0.1)
    }

    generateOrderBook()
    const interval = setInterval(generateOrderBook, 2000)

    return () => clearInterval(interval)
  }, [symbol])

  const maxBidTotal = Math.max(...bids.map((b) => b.total))
  const maxAskTotal = Math.max(...asks.map((a) => a.total))

  return (
    <Card className="trading-card">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Order Book - {symbol}
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              Spread: ${spread.toFixed(2)}
            </Badge>
            <Badge variant="default" className="text-xs">
              Last: ${lastPrice.toFixed(2)}
            </Badge>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Header */}
          <div className="grid grid-cols-4 gap-2 text-xs font-medium text-muted-foreground border-b pb-2">
            <div>Price</div>
            <div className="text-right">Size</div>
            <div className="text-right">Orders</div>
            <div className="text-right">Total</div>
          </div>

          {/* Asks (sell orders) - shown in reverse order */}
          <div className="space-y-1">
            <div className="text-xs font-medium text-red-400 mb-2">Asks</div>
            {asks
              .slice(0, 8)
              .reverse()
              .map((ask, index) => (
                <div key={`ask-${index}`} className="relative">
                  <Progress
                    value={(ask.total / maxAskTotal) * 100}
                    className="absolute inset-0 h-full opacity-20"
                    style={{ backgroundColor: "rgba(239, 68, 68, 0.1)" }}
                  />
                  <div className="relative grid grid-cols-4 gap-2 text-xs py-1 px-2">
                    <div className="font-mono text-red-400">{ask.price.toFixed(2)}</div>
                    <div className="text-right font-mono">{ask.size.toLocaleString()}</div>
                    <div className="text-right text-muted-foreground">{ask.orders}</div>
                    <div className="text-right font-mono text-muted-foreground">{ask.total.toLocaleString()}</div>
                  </div>
                </div>
              ))}
          </div>

          {/* Current Price */}
          <div className="flex items-center justify-center py-2 border-y border-border">
            <Badge variant="secondary" className="font-mono">
              ${lastPrice.toFixed(2)}
            </Badge>
          </div>

          {/* Bids (buy orders) */}
          <div className="space-y-1">
            <div className="text-xs font-medium text-green-400 mb-2">Bids</div>
            {bids.slice(0, 8).map((bid, index) => (
              <div key={`bid-${index}`} className="relative">
                <Progress
                  value={(bid.total / maxBidTotal) * 100}
                  className="absolute inset-0 h-full opacity-20"
                  style={{ backgroundColor: "rgba(34, 197, 94, 0.1)" }}
                />
                <div className="relative grid grid-cols-4 gap-2 text-xs py-1 px-2">
                  <div className="font-mono text-green-400">{bid.price.toFixed(2)}</div>
                  <div className="text-right font-mono">{bid.size.toLocaleString()}</div>
                  <div className="text-right text-muted-foreground">{bid.orders}</div>
                  <div className="text-right font-mono text-muted-foreground">{bid.total.toLocaleString()}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
