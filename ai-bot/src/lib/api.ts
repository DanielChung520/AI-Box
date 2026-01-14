// 代碼功能說明: API 客戶端配置
// 創建日期: 2025-01-27
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-21 (UTC+8)

/**
 * API 客戶端配置
 * 用於統一管理前端與後端的 API 通信
 */

// 從環境變量獲取 API 基礎 URL，如果沒有則使用默認值
// 注意：生產環境應使用 HTTPS 和完整的域名，避免本地網絡請求限制
// 如果當前頁面是 HTTPS，且沒有設置 VITE_API_BASE_URL，則使用當前域名（避免 CORS 問題）
const getDefaultApiUrl = () => {
  // 開發環境：使用 localhost
  if (import.meta.env.DEV) {
    return 'http://localhost:8000';
  }

  // 如果當前頁面是 HTTPS，使用當前域名（避免 CORS 問題）
  if (window.location.protocol === 'https:') {
    return window.location.origin;
  }

  // 默認：使用當前域名
  return window.location.origin;
};

// 優先使用環境變量，如果設置了 VITE_API_BASE_URL，則使用它
// 否則使用默認邏輯
// 注意：如果前端從 HTTPS 頁面訪問，且 VITE_API_BASE_URL 設置為 http://localhost:8000，
// Chrome 會阻止請求。在這種情況下，需要配置反向代理或使用 HTTPS 的 localhost。
let API_BASE_URL = import.meta.env.VITE_API_BASE_URL || getDefaultApiUrl();

// 特殊處理：如果前端從 HTTPS 頁面訪問，但 API_BASE_URL 是 HTTP 的 localhost，
// 這會被 Chrome 阻止。在這種情況下，使用當前域名（通過反向代理）
if (window.location.protocol === 'https:' &&
    API_BASE_URL.startsWith('http://localhost')) {
  // 從 HTTPS 頁面訪問 localhost 會被瀏覽器阻止（混合內容策略）
  // 解決方案：使用當前域名，通過反向代理訪問後端
  // 只在開發環境顯示警告，生產環境靜默處理
  if (import.meta.env.DEV) {
    console.info(
      `[API Config] HTTPS page detected, using current origin ${window.location.origin} for API requests. ` +
      `(Original API_BASE_URL: ${API_BASE_URL})`
    );
  }
  API_BASE_URL = window.location.origin;
}
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
  timeout: 120000, // 120 秒超時（LLM 生成可能需要較長時間）
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

  // 獲取認證 token
  const token = localStorage.getItem('access_token');

  // 調試日誌：檢查 token 是否存在（僅在開發環境或調試時輸出）
  if (!token && !endpoint.includes('/auth/login')) {
    console.warn(`[apiRequest] No access_token found for request to ${endpoint}`);
  }

  // 為本地網絡請求添加 targetAddressSpace 選項（Chrome 安全策略兼容）
  // 重要：Authorization header 必須最後設置，確保不被覆蓋
  const fetchOptions: RequestInit = {
    ...options,
    headers: {
      ...apiConfig.headers,
      ...options.headers, // 先設置用戶自定義 headers
      ...(token ? { Authorization: `Bearer ${token}` } : {}), // 最後設置 Authorization，確保不被覆蓋
    },
  };

  // 如果是從 HTTPS 頁面訪問 localhost，需要特殊處理
  // Chrome 的安全策略不允許從 HTTPS 頁面訪問 localhost
  // 解決方案：如果當前頁面是 HTTPS，且目標是 localhost，則不設置 targetAddressSpace
  const isHttpsPage = window.location.protocol === 'https:';
  const isLocalhostTarget = url.includes('localhost') || url.includes('127.0.0.1');

  if (isLocalNetworkRequest(url) && !(isHttpsPage && isLocalhostTarget)) {
    // @ts-ignore - targetAddressSpace 是較新的 Fetch API 選項
    fetchOptions.targetAddressSpace = 'private';
  }

  try {
    // 添加超时控制
    const controller = new AbortController();
    // 對於 chat 請求，使用更長的超時時間（120 秒），因為 LLM 生成可能需要較長時間
    // 對於文件列表查詢和用戶任務查詢，也使用較長的超時時間（60 秒），因為可能需要查詢大量數據
    const isChatRequest = url.includes('/chat');
    const isFileListRequest = url.includes('/files') && !url.includes('/chat');
    const isUserTaskRequest = url.includes('/user-tasks');
    const timeoutDuration = isChatRequest
      ? 120000
      : (isFileListRequest || isUserTaskRequest)
        ? 60000
        : 30000; // chat: 120秒，文件列表/用戶任務: 60秒，其他: 30秒
    const timeoutId = setTimeout(() => controller.abort(), timeoutDuration);

    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      // 401 未授權錯誤：token 無效或過期，提示用戶重新登錄
      if (response.status === 401) {
        console.warn(`[apiRequest] Authentication failed for ${url}. Token may be missing, invalid, or expired.`);

        // 檢查是否為登錄相關的請求（不應該清除登錄頁面的 token）
        const isLoginEndpoint = endpoint.includes('/auth/login');

        // 只有非登錄相關的請求才清除 token（避免登錄過程中的誤清除）
        if (!isLoginEndpoint) {
          // 檢查 token 是否存在（如果不存在，可能是剛登錄還沒保存）
          const existingToken = localStorage.getItem('access_token');

          // 重要：登錄後的前幾秒內，如果 token 存在但驗證失敗，可能是：
          // 1. Token 剛保存，後端還未完全處理
          // 2. 網絡延遲導致 token 驗證時序問題
          // 3. 後端服務重啟導致 token 驗證邏輯異常
          //
          // 因此，在登錄後的短時間內（5 秒），我們不立即清除 token
          // 而是記錄警告，讓用戶重試
          const loginTime = localStorage.getItem('loginTime');
          const isRecentLogin = loginTime && (Date.now() - new Date(loginTime).getTime()) < 5000; // 5 秒內

          if (existingToken) {
            if (isRecentLogin) {
              console.warn(`[apiRequest] Token exists but authentication failed shortly after login. This may be a timing issue. Not clearing token yet.`);
              // 不清除 token，可能是時序問題，給後端一點時間
            } else {
              console.warn(`[apiRequest] Token exists but authentication failed. Clearing token.`);
              localStorage.removeItem('access_token');
              localStorage.removeItem('refresh_token');
              localStorage.removeItem('isAuthenticated');

              // 觸發認證狀態變化事件，讓前端組件處理（如跳轉到登錄頁）
              window.dispatchEvent(new CustomEvent('authStateChanged', {
                detail: { isAuthenticated: false, reason: 'token_expired' }
              }));
            }
          } else {
            console.warn(`[apiRequest] No token found. Request may have been made before token was saved.`);
          }
        }
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

      // 檢查是否為預期錯誤（新任務創建時的常見情況）
      const isExpectedError =
        // 任務不存在或不屬於當前用戶（403）
        (response.status === 403 && (
          errorMessage.includes('不存在') ||
          errorMessage.includes('不屬於當前用戶') ||
          errorMessage.includes('not found')
        )) ||
        // cursor count not enabled（500，後端配置問題，不影響功能）
        (response.status === 500 && errorMessage.includes('cursor count not enabled')) ||
        // 任務未找到（404，更新任務時可能出現）
        (response.status === 404 && (
          errorMessage.includes('Task not found') ||
          errorMessage.includes('任務') && errorMessage.includes('不存在')
        )) ||
        // 任務已存在（409，並發創建時的常見情況）
        (response.status === 409 && (
          errorMessage.includes('unique constraint') ||
          errorMessage.includes('already exists') ||
          errorMessage.includes('已存在')
        ));

      // 如果是預期錯誤，使用 console.debug 而不是 console.error
      if (isExpectedError) {
        console.debug(`[apiRequest] Expected error for ${url}:`, errorMessage);
      } else if (response.status === 404) {
        // 404 錯誤特別處理（非預期錯誤）
        console.warn(`API endpoint not found: ${url}. Make sure the backend server is running and the endpoint exists.`);
      }

      const error = new Error(errorMessage);
      (error as any).status = response.status;
      (error as any).data = errorData;
      (error as any).isExpected = isExpectedError; // 標記為預期錯誤，供上層使用
      throw error;
    }

    return response.json();
  } catch (error: any) {
    // 超时错误处理
    if (error.name === 'AbortError') {
      console.error(`[apiRequest] Request timeout for ${url}`);
      const isChatRequest = url.includes('/chat');
      const isFileListRequest = url.includes('/files') && !url.includes('/chat');
      const isUserTaskRequest = url.includes('/user-tasks');
      const timeoutDuration = isChatRequest
        ? 120
        : (isFileListRequest || isUserTaskRequest)
          ? 60
          : 30;
      throw new Error(`API request timeout after ${timeoutDuration} seconds`);
    }
    // 網絡錯誤處理（如 CORS、連接失敗等）
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      console.error(`[apiRequest] Failed to fetch from ${url}. Check if the backend server is running and accessible.`, error);
      throw new Error(`無法連接到服務器: ${url}. 請確認後端服務器是否正在運行。`);
    }
    // 如果是預期錯誤，使用 console.debug 而不是 console.error
    if (error.isExpected) {
      console.debug(`[apiRequest] Expected error for ${url}:`, error.message);
    } else {
      console.error(`[apiRequest] Error for ${url}:`, error);
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
export async function apiDelete<T = any>(endpoint: string, data?: any): Promise<T> {
  const options: RequestInit = { method: 'DELETE' };
  if (data) {
    options.body = JSON.stringify(data);
    options.headers = {
      'Content-Type': 'application/json',
    };
  }
  return apiRequest<T>(endpoint, options);
}

/**
 * PATCH 請求
 */
export async function apiPatch<T = any>(
  endpoint: string,
  data?: any
): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'PATCH',
    body: data ? JSON.stringify(data) : undefined,
  });
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
    icon?: string | null;
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
  category_id?: string; // 分類 ID（用於創建 Display Config）
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
 * Gateway 可用 Agent 響應類型
 */
