export interface AssistantMessage {
  id: string
  type: "user" | "assistant" | "system"
  content: string
  rationale: string
  timestamp: Date
  actionType?: "buy" | "sell" | "hold" | "alert"
  symbol?: string
  confidence?: number
}

export interface TradingSignal {
  symbol: string
  action: "buy" | "sell" | "hold"
  price: number
  confidence: number
  reason: string
  timestamp: Date
}

export function createAssistantReply(
  content: string,
  rationale: string,
  extras: Partial<AssistantMessage> = {},
): AssistantMessage {
  return {
    id: Date.now().toString(),
    type: "assistant",
    content,
    rationale,
    timestamp: new Date(),
    ...extras,
  }
}

export function createSignalMessage(signal: TradingSignal): AssistantMessage {
  return createAssistantReply(
    `🎯 High confidence ${signal.action.toUpperCase()} signal for ${signal.symbol} at $${signal.price.toFixed(2)}. ${signal.reason}. Confidence: ${signal.confidence}%`,
    `Signal generated due to ${signal.reason}. Confidence ${signal.confidence}%.`,
    {
      actionType: signal.action,
      symbol: signal.symbol,
      confidence: signal.confidence,
    },
  )
}
