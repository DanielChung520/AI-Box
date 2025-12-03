// 代碼功能說明: API 客戶端配置
// 創建日期: 2025-01-27
// 創建人: Daniel Chung
// 最後修改日期: 2025-01-27

/**
 * API 客戶端配置
 * 用於統一管理前端與後端的 API 通信
 */

// 從環境變量獲取 API 基礎 URL，如果沒有則使用默認值
// 注意：生產環境應使用 HTTPS 和完整的域名，避免本地網絡請求限制
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin);
const API_PREFIX = import.meta.env.VITE_API_PREFIX || '/api/v1';

// 檢查是否為本地網絡請求（用於 Chrome 安全策略兼容）
const isLocalNetworkRequest = (url: string): boolean => {
  try {
    const urlObj = new URL(url);
    const hostname = urlObj.hostname;
    // 檢查是否為 localhost、127.0.0.1、私有 IP 或 .local 域名
    return (
      hostname === 'localhost' ||
      hostname === '127.0.0.1' ||
      hostname === '::1' ||
      hostname.endsWith('.local') ||
      /^10\.|^172\.(1[6-9]|2[0-9]|3[01])\.|^192\.168\./.test(hostname)
    );
  } catch {
    return false;
  }
};

// 完整的 API 基礎 URL
export const API_URL = `${API_BASE_URL}${API_PREFIX}`;

/**
 * API 請求配置
 */
export const apiConfig = {
  baseURL: API_URL,
  timeout: 30000, // 30 秒超時
  headers: {
    'Content-Type': 'application/json',
  },
};

/**
 * 封裝的 fetch 請求函數
 */
