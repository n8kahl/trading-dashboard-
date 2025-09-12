"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

const performanceData = [
  { time: "09:30", pnl: 0, cumulative: 10000 },
  { time: "10:00", pnl: 150, cumulative: 10150 },
  { time: "10:30", pnl: -75, cumulative: 10075 },
  { time: "11:00", pnl: 225, cumulative: 10300 },
  { time: "11:30", pnl: 180, cumulative: 10480 },
  { time: "12:00", pnl: 320, cumulative: 10800 },
  { time: "12:30", pnl: 275, cumulative: 10555 },
  { time: "13:00", pnl: 420, cumulative: 10975 },
  { time: "13:30", pnl: 380, cumulative: 10935 },
  { time: "14:00", pnl: 486, cumulative: 11041 },
]

export function PerformanceChart() {
  return (
    <Card className="trading-card">
      <CardHeader>
        <CardTitle>Daily P&L</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={performanceData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="time" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickFormatter={(value) => `$${value}`} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "6px",
                  color: "hsl(var(--popover-foreground))",
                }}
                formatter={(value: number) => [`$${value.toFixed(2)}`, "P&L"]}
              />
              <Line type="monotone" dataKey="pnl" stroke="hsl(var(--chart-2))" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
