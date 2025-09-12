"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Plus, X } from "lucide-react"

const orders = [
  {
    id: "1",
    symbol: "AAPL",
    side: "buy",
    quantity: 50,
    orderType: "limit",
    price: 185.0,
    status: "pending",
    timeInForce: "GTC",
  },
  {
    id: "2",
    symbol: "TSLA",
    side: "sell",
    quantity: 25,
    orderType: "stop",
    price: 240.0,
    status: "pending",
    timeInForce: "DAY",
  },
]

export function OrdersPanel() {
  return (
    <Card className="trading-card">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Open Orders
          <Button size="sm" variant="outline">
            <Plus className="h-4 w-4" />
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {orders.map((order) => (
            <div
              key={order.id}
              className="flex items-center justify-between p-3 rounded-lg border border-border bg-muted/20"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm">{order.symbol}</span>
                  <Badge variant={order.side === "buy" ? "default" : "secondary"} className="text-xs">
                    {order.side.toUpperCase()}
                  </Badge>
                  <Badge variant="outline" className="text-xs">
                    {order.orderType.toUpperCase()}
                  </Badge>
                </div>
                <div className="text-xs text-muted-foreground">
                  {order.quantity} @ ${order.price.toFixed(2)} • {order.timeInForce}
                </div>
              </div>

              <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive">
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}

          {orders.length === 0 && <div className="text-center py-6 text-muted-foreground text-sm">No open orders</div>}
        </div>
      </CardContent>
    </Card>
  )
}
