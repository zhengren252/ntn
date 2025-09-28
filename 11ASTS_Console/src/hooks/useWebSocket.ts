import { useState, useEffect, useRef, useCallback } from 'react'
import { useSystemStore } from '@/store'

export interface WebSocketMessage {
  type: string
  data: unknown
  timestamp: number
}

export interface WebSocketConfig {
  url: string
  protocols?: string | string[]
  reconnectInterval?: number
  maxReconnectAttempts?: number
  heartbeatInterval?: number
}

export interface UseWebSocketReturn {
  socket: WebSocket | null
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error'
  lastMessage: WebSocketMessage | null
  sendMessage: (message: unknown) => void
  connect: () => void
  disconnect: () => void
  isConnected: boolean
  data: unknown
}

export const useWebSocket = (config: WebSocketConfig): UseWebSocketReturn => {
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected')
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const { addNotification } = useSystemStore()

  const {
    url,
    protocols,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
    heartbeatInterval = 30000
  } = config

  const clearTimeouts = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current)
      heartbeatIntervalRef.current = null
    }
  }, [])

  const startHeartbeat = useCallback(() => {
    if (heartbeatInterval > 0) {
      heartbeatIntervalRef.current = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }))
        }
      }, heartbeatInterval)
    }
  }, [socket, heartbeatInterval])

  const connect = useCallback(() => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      return
    }

    setConnectionState('connecting')
    clearTimeouts()

    try {
      const ws = new WebSocket(url, protocols)

      ws.onopen = () => {
        setConnectionState('connected')
        reconnectAttemptsRef.current = 0
        addNotification({
          type: 'success',
          title: 'WebSocket连接成功',
          message: `已连接到 ${url}`
        })
        startHeartbeat()
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)
          
          // 处理心跳响应
          if (message.type === 'pong') {
            return
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.onclose = (event) => {
        setConnectionState('disconnected')
        clearTimeouts()
        
        if (!event.wasClean && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++
          addNotification({
            type: 'warning',
            title: 'WebSocket连接断开',
            message: `正在尝试重连... (${reconnectAttemptsRef.current}/${maxReconnectAttempts})`
          })
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, reconnectInterval)
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          addNotification({
            type: 'error',
            title: 'WebSocket连接失败',
            message: '已达到最大重连次数，请检查网络连接'
          })
        }
      }

      ws.onerror = (error) => {
        setConnectionState('error')
        console.error('WebSocket error:', error)
        addNotification({
          type: 'error',
          title: 'WebSocket连接错误',
          message: '连接过程中发生错误'
        })
      }

      setSocket(ws)
    } catch (error) {
      setConnectionState('error')
      console.error('Failed to create WebSocket connection:', error)
      addNotification({
        type: 'error',
        title: 'WebSocket创建失败',
        message: '无法创建WebSocket连接'
      })
    }
  }, [url, protocols, maxReconnectAttempts, reconnectInterval, addNotification, startHeartbeat, clearTimeouts])

  const disconnect = useCallback(() => {
    clearTimeouts()
    if (socket) {
      socket.close(1000, 'Manual disconnect')
      setSocket(null)
    }
    setConnectionState('disconnected')
  }, [socket, clearTimeouts])

  const sendMessage = useCallback((message: Record<string, unknown>) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      try {
        const messageWithTimestamp = {
          ...message,
          timestamp: Date.now()
        }
        socket.send(JSON.stringify(messageWithTimestamp))
      } catch (error) {
        console.error('Failed to send WebSocket message:', error)
        addNotification({
          type: 'error',
          title: '消息发送失败',
          message: '无法发送WebSocket消息'
        })
      }
    } else {
      addNotification({
        type: 'warning',
        title: '连接未就绪',
        message: 'WebSocket连接未建立或已断开'
      })
    }
  }, [socket, addNotification])

  useEffect(() => {
    return () => {
      clearTimeouts()
      if (socket) {
        socket.close()
      }
    }
  }, [socket, clearTimeouts])

  const isConnected = connectionState === 'connected'

  return {
    socket,
    connectionState,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
    isConnected,
    data: lastMessage
  }
}

// 预定义的WebSocket连接配置
export const WEBSOCKET_ENDPOINTS = {
  MARKET_DATA: 'ws://localhost:8001/ws/market',
  SYSTEM_STATUS: 'ws://localhost:8001/ws/system',
  TRADING_EVENTS: 'ws://localhost:8001/ws/trading',
  RISK_ALERTS: 'ws://localhost:8001/ws/risk'
} as const

// 市场数据WebSocket Hook
export const useMarketDataWebSocket = () => {
  return useWebSocket({
    url: WEBSOCKET_ENDPOINTS.MARKET_DATA,
    reconnectInterval: 2000,
    maxReconnectAttempts: 10,
    heartbeatInterval: 30000
  })
}

// 系统状态WebSocket Hook
export const useSystemStatusWebSocket = () => {
  return useWebSocket({
    url: WEBSOCKET_ENDPOINTS.SYSTEM_STATUS,
    reconnectInterval: 3000,
    maxReconnectAttempts: 5,
    heartbeatInterval: 15000
  })
}

// 交易事件WebSocket Hook
export const useTradingEventsWebSocket = () => {
  return useWebSocket({
    url: WEBSOCKET_ENDPOINTS.TRADING_EVENTS,
    reconnectInterval: 1000,
    maxReconnectAttempts: 15,
    heartbeatInterval: 10000
  })
}

// 风险警报WebSocket Hook
export const useRiskAlertsWebSocket = () => {
  return useWebSocket({
    url: WEBSOCKET_ENDPOINTS.RISK_ALERTS,
    reconnectInterval: 2000,
    maxReconnectAttempts: 8,
    heartbeatInterval: 20000
  })
}