"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { AlertTriangle, Calculator, TrendingUp, TrendingDown } from "lucide-react"
import { cn } from "@/lib/utils"
import { useTickerData } from "@/hooks/use-market-data"

interface TradeExecutionPanelProps {
  symbol?: string
}

export function TradeExecutionPanel({ symbol = "AAPL" }: TradeExecutionPanelProps) {
  const [orderType, setOrderType] = useState<"market" | "limit" | "stop">("market")
  const [side, setSide] = useState<"buy" | "sell">("buy")
  const [quantity, setQuantity] = useState("")
  const [price, setPrice] = useState("")
  const [stopPrice, setStopPrice] = useState("")
  const [timeInForce, setTimeInForce] = useState("DAY")

  const { data: tickerData } = useTickerData(symbol)

  const calculateOrderValue = () => {
    const qty = Number.parseInt(quantity) || 0
    const orderPrice = orderType === "market" ? tickerData?.price || 0 : Number.parseFloat(price) || 0
    return qty * orderPrice
  }

  const handleSubmitOrder = async () => {
    const orderData = {
      symbol,
      side,
      quantity: Number.parseInt(quantity),
      orderType,
      price: orderType !== "market" ? Number.parseFloat(price) : undefined,
      stopPrice: orderType === "stop" ? Number.parseFloat(stopPrice) : undefined,
      timeInForce,
      preview: true, // Always preview first
    }

    try {
      // This would call your backend API
      console.log("Submitting order:", orderData)
      // const response = await fetch('/api/v1/broker/tradier/order', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(orderData)
      // })
    } catch (error) {
      console.error("Order submission failed:", error)
    }
  }

  return (
    <Card className="trading-card">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Trade Execution
          <Badge variant="outline" className="text-xs">
            {symbol} ${tickerData?.price.toFixed(2) || "---"}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Tabs value={side} onValueChange={(value) => setSide(value as "buy" | "sell")}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="buy" className="text-green-400 data-[state=active]:bg-green-400/20">
              <TrendingUp className="h-4 w-4 mr-2" />
              Buy
            </TabsTrigger>
            <TabsTrigger value="sell" className="text-red-400 data-[state=active]:bg-red-400/20">
              <TrendingDown className="h-4 w-4 mr-2" />
              Sell
            </TabsTrigger>
          </TabsList>

          <TabsContent value={side} className="space-y-4 mt-4">
            {/* Symbol Input */}
            <div className="space-y-2">
              <Label htmlFor="symbol">Symbol</Label>
              <Input id="symbol" value={symbol} className="font-mono" readOnly />
            </div>

            {/* Order Type */}
            <div className="space-y-2">
              <Label htmlFor="orderType">Order Type</Label>
              <Select value={orderType} onValueChange={(value) => setOrderType(value as any)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="market">Market</SelectItem>
                  <SelectItem value="limit">Limit</SelectItem>
                  <SelectItem value="stop">Stop</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Quantity */}
            <div className="space-y-2">
              <Label htmlFor="quantity">Quantity</Label>
              <Input
                id="quantity"
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="0"
                className="font-mono"
              />
            </div>

            {/* Price (for limit orders) */}
            {orderType === "limit" && (
              <div className="space-y-2">
                <Label htmlFor="price">Limit Price</Label>
                <div className="flex gap-2">
                  <Input
                    id="price"
                    type="number"
                    step="0.01"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    placeholder="0.00"
                    className="font-mono"
                  />
                  <Button variant="outline" size="sm" onClick={() => setPrice(tickerData?.bid.toFixed(2) || "")}>
                    Bid
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setPrice(tickerData?.ask.toFixed(2) || "")}>
                    Ask
                  </Button>
                </div>
              </div>
            )}

            {/* Stop Price (for stop orders) */}
            {orderType === "stop" && (
              <div className="space-y-2">
                <Label htmlFor="stopPrice">Stop Price</Label>
                <Input
                  id="stopPrice"
                  type="number"
                  step="0.01"
                  value={stopPrice}
                  onChange={(e) => setStopPrice(e.target.value)}
                  placeholder="0.00"
                  className="font-mono"
                />
              </div>
            )}

            {/* Time in Force */}
            <div className="space-y-2">
              <Label htmlFor="timeInForce">Time in Force</Label>
              <Select value={timeInForce} onValueChange={setTimeInForce}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="DAY">Day</SelectItem>
                  <SelectItem value="GTC">Good Till Canceled</SelectItem>
                  <SelectItem value="IOC">Immediate or Cancel</SelectItem>
                  <SelectItem value="FOK">Fill or Kill</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Separator />

            {/* Order Summary */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Estimated Value:</span>
                <span className="font-mono">${calculateOrderValue().toFixed(2)}</span>
              </div>
              {tickerData && (
                <>
                  <div className="flex justify-between text-sm">
                    <span>Current Bid/Ask:</span>
                    <span className="font-mono">
                      ${tickerData.bid.toFixed(2)} / ${tickerData.ask.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Spread:</span>
                    <span className="font-mono">${(tickerData.ask - tickerData.bid).toFixed(2)}</span>
                  </div>
                </>
              )}
            </div>

            {/* Risk Warning */}
            <div className="flex items-start gap-2 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
              <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
              <div className="text-xs text-yellow-500">
                <p className="font-medium">Sandbox Mode</p>
                <p>This is a simulated trading environment. No real money will be exchanged.</p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1 bg-transparent"
                onClick={handleSubmitOrder}
                disabled={!quantity || (orderType !== "market" && !price)}
              >
                <Calculator className="h-4 w-4 mr-2" />
                Preview Order
              </Button>
              <Button
                className={cn(
                  "flex-1",
                  side === "buy" ? "bg-green-600 hover:bg-green-700" : "bg-red-600 hover:bg-red-700",
                )}
                onClick={handleSubmitOrder}
                disabled={!quantity || (orderType !== "market" && !price)}
              >
                {side === "buy" ? "Buy" : "Sell"} {symbol}
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
