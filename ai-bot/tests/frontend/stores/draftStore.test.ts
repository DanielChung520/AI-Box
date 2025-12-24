// 代碼功能說明: Draft Store 測試
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import { describe, it, expect, beforeEach } from 'vitest';
import { useDraftStore } from '../../../src/stores/draftStore';

describe('draftStore', () => {
  beforeEach(() => {
    // 重置 store 狀態
    const store = useDraftStore.getState();
    store.clearFileState('test-file-1');
    store.clearFileState('test-file-2');
  });

  it('應該初始化為空狀態', () => {
    const store = useDraftStore.getState();

    expect(store.stableContent).toEqual({});
    expect(store.draftContent).toEqual({});
    expect(store.patches).toEqual({});
    expect(store.autoSaveStatus).toEqual({});
  });

  it('應該設置穩定內容', () => {
    const store = useDraftStore.getState();
    store.setStableContent('test-file-1', '原始內容');

    const state = useDraftStore.getState();
    expect(state.stableContent['test-file-1']).toBe('原始內容');
    expect(state.draftContent['test-file-1']).toBe('原始內容');
    expect(state.autoSaveStatus['test-file-1']).toBe('saved');
  });

  it('應該設置草稿內容', () => {
    const store = useDraftStore.getState();
    store.setStableContent('test-file-1', '原始內容');
    store.setDraftContent('test-file-1', '修改後的內容');

    const state = useDraftStore.getState();
    expect(state.draftContent['test-file-1']).toBe('修改後的內容');
    expect(state.autoSaveStatus['test-file-1']).toBe('unsaved');
  });

  it('應該檢測未保存的變更', () => {
    const store = useDraftStore.getState();
    store.setStableContent('test-file-1', '原始內容');
    store.setDraftContent('test-file-1', '修改後的內容');

    expect(store.hasUnsavedChanges('test-file-1')).toBe(true);
  });

  it('應該檢測沒有變更', () => {
    const store = useDraftStore.getState();
    store.setStableContent('test-file-1', '原始內容');

    expect(store.hasUnsavedChanges('test-file-1')).toBe(false);
  });

  it('應該添加 Patch', () => {
    const store = useDraftStore.getState();
    const patch = {
      id: 'patch-1',
      originalRange: { startLine: 1, startColumn: 1, endLine: 1, endColumn: 10 },
      originalText: '原始文本',
      modifiedText: '修改文本',
      status: 'pending_review' as const,
      conflict: false,
    };

    store.addPatch('test-file-1', patch);

    const patches = store.getPatches('test-file-1');
    expect(patches).toHaveLength(1);
    expect(patches[0]).toEqual(patch);
  });

  it('應該應用 Patch', () => {
    const store = useDraftStore.getState();
    const patch = {
      id: 'patch-1',
      originalRange: { startLine: 1, startColumn: 1, endLine: 1, endColumn: 10 },
      originalText: '原始文本',
      modifiedText: '修改文本',
      status: 'pending_review' as const,
      conflict: false,
    };

    store.addPatch('test-file-1', patch);
    store.applyPatch('test-file-1', 'patch-1');

    const patches = store.getPatches('test-file-1');
    expect(patches[0].status).toBe('accepted');
  });

  it('應該拒絕 Patch', () => {
    const store = useDraftStore.getState();
    const patch = {
      id: 'patch-1',
      originalRange: { startLine: 1, startColumn: 1, endLine: 1, endColumn: 10 },
      originalText: '原始文本',
      modifiedText: '修改文本',
      status: 'pending_review' as const,
      conflict: false,
    };

    store.addPatch('test-file-1', patch);
    store.rejectPatch('test-file-1', 'patch-1');

    const patches = store.getPatches('test-file-1');
    expect(patches[0].status).toBe('rejected');
  });

  it('應該清除文件狀態', () => {
    const store = useDraftStore.getState();
    store.setStableContent('test-file-1', '內容');
    store.setDraftContent('test-file-1', '修改內容');

    store.clearFileState('test-file-1');

    const state = useDraftStore.getState();
    expect(state.stableContent['test-file-1']).toBeUndefined();
    expect(state.draftContent['test-file-1']).toBeUndefined();
  });
});
