"use client"

import { TradeExecutionPanel } from "@/components/trade-execution-panel"
import { OrderBook } from "@/components/order-book"
import { QuickTradeButtons } from "@/components/quick-trade-buttons"
import { AITradingAssistant } from "@/components/ai-trading-assistant"
import { MarketAlerts } from "@/components/market-alerts"

export function TradingAssistant() {
  return (
    <div className="p-4 space-y-4 h-full overflow-auto">
      <AITradingAssistant />
      <MarketAlerts />
      <TradeExecutionPanel symbol="AAPL" />
      <QuickTradeButtons symbol="AAPL" />
      <OrderBook symbol="AAPL" />
    </div>
  )
}
