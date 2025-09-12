"use client"

import { useState, useEffect, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Bot, Send, TrendingUp, TrendingDown, AlertTriangle, Lightbulb, Zap } from "lucide-react"
import { cn } from "@/lib/utils"
import { useLiveMarketData } from "@/hooks/use-live-market-data"

interface AssistantMessage {
  id: string
  type: "user" | "assistant" | "system"
  content: string
  timestamp: Date
  actionType?: "buy" | "sell" | "hold" | "alert"
  symbol?: string
  confidence?: number
}

interface TradingSignal {
  symbol: string
  action: "buy" | "sell" | "hold"
  price: number
  confidence: number
  reason: string
  timestamp: Date
}

const DEFAULT_SYMBOLS = ["AAPL", "TSLA", "SPY", "QQQ", "NVDA", "MSFT"]

export function AITradingAssistant() {
  const [messages, setMessages] = useState<AssistantMessage[]>([
    {
      id: "1",
      type: "system",
      content: "Trading Assistant initialized. Monitoring market conditions...",
      timestamp: new Date(),
    },
    {
      id: "2",
      type: "assistant",
      content:
        "Good morning! I'm analyzing current market conditions. SPY is showing bullish momentum with volume confirmation. Consider watching for pullback entries.",
      timestamp: new Date(),
      actionType: "alert",
      symbol: "SPY",
      confidence: 75,
    },
  ])

  const [input, setInput] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const [signals, setSignals] = useState<TradingSignal[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)

  const { marketData, connectionStatus, error } = useLiveMarketData(DEFAULT_SYMBOLS)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // Update signals from live market data stream
  useEffect(() => {
    const latest = Object.values(marketData).sort((a, b) => b.timestamp - a.timestamp)[0]
    if (!latest) return

    const action = latest.change > 0 ? "buy" : latest.change < 0 ? "sell" : "hold"
    const reason =
      action === "buy"
        ? "Price momentum increasing"
        : action === "sell"
          ? "Price momentum decreasing"
          : "No significant change"
    const confidence = Math.min(Math.round(Math.abs(latest.changePercent)), 100)

    const signal: TradingSignal = {
      symbol: latest.symbol,
      action,
      price: latest.price,
      confidence,
      reason,
      timestamp: new Date(),
    }

    setSignals((prev) => [signal, ...prev.slice(0, 4)])

    if (confidence > 80) {
      const message: AssistantMessage = {
        id: Date.now().toString(),
        type: "assistant",
        content: `🎯 High confidence ${action.toUpperCase()} signal for ${latest.symbol} at $${latest.price.toFixed(2)}. ${reason}. Confidence: ${confidence}%`,
        timestamp: new Date(),
        actionType: action,
        symbol: latest.symbol,
        confidence,
      }
      setMessages((prev) => [...prev, message])
    }
  }, [marketData])

  const sendMessage = async () => {
    if (!input.trim()) return

    const userMessage: AssistantMessage = {
      id: Date.now().toString(),
      type: "user",
      content: input,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsTyping(true)

    // Simulate AI response
    setTimeout(() => {
      const responses = [
        "Based on current market conditions, I recommend monitoring SPY for a potential breakout above $446. Volume is increasing.",
        "AAPL is showing strong support at $185. Consider a long position with a stop at $183.",
        "Market volatility is elevated. Consider reducing position sizes and using tighter stops.",
        "TSLA options flow suggests bullish sentiment. Watch for momentum above $245.",
        "The VIX is declining, indicating reduced fear. This could support continued upward movement in equities.",
      ]

      const assistantMessage: AssistantMessage = {
        id: (Date.now() + 1).toString(),
        type: "assistant",
        content: responses[Math.floor(Math.random() * responses.length)],
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])
      setIsTyping(false)
    }, 1500)
  }

  const getActionIcon = (actionType?: string) => {
    switch (actionType) {
      case "buy":
        return <TrendingUp className="h-3 w-3 text-green-400" />
      case "sell":
        return <TrendingDown className="h-3 w-3 text-red-400" />
      case "alert":
        return <AlertTriangle className="h-3 w-3 text-yellow-400" />
      default:
        return <Lightbulb className="h-3 w-3 text-blue-400" />
    }
  }

  return (
    <div className="space-y-4">
      {/* Live Signals */}
      <Card className="trading-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Zap className="h-4 w-4" />
            Live Signals
          </CardTitle>
        </CardHeader>
        <CardContent>
          {connectionStatus === "error" || connectionStatus === "disconnected" ? (
            <div className="flex items-center gap-1 text-xs text-yellow-500 mb-2">
              <AlertTriangle className="h-3 w-3" />
              <span>{error || "Connection lost. Attempting to reconnect..."}</span>
            </div>
          ) : connectionStatus === "connecting" ? (
            <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
              <span>Connecting to market data...</span>
            </div>
          ) : null}
          <div className="space-y-2">
            {signals.slice(0, 3).map((signal) => (
              <div
                key={signal.timestamp.getTime()}
                className="flex items-center justify-between p-2 rounded bg-muted/20 border border-border"
              >
                <div className="flex items-center gap-2">
                  {signal.action === "buy" ? (
                    <TrendingUp className="h-3 w-3 text-green-400" />
                  ) : signal.action === "sell" ? (
                    <TrendingDown className="h-3 w-3 text-red-400" />
                  ) : (
                    <Lightbulb className="h-3 w-3 text-yellow-400" />
                  )}
                  <span className="font-semibold text-xs">{signal.symbol}</span>
                  <Badge
                    variant={
                      signal.action === "buy" ? "default" : signal.action === "sell" ? "destructive" : "secondary"
                    }
                    className="text-xs"
                  >
                    {signal.action.toUpperCase()}
                  </Badge>
                </div>
                <div className="text-right">
                  <div className="text-xs font-mono">${signal.price.toFixed(2)}</div>
                  <div className="text-xs text-muted-foreground">{signal.confidence}%</div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Chat Interface */}
      <Card className="trading-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Bot className="h-4 w-4" />
            AI Assistant
            <Badge variant="outline" className="text-xs ml-auto">
              {connectionStatus === "connected"
                ? "Online"
                : connectionStatus === "connecting"
                  ? "Connecting"
                  : connectionStatus === "error"
                    ? "Error"
                    : "Offline"}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {connectionStatus === "error" || connectionStatus === "disconnected" ? (
            <div className="flex items-center gap-1 text-xs text-yellow-500 mb-2 p-4">
              <AlertTriangle className="h-3 w-3" />
              <span>{error || "Connection lost. Responses may be delayed."}</span>
            </div>
          ) : null}
          <ScrollArea className="h-64 p-4" ref={scrollRef}>
            <div className="space-y-3">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn("flex gap-2", message.type === "user" ? "justify-end" : "justify-start")}
                >
                  <div
                    className={cn(
                      "max-w-[80%] rounded-lg p-2 text-xs",
                      message.type === "user"
                        ? "bg-primary text-primary-foreground"
                        : message.type === "system"
                          ? "bg-muted text-muted-foreground"
                          : "bg-muted",
                    )}
                  >
                    <div className="flex items-start gap-2">
                      {message.type === "assistant" && getActionIcon(message.actionType)}
                      <div className="flex-1">
                        <p>{message.content}</p>
                        <div className="flex items-center justify-between mt-1">
                          <span className="text-xs opacity-70">{message.timestamp.toLocaleTimeString()}</span>
                          {message.confidence && (
                            <Badge variant="outline" className="text-xs">
                              {message.confidence}%
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              {isTyping && (
                <div className="flex gap-2 justify-start">
                  <div className="bg-muted rounded-lg p-2 text-xs">
                    <div className="flex items-center gap-1">
                      <Bot className="h-3 w-3" />
                      <span>Assistant is typing...</span>
                      <div className="flex gap-1">
                        <div className="w-1 h-1 bg-current rounded-full animate-bounce" />
                        <div
                          className="w-1 h-1 bg-current rounded-full animate-bounce"
                          style={{ animationDelay: "0.1s" }}
                        />
                        <div
                          className="w-1 h-1 bg-current rounded-full animate-bounce"
                          style={{ animationDelay: "0.2s" }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>
          <Separator />
          <div className="p-4">
            <div className="flex gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about market conditions, strategies, or specific symbols..."
                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                className="text-xs"
              />
              <Button
                size="sm"
                onClick={sendMessage}
                disabled={!input.trim() || isTyping || connectionStatus !== "connected"}
              >
                <Send className="h-3 w-3" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
