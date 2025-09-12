"use client"

import { useProductionReady } from "@/hooks/use-production-ready"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { CheckCircle, XCircle, AlertTriangle } from "lucide-react"
import { useState } from "react"

export function ProductionStatus() {
  const status = useProductionReady()
  const [showDetails, setShowDetails] = useState(false)

  if (!showDetails) {
    return (
      <Button variant="ghost" size="sm" onClick={() => setShowDetails(true)} className="h-8">
        {status.isReady ? (
          <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
        ) : (
          <AlertTriangle className="w-4 h-4 text-yellow-500 mr-2" />
        )}
        Production Status
      </Button>
    )
  }

  return (
    <Card className="w-80">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Production Status</CardTitle>
          <Button variant="ghost" size="sm" onClick={() => setShowDetails(false)} className="h-6 w-6 p-0">
            ×
          </Button>
        </div>
        <CardDescription>System readiness for live trading</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          {Object.entries(status.checks).map(([check, passed]) => (
            <div key={check} className="flex items-center justify-between">
              <span className="text-sm capitalize">{check.replace(/([A-Z])/g, " $1").trim()}</span>
              {passed ? (
                <CheckCircle className="w-4 h-4 text-green-500" />
              ) : (
                <XCircle className="w-4 h-4 text-red-500" />
              )}
            </div>
          ))}
        </div>

        {status.warnings.length > 0 && (
          <div className="space-y-1">
            <h4 className="text-sm font-medium text-yellow-600">Warnings:</h4>
            {status.warnings.map((warning, i) => (
              <p key={i} className="text-xs text-yellow-600">
                • {warning}
              </p>
            ))}
          </div>
        )}

        {status.errors.length > 0 && (
          <div className="space-y-1">
            <h4 className="text-sm font-medium text-red-600">Errors:</h4>
            {status.errors.map((error, i) => (
              <p key={i} className="text-xs text-red-600">
                • {error}
              </p>
            ))}
          </div>
        )}

        <Badge variant={status.isReady ? "default" : "destructive"} className="w-full justify-center">
          {status.isReady ? "Production Ready" : "Not Ready"}
        </Badge>
      </CardContent>
    </Card>
  )
}
