"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Layout, Eye, EyeOff, Move, RotateCcw } from "lucide-react"

interface DashboardWidget {
  id: string
  name: string
  enabled: boolean
  position: { x: number; y: number }
  size: { width: number; height: number }
}

export function DashboardConfig() {
  const [widgets, setWidgets] = useState<DashboardWidget[]>([
    {
      id: "market-overview",
      name: "Market Overview",
      enabled: true,
      position: { x: 0, y: 0 },
      size: { width: 12, height: 2 },
    },
    { id: "positions", name: "Positions", enabled: true, position: { x: 0, y: 2 }, size: { width: 8, height: 4 } },
    { id: "watchlist", name: "Watchlist", enabled: true, position: { x: 8, y: 2 }, size: { width: 4, height: 4 } },
    {
      id: "performance",
      name: "Performance Chart",
      enabled: true,
      position: { x: 0, y: 6 },
      size: { width: 8, height: 4 },
    },
    { id: "orders", name: "Open Orders", enabled: true, position: { x: 8, y: 6 }, size: { width: 4, height: 4 } },
    {
      id: "real-time-ticker",
      name: "Real-Time Ticker",
      enabled: true,
      position: { x: 0, y: 10 },
      size: { width: 4, height: 2 },
    },
    { id: "level2", name: "Level 2 Data", enabled: false, position: { x: 4, y: 10 }, size: { width: 4, height: 2 } },
    {
      id: "market-depth",
      name: "Market Depth",
      enabled: false,
      position: { x: 8, y: 10 },
      size: { width: 4, height: 2 },
    },
  ])

  const toggleWidget = (id: string) => {
    setWidgets((prev) => prev.map((widget) => (widget.id === id ? { ...widget, enabled: !widget.enabled } : widget)))
  }

  const resetLayout = () => {
    // Reset to default layout
    console.log("Resetting dashboard layout")
  }

  const saveLayout = () => {
    localStorage.setItem("dashboardLayout", JSON.stringify(widgets))
    console.log("Dashboard layout saved")
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Layout className="h-6 w-6" />
          Dashboard Configuration
        </h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={resetLayout}>
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset Layout
          </Button>
          <Button size="sm" onClick={saveLayout}>
            Save Layout
          </Button>
        </div>
      </div>

      <Card className="trading-card">
        <CardHeader>
          <CardTitle>Widget Visibility</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {widgets.map((widget) => (
              <div key={widget.id} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {widget.enabled ? (
                    <Eye className="h-4 w-4 text-green-400" />
                  ) : (
                    <EyeOff className="h-4 w-4 text-muted-foreground" />
                  )}
                  <div>
                    <Label className="font-medium">{widget.name}</Label>
                    <p className="text-xs text-muted-foreground">
                      Position: {widget.position.x}, {widget.position.y} • Size: {widget.size.width}x
                      {widget.size.height}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={widget.enabled ? "default" : "secondary"} className="text-xs">
                    {widget.enabled ? "Visible" : "Hidden"}
                  </Badge>
                  <Switch checked={widget.enabled} onCheckedChange={() => toggleWidget(widget.id)} />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="trading-card">
        <CardHeader>
          <CardTitle>Layout Options</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Button variant="outline" className="h-20 flex flex-col items-center justify-center gap-2 bg-transparent">
              <Layout className="h-6 w-6" />
              <span className="text-sm">Compact Layout</span>
            </Button>
            <Button variant="outline" className="h-20 flex flex-col items-center justify-center gap-2 bg-transparent">
              <Move className="h-6 w-6" />
              <span className="text-sm">Expanded Layout</span>
            </Button>
          </div>

          <Separator />

          <div className="text-sm text-muted-foreground">
            <p>• Drag and drop widgets to rearrange them</p>
            <p>• Resize widgets by dragging the corners</p>
            <p>• Toggle widget visibility using the switches above</p>
            <p>• Changes are automatically saved to your browser</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
