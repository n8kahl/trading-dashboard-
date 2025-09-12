"use client"

import { useState } from "react"
import { TradingDashboard } from "@/components/trading-dashboard"
import { Sidebar } from "@/components/sidebar"
import { TopBar } from "@/components/top-bar"
import { TradingAssistant } from "@/components/trading-assistant"
import { SettingsPanel } from "@/components/settings-panel"
import { DashboardConfig } from "@/components/dashboard-config"
import { ConnectionStatus } from "@/components/connection-status"
import { useErrorHandler } from "@/hooks/use-error-handler"
import { Toaster } from "sonner"

export default function HomePage() {
  const [activeView, setActiveView] = useState("dashboard")
  const { handleError } = useErrorHandler()

  const renderMainContent = () => {
    switch (activeView) {
      case "dashboard":
        return <TradingDashboard />
      case "settings":
        return <SettingsPanel />
      case "config":
        return <DashboardConfig />
      default:
        return <TradingDashboard />
    }
  }

  return (
    <div className="trading-grid">
      <TopBar />
      <Sidebar activeView={activeView} onViewChange={setActiveView} />
      <main className="bg-background overflow-hidden">{renderMainContent()}</main>
      <aside className="bg-card border-l border-border">
        <TradingAssistant />
      </aside>
      <div className="fixed bottom-4 right-4 z-50">
        <ConnectionStatus />
      </div>
      <Toaster position="top-right" />
    </div>
  )
}
