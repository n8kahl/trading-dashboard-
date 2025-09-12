"use client"

import { useConnectionMonitor } from "@/hooks/use-connection-monitor"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Wifi, WifiOff, RefreshCw } from "lucide-react"

export function ConnectionStatus() {
  const { isOnline, apiHealthy, retryCount, retryConnection } = useConnectionMonitor()

  if (isOnline && apiHealthy) {
    return (
      <Badge variant="secondary" className="bg-green-100 text-green-800 border-green-200">
        <Wifi className="w-3 h-3 mr-1" />
        Connected
      </Badge>
    )
  }

  if (!isOnline) {
    return (
      <Badge variant="destructive">
        <WifiOff className="w-3 h-3 mr-1" />
        Offline
      </Badge>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <Badge variant="destructive">
        <WifiOff className="w-3 h-3 mr-1" />
        API Disconnected
      </Badge>
      {retryCount > 0 && retryCount < 5 && (
        <Button size="sm" variant="outline" onClick={retryConnection} className="h-6 px-2 text-xs bg-transparent">
          <RefreshCw className="w-3 h-3 mr-1" />
          Retry ({retryCount}/5)
        </Button>
      )}
    </div>
  )
}