export interface GatewayAvailableAgent {
  pattern: string;
  target: string;
  agent_name: string;
  is_registered: boolean;
  suggested_agent_id: string;
  suggested_capabilities: string[];
}

export interface GatewayAvailableAgentsResponse {
  success: boolean;
  data?: {
    available_agents: GatewayAvailableAgent[];
    total: number;
    gateway_endpoint: string;
  };
  message?: string;
  error?: string;
}

/**
 * 查詢 Cloudflare Gateway 上已配置但尚未在 AI-Box 註冊的 Agent
 */
export async function getGatewayAvailableAgents(): Promise<GatewayAvailableAgentsResponse> {
  try {
    const response = await apiGet<GatewayAvailableAgentsResponse>(
      '/gateway/available-agents'
    );
    return response;
  } catch (error: any) {
    const errorMessage =
      error?.message || 'Failed to query gateway available agents';
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

/**
 * 文件上傳響應類型
 */
export interface FileUploadResponse {
  success: boolean;
  data?: {
    uploaded: Array<{
      file_id: string;
      filename: string;
      file_type: string;
      file_size: number;
      file_path: string;
    }>;
    errors: Array<{
      filename: string;
      error: string;
    }>;
    total: number;
    success_count: number;
    error_count: number;
  };
  message?: string;
  error?: string;
}

/**
 * 建立空白 Markdown 檔案（不走 multipart upload）
 */
// 注意：新增檔案目前改為「前端草稿」；實際提交請走 /docs 的 preview-first apply

/**
 * 獲取認證 Token（從 localStorage）
 */
function getAuthToken(): string | null {
  return localStorage.getItem('access_token');
}

/**
 * 文件上傳（支持進度回調）
 *
 * @param files - 要上傳的文件列表
 * @param onProgress - 進度回調函數，參數為 0-100 的進度百分比
 * @param taskId - 任務ID（可選，用於組織文件到工作區，默認為 "temp-workspace"）
 * @returns 上傳響應
 */
export async function uploadFiles(
  files: File[],
  onProgress?: (progress: number) => void,
  taskId?: string
): Promise<FileUploadResponse> {
  if (files.length === 0) {
    throw new Error('請選擇至少一個文件');
  }

  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  // 修改時間：2025-01-27 - 移除 temp-workspace，task_id 必須提供
  // 如果未提供 task_id，後端會自動創建新任務
  if (taskId) {
    formData.append('task_id', taskId);
  }

  const url = `${API_URL}/files/upload`;

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    // 進度監聽
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        const percentComplete = Math.round((e.loaded / e.total) * 100);
        onProgress(percentComplete);
      }
    });

    // 完成處理
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText);
          // 修改時間：2025-12-12 - 上傳成功後通知前端刷新文件樹/列表
          try {
            const uploadedItems = response?.data?.uploaded || [];
            const uploadedFileIds = Array.isArray(uploadedItems)
              ? uploadedItems.map((i: any) => i?.file_id).filter(Boolean)
              : [];
            const resolvedTaskId =
              taskId ||
              response?.data?.task_id ||
              (uploadedItems?.[0]?.task_id ?? undefined);

            // 修改時間：2025-12-12 - 暫存最近一次上傳資訊，支援「上傳在聊天頁、切到文件頁」的刷新
            try {
              localStorage.setItem(
                'lastUploadInfo',
                JSON.stringify({
                  taskId: resolvedTaskId,
                  fileIds: uploadedFileIds,
                  ts: Date.now(),
                })
              );
            } catch {
              // ignore storage errors
            }

            // 向後兼容：同時派發 fileUploaded / filesUploaded（部分組件只聽其一）
            window.dispatchEvent(
              new CustomEvent('fileUploaded', {
                detail: {
                  fileIds: uploadedFileIds,
                  taskId: resolvedTaskId,
                },
              })
            );
            window.dispatchEvent(
              new CustomEvent('filesUploaded', {
                detail: {
                  files: uploadedItems,
                  taskId: resolvedTaskId,
                },
              })
            );
          } catch {
            // ignore event dispatch errors
          }
          resolve(response);
        } catch (error) {
          reject(new Error('無法解析服務器響應'));
        }
      } else {
        // 錯誤響應
        let errorMessage = `上傳失敗 (${xhr.status})`;
        try {
          const errorData = JSON.parse(xhr.responseText);
          errorMessage =
            errorData?.detail ||
            errorData?.message ||
            errorData?.error ||
            errorMessage;
        } catch {
          errorMessage = xhr.statusText || errorMessage;
        }

        // 401 未授權錯誤：清除無效 token 並觸發認證狀態變化
        if (xhr.status === 401) {
          console.warn('[uploadFiles] Authentication failed. Token may be missing, invalid, or expired.');
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('isAuthenticated');
          window.dispatchEvent(new CustomEvent('authStateChanged', {
            detail: { isAuthenticated: false, reason: 'token_expired' }
          }));
        }

        const error = new Error(errorMessage);
        (error as any).status = xhr.status;
        reject(error);
      }
    });

    // 錯誤處理
    xhr.addEventListener('error', () => {
      reject(new Error('網絡錯誤，請檢查網絡連接'));
    });

    // 中止處理
    xhr.addEventListener('abort', () => {
      reject(new Error('上傳已取消'));
    });

    xhr.open('POST', url);

    // 添加認證頭（必須在 open() 之後設置）
    const token = getAuthToken();
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      console.log('[uploadFiles] Authorization header set with token');
    } else {
      console.warn('[uploadFiles] No access token found in localStorage. Upload may fail with 401 error.');
    }

    // 不設置 Content-Type，讓瀏覽器自動設置 multipart/form-data 邊界
    xhr.send(formData);
  });
}

/**
 * 獲取上傳進度
 *
 * @param fileId - 文件ID
 * @returns 進度信息
 */
export interface UploadProgressResponse {
  success: boolean;
  data?: {
    file_id: string;
    status: 'uploading' | 'completed' | 'failed';
    progress: number;
    message?: string;
  };
  message?: string;
}

export async function getUploadProgress(
  fileId: string
): Promise<UploadProgressResponse> {
  return apiGet<UploadProgressResponse>(`/files/upload/${fileId}/progress`);
}

/**
 * 文件訪問級別枚舉
 */
export enum FileAccessLevel {
  PUBLIC = 'public',
  ORGANIZATION = 'organization',
  SECURITY_GROUP = 'security_group',
  PRIVATE = 'private',
}

/**
 * 數據分類級別枚舉
 */
export enum DataClassification {
  PUBLIC = 'public',
  INTERNAL = 'internal',
  CONFIDENTIAL = 'confidential',
  RESTRICTED = 'restricted',
}

/**
 * 敏感性標籤枚舉
 */
export enum SensitivityLabel {
  PII = 'pii',
  PHI = 'phi',
  FINANCIAL = 'financial',
  IP = 'ip',
  CUSTOMER = 'customer',
  PROPRIETARY = 'proprietary',
}

