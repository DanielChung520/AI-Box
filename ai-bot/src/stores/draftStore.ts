// 代碼功能說明: Draft 狀態管理 Store (Zustand)
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import { create } from 'zustand';
import type { AIPatch } from '../types/draft';

interface DraftState {
  // Stable State（已保存的文件内容）
  stableContent: Record<string, string>; // fileId -> content

  // Draft State（正在编辑的内容）
  draftContent: Record<string, string>; // fileId -> content

  // Patch 队列
  patches: Record<string, AIPatch[]>; // fileId -> patches

  // 自动保存状态
  autoSaveStatus: Record<string, 'saved' | 'saving' | 'unsaved'>; // fileId -> status

  // Actions
  setStableContent: (fileId: string, content: string) => void;
  setDraftContent: (fileId: string, content: string) => void;
  getContentDiff: (fileId: string) => { hasChanges: boolean; diff: string };
  hasUnsavedChanges: (fileId: string) => boolean;
  addPatch: (fileId: string, patch: AIPatch) => void;
  applyPatch: (fileId: string, patchId: string) => void;
  rejectPatch: (fileId: string, patchId: string) => void;
  getPatches: (fileId: string, status?: AIPatch['status']) => AIPatch[];
  setAutoSaveStatus: (fileId: string, status: 'saved' | 'saving' | 'unsaved') => void;
  clearFileState: (fileId: string) => void;
}

export const useDraftStore = create<DraftState>((set, get) => ({
  stableContent: {},
  draftContent: {},
  patches: {},
  autoSaveStatus: {},

  setStableContent: (fileId, content) => {
    set((state) => ({
      stableContent: {
        ...state.stableContent,
        [fileId]: content,
      },
      // 同时设置 draftContent 为相同内容
      draftContent: {
        ...state.draftContent,
        [fileId]: content,
      },
      autoSaveStatus: {
        ...state.autoSaveStatus,
        [fileId]: 'saved',
      },
    }));
  },

  setDraftContent: (fileId, content) => {
    set((state) => ({
      draftContent: {
        ...state.draftContent,
        [fileId]: content,
      },
      autoSaveStatus: {
        ...state.autoSaveStatus,
        [fileId]: state.stableContent[fileId] === content ? 'saved' : 'unsaved',
      },
    }));
  },

  getContentDiff: (fileId) => {
    const state = get();
    const stable = state.stableContent[fileId] || '';
    const draft = state.draftContent[fileId] || '';
    return {
      hasChanges: stable !== draft,
      diff: draft,
    };
  },

  hasUnsavedChanges: (fileId) => {
    const state = get();
    const stable = state.stableContent[fileId] || '';
    const draft = state.draftContent[fileId] || '';
    return stable !== draft;
  },

  addPatch: (fileId, patch) => {
    set((state) => ({
      patches: {
        ...state.patches,
        [fileId]: [...(state.patches[fileId] || []), patch],
      },
    }));
  },

  applyPatch: (fileId, patchId) => {
    set((state) => ({
      patches: {
        ...state.patches,
        [fileId]: (state.patches[fileId] || []).map((patch) =>
          patch.id === patchId ? { ...patch, status: 'accepted' as const } : patch
        ),
      },
    }));
  },

  rejectPatch: (fileId, patchId) => {
    set((state) => ({
      patches: {
        ...state.patches,
        [fileId]: (state.patches[fileId] || []).map((patch) =>
          patch.id === patchId ? { ...patch, status: 'rejected' as const } : patch
        ),
      },
    }));
  },

  getPatches: (fileId, status) => {
    const state = get();
    const patches = state.patches[fileId] || [];
    if (status) {
      return patches.filter((patch) => patch.status === status);
    }
    return patches;
  },

  setAutoSaveStatus: (fileId, status) => {
    set((state) => ({
      autoSaveStatus: {
        ...state.autoSaveStatus,
        [fileId]: status,
      },
    }));
  },

  clearFileState: (fileId) => {
    set((state) => {
      const newState = { ...state };
      delete newState.stableContent[fileId];
      delete newState.draftContent[fileId];
      delete newState.patches[fileId];
      delete newState.autoSaveStatus[fileId];
      return newState;
    });
  },
}));
