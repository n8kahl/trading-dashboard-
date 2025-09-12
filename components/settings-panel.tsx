"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { AlertTriangle, Save, RefreshCw, Shield, Bell, Palette, Database } from "lucide-react"

interface TradingSettings {
  // Risk Management
  maxDailyLoss: number
  maxPositionSize: number
  stopLossPercent: number
  takeProfitPercent: number

  // Trading Preferences
  defaultOrderType: "market" | "limit"
  defaultTimeInForce: "DAY" | "GTC" | "IOC" | "FOK"
  confirmOrders: boolean
  autoStopLoss: boolean

  // Display Settings
  theme: "dark" | "light" | "auto"
  refreshRate: number
  showAdvancedMetrics: boolean
  soundAlerts: boolean

  // API Settings
  tradierSandbox: boolean
  polygonApiKey: string
  tradierApiKey: string
}

export function SettingsPanel() {
  const [settings, setSettings] = useState<TradingSettings>({
    maxDailyLoss: 1000,
    maxPositionSize: 10000,
    stopLossPercent: 2,
    takeProfitPercent: 4,
    defaultOrderType: "limit",
    defaultTimeInForce: "DAY",
    confirmOrders: true,
    autoStopLoss: false,
    theme: "dark",
    refreshRate: 1000,
    showAdvancedMetrics: true,
    soundAlerts: true,
    tradierSandbox: true,
    polygonApiKey: "",
    tradierApiKey: "",
  })

  const [hasChanges, setHasChanges] = useState(false)

  const updateSetting = <K extends keyof TradingSettings>(key: K, value: TradingSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }))
    setHasChanges(true)
  }

  const saveSettings = () => {
    // Save to localStorage or API
    localStorage.setItem("tradingSettings", JSON.stringify(settings))
    setHasChanges(false)
    console.log("Settings saved:", settings)
  }

  const resetSettings = () => {
    // Reset to defaults
    setHasChanges(false)
    // Would reload from defaults
  }

  return (
    <div className="p-6 space-y-6 h-full overflow-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Settings</h1>
        <div className="flex items-center gap-2">
          {hasChanges && (
            <Badge variant="secondary" className="text-xs">
              Unsaved Changes
            </Badge>
          )}
          <Button variant="outline" size="sm" onClick={resetSettings}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Reset
          </Button>
          <Button size="sm" onClick={saveSettings} disabled={!hasChanges}>
            <Save className="h-4 w-4 mr-2" />
            Save Changes
          </Button>
        </div>
      </div>

      <Tabs defaultValue="risk" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="risk" className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Risk
          </TabsTrigger>
          <TabsTrigger value="trading" className="flex items-center gap-2">
            <Database className="h-4 w-4" />
            Trading
          </TabsTrigger>
          <TabsTrigger value="display" className="flex items-center gap-2">
            <Palette className="h-4 w-4" />
            Display
          </TabsTrigger>
          <TabsTrigger value="api" className="flex items-center gap-2">
            <Bell className="h-4 w-4" />
            API
          </TabsTrigger>
        </TabsList>

        {/* Risk Management */}
        <TabsContent value="risk">
          <Card className="trading-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Risk Management
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="maxDailyLoss">Max Daily Loss ($)</Label>
                  <Input
                    id="maxDailyLoss"
                    type="number"
                    value={settings.maxDailyLoss}
                    onChange={(e) => updateSetting("maxDailyLoss", Number.parseFloat(e.target.value))}
                    className="font-mono"
                  />
                  <p className="text-xs text-muted-foreground">
                    Trading will be disabled if daily losses exceed this amount
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="maxPositionSize">Max Position Size ($)</Label>
                  <Input
                    id="maxPositionSize"
                    type="number"
                    value={settings.maxPositionSize}
                    onChange={(e) => updateSetting("maxPositionSize", Number.parseFloat(e.target.value))}
                    className="font-mono"
                  />
                  <p className="text-xs text-muted-foreground">Maximum value for a single position</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="stopLossPercent">Default Stop Loss (%)</Label>
                  <Input
                    id="stopLossPercent"
                    type="number"
                    step="0.1"
                    value={settings.stopLossPercent}
                    onChange={(e) => updateSetting("stopLossPercent", Number.parseFloat(e.target.value))}
                    className="font-mono"
                  />
                  <p className="text-xs text-muted-foreground">Default stop loss percentage from entry</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="takeProfitPercent">Default Take Profit (%)</Label>
                  <Input
                    id="takeProfitPercent"
                    type="number"
                    step="0.1"
                    value={settings.takeProfitPercent}
                    onChange={(e) => updateSetting("takeProfitPercent", Number.parseFloat(e.target.value))}
                    className="font-mono"
                  />
                  <p className="text-xs text-muted-foreground">Default take profit percentage from entry</p>
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Auto Stop Loss</Label>
                    <p className="text-xs text-muted-foreground">
                      Automatically place stop loss orders on new positions
                    </p>
                  </div>
                  <Switch
                    checked={settings.autoStopLoss}
                    onCheckedChange={(checked) => updateSetting("autoStopLoss", checked)}
                  />
                </div>
              </div>

              <div className="flex items-start gap-2 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                <div className="text-xs text-yellow-500">
                  <p className="font-medium">Risk Warning</p>
                  <p>These settings help manage risk but do not guarantee protection against losses.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Trading Preferences */}
        <TabsContent value="trading">
          <Card className="trading-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                Trading Preferences
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="defaultOrderType">Default Order Type</Label>
                  <Select
                    value={settings.defaultOrderType}
                    onValueChange={(value) => updateSetting("defaultOrderType", value as any)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="market">Market</SelectItem>
                      <SelectItem value="limit">Limit</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="defaultTimeInForce">Default Time in Force</Label>
                  <Select
                    value={settings.defaultTimeInForce}
                    onValueChange={(value) => updateSetting("defaultTimeInForce", value as any)}
                  >
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
              </div>

              <Separator />

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Order Confirmation</Label>
                    <p className="text-xs text-muted-foreground">Require confirmation before placing orders</p>
                  </div>
                  <Switch
                    checked={settings.confirmOrders}
                    onCheckedChange={(checked) => updateSetting("confirmOrders", checked)}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Display Settings */}
        <TabsContent value="display">
          <Card className="trading-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Palette className="h-5 w-5" />
                Display Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="theme">Theme</Label>
                  <Select value={settings.theme} onValueChange={(value) => updateSetting("theme", value as any)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="dark">Dark</SelectItem>
                      <SelectItem value="light">Light</SelectItem>
                      <SelectItem value="auto">Auto</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="refreshRate">Refresh Rate (ms)</Label>
                  <Select
                    value={settings.refreshRate.toString()}
                    onValueChange={(value) => updateSetting("refreshRate", Number.parseInt(value))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="500">500ms (Fast)</SelectItem>
                      <SelectItem value="1000">1000ms (Normal)</SelectItem>
                      <SelectItem value="2000">2000ms (Slow)</SelectItem>
                      <SelectItem value="5000">5000ms (Very Slow)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Advanced Metrics</Label>
                    <p className="text-xs text-muted-foreground">Show advanced trading metrics and indicators</p>
                  </div>
                  <Switch
                    checked={settings.showAdvancedMetrics}
                    onCheckedChange={(checked) => updateSetting("showAdvancedMetrics", checked)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Sound Alerts</Label>
                    <p className="text-xs text-muted-foreground">Play sounds for order fills and alerts</p>
                  </div>
                  <Switch
                    checked={settings.soundAlerts}
                    onCheckedChange={(checked) => updateSetting("soundAlerts", checked)}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* API Settings */}
        <TabsContent value="api">
          <Card className="trading-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5" />
                API Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Tradier Sandbox Mode</Label>
                    <p className="text-xs text-muted-foreground">Use sandbox environment for safe testing</p>
                  </div>
                  <Switch
                    checked={settings.tradierSandbox}
                    onCheckedChange={(checked) => updateSetting("tradierSandbox", checked)}
                  />
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="polygonApiKey">Polygon API Key</Label>
                  <Input
                    id="polygonApiKey"
                    type="password"
                    value={settings.polygonApiKey}
                    onChange={(e) => updateSetting("polygonApiKey", e.target.value)}
                    placeholder="Enter your Polygon API key"
                  />
                  <p className="text-xs text-muted-foreground">Used for real-time market data</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="tradierApiKey">Tradier API Key</Label>
                  <Input
                    id="tradierApiKey"
                    type="password"
                    value={settings.tradierApiKey}
                    onChange={(e) => updateSetting("tradierApiKey", e.target.value)}
                    placeholder="Enter your Tradier API key"
                  />
                  <p className="text-xs text-muted-foreground">Used for order execution and account data</p>
                </div>
              </div>

              <div className="flex items-start gap-2 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                <AlertTriangle className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                <div className="text-xs text-blue-500">
                  <p className="font-medium">API Keys</p>
                  <p>API keys are stored locally and never transmitted to our servers.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
