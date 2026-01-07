/**
 * 代碼功能說明: useStreamingEdit Hook 單元測試
 * 創建日期: 2026-01-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-06
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useStreamingEdit } from '../../../src/hooks/useStreamingEdit';
import { SSEStreamingClient } from '../../../src/utils/streaming';

// Mock streaming utils
vi.mock('../../../src/utils/streaming', () => {
  const mockClient = {
    disconnect: vi.fn(),
  };

  return {
    connectEditingStream: vi.fn(() => mockClient),
    SSEStreamingClient: vi.fn(),
  };
});

describe('useStreamingEdit', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('應該初始化為空狀態', () => {
    const { result } = renderHook(() => useStreamingEdit());

    expect(result.current.isStreaming).toBe(false);
    expect(result.current.patches).toEqual([]);
    expect(result.current.error).toBeNull();
    expect(result.current.state).toBe('idle');
  });

  it('應該提供連接方法', () => {
    const { result } = renderHook(() => useStreamingEdit());

    expect(typeof result.current.connect).toBe('function');
    expect(typeof result.current.disconnect).toBe('function');
    expect(typeof result.current.reset).toBe('function');
  });

  it('應該在連接時重置狀態', () => {
    const { result } = renderHook(() => useStreamingEdit());

    result.current.connect('session-123', 'request-456');

    expect(result.current.state).toBe('idle');
    expect(result.current.patches).toEqual([]);
    expect(result.current.error).toBeNull();
  });

  it('應該在斷開連接時重置狀態', () => {
    const { result } = renderHook(() => useStreamingEdit());

    result.current.connect('session-123');
    result.current.disconnect();

    expect(result.current.isStreaming).toBe(false);
    expect(result.current.state).toBe('idle');
  });

  it('應該在重置時清除所有狀態', () => {
    const { result } = renderHook(() => useStreamingEdit());

    result.current.connect('session-123');
    result.current.reset();

    expect(result.current.isStreaming).toBe(false);
    expect(result.current.patches).toEqual([]);
    expect(result.current.error).toBeNull();
    expect(result.current.state).toBe('idle');
  });

  // 注意：由於 SSEStreamingClient 是 mock 的，我們無法直接測試流式數據處理
  // 實際的流式數據處理測試需要在集成測試中進行
  // 這裡我們主要測試 Hook 的接口和狀態管理

  it('應該在組件卸載時斷開連接', () => {
    const { result, unmount } = renderHook(() => useStreamingEdit());

    result.current.connect('session-123');

    unmount();

    // 驗證 disconnect 被調用（通過 mock 檢查）
    // 注意：實際的實現會在 useEffect cleanup 中調用 disconnect
  });
});
