"use client"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Bell, Settings, User, Wifi, WifiOff } from "lucide-react"
import { useState, useEffect } from "react"

export function TopBar() {
  const [isConnected, setIsConnected] = useState(true)
  const [currentTime, setCurrentTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <header className="col-span-3 bg-card border-b border-border flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-bold text-card-foreground">Trading Assistant Pro</h1>
        <Badge variant={isConnected ? "default" : "destructive"} className="flex items-center gap-1">
          {isConnected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
          {isConnected ? "Connected" : "Disconnected"}
        </Badge>
      </div>

      <div className="flex items-center gap-4">
        <div className="text-sm text-muted-foreground font-mono">
          {currentTime.toLocaleTimeString("en-US", {
            hour12: false,
            timeZone: "America/New_York",
          })}{" "}
          EST
        </div>
        <Button variant="ghost" size="sm">
          <Bell className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="sm">
          <Settings className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="sm">
          <User className="h-4 w-4" />
        </Button>
      </div>
    </header>
  )
}