/**
 * 文件訪問控制接口
 */
export interface FileAccessControl {
  access_level: FileAccessLevel;
  authorized_organizations?: string[];
  authorized_security_groups?: string[];
  authorized_users?: string[];
  data_classification?: DataClassification;
  sensitivity_labels?: SensitivityLabel[];
  owner_id: string;
  owner_tenant_id?: string;
  access_log_enabled?: boolean;
  access_expires_at?: string; // ISO 8601 format
}

/**
 * 文件元數據接口
 */
export interface FileMetadata {
  file_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  user_id?: string;
  task_id?: string;
  tags: string[];
  description?: string;
  status?: string;
  processing_status?: string;
  chunk_count?: number;
  vector_count?: number;
  kg_status?: string;
  upload_time: string;
  created_at?: string;
  updated_at?: string;
  access_control?: FileAccessControl;
  data_classification?: DataClassification;
  sensitivity_labels?: SensitivityLabel[];
}

/**
 * 文件列表響應接口
 */
export interface FileListResponse {
  success: boolean;
  data: {
    files: FileMetadata[];
    total: number;
    limit: number;
    offset: number;
  };
  message?: string;
}

/**
 * 文件搜索響應接口
 */
export interface FileSearchResponse {
  success: boolean;
  data: {
    files: FileMetadata[];
    total: number;
    query: string;
  };
  message?: string;
}

/**
 * 文件樹響應接口
 */
export interface FileTreeResponse {
  success: boolean;
  data: {
    tree: Record<string, FileMetadata[]>;
    folders?: Record<string, {
      folder_name: string;
      parent_task_id?: string | null;
      task_id?: string; // 修改時間：2025-12-13 18:28:38 (UTC+8) - 兼容前端取資料夾所屬 task_id
      user_id: string;
      folder_type?: string; // 修改時間：2025-01-27 - 添加 folder_type 屬性（workspace, scheduled 等）
    }>;
    total_tasks: number;
    total_files: number;
  };
  message?: string;
}

/**
 * 獲取文件列表
 */
export async function getFileList(params?: {
  user_id?: string;
  task_id?: string;
  file_type?: string;
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  view_all_files?: boolean; // 修改時間：2026-01-06 - 添加 view_all_files 參數，允許管理員查看所有文件
}): Promise<FileListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.user_id) queryParams.append('user_id', params.user_id);
  if (params?.task_id) queryParams.append('task_id', params.task_id);
  if (params?.file_type) queryParams.append('file_type', params.file_type);
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  if (params?.offset) queryParams.append('offset', params.offset.toString());
  if (params?.sort_by) queryParams.append('sort_by', params.sort_by);
  if (params?.sort_order) queryParams.append('sort_order', params.sort_order);
  if (params?.view_all_files) queryParams.append('view_all_files', 'true');

  const query = queryParams.toString();
  const url = `/files${query ? `?${query}` : ''}`;
  console.log('[API] getFileList 請求:', url, '參數:', params);
  const response = await apiGet<FileListResponse>(url);
  console.log('[API] getFileList 響應:', {
    success: response.success,
    hasData: !!response.data,
    filesCount: response.data?.files?.length || 0,
    total: response.data?.total || 0,
    message: response.message,
  });
  return response;
}


/**
 * 搜索文件
 */
export async function searchFiles(params: {
  query: string;
  user_id?: string;
  file_type?: string;
  limit?: number;
}): Promise<FileSearchResponse> {
  const queryParams = new URLSearchParams();
  queryParams.append('query', params.query);
  if (params.user_id) queryParams.append('user_id', params.user_id);
  if (params.file_type) queryParams.append('file_type', params.file_type);
  if (params.limit) queryParams.append('limit', params.limit.toString());

  return apiGet<FileSearchResponse>(`/files/search?${queryParams.toString()}`);
}

/**
 * 獲取文件樹結構
 */
export async function getFileTree(params?: {
  user_id?: string;
  task_id?: string;
}): Promise<FileTreeResponse> {
  const queryParams = new URLSearchParams();
  if (params?.user_id) queryParams.append('user_id', params.user_id);
  // 修改時間：2025-12-09 - 如果 task_id 是 'temp-workspace'，不傳遞 task_id 參數，避免 403 錯誤
  if (params?.task_id && params.task_id !== 'temp-workspace') {
    queryParams.append('task_id', params.task_id);
  }

  const query = queryParams.toString();
  try {
    return await apiGet<FileTreeResponse>(`/files/tree${query ? `?${query}` : ''}`);
  } catch (error: any) {
    // 修改時間：2026-01-06 - 如果任務不存在（403），返回空文件樹，避免顯示錯誤
    if (error?.status === 403 || error?.message?.includes('403') || error?.message?.includes('不存在') || error?.message?.includes('不屬於')) {
      console.debug('[getFileTree] Task not found or access denied, returning empty tree', { task_id: params?.task_id });
      return {
        success: true,
        data: {
          tree: {},
          total_tasks: 0,
          total_files: 0,
        }
      };
    }
    // 其他錯誤繼續拋出
    throw error;
  }
}

/**
 * 下載文件
 */
export async function downloadFile(fileId: string): Promise<Blob> {
  const url = `${API_URL}/files/${fileId}/download`;
  const token = localStorage.getItem('access_token');

  console.log('[downloadFile] 開始下載文件:', { fileId, url, hasToken: !!token });

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  console.log('[downloadFile] 響應狀態:', response.status, response.statusText);
  console.log('[downloadFile] 響應頭:', {
    contentType: response.headers.get('content-type'),
    contentLength: response.headers.get('content-length')
  });

  if (!response.ok) {
    // 嘗試讀取錯誤詳情
    let errorMessage = `下載失敗`;

    // 先檢查 Content-Type，決定如何讀取響應
    const contentType = response.headers.get('content-type') || '';
    const isJson = contentType.includes('application/json');

    try {
      if (isJson) {
        // JSON 響應
        const errorJson = await response.json();
        errorMessage = errorJson.detail || errorJson.message || errorJson.error || errorMessage;
        console.log('[downloadFile] JSON 錯誤響應:', errorJson);
      } else {
        // 文本響應
        const errorText = await response.text();
        if (errorText && errorText.trim()) {
          // 嘗試解析為 JSON（有些 API 返回 JSON 但 Content-Type 不對）
          try {
            const errorJson = JSON.parse(errorText);
            errorMessage = errorJson.detail || errorJson.message || errorJson.error || errorText;
          } catch {
            errorMessage = errorText;
          }
        } else {
          // 如果沒有文本內容，使用狀態碼和狀態文本
          if (response.statusText) {
            errorMessage = `下載失敗: ${response.statusText}`;
          } else {
            errorMessage = `下載失敗 (HTTP ${response.status})`;
          }
        }
        console.log('[downloadFile] 文本錯誤響應:', errorText);
      }
    } catch (parseError) {
      // 如果讀取響應失敗，使用狀態碼
      console.error('[downloadFile] 讀取錯誤響應失敗:', parseError);
      if (response.statusText) {
        errorMessage = `下載失敗: ${response.statusText}`;
      } else {
        errorMessage = `下載失敗 (HTTP ${response.status})`;
  }
    }

    const error: any = new Error(errorMessage);
    error.status = response.status;
    error.statusText = response.statusText || '';
    console.error('[downloadFile] 下載失敗:', {
      status: response.status,
      statusText: response.statusText,
      errorMessage: errorMessage
    });
    throw error;
  }

  const blob = await response.blob();
  console.log('[downloadFile] 下載成功，文件大小:', blob.size, 'bytes', '類型:', blob.type);
  return blob;
}

/**
 * 預覽文件
 */
export interface FilePreviewResponse {
  success: boolean;
  data: {
    file_id: string;
    filename: string;
    file_type: string;
    content: string;
    is_truncated: boolean;
    file_size: number;
  };
  message?: string;
}

export async function previewFile(fileId: string): Promise<FilePreviewResponse> {
  return apiGet<FilePreviewResponse>(`/files/${fileId}/preview`);
}

/**
 * 保存文件内容
 * @param fileId - 文件 ID
 * @param content - 文件内容
 */
/**
 * 保存文件内容
 * @param fileId - 文件 ID
 * @param content - 文件内容
 */
