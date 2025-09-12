"use client"
import { MarketOverview } from "@/components/market-overview"
import { PositionsPanel } from "@/components/positions-panel"
import { WatchlistPanel } from "@/components/watchlist-panel"
import { OrdersPanel } from "@/components/orders-panel"
import { PerformanceChart } from "@/components/performance-chart"
import { RealTimeTicker } from "@/components/real-time-ticker"
import { Level2Data } from "@/components/level-2-data"
import { MarketDepthChart } from "@/components/market-depth-chart"

export function TradingDashboard() {
  return (
    <div className="p-6 space-y-6 h-full overflow-auto">
      {/* Market Overview */}
      <MarketOverview />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <RealTimeTicker symbols={["SPY", "QQQ", "IWM", "VIX"]} />
        <Level2Data symbol="AAPL" />
        <MarketDepthChart symbol="AAPL" />
      </div>

      {/* Main Trading Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Positions & Performance */}
        <div className="lg:col-span-2 space-y-6">
          <PositionsPanel />
          <PerformanceChart />
        </div>

        {/* Right Column - Watchlist & Orders */}
        <div className="space-y-6">
          <WatchlistPanel />
          <OrdersPanel />
        </div>
      </div>
    </div>
  )
}