export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_URL}${endpoint}`;

  // 為本地網絡請求添加 targetAddressSpace 選項（Chrome 安全策略兼容）
  const fetchOptions: RequestInit = {
    ...options,
    headers: {
      ...apiConfig.headers,
      ...options.headers,
    },
  };

  // 如果是本地網絡請求，添加 targetAddressSpace 標記
  if (isLocalNetworkRequest(url)) {
    // @ts-ignore - targetAddressSpace 是較新的 Fetch API 選項
    fetchOptions.targetAddressSpace = 'private';
  }

  try {
    const response = await fetch(url, fetchOptions);

    if (!response.ok) {
      // 404 錯誤特別處理
      if (response.status === 404) {
        console.warn(`API endpoint not found: ${url}. Make sure the backend server is running and the endpoint exists.`);
      }

      let errorData: any;
      try {
        errorData = await response.json();
      } catch {
        errorData = { message: response.statusText };
      }

      // 嘗試提取詳細錯誤信息（支持多種 API 響應格式）
      const errorMessage =
        errorData?.detail ||
        errorData?.message ||
        errorData?.error ||
        `HTTP error! status: ${response.status}`;

      const error = new Error(errorMessage);
      (error as any).status = response.status;
      (error as any).data = errorData;
      throw error;
    }

    return response.json();
  } catch (error: any) {
    // 網絡錯誤處理（如 CORS、連接失敗等）
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      console.error(`Failed to fetch from ${url}. Check if the backend server is running and accessible.`, error);
      throw new Error(`無法連接到服務器: ${url}. 請確認後端服務器是否正在運行。`);
    }
    throw error;
  }
}

/**
 * GET 請求
 */
export async function apiGet<T = any>(endpoint: string): Promise<T> {
  return apiRequest<T>(endpoint, { method: 'GET' });
}

/**
 * POST 請求
 */
export async function apiPost<T = any>(endpoint: string, data?: any): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  });
}

/**
 * PUT 請求
 */
export async function apiPut<T = any>(endpoint: string, data?: any): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined,
  });
}

/**
 * DELETE 請求
 */
export async function apiDelete<T = any>(endpoint: string): Promise<T> {
  return apiRequest<T>(endpoint, { method: 'DELETE' });
}

/**
 * 健康檢查
 */
export async function healthCheck(): Promise<{ status: string }> {
  return apiGet<{ status: string }>('/health');
}

/**
 * 獲取版本信息
 */
export async function getVersion(): Promise<{
  version: string;
  major: number;
  minor: number;
  patch: number;
  prefix: string;
}> {
  // 版本端點不在 API_PREFIX 下
  const url = `${API_BASE_URL}/version`;

  // 為本地網絡請求添加 targetAddressSpace 選項
  const fetchOptions: RequestInit = {};
  if (isLocalNetworkRequest(url)) {
    // @ts-ignore - targetAddressSpace 是較新的 Fetch API 選項
    fetchOptions.targetAddressSpace = 'private';
  }

  const response = await fetch(url, fetchOptions);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

/**
 * Agent 註冊請求數據類型
 */
export interface AgentRegistrationRequest {
  agent_id: string;
  agent_type: string;
  name: string;
  endpoints: {
    http?: string | null;
    mcp?: string | null;
    protocol: 'http' | 'mcp';
    is_internal: boolean;
  };
  capabilities?: string[];
  metadata?: {
    version?: string;
    description?: string | null;
    tags?: string[];
    capabilities?: Record<string, any>;
  };
  permissions?: {
    read?: boolean;
    write?: boolean;
    execute?: boolean;
    admin?: boolean;
    allowed_memory_namespaces?: string[];
    allowed_tools?: string[];
    allowed_llm_providers?: string[];
    allowed_databases?: string[];
    allowed_file_paths?: string[];
    secret_id?: string;
    api_key?: string;
    server_certificate?: string;
    ip_whitelist?: string[];
    server_fingerprint?: string;
  };
}

/**
 * Agent 註冊響應類型
 */
export interface AgentRegistrationResponse {
  success: boolean;
  data?: {
    agent_id: string;
    is_internal: boolean;
    protocol?: string;
  };
  message?: string;
  error?: string;
}

/**
 * 註冊 Agent
 */
export async function registerAgent(
  request: AgentRegistrationRequest
): Promise<AgentRegistrationResponse> {
  try {
    const response = await apiPost<any>('/agents/register', request);

    // API 返回格式為 { success: true, message: "...", data: {...} }
    if (response && response.success !== false) {
      return {
        success: true,
        data: response.data || response,
        message: response.message || 'Agent registered successfully',
      };
    }

    // 如果 success 為 false，拋出錯誤
    throw new Error(response.message || 'Agent registration failed');
  } catch (error: any) {
    // 嘗試從錯誤響應中提取詳細錯誤信息
    let errorMessage = 'Agent registration failed';

    if (error?.message) {
      errorMessage = error.message;
    } else if (error?.data?.detail) {
      errorMessage = typeof error.data.detail === 'string'
        ? error.data.detail
        : JSON.stringify(error.data.detail);
    } else if (error?.data?.message) {
      errorMessage = error.data.message;
    }

    throw new Error(errorMessage);
  }
}

/**
 * 獲取 Agent 列表
 */
export async function getAgents(): Promise<any> {
  return apiGet('/agents/catalog');
}

/**
 * 獲取 Agent 詳情
 */
export async function getAgent(agentId: string): Promise<any> {
  return apiGet(`/agents/${agentId}`);
}

/**
 * 取消註冊 Agent
 */
export async function unregisterAgent(agentId: string): Promise<any> {
  return apiDelete(`/agents/${agentId}`);
}

/**
 * Secret 驗證請求類型
 */
export interface SecretVerificationRequest {
  secret_id: string;
  secret_key: string;
}

/**
 * Secret 驗證響應類型
 */
export interface SecretVerificationResponse {
  success: boolean;
  data?: {
    valid: boolean;
    secret_id: string;
    is_bound: boolean;
    secret_info?: any;
  };
  message?: string;
  error?: string;
}

/**
 * 驗證 Secret ID/Key
 */
export async function verifySecret(
  request: SecretVerificationRequest
): Promise<SecretVerificationResponse> {
  try {
    const response = await apiPost<SecretVerificationResponse>(
      '/agents/secrets/verify',
      request
    );
    return response;
  } catch (error: any) {
    const errorMessage =
      error?.message || 'Secret verification failed';
    throw new Error(errorMessage);
  }
}

/**
 * 生成 Secret ID/Key（用於測試）
 */
export async function generateSecret(organization?: string): Promise<any> {
  return apiPost('/agents/secrets/generate', {
    organization: organization || undefined,
  });
}