export async function saveFile(
  fileId: string,
  content: string
): Promise<{ success: boolean; message?: string }> {
  try {
    // 使用文档编辑 API 保存文件
    // 创建编辑请求
    const editResponse = await createDocEdit({
      file_id: fileId,
      instruction: 'Save file content',
    });

    if (!editResponse.success || !editResponse.data?.request_id) {
      return { success: false, message: 'Failed to create edit request' };
    }

    const requestId = editResponse.data.request_id;

    // 等待编辑请求完成
    const maxRetries = 20;
    let retries = 0;
    let stateResponse;

    while (retries < maxRetries) {
      await new Promise((resolve) => setTimeout(resolve, 500));
      stateResponse = await getDocEditState(requestId);

      if (stateResponse.success && stateResponse.data) {
        const status = stateResponse.data.status;
        if (status === 'succeeded' || status === 'completed') {
          break;
        }
        if (status === 'failed' || status === 'aborted') {
          return {
            success: false,
            message: stateResponse.data.error_message || 'Edit request failed',
          };
        }
      }

      retries++;
    }

    if (!stateResponse?.success || stateResponse.data?.status !== 'succeeded') {
      return { success: false, message: 'Edit request timeout' };
    }

    // 应用编辑（实际保存文件）
    await applyDocEdit(requestId);

    return { success: true };
  } catch (error: any) {
    return { success: false, message: error?.message || 'Failed to save file' };
  }
}

/**
 * 文件助手（Doc Editing / Generation）
 */
export interface DocEditCreateRequest {
  file_id: string;
  instruction: string;
  base_version?: number;
}

export interface DocEditCreateResponse {
  success: boolean;
  data: {
    request_id: string;
    status: string;
  };
}

export interface DocEditStateResponse {
  success: boolean;
  data: {
    request_id: string;
    status: string;
    file_id: string;
    base_version: number;
    preview?: {
      patch_kind: 'unified_diff' | 'json_patch';
      patch: any;
      summary?: string;
    };
    apply_result?: {
      new_version: number;
    };
    error_code?: string;
    error_message?: string;
  };
}

export async function createDocEdit(payload: DocEditCreateRequest): Promise<DocEditCreateResponse> {
  return apiPost<DocEditCreateResponse>('/docs/edits', payload);
}

export async function getDocEditState(requestId: string): Promise<DocEditStateResponse> {
  return apiGet<DocEditStateResponse>(`/docs/edits/${requestId}`);
}

export async function abortDocEdit(requestId: string): Promise<any> {
  return apiPost(`/docs/edits/${requestId}/abort`);
}

export async function applyDocEdit(requestId: string): Promise<any> {
  return apiPost(`/docs/edits/${requestId}/apply`);
}

export async function listDocVersions(fileId: string): Promise<any> {
  return apiGet(`/docs/files/${fileId}/versions`);
}

export async function rollbackDocVersion(fileId: string, toVersion: number): Promise<any> {
  return apiPost(`/docs/files/${fileId}/rollback?to_version=${encodeURIComponent(String(toVersion))}`);
}

export interface DocGenCreateRequest {
  task_id: string;
  filename: string;
  doc_format: 'md' | 'txt' | 'json';
  instruction: string;
}

export interface DocGenCreateResponse {
  success: boolean;
  data: {
    request_id: string;
    status: string;
  };
}

export interface DocGenStateResponse {
  success: boolean;
  data: {
    request_id: string;
    status: string;
    preview?: { content: string };
    apply_result?: { file_id: string };
    error_code?: string;
    error_message?: string;
  };
}

export async function createDocGeneration(payload: DocGenCreateRequest): Promise<DocGenCreateResponse> {
  return apiPost<DocGenCreateResponse>('/docs/generations', payload);
}

export async function getDocGenerationState(requestId: string): Promise<DocGenStateResponse> {
  return apiGet<DocGenStateResponse>(`/docs/generations/${requestId}`);
}

export async function abortDocGeneration(requestId: string): Promise<any> {
  return apiPost(`/docs/generations/${requestId}/abort`);
}

export async function applyDocGeneration(requestId: string): Promise<any> {
  return apiPost(`/docs/generations/${requestId}/apply`);
}

/**
 * 刪除文件
 */
export async function deleteFile(fileId: string): Promise<{ success: boolean; message?: string }> {
  return apiDelete<{ success: boolean; message?: string }>(`/files/${fileId}`);
}

/**
 * 處理狀態響應接口
 */
export interface ProcessingStatusResponse {
  success: boolean;
  data: {
    file_id: string;
    status: string;
    progress: number;
    chunking?: {
      status: string;
      progress: number;
      message?: string;
    };
    vectorization?: {
      status: string;
      progress: number;
      message?: string;
    };
    storage?: {
      status: string;
      progress: number;
      message?: string;
      collection_name?: string;
      vector_count?: number;
    };
    kg_extraction?: {
      status: string;
      progress: number;
      message?: string;
      triples_count?: number;
      entities_count?: number;
      relations_count?: number;
      job_id?: string | null;
      next_job_id?: string | null;
      mode?: string;
      total_chunks?: number;
      completed_chunks?: number[];
      remaining_chunks?: number[];
      failed_chunks?: number[];
      failed_permanent_chunks?: number[];
    };
    message?: string;
  };
  message?: string;
}

/**
 * 獲取文件處理狀態
 */
export async function getProcessingStatus(fileId: string): Promise<ProcessingStatusResponse> {
  return apiGet<ProcessingStatusResponse>(`/files/${fileId}/processing-status`);
}

/**
 * KG 分塊狀態響應接口
 */
export interface KgChunkStatusResponse {
  success: boolean;
  data: {
    file_id: string;
    exists: boolean;
    total_chunks: number;
    completed_chunks: number[];
    failed_chunks: number[];
    failed_permanent_chunks: number[];
    attempts?: Record<string, number>;
    errors?: Record<string, { error?: string; ts?: number }>;
    chunks?: Record<string, any>;
  };
  message?: string;
}

/**
 * 獲取 KG 分塊狀態（用於可視化 chunk 進度）
 */
export async function getKgChunkStatus(fileId: string): Promise<KgChunkStatusResponse> {
  return apiGet<KgChunkStatusResponse>(`/files/${fileId}/kg/chunk-status`);
}

/**
 * 文件重命名請求接口
 */
export interface FileRenameRequest {
  new_name: string;
}

/**
 * 文件複製請求接口
 */
export interface FileCopyRequest {
  target_task_id?: string;
}

/**
 * 文件移動請求接口
 */
export interface FileMoveRequest {
  target_task_id: string;
}

/**
 * 資料夾創建請求接口
 */
export interface FolderCreateRequest {
  folder_name: string;
  parent_task_id?: string;
}

/**
 * 資料夾重命名請求接口
 */
export interface FolderRenameRequest {
  new_name: string;
}

/**
 * 重命名文件
 */
export async function renameFile(
  fileId: string,
  newName: string
): Promise<{ success: boolean; data?: any; message?: string }> {
  return apiPut(`/files/${fileId}/rename`, { new_name: newName });
}

/**
 * 複製文件
 */
export async function copyFile(
  fileId: string,
  targetTaskId?: string
): Promise<{ success: boolean; data?: any; message?: string }> {
  return apiPost(`/files/${fileId}/copy`, { target_task_id: targetTaskId });
}

/**
 * 移動文件
 */
export async function moveFile(
  fileId: string,
  targetTaskId: string,
  targetFolderId?: string | null
): Promise<{ success: boolean; data?: any; message?: string }> {
  return apiPut(`/files/${fileId}/move`, {
    target_task_id: targetTaskId,
    target_folder_id: targetFolderId ?? undefined,
  });
}

/**
 * 創建資料夾
 */
export async function createFolder(
  folderName: string,
  parentTaskId?: string | null
): Promise<{ success: boolean; data?: any; message?: string }> {
  // 如果 parentTaskId 是 null，明確傳遞 null（在根節點創建）
  // 如果 parentTaskId 是 undefined，不傳遞該字段（使用默認值）
  const body: { folder_name: string; parent_task_id?: string | null } = {
    folder_name: folderName,
  };
  if (parentTaskId !== undefined) {
    body.parent_task_id = parentTaskId;
  }
  return apiPost('/files/folders', body);
}

/**
 * 重命名資料夾
 */
export async function renameFolder(
  folderId: string,
  newName: string
): Promise<{ success: boolean; data?: any; message?: string }> {
  return apiPut(`/files/folders/${folderId}`, { new_name: newName });
}

/**
 * 刪除資料夾
 */
export async function deleteFolder(
  folderId: string
): Promise<{ success: boolean; data?: any; message?: string }> {
  return apiDelete(`/files/folders/${folderId}`);
}

