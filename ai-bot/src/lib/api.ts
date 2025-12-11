// 代碼功能說明: API 客戶端配置
// 創建日期: 2025-01-27
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-06

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
  console.warn(
    `[API Config] HTTPS page detected, but API_BASE_URL is ${API_BASE_URL}. ` +
    `Using current origin ${window.location.origin} instead. ` +
    `Make sure reverse proxy is configured.`
  );
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
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30秒超时

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
        const isAuthEndpoint = endpoint.includes('/auth/');
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
    // 超时错误处理
    if (error.name === 'AbortError') {
      console.error(`[apiRequest] Request timeout for ${url}`);
      throw new Error('API request timeout after 30 seconds');
    }
    // 網絡錯誤處理（如 CORS、連接失敗等）
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      console.error(`[apiRequest] Failed to fetch from ${url}. Check if the backend server is running and accessible.`, error);
      throw new Error(`無法連接到服務器: ${url}. 請確認後端服務器是否正在運行。`);
    }
    console.error(`[apiRequest] Error for ${url}:`, error);
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
}): Promise<FileListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.user_id) queryParams.append('user_id', params.user_id);
  if (params?.task_id) queryParams.append('task_id', params.task_id);
  if (params?.file_type) queryParams.append('file_type', params.file_type);
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  if (params?.offset) queryParams.append('offset', params.offset.toString());
  if (params?.sort_by) queryParams.append('sort_by', params.sort_by);
  if (params?.sort_order) queryParams.append('sort_order', params.sort_order);

  const query = queryParams.toString();
  return apiGet<FileListResponse>(`/files${query ? `?${query}` : ''}`);
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
  return apiGet<FileTreeResponse>(`/files/tree${query ? `?${query}` : ''}`);
}

/**
 * 下載文件
 */
export async function downloadFile(fileId: string): Promise<Blob> {
  const url = `${API_URL}/files/${fileId}/download`;
  const token = localStorage.getItem('access_token');

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (!response.ok) {
    throw new Error(`下載失敗: ${response.statusText}`);
  }

  return response.blob();
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
  dueDate?: string;
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
  };
  fileTree?: Array<{
    id: string;
    name: string;
    type: 'folder' | 'file';
    children?: Array<any>;
  }>;
  created_at: string;
  updated_at: string;
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
 */
export async function listUserTasks(): Promise<ListUserTasksResponse> {
  return apiGet<ListUserTasksResponse>('/user-tasks');
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
 */
export async function deleteUserTask(taskId: string): Promise<{ success: boolean; message?: string }> {
  return apiDelete(`/user-tasks/${taskId}`);
}
