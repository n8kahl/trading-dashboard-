import { describe, expect, test, vi, beforeEach, afterEach } from "vitest"
import { act } from "react-dom/test-utils"
import { createRoot } from "react-dom/client"
import React from "react"
import { useAssistantConversation } from "../../hooks/useAssistantConversation"

function mockScroll(ref: any) {
  Object.defineProperty(ref, "scrollHeight", { value: 100, writable: true })
  Object.defineProperty(ref, "scrollTop", { value: 0, writable: true })
}

describe("useAssistantConversation", () => {
  const originalFetch = global.fetch

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    global.fetch = originalFetch
  })

  test("handles message flow with rationale and auto-scroll", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ content: "response", rationale: "because" }),
    }) as any

    const result: { current: ReturnType<typeof useAssistantConversation> } = { current: null as any }
    function Test() {
      result.current = useAssistantConversation()
      return null
    }
    const container = document.createElement("div")
    const root = createRoot(container)
    act(() => {
      root.render(React.createElement(Test))
    })
    const div = document.createElement("div")
    mockScroll(div)
    result.current.scrollRef.current = div

    await act(async () => {
      await result.current.sendMessage("hello")
    })

    const msgs = result.current.messages
    expect(msgs.at(-3)?.content).toBe("hello")
    expect(msgs.at(-2)?.content).toBe("response")
    expect(msgs.at(-1)?.content).toBe("because")
    expect(result.current.isTyping).toBe(false)
    expect(result.current.scrollRef.current?.scrollTop).toBe(100)
  })

  test("handles API errors", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500 }) as any

    const result2: { current: ReturnType<typeof useAssistantConversation> } = { current: null as any }
    function Test2() {
      result2.current = useAssistantConversation()
      return null
    }
    const container2 = document.createElement("div")
    const root2 = createRoot(container2)
    act(() => {
      root2.render(React.createElement(Test2))
    })

    await act(async () => {
      await result2.current.sendMessage("hi")
    })

    const last = result2.current.messages.at(-1)
    expect(last?.type).toBe("system")
    expect(last?.content).toContain("Error")
    expect(result2.current.isTyping).toBe(false)
  })
})