/**
 * 移動資料夾（更改父資料夾）
 */
export async function moveFolder(
  folderId: string,
  parentTaskId: string | null
): Promise<{ success: boolean; data?: any; message?: string }> {
  return apiPatch(`/files/folders/${folderId}/move`, {
    parent_task_id: parentTaskId,
  });
}

/**
 * 附加文件到聊天
 */
export async function attachFileToChat(
  fileId: string
): Promise<{ success: boolean; data?: any; message?: string }> {
  return apiPost(`/files/${fileId}/attach`, {});
}

/**
 * 獲取文件的向量資料
 */
export async function getFileVectors(
  fileId: string,
  limit: number = 100,
  offset: number = 0
): Promise<{ success: boolean; data?: any; message?: string }> {
  return apiGet(`/files/${fileId}/vectors?limit=${limit}&offset=${offset}`);
}

/**
 * 獲取文件的圖譜資料
 */
export async function getFileGraph(
  fileId: string,
  limit: number = 100,
  offset: number = 0
): Promise<{ success: boolean; data?: any; message?: string }> {
  return apiGet(`/files/${fileId}/graph?limit=${limit}&offset=${offset}`);
}

/**
 * 更新文件元數據
 * 修改時間：2026-01-06 - 添加通用文件元數據更新函數
 */
export async function updateFileMetadata(
  fileId: string,
  update: {
    description?: string;
    custom_metadata?: Record<string, any>;
    tags?: string[];
    task_id?: string;
    folder_id?: string;
  }
): Promise<{ success: boolean; data?: FileMetadata; message?: string }> {
  return apiPut(`/files/${fileId}/metadata`, update);
}

/**
 * 更新文件訪問控制配置 (WBS-4.5.4)
 */
export async function updateFileAccessControl(
  fileId: string,
  accessControl: FileAccessControl
): Promise<{ success: boolean; data?: FileMetadata; message?: string }> {
  return apiPut(`/files/${fileId}/metadata`, {
    access_control: accessControl,
    data_classification: accessControl.data_classification,
    sensitivity_labels: accessControl.sensitivity_labels,
  });
}

/**
 * 獲取文件訪問控制配置 (WBS-4.5.4)
 */
export async function getFileAccessControl(
  fileId: string
): Promise<{ success: boolean; data?: FileAccessControl; message?: string }> {
  try {
    const response = await apiGet<{ success: boolean; data?: FileMetadata }>(`/files/${fileId}`);
    if (response.success && response.data?.access_control) {
      return {
        success: true,
        data: response.data.access_control,
      };
    }
    return { success: false, message: 'File access control not found' };
  } catch (error: any) {
    return { success: false, message: error.message || 'Failed to get file access control' };
  }
}

/**
 * 獲取文件訪問日誌 (WBS-4.5.4)
 */
export interface FileAccessLogQueryParams {
  file_id?: string;
  user_id?: string;
  granted?: boolean;
  start_date?: string; // ISO 8601 format
  end_date?: string; // ISO 8601 format
  limit?: number;
  offset?: number;
}

export interface FileAccessLog {
  user_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  timestamp: string;
  ip_address: string;
  user_agent: string;
  details: {
    reason: string;
    granted: boolean;
    access_level?: string;
    data_classification?: string;
    sensitivity_labels?: string[];
    owner_id?: string;
    required_permission?: string;
  };
}

export interface FileAccessLogsResponse {
  success: boolean;
  data?: {
    logs: FileAccessLog[];
    total: number;
    limit: number;
    offset: number;
  };
  message?: string;
}

export async function getFileAccessLogs(
  params: FileAccessLogQueryParams
): Promise<FileAccessLogsResponse> {
  const queryParams = new URLSearchParams();
  if (params.file_id) queryParams.append('file_id', params.file_id);
  if (params.user_id) queryParams.append('user_id', params.user_id);
  if (params.granted !== undefined) queryParams.append('granted', String(params.granted));
  if (params.start_date) queryParams.append('start_date', params.start_date);
  if (params.end_date) queryParams.append('end_date', params.end_date);
  if (params.limit) queryParams.append('limit', String(params.limit));
  if (params.offset) queryParams.append('offset', String(params.offset));

  return apiGet<FileAccessLogsResponse>(`/files/audit/logs?${queryParams.toString()}`);
}

/**
 * 重新生成文件的向量或圖譜數據
 * @param fileId 文件ID
 * @param type 重新生成的類型：'vector' 或 'graph'
 */
export async function regenerateFileData(
  fileId: string,
  type: 'vector' | 'graph'
): Promise<{ success: boolean; data?: any; message?: string }> {
  return apiPost(`/files/${fileId}/regenerate`, { type });
}

/**
 * 批量操作：批量重命名
 */
export async function batchRenameFiles(
  fileIds: string[],
  newNames: string[]
): Promise<Array<{ success: boolean; fileId: string; message?: string }>> {
  const results = [];
  for (let i = 0; i < fileIds.length; i++) {
    try {
      const result = await renameFile(fileIds[i], newNames[i]);
      results.push({
        success: result.success || false,
        fileId: fileIds[i],
        message: result.message,
      });
    } catch (error: any) {
      results.push({
        success: false,
        fileId: fileIds[i],
        message: error.message || '重命名失敗',
      });
    }
  }
  return results;
}

/**
 * 批量操作：批量複製
 */
export async function batchCopyFiles(
  fileIds: string[],
  targetTaskId?: string
): Promise<Array<{ success: boolean; fileId: string; message?: string }>> {
  const results = [];
  for (const fileId of fileIds) {
    try {
      const result = await copyFile(fileId, targetTaskId);
      results.push({
        success: result.success || false,
        fileId,
        message: result.message,
      });
    } catch (error: any) {
      results.push({
        success: false,
        fileId,
        message: error.message || '複製失敗',
      });
    }
  }
  return results;
}

/**
 * 批量操作：批量移動
 */
export async function batchMoveFiles(
  fileIds: string[],
  targetTaskId: string
): Promise<Array<{ success: boolean; fileId: string; message?: string }>> {
  const results = [];
  for (const fileId of fileIds) {
    try {
      const result = await moveFile(fileId, targetTaskId);
      results.push({
        success: result.success || false,
        fileId,
        message: result.message,
      });
    } catch (error: any) {
      results.push({
        success: false,
        fileId,
        message: error.message || '移動失敗',
      });
    }
  }
  return results;
}

/**
 * 批量操作：批量刪除
 */
export async function batchDeleteFiles(
  fileIds: string[]
): Promise<Array<{ success: boolean; fileId: string; message?: string }>> {
  const results = [];
  for (const fileId of fileIds) {
    try {
      const result = await deleteFile(fileId);
      results.push({
        success: result.success || false,
        fileId,
        message: result.message,
      });
    } catch (error: any) {
      results.push({
        success: false,
        fileId,
        message: error.message || '刪除失敗',
      });
    }
  }
  return results;
}

/**
 * 批量下載文件
 * 根據文件數量自動選擇下載方式：
 * - 文件數量 <= 5：前端循環調用單個下載API
 * - 文件數量 > 5：後端打包ZIP下載
 */
