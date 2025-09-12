export const config = {
  // API Configuration
  api: {
    baseUrl: process.env.API_BASE_URL || "https://tradingassistantmcpready-production.up.railway.app",
    timeout: 30000, // 30 seconds
    retryAttempts: 3,
    retryDelay: 1000, // 1 second base delay
  },

  // WebSocket Configuration
  websocket: {
    url: process.env.NEXT_PUBLIC_WS_URL || "wss://tradingassistantmcpready-production.up.railway.app/ws",
    reconnectInterval: 3000, // 3 seconds
    maxReconnectAttempts: 5,
    heartbeatInterval: 30000, // 30 seconds
  },

  // Trading Configuration
  trading: {
    defaultOrderType: "limit" as const,
    defaultDuration: "day" as const,
    maxOrderValue: 10000, // $10,000 max order
    riskManagement: {
      maxPositionSize: 0.1, // 10% of portfolio
      stopLossPercent: 0.02, // 2% stop loss
      takeProfitPercent: 0.06, // 6% take profit
    },
  },

  // Market Data Configuration
  marketData: {
    updateInterval: 1000, // 1 second for real-time updates
    batchSize: 50, // Max symbols per batch
    cacheTimeout: 300000, // 5 minutes cache
    fallbackToDaily: true,
  },

  // Production Settings
  production: {
    enableLogging: true,
    enableAnalytics: false, // Disable until privacy policy is in place
    enableErrorReporting: true,
    sandboxMode: true, // Keep in sandbox for safety
  },

  // Feature Flags
  features: {
    realTimeData: true,
    paperTrading: true,
    liveTrading: false, // Disabled for safety
    advancedCharts: true,
    aiAssistant: true,
    optionsTrading: true,
  },
} as const

export type Config = typeof config
