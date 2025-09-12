"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { useEffect, useState } from "react"

interface DepthData {
  price: number
  bidDepth: number
  askDepth: number
}

interface MarketDepthChartProps {
  symbol: string
}

export function MarketDepthChart({ symbol }: MarketDepthChartProps) {
  const [depthData, setDepthData] = useState<DepthData[]>([])

  useEffect(() => {
    // Generate mock market depth data
    const generateDepthData = () => {
      const basePrice = 187.25
      const data: DepthData[] = []

      // Generate depth data around current price
      for (let i = -20; i <= 20; i++) {
        const price = basePrice + i * 0.05
        const distance = Math.abs(i)

        data.push({
          price,
          bidDepth: i <= 0 ? Math.max(0, 10000 - distance * 200 + Math.random() * 1000) : 0,
          askDepth: i >= 0 ? Math.max(0, 10000 - distance * 200 + Math.random() * 1000) : 0,
        })
      }

      setDepthData(data)
    }

    generateDepthData()
    const interval = setInterval(generateDepthData, 5000)

    return () => clearInterval(interval)
  }, [symbol])

  return (
    <Card className="trading-card">
      <CardHeader>
        <CardTitle>Market Depth - {symbol}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={depthData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="price"
                stroke="hsl(var(--muted-foreground))"
                fontSize={10}
                tickFormatter={(value) => `$${value.toFixed(2)}`}
              />
              <YAxis
                stroke="hsl(var(--muted-foreground))"
                fontSize={10}
                tickFormatter={(value) => `${(value / 1000).toFixed(0)}K`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "6px",
                  color: "hsl(var(--popover-foreground))",
                }}
                formatter={(value: number, name: string) => [
                  `${(value / 1000).toFixed(1)}K`,
                  name === "bidDepth" ? "Bid Depth" : "Ask Depth",
                ]}
                labelFormatter={(value) => `Price: $${value}`}
              />
              <Area type="monotone" dataKey="bidDepth" stackId="1" stroke="#22c55e" fill="#22c55e" fillOpacity={0.3} />
              <Area type="monotone" dataKey="askDepth" stackId="2" stroke="#ef4444" fill="#ef4444" fillOpacity={0.3} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