export async function batchDownloadFiles(
  fileIds: string[],
  onProgress?: (progress: number, currentFile: string) => void
): Promise<{ success: boolean; message?: string; errors?: Array<{ fileId: string; error: string }> }> {
  if (fileIds.length === 0) {
    return { success: false, message: '請選擇至少一個文件' };
  }

  const errors: Array<{ fileId: string; error: string }> = [];
  const BATCH_DOWNLOAD_THRESHOLD = 5;

  // 如果文件數量 <= 5，使用前端循環下載
  if (fileIds.length <= BATCH_DOWNLOAD_THRESHOLD) {
    for (let i = 0; i < fileIds.length; i++) {
      const fileId = fileIds[i];
      try {
        if (onProgress) {
          onProgress(Math.round(((i + 1) / fileIds.length) * 100), fileId);
        }

        // 下載文件
        const blob = await downloadFile(fileId);

        // 獲取文件名（從API獲取文件元數據）
        let filename = fileId;
        try {
          const fileInfo = await getFileInfo(fileId);
          if (fileInfo.success && fileInfo.data) {
            filename = fileInfo.data.filename || fileId;
          }
        } catch (e) {
          // 如果獲取文件名失敗，使用 fileId
          console.warn('無法獲取文件名，使用 fileId:', e);
        }

        // 創建下載鏈接並觸發下載
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        // 添加延遲，避免瀏覽器阻止多個下載
        if (i < fileIds.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      } catch (error: any) {
        console.error(`下載文件失敗: ${fileId}`, error);
        errors.push({
          fileId,
          error: error.message || '下載失敗',
        });
      }
    }

    return {
      success: errors.length === 0,
      message: errors.length === 0
        ? `成功下載 ${fileIds.length} 個文件`
        : `下載完成，但有 ${errors.length} 個文件下載失敗`,
      errors: errors.length > 0 ? errors : undefined,
    };
  } else {
    // 如果文件數量 > 5，使用後端打包ZIP下載
    try {
      const url = `${API_URL}/files/batch/download`;
      const token = getAuthToken();

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ file_ids: fileIds }),
      });

      if (!response.ok) {
        throw new Error(`批量下載失敗: ${response.statusText}`);
      }

      // 獲取ZIP文件
      const blob = await response.blob();

      // 創建下載鏈接並觸發下載
      const url_download = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url_download;
      link.download = `files-${Date.now()}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url_download);

      if (onProgress) {
        onProgress(100, '所有文件');
      }

      return {
        success: true,
        message: `成功下載 ${fileIds.length} 個文件（ZIP格式）`,
      };
    } catch (error: any) {
      console.error('批量下載失敗:', error);
      return {
        success: false,
        message: error.message || '批量下載失敗',
        errors: [{ fileId: 'batch', error: error.message || '批量下載失敗' }],
      };
    }
  }
}

/**
 * 獲取文件信息（用於下載時獲取文件名）
 */
async function getFileInfo(fileId: string): Promise<{ success: boolean; data?: { filename: string } }> {
  try {
    // 使用文件列表API獲取文件信息
    const response = await apiGet<{ success: boolean; data?: Array<{ file_id: string; filename: string }> }>(`/files?file_id=${fileId}&limit=1`);
    if (response.success && response.data && Array.isArray(response.data) && response.data.length > 0) {
      return {
        success: true,
        data: { filename: response.data[0].filename },
      };
    }
    return { success: false };
  } catch (error: any) {
    return { success: false };
  }
}

/**
 * 導出 api 對象（用於兼容性）
 */
/**
 * 模組化文檔 API
 */

/**
 * 模組化文檔子文檔引用
 */
export interface SubDocumentRef {
  sub_file_id: string;
  filename: string;
  section_title: string;
  order: number;
  transclusion_syntax: string;
  header_path?: string;
}

/**
 * 模組化文檔
 */
export interface ModularDocument {
  doc_id: string;
  master_file_id: string;
  title: string;
  task_id: string;
  description?: string;
  metadata: Record<string, any>;
  sub_documents: SubDocumentRef[];
  created_at: string;
  updated_at: string;
}

/**
 * 創建模組化文檔請求
 */
export interface ModularDocumentCreateRequest {
  doc_id?: string;
  master_file_id: string;
  title: string;
  task_id: string;
  description?: string;
  metadata?: Record<string, any>;
  sub_documents?: SubDocumentRef[];
}

/**
 * 模組化文檔 API 響應
 */
export interface ModularDocumentResponse {
  success: boolean;
  data: ModularDocument;
  message?: string;
}

/**
 * 模組化文檔列表響應
 */
export interface ModularDocumentListResponse {
  success: boolean;
  data: ModularDocument[];
  message?: string;
}

/**
 * 創建模組化文檔
 */
export async function createModularDocument(
  request: ModularDocumentCreateRequest
): Promise<ModularDocumentResponse> {
  return apiPost<ModularDocumentResponse>('/modular-documents', request);
}

/**
 * 獲取模組化文檔
 */
export async function getModularDocument(
  docId: string
): Promise<ModularDocumentResponse> {
  return apiGet<ModularDocumentResponse>(`/modular-documents/${docId}`);
}

/**
 * 根據主文檔文件 ID 獲取模組化文檔
 */
export async function getModularDocumentByMasterFile(
  masterFileId: string
): Promise<ModularDocumentResponse> {
  return apiGet<ModularDocumentResponse>(`/modular-documents/master-file/${masterFileId}`);
}

/**
 * 根據任務 ID 列出模組化文檔
 */
export async function listModularDocumentsByTask(
  taskId: string
): Promise<ModularDocumentListResponse> {
  return apiGet<ModularDocumentListResponse>(`/modular-documents/task/${taskId}/list`);
}

/**
 * 添加分文檔請求
 */
export interface AddSubDocumentRequest {
  sub_file_id: string;
  filename: string;
  section_title: string;
  order?: number;
  header_path?: string;
}

/**
 * 添加分文檔
 */
export async function addSubDocument(
  docId: string,
  request: AddSubDocumentRequest
): Promise<ModularDocumentResponse> {
  return apiPost<ModularDocumentResponse>(`/modular-documents/${docId}/sub-documents`, request);
}

/**
 * 移除分文檔請求
 */
export interface RemoveSubDocumentRequest {
  sub_file_id: string;
}

/**
 * 移除分文檔
 */
export async function removeSubDocument(
  docId: string,
  request: RemoveSubDocumentRequest
): Promise<ModularDocumentResponse> {
  return apiDelete<ModularDocumentResponse>(`/modular-documents/${docId}/sub-documents`, request);
}

export const api = {
  get: apiGet,
  post: apiPost,
  put: apiPut,
  delete: apiDelete,
  uploadFiles,
  getUploadProgress,
  getFileList,
  searchFiles,
  getFileTree,
  downloadFile,
  previewFile,
  deleteFile,
  getProcessingStatus,
  renameFile,
  copyFile,
  moveFile,
  createFolder,
  renameFolder,
  deleteFolder,
  moveFolder,
  attachFileToChat,
  getFileVectors,
  getFileGraph,
  batchRenameFiles,
  batchCopyFiles,
  batchMoveFiles,
  batchDeleteFiles,
  batchDownloadFiles,
  updateFileAccessControl,
  getFileAccessControl,
  getFileAccessLogs,
};

/**
 * 從文件庫上傳文件
 */
export interface LibraryUploadRequest {
  file_ids: string[];
  target_task_id: string;
}

export interface LibraryUploadResponse {
  success: boolean;
  data?: {
    uploaded: Array<{
      file_id: string;
      filename: string;
      file_type: string;
      file_size: number;
    }>;
    failed: Array<{
      file_id: string;
      error: string;
    }>;
    total: number;
    uploaded_count: number;
    failed_count: number;
  };
  message?: string;
}

export async function uploadFromLibrary(
  fileIds: string[],
  targetTaskId: string
): Promise<LibraryUploadResponse> {
  return apiPost<LibraryUploadResponse>('/files/library/upload', {
    file_ids: fileIds,
    target_task_id: targetTaskId,
  });
}

/**
 * 傳回文件庫
 */
export interface LibraryReturnRequest {
  file_ids: string[];
}

export interface LibraryReturnResponse {
  success: boolean;
  data?: {
    returned: Array<{
      file_id: string;
      filename: string;
    }>;
    failed: Array<{
      file_id: string;
      error: string;
    }>;
    total: number;
    returned_count: number;
    failed_count: number;
  };
  message?: string;
}

export async function returnToLibrary(
  fileIds: string[]
): Promise<LibraryReturnResponse> {
  return apiPost<LibraryReturnResponse>('/files/library/return', {
    file_ids: fileIds,
  });
}

/**
 * 同步文件
 */
export interface SyncFilesRequest {
  task_id?: string;
  file_ids?: string[];
}

export interface SyncFilesResponse {
  success: boolean;
  data?: {
    synced: Array<{
      file_id: string;
      filename: string;
      status: string;
      checks: {
        file_exists: boolean;
        metadata_exists: boolean;
        vector_exists: boolean;
      };
      updates: string[];
    }>;
    total: number;
  };
  message?: string;
}

export async function syncFiles(
  request: SyncFilesRequest
): Promise<SyncFilesResponse> {
  return apiPost<SyncFilesResponse>('/files/sync', request);
}

/**
 * 搜尋文件庫
 */
export interface LibrarySearchRequest {
  query: string;
  page?: number;
  limit?: number;
}

export interface LibrarySearchResponse {
  success: boolean;
  data?: {
    files: Array<{
      file_id: string;
      filename: string;
      file_type: string;
      file_size: number;
    }>;
    total: number;
    page: number;
    limit: number;
    total_pages: number;
  };
  message?: string;
}

export async function searchLibrary(
  params: LibrarySearchRequest
): Promise<LibrarySearchResponse> {
  const queryParams = new URLSearchParams();
  queryParams.append('query', params.query);
  if (params.page) queryParams.append('page', params.page.toString());
  if (params.limit) queryParams.append('limit', params.limit.toString());

  return apiGet<LibrarySearchResponse>(`/files/library/search?${queryParams.toString()}`);
}

/**
 * 用戶任務同步相關 API
 */

export interface UserTask {
  task_id: string;
  user_id: string;
  title: string;
  status: 'pending' | 'in-progress' | 'completed';
  task_status?: 'activate' | 'archive';
  label_color?: string | null;
  dueDate?: string;
  created_at?: string; // 修改時間：2026-01-06 - 添加創建時間（ISO 8601 格式字符串）
  updated_at?: string; // 修改時間：2026-01-06 - 添加更新時間（ISO 8601 格式字符串）
  messages?: Array<{
    id: string;
    sender: 'user' | 'ai';
    content: string;
    timestamp: string;
    containsMermaid?: boolean;
  }>;
  executionConfig?: {
    mode: 'free' | 'assistant' | 'agent';
    assistantId?: string;
    agentId?: string;
    modelId?: string; // 產品級 Chat：任務維度模型選擇
    sessionId?: string; // 產品級 Chat：任務維度 session_id
  };
  fileTree?: Array<{
    id: string;
    name: string;
    type: 'folder' | 'file';
    children?: Array<any>;
  }>;
}

export interface ListUserTasksResponse {
  success: boolean;
  data?: {
    tasks: UserTask[];
    total: number;
  };
  message?: string;
}

export interface SyncTasksRequest {
  tasks: Array<{
    id: number | string;
    task_id?: number | string;
    title: string;
    status?: 'pending' | 'in-progress' | 'completed';
    dueDate?: string;
    messages?: Array<any>;
    executionConfig?: any;
    fileTree?: Array<any>;
  }>;
}

export interface SyncTasksResponse {
  success: boolean;
  data?: {
    created: number;
    updated: number;
    errors: number;
    total: number;
  };
  message?: string;
}

/**
 * 列出用戶的所有任務
 * @param includeArchived 是否包含歸檔的任務（默認 false，只顯示激活的任務）
 */
export async function listUserTasks(includeArchived: boolean = false, limit: number = 100, offset: number = 0): Promise<ListUserTasksResponse> {
  const params = new URLSearchParams();
  if (includeArchived) {
    params.append('include_archived', 'true');
  }
  if (limit !== 100) {
    params.append('limit', limit.toString());
  }
  if (offset !== 0) {
    params.append('offset', offset.toString());
  }
  const queryString = params.toString();
  const url = `/user-tasks${queryString ? `?${queryString}` : ''}`;
  return apiGet<ListUserTasksResponse>(url);
}

/**
 * 同步任務列表到後台
 */
export async function syncTasks(
  tasks: SyncTasksRequest['tasks']
): Promise<SyncTasksResponse> {
  return apiPost<SyncTasksResponse>('/user-tasks/sync', { tasks });
}

/**
 * 獲取指定任務
 */
export async function getUserTask(taskId: string): Promise<{ success: boolean; data?: UserTask; message?: string }> {
  return apiGet(`/user-tasks/${taskId}`);
}

/**
 * 創建用戶任務
 */
// 修改時間：2025-01-27 - user_id 改為可選，後端會自動使用當前認證用戶的 user_id
export async function createUserTask(task: {
  task_id: string;
  user_id?: string; // 可選，後端會自動使用當前認證用戶的 user_id
  title: string;
  status?: 'pending' | 'in-progress' | 'completed';
  dueDate?: string;
  created_at?: string; // 修改時間：2026-01-06 - 添加創建時間（ISO 8601 格式字符串）
  updated_at?: string; // 修改時間：2026-01-06 - 添加更新時間（ISO 8601 格式字符串）
  messages?: Array<any>;
  executionConfig?: any;
  fileTree?: Array<any>;
}): Promise<{ success: boolean; data?: UserTask; message?: string }> {
  // 不傳遞 user_id，後端會自動使用當前認證用戶的 user_id
  const { user_id, ...taskWithoutUserId } = task;
  return apiPost('/user-tasks', taskWithoutUserId);
}

/**
 * 更新用戶任務
 */
export async function updateUserTask(
  taskId: string,
  update: {
    title?: string;
    status?: 'pending' | 'in-progress' | 'completed';
    task_status?: 'activate' | 'archive'; // 修改時間：2025-12-09 - 添加任務顯示狀態
    label_color?: string | null; // 修改時間：2025-12-09 - 添加任務顏色標籤
    dueDate?: string;
    messages?: Array<any>;
    executionConfig?: any;
    fileTree?: Array<any>;
  }
): Promise<{ success: boolean; data?: UserTask; message?: string }> {
  return apiPut(`/user-tasks/${taskId}`, update);
}

/**
 * 刪除用戶任務
 * 修改時間：2026-01-06 - 改進錯誤處理：如果任務不存在（404），返回 success: false 而不是拋出異常
 */
export async function deleteUserTask(taskId: string): Promise<{ success: boolean; message?: string }> {
  try {
    return await apiDelete<{ success: boolean; message?: string }>(`/user-tasks/${taskId}`);
  } catch (error: any) {
    // 如果是 404 錯誤（任務不存在），返回 success: false 而不是拋出異常
    // 這樣前端可以根據情況決定是否繼續刪除本地任務
    if (error?.status === 404 || error?.message?.includes('404') || error?.message?.includes('not found')) {
      return {
        success: false,
        message: 'Task not found',
      };
    }
    // 其他錯誤繼續拋出
    throw error;
  }
}

/**
 * 產品級 Chat API（/api/v1/chat）
 */

export type ChatRole = 'system' | 'user' | 'assistant';
export type ModelSelectorMode = 'auto' | 'manual' | 'favorite';

export type ChatAction =
  | {
      type: 'file_created';
      file_id: string;
      filename: string;
      task_id?: string;
      folder_id?: string | null;
      folder_path?: string | null;
    }
  | {
      type: 'file_edited';
      file_id: string;
      filename: string;
      request_id: string;
      preview?: any;
      task_id?: string;
      is_draft?: boolean;
    }
  | Record<string, any>;

export interface ChatProductMessage {
  role: ChatRole;
  content: string;
}

export interface ModelSelector {
  mode: ModelSelectorMode;
  model_id?: string;
  policy_overrides?: Record<string, any>;
}

export interface ChatAttachment {
  file_id: string;
  file_name: string;
  file_path?: string;
  task_id?: string;
}

export interface ChatProductRequest {
  messages: ChatProductMessage[];
  session_id?: string;
  task_id?: string;
  model_selector: ModelSelector;
  attachments?: ChatAttachment[];
  allowed_tools?: string[]; // 允许使用的工具列表，例如 ['web_search']
  assistant_id?: string; // 当前选中的助理 ID
  agent_id?: string; // 修改時間：2026-01-27 - 當前選中的代理 ID
}

export interface ChatProductResult {
  content: string;
  session_id: string;
  task_id?: string;
  actions?: ChatAction[] | null;
  routing: {
    provider: string;
    model?: string | null;
    strategy: string;
    latency_ms?: number | null;
    failover_used: boolean;
    fallback_provider?: string | null;
  };
  observability?: Record<string, any> | null;
}

export interface ChatProductResponse {
  success: boolean;
  data?: ChatProductResult;
  message?: string;
  error_code?: string;
  details?: any;
}

export async function chatProduct(request: ChatProductRequest): Promise<ChatProductResponse> {
  return apiPost<ChatProductResponse>('/chat', request);
}

/**
 * 產品級 Chat API - 流式版本（/api/v1/chat/stream）
 * 返回一個 async generator，逐塊接收內容
 */
export async function* chatProductStream(
  request: ChatProductRequest
): AsyncGenerator<{ type: string; data: any }, void, unknown> {
  const url = `${API_URL}/chat/stream`;
  const token = localStorage.getItem('access_token');

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 120000); // 120秒超時

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        ...apiConfig.headers,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    if (!response.body) {
      throw new Error('Response body is null');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // 處理 SSE 格式：每行以 "data: " 開頭
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 保留最後一個不完整的行

        for (const line of lines) {
          if (line.trim() === '') continue;
          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6); // 移除 "data: " 前綴
              const event = JSON.parse(jsonStr);
              yield event;
            } catch (e) {
              console.warn('[chatProductStream] Failed to parse SSE data:', line, e);
            }
          }
        }
      }

      // 處理最後的 buffer
      if (buffer.trim()) {
        const lines = buffer.split('\n');
        for (const line of lines) {
          if (line.trim() === '') continue;
          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6);
              const event = JSON.parse(jsonStr);
              yield event;
            } catch (e) {
              console.warn('[chatProductStream] Failed to parse SSE data:', line, e);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  } catch (error: any) {
    if (error.name === 'AbortError') {
      throw new Error('API request timeout after 120 seconds');
    }
    throw error;
  }
}

/**
 * 收藏模型偏好（hybrid：API 優先，失敗 fallback localStorage）
 */

const FAVORITE_MODELS_STORAGE_KEY = 'ai-box-favorite-models';

const loadFavoriteModelsLocal = (): string[] => {
  try {
    const raw = localStorage.getItem(FAVORITE_MODELS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.map(String) : [];
  } catch {
    return [];
  }
};

const saveFavoriteModelsLocal = (modelIds: string[]): void => {
  try {
    localStorage.setItem(FAVORITE_MODELS_STORAGE_KEY, JSON.stringify(modelIds));
  } catch {
    // ignore
  }
};

export interface FavoriteModelsResponse {
  success: boolean;
  data?: { model_ids: string[] };
  message?: string;
  error_code?: string;
}

export async function getFavoriteModels(): Promise<FavoriteModelsResponse> {
  try {
    const resp = await apiGet<FavoriteModelsResponse>('/chat/preferences/models');
    if (resp?.success && resp.data?.model_ids) {
      saveFavoriteModelsLocal(resp.data.model_ids);
    }
    return resp;
  } catch (error: any) {
    return {
      success: true,
      data: { model_ids: loadFavoriteModelsLocal() },
      message: 'Fallback to localStorage',
    };
  }
}

export async function setFavoriteModels(model_ids: string[]): Promise<FavoriteModelsResponse> {
  // 先本地保存，避免 UI 受網路波動影響
  saveFavoriteModelsLocal(model_ids);
  try {
    return await apiPut<FavoriteModelsResponse>('/chat/preferences/models', { model_ids });
  } catch (error: any) {
    return {
      success: true,
      data: { model_ids },
      message: 'Saved to localStorage (API unavailable)',
    };
  }
}

/**
 * LLM 模型相關 API
 */

export interface LLMModel {
  model_id: string;
  name: string;
  provider: string;
  description?: string;
  capabilities?: string[];
  status?: string;
  context_window?: number;
  max_output_tokens?: number;
  parameters?: string;
  release_date?: string;
  license?: string;
  languages?: string[];
  icon?: string;
  color?: string;
  order?: number;
  is_default?: boolean;
  metadata?: Record<string, any>;
  source?: string; // 'database' | 'ollama_discovered'
  ollama_endpoint?: string;
  ollama_node?: string;
  is_favorite?: boolean;
  is_active?: boolean; // 模型是否可用（根據 Provider API Key 配置判斷）
}

export interface LLMModelsResponse {
  success: boolean;
  data?: {
    models: LLMModel[];
    total: number;
  };
  message?: string;
  error_code?: string;
}

export interface GetModelsParams {
  provider?: string;
  status_filter?: string;
  capability?: string;
  search?: string;
  include_discovered?: boolean;
  include_favorite_status?: boolean;
  limit?: number;
  offset?: number;
}

/**
 * 獲取 LLM 模型列表
 */
export async function getModels(params?: GetModelsParams): Promise<LLMModelsResponse> {
  try {
    const queryParams = new URLSearchParams();
    if (params?.provider) queryParams.append('provider', params.provider);
    if (params?.status_filter) queryParams.append('status_filter', params.status_filter);
    if (params?.capability) queryParams.append('capability', params.capability);
    if (params?.search) queryParams.append('search', params.search);
    if (params?.include_discovered !== undefined) {
      queryParams.append('include_discovered', String(params.include_discovered));
    }
    if (params?.include_favorite_status !== undefined) {
      queryParams.append('include_favorite_status', String(params.include_favorite_status));
    }
    if (params?.limit) queryParams.append('limit', String(params.limit));
    if (params?.offset) queryParams.append('offset', String(params.offset));

    const endpoint = `/models${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    return await apiGet<LLMModelsResponse>(endpoint);
  } catch (error: any) {
    console.error('[getModels] Failed to fetch models:', error);
    throw error;
  }
}

