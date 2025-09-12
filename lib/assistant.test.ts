import { describe, it, expect } from 'vitest'
import { createAssistantReply, createSignalMessage } from './assistant'

describe('assistant message rationale', () => {
  it('adds rationale to assistant replies', () => {
    const msg = createAssistantReply('Content', 'Reason')
    expect(msg.rationale).toBe('Reason')
    expect(msg.type).toBe('assistant')
  })

  it('adds rationale to signal messages', () => {
    const msg = createSignalMessage({
      symbol: 'AAPL',
      action: 'buy',
      price: 150,
      confidence: 90,
      reason: 'Technical breakout detected',
      timestamp: new Date(),
    })
    expect(msg.rationale).toContain('Technical breakout detected')
    expect(msg.actionType).toBe('buy')
  })
})
