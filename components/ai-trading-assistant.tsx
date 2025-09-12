"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Bot, Send, TrendingUp, TrendingDown, AlertTriangle, Lightbulb, Zap } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAssistantConversation, AssistantMessage } from "@/hooks/useAssistantConversation"

interface TradingSignal {
  symbol: string
  action: "buy" | "sell" | "hold"
  price: number
  confidence: number
  reason: string
  timestamp: Date
}

export function AITradingAssistant() {
  const [input, setInput] = useState("")
  const [signals, setSignals] = useState<TradingSignal[]>([])
  const { messages, isTyping, sendMessage, scrollRef, addMessage } = useAssistantConversation()

  // Simulate live trading signals
  useEffect(() => {
    const generateSignal = () => {
      const symbols = ["AAPL", "TSLA", "SPY", "QQQ", "NVDA", "MSFT"]
      const actions = ["buy", "sell", "hold"] as const
      const reasons = [
        "Technical breakout detected",
        "Volume surge with price confirmation",
        "RSI oversold condition",
        "Support level holding strong",
        "Resistance level broken",
        "Moving average crossover",
        "Unusual options activity",
        "Earnings momentum play",
      ]

      const symbol = symbols[Math.floor(Math.random() * symbols.length)]
      const action = actions[Math.floor(Math.random() * actions.length)]
      const confidence = Math.floor(Math.random() * 40) + 60 // 60-100%
      const reason = reasons[Math.floor(Math.random() * reasons.length)]

      const signal: TradingSignal = {
        symbol,
        action,
        price: 100 + Math.random() * 400,
        confidence,
        reason,
        timestamp: new Date(),
      }

      setSignals((prev) => [signal, ...prev.slice(0, 4)]) // Keep last 5 signals

      // Add assistant message for significant signals
      if (confidence > 80) {
        const message: AssistantMessage = {
          id: Date.now().toString(),
          type: "assistant",
          content: `🎯 High confidence ${action.toUpperCase()} signal for ${symbol} at $${signal.price.toFixed(2)}. ${reason}. Confidence: ${confidence}%`,
          timestamp: new Date(),
          actionType: action,
          symbol,
          confidence,
        }
        addMessage(message)
      }
    }

    const interval = setInterval(generateSignal, 8000 + Math.random() * 12000) // 8-20 seconds
    return () => clearInterval(interval)
  }, [])

  const handleSend = async () => {
    if (!input.trim()) return
    await sendMessage(input)
    setInput("")
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
          <div className="space-y-2">
            {signals.slice(0, 3).map((signal, index) => (
              <div
                key={index}
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
              Online
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
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
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                className="text-xs"
              />
              <Button size="sm" onClick={handleSend} disabled={!input.trim() || isTyping}>
                <Send className="h-3 w-3" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
