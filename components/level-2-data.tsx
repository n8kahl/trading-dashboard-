"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useEffect, useState } from "react"

interface OrderBookEntry {
  price: number
  size: number
  orders: number
}

interface Level2DataProps {
  symbol: string
}

export function Level2Data({ symbol }: Level2DataProps) {
  const [bids, setBids] = useState<OrderBookEntry[]>([])
  const [asks, setAsks] = useState<OrderBookEntry[]>([])
  const [spread, setSpread] = useState(0)

  useEffect(() => {
    // Mock Level 2 data generation
    const generateOrderBook = () => {
      const basePrice = 187.25
      const newBids: OrderBookEntry[] = []
      const newAsks: OrderBookEntry[] = []

      // Generate bids (below current price)
      for (let i = 0; i < 10; i++) {
        newBids.push({
          price: basePrice - (i + 1) * 0.01,
          size: Math.floor(Math.random() * 1000) + 100,
          orders: Math.floor(Math.random() * 10) + 1,
        })
      }

      // Generate asks (above current price)
      for (let i = 0; i < 10; i++) {
        newAsks.push({
          price: basePrice + (i + 1) * 0.01,
          size: Math.floor(Math.random() * 1000) + 100,
          orders: Math.floor(Math.random() * 10) + 1,
        })
      }

      setBids(newBids)
      setAsks(newAsks)
      setSpread(newAsks[0]?.price - newBids[0]?.price || 0)
    }

    generateOrderBook()
    const interval = setInterval(generateOrderBook, 3000)

    return () => clearInterval(interval)
  }, [symbol])

  return (
    <Card className="trading-card">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Level 2 - {symbol}
          <Badge variant="outline" className="text-xs">
            Spread: ${spread.toFixed(2)}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          {/* Bids */}
          <div>
            <h4 className="text-sm font-semibold mb-2 text-green-400">Bids</h4>
            <div className="space-y-1">
              {bids.slice(0, 5).map((bid, index) => (
                <div key={index} className="flex justify-between text-xs">
                  <span className="font-mono">${bid.price.toFixed(2)}</span>
                  <span className="text-muted-foreground">{bid.size}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Asks */}
          <div>
            <h4 className="text-sm font-semibold mb-2 text-red-400">Asks</h4>
            <div className="space-y-1">
              {asks.slice(0, 5).map((ask, index) => (
                <div key={index} className="flex justify-between text-xs">
                  <span className="font-mono">${ask.price.toFixed(2)}</span>
                  <span className="text-muted-foreground">{ask.size}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
