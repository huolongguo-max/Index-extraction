/**
 * SSE 实时数据流 composable
 * 自动连接、解析事件、更新响应式数据、断开清理
 */
import { ref, onMounted, onUnmounted, type Ref } from 'vue'
import { SSE_URL } from '@/utils/api'

export interface SSEData {
  type: 'update' | 'status' | 'heartbeat' | 'error'
  payload: Record<string, unknown>
  timestamp: number
}

export function useSSE(options?: {
  onUpdate?: (payload: Record<string, unknown>) => void
  onStatus?: (payload: Record<string, unknown>) => void
  onError?: (payload: Record<string, unknown>) => void
}) {
  const connected = ref(false)
  const lastEvent = ref<SSEData | null>(null)
  const updateData = ref<Record<string, unknown>[]>([])
  const schedulerStatus = ref<Record<string, unknown> | null>(null)
  const errorMsg = ref<string | null>(null)

  let eventSource: EventSource | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  function connect() {
    if (eventSource) return

    eventSource = new EventSource(SSE_URL)

    eventSource.onopen = () => {
      connected.value = true
      errorMsg.value = null
    }

    eventSource.onmessage = (event: MessageEvent) => {
      try {
        const data: SSEData = JSON.parse(event.data)
        lastEvent.value = data

        switch (data.type) {
          case 'update': {
            const payload = data.payload as Record<string, unknown>
            const rows = (payload.data as Record<string, unknown>[]) || []
            updateData.value = rows
            options?.onUpdate?.(payload)
            break
          }
          case 'status': {
            schedulerStatus.value = data.payload
            options?.onStatus?.(data.payload)
            break
          }
          case 'error': {
            errorMsg.value = (data.payload.msg as string) || '采集异常'
            options?.onError?.(data.payload)
            break
          }
          case 'heartbeat':
            break
        }
      } catch {
        // JSON parse error — ignore malformed events
      }
    }

    eventSource.onerror = () => {
      connected.value = false
      eventSource?.close()
      eventSource = null
      // 3 秒后自动重连
      reconnectTimer = setTimeout(connect, 3000)
    }
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    eventSource?.close()
    eventSource = null
    connected.value = false
  }

  onMounted(() => connect())
  onUnmounted(() => disconnect())

  return {
    connected,
    lastEvent,
    updateData,
    schedulerStatus,
    errorMsg,
    connect,
    disconnect,
  }
}
