import axios from 'axios';

// Data-Agent API (端口 8004 - 使用 DuckDB)
const DATA_AGENT_API = 'http://localhost:8004';
// Frontend API (端口 8005 - DataLakeClient)
const FRONTEND_API = 'http://localhost:8005';
// MM-Agent API (端口 8003)
const MM_AGENT_API = 'http://localhost:8003';

// Data-Agent 實例 (用於 executeSqlQuery)
export const dataAgentApi = axios.create({
  baseURL: DATA_AGENT_API,
  timeout: 30000,
});

// Frontend API 實例 (用於 datalake 查詢)
export const frontendApi = axios.create({
  baseURL: FRONTEND_API,
  timeout: 30000,
});

// MM-Agent 實例
export const mmAgentApi = axios.create({
  baseURL: MM_AGENT_API,
  timeout: 120000,  // 增加到 120 秒，支援 LLM 調用
});

// 向後兼容：保留原有 api 導出
export const api = dataAgentApi;

// 數據查詢 API
export async function fetchInventoryData() {
  const response = await frontendApi.get('/api/v1/datalake/inventory');
  return response.data;
}

export async function fetchTransactionData() {
  const response = await frontendApi.get('/api/v1/datalake/transactions');
  return response.data;
}

export async function fetchItemsData() {
  const response = await frontendApi.get('/api/v1/datalake/items');
  return response.data;
}

export async function fetchPurchaseData() {
  const [pmm, pmn, rvb, vendors] = await Promise.all([
    frontendApi.get('/api/v1/datalake/purchase/pmm'),
    frontendApi.get('/api/v1/datalake/purchase/pmn'),
    frontendApi.get('/api/v1/datalake/purchase/rvb'),
    frontendApi.get('/api/v1/datalake/vendors'),
  ]);
  return { pmm: pmm.data, pmn: pmn.data, rvb: rvb.data, vendors: vendors.data };
}

export async function fetchOrderData() {
  const [coptc, coptd, prc, customers] = await Promise.all([
    frontendApi.get('/api/v1/datalake/orders/coptc'),
    frontendApi.get('/api/v1/datalake/orders/coptd'),
    frontendApi.get('/api/v1/datalake/pricing'),
    frontendApi.get('/api/v1/datalake/customers'),
  ]);
  return { coptc: coptc.data, coptd: coptd.data, prc: prc.data, customers: customers.data };
}

// 舊版 NLP 查詢（Data-Agent）
export async function nlpQuery(query: string) {
  const response = await frontendApi.post('/api/v1/data-agent/query', { query });
  return response.data;
}

// 直接執行 SQL 查詢
export async function executeSqlQuery(sqlQuery: string) {
  const response = await dataAgentApi.post('/execute', {
    task_id: 'sql-execute',
    task_type: 'data_query',
    task_data: {
      action: 'execute_sql_on_datalake',
      sql_query_datalake: sqlQuery,
      max_rows: 100,
    },
  });
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
  const response = await mmAgentApi.post('/api/v1/chat', {
    instruction,
    session_id: sessionId,
    user_id: userId,
  });
  return response.data;
}

/**
 * 執行 MM-Agent 工作流程下一步
 * @param instruction 用戶回應
 * @param sessionId 會話 ID
 */
export async function mmAgentExecuteStep(
  instruction: string,
  sessionId: string
) {
  const response = await mmAgentApi.post('/api/v1/chat/execute-step', {
    instruction,
    session_id: sessionId,
  });
  return response.data;
}

/**
 * 獲取 MM-Agent 工作流程狀態
 * @param sessionId 會話 ID
 */
export async function mmAgentGetWorkflowState(sessionId: string) {
  const response = await mmAgentApi.get(`/api/v1/chat/workflow/${sessionId}`);
  return response.data;
}

/**
 * 清除 MM-Agent 工作流程狀態
 * @param sessionId 會話 ID
 */
export async function mmAgentClearWorkflowState(sessionId: string) {
  const response = await mmAgentApi.delete(`/api/v1/chat/workflow/${sessionId}`);
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