/**
 * 編輯 Session API
 * 修改時間：2026-01-06 - 添加文件編輯 Session 支持
 */

export interface StartEditingSessionRequest {
  doc_id: string;
  ttl_seconds?: number;
}

export interface StartEditingSessionResponse {
  success: boolean;
  data?: {
    session_id: string;
    ws_url?: string;
  };
  message?: string;
  error_code?: string;
}

export async function startEditingSession(
  request: StartEditingSessionRequest
): Promise<StartEditingSessionResponse> {
  return apiPost<StartEditingSessionResponse>('/editing/session/start', request);
}

export interface SubmitEditingCommandRequest {
  session_id: string;
  command: string;
  cursor_context?: {
    file?: string;
    line?: number;
    column?: number;
    selection?: string;
  };
}

export interface SubmitEditingCommandResponse {
  success: boolean;
  data?: {
    request_id: string;
    status: string;
  };
  message?: string;
  error_code?: string;
}

export async function submitEditingCommand(
  request: SubmitEditingCommandRequest
): Promise<SubmitEditingCommandResponse> {
  return apiPost<SubmitEditingCommandResponse>('/editing/command', request);
}

/**
 * Agent Display Config API
 * 修改時間：2026-01-13 - 添加代理展示配置 API
 */

import type { AgentDisplayConfigResponse } from '../types/agentDisplayConfig';

