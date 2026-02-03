import axios from 'axios';

// Data-Agent API (端口 8005)
const DATA_AGENT_API = 'http://localhost:8005';
// MM-Agent API (端口 8003)
const MM_AGENT_API = 'http://localhost:8003';

// Data-Agent 實例
export const dataAgentApi = axios.create({
  baseURL: DATA_AGENT_API,
  timeout: 30000,
});

// MM-Agent 實例
export const mmAgentApi = axios.create({
  baseURL: MM_AGENT_API,
  timeout: 30000,
});

// 向後兼容：保留原有 api 導出
export const api = dataAgentApi;

// 數據查詢 API
export async function fetchInventoryData() {
  const response = await dataAgentApi.get('/api/v1/datalake/inventory');
  return response.data;
}

export async function fetchTransactionData() {
  const response = await dataAgentApi.get('/api/v1/datalake/transactions');
  return response.data;
}

export async function fetchItemsData() {
  const response = await dataAgentApi.get('/api/v1/datalake/items');
  return response.data;
}

export async function fetchPurchaseData() {
  const [pmm, pmn, rvb, vendors] = await Promise.all([
    dataAgentApi.get('/api/v1/datalake/purchase/pmm'),
    dataAgentApi.get('/api/v1/datalake/purchase/pmn'),
    dataAgentApi.get('/api/v1/datalake/purchase/rvb'),
    dataAgentApi.get('/api/v1/datalake/vendors'),
  ]);
  return { pmm: pmm.data, pmn: pmn.data, rvb: rvb.data, vendors: vendors.data };
}

export async function fetchOrderData() {
  const [coptc, coptd, prc, customers] = await Promise.all([
    dataAgentApi.get('/api/v1/datalake/orders/coptc'),
    dataAgentApi.get('/api/v1/datalake/orders/coptd'),
    dataAgentApi.get('/api/v1/datalake/pricing'),
    dataAgentApi.get('/api/v1/datalake/customers'),
  ]);
  return { coptc: coptc.data, coptd: coptd.data, prc: prc.data, customers: customers.data };
}

// 舊版 NLP 查詢（Data-Agent）
export async function nlpQuery(query: string) {
  const response = await dataAgentApi.post('/api/v1/data-agent/query', { query });
  return response.data;
}

// ============ MM-Agent API（多輪對話支持） ============

/**
 * MM-Agent 對話查詢（支持多輪對話）
 * @param instruction 用戶輸入
 * @param sessionId 對話會話 ID（可選，不提供則創建新會話）
 * @param userId 用戶 ID（可選）
 */
export async function mmAgentChat(
  instruction: string,
  sessionId?: string,
  userId?: string
) {
  const response = await mmAgentApi.post('/api/v1/mm-agent/chat', {
    instruction,
    session_id: sessionId,
    user_id: userId,
  });
  return response.data;
}

/**
 * MM-Agent 語意轉譯
 * @param instruction 用戶輸入
 */
export async function mmAgentTranslate(instruction: string) {
  const response = await mmAgentApi.post('/api/v1/mm-agent/translate', {
    instruction,
  });
  return response.data;
}

/**
 * 檢查查詢是否有效
 * @param instruction 用戶輸入
 */
export async function mmAgentCheck(instruction: string) {
  const response = await mmAgentApi.post('/api/v1/mm-agent/check', {
    instruction,
  });
  return response.data;
}
