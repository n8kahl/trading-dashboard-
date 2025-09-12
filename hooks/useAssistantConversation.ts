import { useState } from "react"
import type { AssistantMessage } from "@/lib/types"

export function useAssistantConversation() {
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
  const [isTyping, setIsTyping] = useState(false)
  const [retryMessage, setRetryMessage] = useState<AssistantMessage | null>(null)

  const addSignalMessage = (message: AssistantMessage) => {
    setMessages((prev) => [...prev, message])
  }

  return {
    messages,
    setMessages,
    isTyping,
    setIsTyping,
    retryMessage,
    setRetryMessage,
    addSignalMessage,
  }
}
