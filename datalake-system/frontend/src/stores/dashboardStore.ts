import { create } from 'zustand';

export interface InventoryItem {
  img01: string;
  ima02?: string;
  img02: string;
  img03: string;
  img10: number;
  ima25?: string;
}

export interface TransactionItem {
  tlf01: string;
  ima02?: string;
  tlf19: string;
  交易名稱?: string;
  tlf06: string;
  tlf10: number;
  tlf061: string;
  ima25?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface DashboardState {
  currentPage: string;
  setCurrentPage: (page: string) => void;
  inventoryData: InventoryItem[];
  setInventoryData: (data: InventoryItem[]) => void;
  transactionData: TransactionItem[];
  setTransactionData: (data: TransactionItem[]) => void;
  itemsData: any[];
  setItemsData: (data: any[]) => void;
  purchaseData: { pmm: any[]; pmn: any[]; rvb: any[]; vendors: any[] };
  setPurchaseData: (data: { pmm: any[]; pmn: any[]; rvb: any[]; vendors: any[] }) => void;
  orderData: { coptc: any[]; coptd: any[]; prc: any[]; customers: any[] };
  setOrderData: (data: { coptc: any[]; coptd: any[]; prc: any[]; customers: any[] }) => void;
  chatMessages: Message[];
  addChatMessage: (message: Message) => void;
  clearChatMessages: () => void;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  resultPanelCollapsed: boolean;
  toggleResultPanel: () => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  currentPage: 'home',
  setCurrentPage: (page) => set({ currentPage: page }),
  inventoryData: [],
  setInventoryData: (data) => set({ inventoryData: data }),
  transactionData: [],
  setTransactionData: (data) => set({ transactionData: data }),
  itemsData: [],
  setItemsData: (data) => set({ itemsData: data }),
  purchaseData: { pmm: [], pmn: [], rvb: [], vendors: [] },
  setPurchaseData: (data) => set({ purchaseData: data }),
  orderData: { coptc: [], coptd: [], prc: [], customers: [] },
  setOrderData: (data) => set({ orderData: data }),
  chatMessages: [],
  addChatMessage: (message) =>
    set((state) => ({ chatMessages: [...state.chatMessages, message] })),
  clearChatMessages: () => set({ chatMessages: [] }),
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  resultPanelCollapsed: false,
  toggleResultPanel: () =>
    set((state) => ({ resultPanelCollapsed: !state.resultPanelCollapsed })),
}));