/**
 * API 響應格式
 */
interface APIResponse<T> {
  success: boolean;
  message?: string;
  data?: T;
}

/**
 * 獲取代理展示配置
 */
export async function getAgentDisplayConfig(
  tenantId?: string,
  includeInactive: boolean = false
): Promise<AgentDisplayConfigResponse> {
  const params = new URLSearchParams();
  if (tenantId) params.append('tenant_id', tenantId);
  if (includeInactive) params.append('include_inactive', 'true');

  const queryString = params.toString();
  const endpoint = queryString ? `/agent-display-configs?${queryString}` : '/agent-display-configs';

  const response = await apiGet<APIResponse<AgentDisplayConfigResponse>>(endpoint);

  // 從 API 響應中提取 data 字段
  if (response && response.success && response.data) {
    return response.data;
  }

  // 如果響應格式不符合預期，嘗試直接返回（向後兼容）
  if (response && (response as any).categories) {
    return response as unknown as AgentDisplayConfigResponse;
  }

  // 如果都沒有，返回空結構
  return { categories: [] };
}

/**
 * 獲取單個代理配置
 */
export async function getAgentConfig(
  agentId: string,
  tenantId?: string
): Promise<any> {
  const params = new URLSearchParams();
  if (tenantId) params.append('tenant_id', tenantId);

  const queryString = params.toString();
  const endpoint = `/agent-display-configs/agents/${agentId}${queryString ? `?${queryString}` : ''}`;

  const response = await apiGet<APIResponse<any>>(endpoint);

  if (response && response.success && response.data) {
    return response.data;
  }

  throw new Error(response?.message || 'Failed to get agent config');
}

/**
 * 更新代理配置
 */
export async function updateAgentConfig(
  agentId: string,
  agentConfig: any,
  tenantId?: string
): Promise<any> {
  const params = new URLSearchParams();
  if (tenantId) params.append('tenant_id', tenantId);

  const queryString = params.toString();
  const endpoint = `/agent-display-configs/agents/${agentId}${queryString ? `?${queryString}` : ''}`;

  const response = await apiPut<APIResponse<any>>(endpoint, agentConfig);

  if (response && response.success) {
    return response.data;
  }

  throw new Error(response?.message || 'Failed to update agent config');
}

/**
 * 刪除代理配置
 */
export async function deleteAgentConfig(
  agentId: string,
  tenantId?: string
): Promise<any> {
  const params = new URLSearchParams();
  if (tenantId) params.append('tenant_id', tenantId);

  const queryString = params.toString();
  const endpoint = `/agent-display-configs/agents/${agentId}${queryString ? `?${queryString}` : ''}`;

  const response = await apiDelete<APIResponse<any>>(endpoint);

  if (response && response.success) {
    return response.data;
  }

  throw new Error(response?.message || 'Failed to delete agent config');
}
