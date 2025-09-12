"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Plus, Search, Star } from "lucide-react"
import { cn } from "@/lib/utils"
import { useState } from "react"

const watchlistItems = [
  { symbol: "NVDA", price: 875.3, change: 12.45, changePercent: 1.44, starred: true },
  { symbol: "MSFT", price: 378.85, change: -2.15, changePercent: -0.56, starred: false },
  { symbol: "GOOGL", price: 142.56, change: 0.87, changePercent: 0.61, starred: true },
  { symbol: "AMZN", price: 155.89, change: -1.23, changePercent: -0.78, starred: false },
  { symbol: "META", price: 485.67, change: 8.92, changePercent: 1.87, starred: true },
]

export function WatchlistPanel() {
  const [searchTerm, setSearchTerm] = useState("")

  return (
    <Card className="trading-card">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Watchlist
          <Button size="sm" variant="outline">
            <Plus className="h-4 w-4" />
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search symbols..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>

          <div className="space-y-2">
            {watchlistItems.map((item) => {
              const isPositive = item.change > 0

              return (
                <div
                  key={item.symbol}
                  className="flex items-center justify-between p-2 rounded hover:bg-muted/50 cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm" className="p-0 h-auto">
                      <Star
                        className={cn(
                          "h-4 w-4",
                          item.starred ? "fill-yellow-400 text-yellow-400" : "text-muted-foreground",
                        )}
                      />
                    </Button>
                    <div>
                      <div className="font-semibold text-sm">{item.symbol}</div>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="font-mono text-sm">${item.price.toFixed(2)}</div>
                    <div className={cn("text-xs", isPositive ? "price-up" : "price-down")}>
                      {isPositive ? "+" : ""}
                      {item.changePercent.toFixed(2)}%
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
