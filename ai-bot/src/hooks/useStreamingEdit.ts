/**
 * 代碼功能說明: 流式編輯 Hook - 管理編輯 Session 的流式數據接收和解析
 * 創建日期: 2026-01-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-06
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  connectEditingStream,
  SSEStreamingClient,
  StreamingMessage,
  StreamingState,
} from '../utils/streaming';

/**
 * 防抖函數 - 性能優化：避免頻繁更新
 */
function debounce<T extends (...args: any[]) => void>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;
  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      func(...args);
    };
    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(later, wait);
  };
}

/**
 * Search-and-Replace Patch 格式
 */
export interface SearchReplacePatch {
  search_block: string;
  replace_block: string;
}

/**
 * useStreamingEdit Hook 返回值
 */
export interface UseStreamingEditReturn {
  /** 是否正在流式傳輸 */
  isStreaming: boolean;
  /** 解析後的 patches 數組 */
  patches: SearchReplacePatch[];
  /** 錯誤信息 */
  error: Error | null;
  /** 當前流式狀態 */
  state: StreamingState;
  /** 連接流式端點 */
  connect: (sessionId: string, requestId?: string) => void;
  /** 斷開連接 */
  disconnect: () => void;
  /** 重置狀態 */
  reset: () => void;
}

/**
 * 流式編輯 Hook
 *
 * 用於管理編輯 Session 的流式數據接收和解析
 */
export function useStreamingEdit(): UseStreamingEditReturn {
  const [isStreaming, setIsStreaming] = useState(false);
  const [patches, setPatches] = useState<SearchReplacePatch[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [state, setState] = useState<StreamingState>('idle');

  const clientRef = useRef<SSEStreamingClient | null>(null);
  const bufferRef = useRef<string>('');
  const lastParseTimeRef = useRef<number>(0);
  const parseDebounceMs = 100; // 防抖延遲：100ms

  /**
   * 解析並更新 patches（帶防抖）
   */
  const parseAndUpdatePatches = useCallback(() => {
    if (!bufferRef.current) {
      return;
    }

    try {
      const parsed = JSON.parse(bufferRef.current);
      if (parsed.patches && Array.isArray(parsed.patches)) {
        // 驗證 patches 格式
        const validPatches = parsed.patches.filter(
          (patch: any) =>
            patch &&
            typeof patch === 'object' &&
            typeof patch.search_block === 'string' &&
            typeof patch.replace_block === 'string'
        );
        if (validPatches.length > 0) {
          setPatches(validPatches);
          // 性能監控：記錄解析時間
          const now = Date.now();
          if (now - lastParseTimeRef.current > 1000) {
            console.debug(
              `Streaming patches parsed: ${validPatches.length} patches, buffer size: ${bufferRef.current.length} chars`
            );
            lastParseTimeRef.current = now;
          }
        }
      }
    } catch {
      // JSON 不完整，繼續累積
    }
  }, []);

  // 創建防抖版本的解析函數
  const debouncedParseAndUpdate = useRef(
    debounce(parseAndUpdatePatches, parseDebounceMs)
  ).current;

  /**
   * 處理流式消息
   */
  const handleMessage = useCallback((message: StreamingMessage) => {
    try {
      switch (message.type) {
        case 'patch_start':
          bufferRef.current = '';
          setPatches([]);
          setError(null);
          setIsStreaming(true);
          lastParseTimeRef.current = Date.now();
          break;

        case 'patch_chunk':
          // 累積數據塊
          if (message.data.chunk && typeof message.data.chunk === 'string') {
            bufferRef.current += message.data.chunk;

            // 性能優化：使用防抖避免頻繁解析
            // 只在 buffer 達到一定大小或經過一定時間後才解析
            debouncedParseAndUpdate();
          }
          break;

        case 'patch_end':
          // 解析完整的數據
          if (bufferRef.current) {
            try {
              const completeData = JSON.parse(bufferRef.current);
              if (completeData.patches && Array.isArray(completeData.patches)) {
                // 驗證並設置 patches
                const validPatches = completeData.patches.filter(
                  (patch: any) =>
                    patch &&
                    typeof patch === 'object' &&
                    typeof patch.search_block === 'string' &&
                    typeof patch.replace_block === 'string'
                );
                setPatches(validPatches);
              } else if (message.data.complete) {
                // 如果 message.data 中已經有完整數據
                const complete = message.data.complete as any;
                if (complete.patches && Array.isArray(complete.patches)) {
                  const validPatches = complete.patches.filter(
                    (patch: any) =>
                      patch &&
                      typeof patch === 'object' &&
                      typeof patch.search_block === 'string' &&
                      typeof patch.replace_block === 'string'
                  );
                  setPatches(validPatches);
                }
              }
            } catch (parseError) {
              console.error('Failed to parse complete data:', parseError);
              setError(new Error('Failed to parse patch data'));
            }
          }
          setIsStreaming(false);
          break;

        case 'error':
          setIsStreaming(false);
          const errorMessage = message.data.error as string || 'Unknown error';
          setError(new Error(errorMessage));
          break;

        default:
          console.warn('Unknown message type:', message.type);
      }
    } catch (err) {
      console.error('Error handling streaming message:', err);
      setError(err instanceof Error ? err : new Error('Unknown error'));
      setIsStreaming(false);
    }
  }, []);

  /**
   * 處理狀態變化
   */
  const handleStateChange = useCallback((newState: StreamingState) => {
    setState(newState);
    if (newState === 'streaming') {
      setIsStreaming(true);
    } else if (newState === 'completed' || newState === 'error') {
      setIsStreaming(false);
    }
  }, []);

  /**
   * 處理錯誤
   */
  const handleError = useCallback((err: Error) => {
    console.error('Streaming error:', err);
    setError(err);
    setIsStreaming(false);
    setState('error');
  }, []);

  /**
   * 處理完成
   */
  const handleComplete = useCallback(() => {
    setIsStreaming(false);
    setState('completed');
  }, []);

  /**
   * 連接到流式端點
   */
  const connect = useCallback((sessionId: string, requestId?: string) => {
    // 如果已經連接，先斷開
    if (clientRef.current) {
      clientRef.current.disconnect();
    }

    // 重置狀態
    setError(null);
    setPatches([]);
    bufferRef.current = '';
    setState('idle');

    // 創建新的連接
    const client = connectEditingStream(sessionId, requestId, {
      onMessage: handleMessage,
      onStateChange: handleStateChange,
      onError: handleError,
      onComplete: handleComplete,
    });

    clientRef.current = client;
  }, [handleMessage, handleStateChange, handleError, handleComplete]);

  /**
   * 斷開連接
   */
  const disconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect();
      clientRef.current = null;
    }
    setIsStreaming(false);
    setState('idle');
  }, []);

  /**
   * 重置狀態
   */
  const reset = useCallback(() => {
    disconnect();
    setPatches([]);
    setError(null);
    bufferRef.current = '';
    setState('idle');
  }, [disconnect]);

  // 組件卸載時斷開連接
  useEffect(() => {
    return () => {
      if (clientRef.current) {
        clientRef.current.disconnect();
      }
    };
  }, []);

  return {
    isStreaming,
    patches,
    error,
    state,
    connect,
    disconnect,
    reset,
  };
}
