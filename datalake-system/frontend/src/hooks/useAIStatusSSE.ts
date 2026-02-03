import { useEffect, useRef, useCallback } from 'react';
import { useAIStatusStore } from '../../stores/aiStatusStore';

interface UseAIStatusSSEOptions {
  requestId: string | null;
  enabled?: boolean;
}

export function useAIStatusSSE({ requestId, enabled = true }: UseAIStatusSSEOptions) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const {
    addEvent,
    setCurrentStatus,
    setIsConnected,
    setCurrentRequestId,
    clearEvents,
    isWindowOpen,
  } = useAIStatusStore();

  const connect = useCallback(() => {
    if (!requestId || !enabled) return;

    console.log('[SSE] 連接到狀態流:', requestId);

    const apiBase = import.meta.env.VITE_API_BASE_URL || '';
    const url = `${apiBase}/api/v1/agent-status/stream/${requestId}`;

    try {
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('[SSE] 連線已建立');
        setIsConnected(true);
        setCurrentRequestId(requestId);
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('[SSE] 收到狀態:', data);

          addEvent(data);
          setCurrentStatus(data.status);

          if (data.status === 'completed' || data.status === 'error') {
            eventSource.close();
            setIsConnected(false);
          }
        } catch (error) {
          console.error('[SSE] 解析狀態失敗:', error);
        }
      };

      eventSource.onerror = (error) => {
        console.error('[SSE] 連線錯誤:', error);
        setIsConnected(false);

        eventSource.close();
        eventSourceRef.current = null;
      };
    } catch (error) {
      console.error('[SSE] 建立連線失敗:', error);
      setIsConnected(false);
    }
  }, [requestId, enabled, addEvent, setCurrentStatus, setIsConnected, setCurrentRequestId]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      console.log('[SSE] 斷開連線');
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  }, [setIsConnected]);

  useEffect(() => {
    if (isWindowOpen && requestId) {
      clearEvents();
      connect();
    }

    return () => {
      disconnect();
    };
  }, [isWindowOpen, requestId, connect, disconnect, clearEvents]);

  return {
    connect,
    disconnect,
  };
}
