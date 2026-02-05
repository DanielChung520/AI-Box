import { create } from 'zustand';

export type AIStatusType = 'idle' | 'processing' | 'completed' | 'error';

export interface AIStatusEvent {
  request_id: string;
  step: string;
  status: AIStatusType;
  message: string;
  progress: number;
  timestamp: string;
}

interface AIStatusState {
  isWindowOpen: boolean;
  toggleWindow: () => void;
  closeWindow: () => void;
  openWindow: () => void;
  currentStatus: AIStatusType;
  setCurrentStatus: (status: AIStatusType) => void;
  events: AIStatusEvent[];
  addEvent: (event: AIStatusEvent) => void;
  clearEvents: () => void;
  currentRequestId: string | null;
  setCurrentRequestId: (id: string | null) => void;
  isConnected: boolean;
  setIsConnected: (connected: boolean) => void;
  // 修改時間：2026-02-03 - 添加 requestId 和 requestIdChange 兩個字段
  // requestId: 當前正在處理的請求ID
  requestId: string | null;
  setRequestId: (id: string | null) => void;
}

export const useAIStatusStore = create<AIStatusState>((set) => ({
  isWindowOpen: false,
  toggleWindow: () => set((state) => ({ isWindowOpen: !state.isWindowOpen })),
  closeWindow: () => set({ isWindowOpen: false }),
  openWindow: () => set({ isWindowOpen: true }),
  currentStatus: 'idle',
  setCurrentStatus: (status) => set({ currentStatus: status }),
  events: [],
  addEvent: (event) =>
    set((state) => ({
      events: [...state.events, event].slice(-50),
    })),
  clearEvents: () => set({ events: [] }),
  currentRequestId: null,
  setCurrentRequestId: (id) => set({ currentRequestId: id }),
  isConnected: false,
  setIsConnected: (connected) => set({ isConnected: connected }),
  requestId: null,
  setRequestId: (id) => set({ requestId: id }),
}));
