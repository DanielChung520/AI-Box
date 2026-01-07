/**
 * 代碼功能說明: FileEditingContext 單元測試
 * 創建日期: 2026-01-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-06
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { FileEditingProvider, useFileEditing } from '../../../src/contexts/fileEditingContext';
import { SearchReplacePatch } from '../../../src/hooks/useStreamingEdit';

describe('FileEditingContext', () => {
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <FileEditingProvider>{children}</FileEditingProvider>
  );

  beforeEach(() => {
    // 每個測試前重置狀態
  });

  it('應該提供初始狀態', () => {
    const { result } = renderHook(() => useFileEditing(), { wrapper });

    expect(result.current.editingFileId).toBeNull();
    expect(result.current.patches).toEqual([]);
    expect(result.current.originalContent).toBeNull();
    expect(result.current.modifiedContent).toBeNull();
    expect(result.current.currentRequestId).toBeNull();
    expect(result.current.hasUnsavedChanges).toBe(false);
  });

  it('應該設置編輯文件', () => {
    const { result } = renderHook(() => useFileEditing(), { wrapper });

    act(() => {
      result.current.setEditingFile('file-123');
    });

    expect(result.current.editingFileId).toBe('file-123');
  });

  it('應該設置原始內容', () => {
    const { result } = renderHook(() => useFileEditing(), { wrapper });

    act(() => {
      result.current.setOriginalContent('# 原始內容');
    });

    expect(result.current.originalContent).toBe('# 原始內容');
  });

  it('應該設置 patches', () => {
    const { result } = renderHook(() => useFileEditing(), { wrapper });

    const patches: SearchReplacePatch[] = [
      {
        search_block: '原始',
        replace_block: '修改後',
      },
    ];

    act(() => {
      result.current.setPatches(patches);
    });

    expect(result.current.patches).toEqual(patches);
  });

  it('應該應用 patches 生成 modifiedContent', () => {
    const { result } = renderHook(() => useFileEditing(), { wrapper });

    act(() => {
      result.current.setOriginalContent('這是原始內容。');
    });

    const patches: SearchReplacePatch[] = [
      {
        search_block: '原始',
        replace_block: '修改後',
      },
    ];

    act(() => {
      result.current.setPatches(patches);
    });

    // patches 應該自動應用到 modifiedContent
    expect(result.current.modifiedContent).toBe('這是修改後內容。');
  });

  it('應該計算 hasUnsavedChanges', () => {
    const { result } = renderHook(() => useFileEditing(), { wrapper });

    act(() => {
      result.current.setOriginalContent('原始內容');
    });

    const patches: SearchReplacePatch[] = [
      {
        search_block: '原始',
        replace_block: '修改後',
      },
    ];

    act(() => {
      result.current.setPatches(patches);
    });

    expect(result.current.hasUnsavedChanges).toBe(true);
  });

  it('應該在沒有修改時 hasUnsavedChanges 為 false', () => {
    const { result } = renderHook(() => useFileEditing(), { wrapper });

    act(() => {
      result.current.setOriginalContent('原始內容');
    });

    expect(result.current.hasUnsavedChanges).toBe(false);
  });

  it('應該接受修改', () => {
    const { result } = renderHook(() => useFileEditing(), { wrapper });

    act(() => {
      result.current.setOriginalContent('原始內容');
    });

    const patches: SearchReplacePatch[] = [
      {
        search_block: '原始',
        replace_block: '修改後',
      },
    ];

    act(() => {
      result.current.setPatches(patches);
    });

    expect(result.current.hasUnsavedChanges).toBe(true);

    act(() => {
      result.current.acceptChanges();
    });

    expect(result.current.originalContent).toBe('修改後內容');
    expect(result.current.patches).toEqual([]);
    expect(result.current.hasUnsavedChanges).toBe(false);
  });

  it('應該拒絕修改', () => {
    const { result } = renderHook(() => useFileEditing(), { wrapper });

    act(() => {
      result.current.setOriginalContent('原始內容');
    });

    const patches: SearchReplacePatch[] = [
      {
        search_block: '原始',
        replace_block: '修改後',
      },
    ];

    act(() => {
      result.current.setPatches(patches);
    });

    expect(result.current.modifiedContent).toBe('修改後內容');

    act(() => {
      result.current.rejectChanges();
    });

    expect(result.current.modifiedContent).toBe('原始內容');
    expect(result.current.patches).toEqual([]);
    expect(result.current.hasUnsavedChanges).toBe(false);
  });

  it('應該清除編輯狀態', () => {
    const { result } = renderHook(() => useFileEditing(), { wrapper });

    act(() => {
      result.current.setEditingFile('file-123');
      result.current.setOriginalContent('內容');
      result.current.setPatches([
        { search_block: '內容', replace_block: '新內容' },
      ]);
    });

    act(() => {
      result.current.clearEditing();
    });

    expect(result.current.editingFileId).toBeNull();
    expect(result.current.patches).toEqual([]);
    expect(result.current.originalContent).toBeNull();
    expect(result.current.modifiedContent).toBeNull();
    expect(result.current.currentRequestId).toBeNull();
  });

  it('應該設置當前請求 ID', () => {
    const { result } = renderHook(() => useFileEditing(), { wrapper });

    act(() => {
      result.current.setCurrentRequestId('request-123');
    });

    expect(result.current.currentRequestId).toBe('request-123');
  });

  it('應該在設置編輯文件為 null 時清除所有狀態', () => {
    const { result } = renderHook(() => useFileEditing(), { wrapper });

    act(() => {
      result.current.setEditingFile('file-123');
      result.current.setOriginalContent('內容');
      result.current.setPatches([
        { search_block: '內容', replace_block: '新內容' },
      ]);
    });

    act(() => {
      result.current.setEditingFile(null);
    });

    expect(result.current.editingFileId).toBeNull();
    expect(result.current.patches).toEqual([]);
    expect(result.current.originalContent).toBeNull();
    expect(result.current.modifiedContent).toBeNull();
    expect(result.current.currentRequestId).toBeNull();
  });
});
