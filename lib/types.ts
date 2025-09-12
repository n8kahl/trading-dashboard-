export interface AssistantMessage {
  id: string
  type: "user" | "assistant" | "system"
  content: string
  timestamp: Date
  actionType?: "buy" | "sell" | "hold" | "alert"
  symbol?: string
  confidence?: number
}
