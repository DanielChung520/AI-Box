// 代碼功能說明: useAutoSave Hook 測試
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useAutoSave } from '../../../src/hooks/useAutoSave';
import { useDraftStore } from '../../../src/stores/draftStore';
import * as apiModule from '../../../src/lib/api';

// Mock API
vi.mock('../../../src/lib/api', () => ({
  saveFile: vi.fn(),
}));

// Mock toast
vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
  },
}));

describe('useAutoSave', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    // 重置 store 狀態
    const store = useDraftStore.getState();
    store.clearFileState('test-file-1');
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('應該在內容變化後觸發自動保存', async () => {
    const mockSaveFile = vi.mocked(apiModule.saveFile);
    mockSaveFile.mockResolvedValue({ success: true });

    const store = useDraftStore.getState();
    store.setStableContent('test-file-1', '原始內容');
    store.setDraftContent('test-file-1', '修改後的內容');

    renderHook(() => useAutoSave({ fileId: 'test-file-1', delay: 1000 }));

    // 等待防抖延遲
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(mockSaveFile).toHaveBeenCalledWith('test-file-1', '修改後的內容');
    });
  });

  it('應該在內容未變化時不觸發保存', async () => {
    const mockSaveFile = vi.mocked(apiModule.saveFile);

    const store = useDraftStore.getState();
    store.setStableContent('test-file-1', '相同內容');
    store.setDraftContent('test-file-1', '相同內容');

    renderHook(() => useAutoSave({ fileId: 'test-file-1', delay: 1000 }));

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(mockSaveFile).not.toHaveBeenCalled();
    });
  });

  it('應該處理保存失敗的情況', async () => {
    const mockSaveFile = vi.mocked(apiModule.saveFile);
    mockSaveFile.mockResolvedValue({ success: false, message: '保存失敗' });

    const store = useDraftStore.getState();
    store.setStableContent('test-file-1', '原始內容');
    store.setDraftContent('test-file-1', '修改後的內容');

    renderHook(() => useAutoSave({ fileId: 'test-file-1', delay: 1000 }));

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(mockSaveFile).toHaveBeenCalled();
      const status = useDraftStore.getState().autoSaveStatus['test-file-1'];
      expect(status).toBe('unsaved');
    });
  });

  it('應該支持手動保存', async () => {
    const mockSaveFile = vi.mocked(apiModule.saveFile);
    mockSaveFile.mockResolvedValue({ success: true });

    const store = useDraftStore.getState();
    store.setStableContent('test-file-1', '原始內容');
    store.setDraftContent('test-file-1', '修改後的內容');

    const { result } = renderHook(() => useAutoSave({ fileId: 'test-file-1', delay: 1000 }));

    await act(async () => {
      await result.current.manualSave();
    });

    expect(mockSaveFile).toHaveBeenCalledWith('test-file-1', '修改後的內容');
  });

  it('應該在沒有 fileId 時不執行保存', async () => {
    const mockSaveFile = vi.mocked(apiModule.saveFile);

    renderHook(() => useAutoSave({ fileId: null, delay: 1000 }));

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(mockSaveFile).not.toHaveBeenCalled();
    });
  });

  it('應該正確處理防抖延遲', async () => {
    const mockSaveFile = vi.mocked(apiModule.saveFile);
    mockSaveFile.mockResolvedValue({ success: true });

    const store = useDraftStore.getState();
    store.setStableContent('test-file-1', '原始內容');

    renderHook(() => useAutoSave({ fileId: 'test-file-1', delay: 2000 }));

    // 第一次修改
    act(() => {
      store.setDraftContent('test-file-1', '第一次修改');
      vi.advanceTimersByTime(1000);
    });

    // 第二次修改（應該重置計時器）
    act(() => {
      store.setDraftContent('test-file-1', '第二次修改');
      vi.advanceTimersByTime(1000);
    });

    // 應該還沒有觸發保存
    expect(mockSaveFile).not.toHaveBeenCalled();

    // 再等待 1 秒（總共 2 秒）
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(mockSaveFile).toHaveBeenCalledTimes(1);
      expect(mockSaveFile).toHaveBeenCalledWith('test-file-1', '第二次修改');
    });
  });
});
