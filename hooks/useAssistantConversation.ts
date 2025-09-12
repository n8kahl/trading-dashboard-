"use client"

import { useState, useRef, useEffect } from "react"

export interface AssistantMessage {
  id: string
  type: "user" | "assistant" | "system"
  content: string
  timestamp: Date
  actionType?: "buy" | "sell" | "hold" | "alert"
  symbol?: string
  confidence?: number
}

interface ApiResponse {
  content: string
  rationale?: string
}

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
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const addMessage = (message: AssistantMessage) => {
    setMessages((prev) => [...prev, message])
  }

  const sendMessage = async (input: string) => {
    if (!input.trim()) return

    const userMessage: AssistantMessage = {
      id: Date.now().toString(),
      type: "user",
      content: input,
      timestamp: new Date(),
    }

    addMessage(userMessage)
    setIsTyping(true)

    try {
      const response = await fetch("/api/assistant", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: input }),
      })

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`)
      }

      const data: ApiResponse = await response.json()

      const assistantMessage: AssistantMessage = {
        id: (Date.now() + 1).toString(),
        type: "assistant",
        content: data.content,
        timestamp: new Date(),
      }

      addMessage(assistantMessage)

      if (data.rationale) {
        const rationaleMessage: AssistantMessage = {
          id: (Date.now() + 2).toString(),
          type: "system",
          content: data.rationale,
          timestamp: new Date(),
        }
        addMessage(rationaleMessage)
      }
    } catch (err: any) {
      const errorMessage: AssistantMessage = {
        id: (Date.now() + 3).toString(),
        type: "system",
        content: `Error: ${err.message}`,
        timestamp: new Date(),
      }
      addMessage(errorMessage)
    } finally {
      setIsTyping(false)
    }
  }

  return { messages, isTyping, sendMessage, scrollRef, addMessage }
}

