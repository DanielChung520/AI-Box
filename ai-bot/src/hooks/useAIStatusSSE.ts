import { useEffect, useRef, useCallback } from 'react';
import { useAIStatusStore } from '../stores/aiStatusStore';

export function useAIStatusSSE() {
  const { isWindowOpen, requestId } = useAIStatusStore();
  const eventSourceRef = useRef<EventSource | null>(null);
  const connectionIdRef = useRef<string | null>(null);
  const isUnmountedRef = useRef(false);
  const { addEvent, setCurrentStatus, setIsConnected, clearEvents, setRequestId } = useAIStatusStore();

  const connect = useCallback((targetRequestId: string) => {
    console.log('[SSE] connect() 被調用, requestId:', targetRequestId);
    
    if (isUnmountedRef.current) {
      return;
    }
    
    if (!targetRequestId) {
      console.log('[SSE] 沒有 requestId');
      return;
    }

    const url = `/api/v1/agent-status/stream/${targetRequestId}`;
    console.log('[SSE] 連接 URL:', url);

    try {
      if (eventSourceRef.current) {
        console.log('[SSE] 關閉現有連接');
        eventSourceRef.current.close();
        eventSourceRef.current = null;
        connectionIdRef.current = null;
      }

      console.log('[SSE] 創建 EventSource...');
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;
      connectionIdRef.current = targetRequestId;

      eventSource.onopen = () => {
        console.log('[SSE] ✅ onopen 觸發!');
        if (!isUnmountedRef.current) {
          setIsConnected(true);
        }
      };

      eventSource.onmessage = (event) => {
        console.log('[SSE] 📩 onmessage:', event.data);
        if (isUnmountedRef.current || connectionIdRef.current !== targetRequestId) {
          console.log('[SSE] 忽略過期消息');
          return;
        }
        
        try {
          const data = JSON.parse(event.data);
          console.log('[SSE] 解析成功:', data.step);
          addEvent(data);
          setCurrentStatus(data.status);
          
          if (data.status === 'completed' || data.status === 'error') {
            console.log('[SSE] 任務完成');
            eventSource.close();
            eventSourceRef.current = null;
            connectionIdRef.current = null;
            setIsConnected(false);
          }
        } catch (e) {
          console.error('[SSE] 解析錯誤:', e);
        }
      };

      eventSource.onerror = (error) => {
        console.error('[SSE] ❌ onerror, readyState:', eventSource.readyState);
        
        if (eventSource.readyState === EventSource.CONNECTING) {
          console.log('[SSE] 正在連接中...');
          return;
        }
        
        if (connectionIdRef.current === targetRequestId) {
          console.log('[SSE] 連接失敗');
          eventSource.close();
          eventSourceRef.current = null;
          connectionIdRef.current = null;
          setIsConnected(false);
        }
      };

    } catch (error) {
      console.error('[SSE] 創建 EventSource 失敗:', error);
      setIsConnected(false);
    }
  }, [addEvent, setCurrentStatus, setIsConnected]);

  const disconnect = useCallback(() => {
    console.log('[SSE] disconnect() 被調用');
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      connectionIdRef.current = null;
      setIsConnected(false);
    }
  }, [setIsConnected]);

  useEffect(() => {
    isUnmountedRef.current = false;
    console.log('[SSE] 📍 useEffect 執行, isWindowOpen:', isWindowOpen, 'requestId:', requestId);
    
    if (isWindowOpen && requestId) {
      console.log('[SSE] 條件滿足，調用 connect()');
      clearEvents();
      connect(requestId);
    }

    return () => {
      isUnmountedRef.current = true;
      console.log('[SSE] 🧹 cleanup');
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
        connectionIdRef.current = null;
        setIsConnected(false);
      }
    };
  }, [isWindowOpen, requestId, connect, clearEvents, setIsConnected]);

  return { connect, disconnect };
}
