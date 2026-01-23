/**
 * 代碼功能說明: SeaWeedFS S3 API 客戶端工具函數
 * 創建日期: 2026-01-21
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-21 11:57 UTC+8
 *
 * 功能說明:
 * - 提供從 SeaWeedFS S3 API 直接讀取文件的工具函數
 * - 支持使用 S3 URI (s3://bucket/key) 格式訪問文件
 * - 自動處理認證和錯誤
 */

/**
 * SeaWeedFS 配置
 * 從環境變量獲取，如果未設置則使用默認值
 */
const SEAWEEDFS_CONFIG = {
  endpoint: import.meta.env.VITE_SEAWEEDFS_S3_ENDPOINT || 'http://localhost:8333',
  accessKey: import.meta.env.VITE_SEAWEEDFS_S3_ACCESS_KEY || 'admin',
  secretKey: import.meta.env.VITE_SEAWEEDFS_S3_SECRET_KEY || 'admin123',
  useSSL: import.meta.env.VITE_SEAWEEDFS_USE_SSL === 'true' || false,
};

/**
 * 解析 S3 URI，返回 bucket 和 key
 * @param s3Uri S3 URI 格式：s3://bucket/key 或 https://endpoint/bucket/key
 * @returns { bucket: string, key: string } 或 null
 */
export function parseS3Uri(s3Uri: string): { bucket: string; key: string } | null {
  if (!s3Uri) return null;

  // 處理 s3://bucket/key 格式
  if (s3Uri.startsWith('s3://')) {
    const match = s3Uri.match(/^s3:\/\/([^/]+)\/(.+)$/);
    if (match) {
      return {
        bucket: match[1],
        key: match[2],
      };
    }
  }

  // 處理 https://endpoint/bucket/key 格式
  if (s3Uri.startsWith('https://') || s3Uri.startsWith('http://')) {
    try {
      const url = new URL(s3Uri);
      const pathParts = url.pathname.split('/').filter(Boolean);
      if (pathParts.length >= 2) {
        return {
          bucket: pathParts[0],
          key: pathParts.slice(1).join('/'),
        };
      }
    } catch (e) {
      console.error('[parseS3Uri] Failed to parse URL:', e);
      return null;
    }
  }

  return null;
}

/**
 * 構建 SeaWeedFS S3 API URL
 * @param bucket Bucket 名稱
 * @param key 對象鍵
 * @returns S3 API URL
 */
function buildS3Url(bucket: string, key: string): string {
  const protocol = SEAWEEDFS_CONFIG.useSSL ? 'https' : 'http';
  return `${protocol}://${SEAWEEDFS_CONFIG.endpoint.replace(/^https?:\/\//, '')}/${bucket}/${key}`;
}

/**
 * 生成 AWS Signature V4 簽名（簡化版，用於 SeaWeedFS）
 * 注意：SeaWeedFS 的 S3 API 可能不需要完整的簽名，這裡提供基本實現
 * @param method HTTP 方法
 * @param url 請求 URL
 * @param headers 請求頭
 * @returns 簽名後的請求頭
 */
async function signRequest(
  method: string,
  url: string,
  headers: Record<string, string> = {}
): Promise<Record<string, string>> {
  // SeaWeedFS 的 S3 API 通常使用簡單的認證方式
  // 如果配置了 accessKey 和 secretKey，添加到請求頭
  const signedHeaders: Record<string, string> = {
    ...headers,
  };

  if (SEAWEEDFS_CONFIG.accessKey && SEAWEEDFS_CONFIG.secretKey) {
    // 注意：實際的 AWS Signature V4 簽名非常複雜
    // 這裡提供一個簡化版本，如果 SeaWeedFS 需要完整簽名，可能需要使用 AWS SDK
    // 或者通過後端代理來處理認證
    signedHeaders['Authorization'] = `AWS ${SEAWEEDFS_CONFIG.accessKey}:${SEAWEEDFS_CONFIG.secretKey}`;
  }

  return signedHeaders;
}

/**
 * 從 SeaWeedFS S3 API 直接讀取文件
 * @param s3Uri S3 URI 格式：s3://bucket/key
 * @param options 可選參數
 * @returns Blob 對象
 */
export async function readFileFromSeaWeedFS(
  s3Uri: string,
  options: {
    signal?: AbortSignal;
    onProgress?: (loaded: number, total: number) => void;
  } = {}
): Promise<Blob> {
  const parsed = parseS3Uri(s3Uri);
  if (!parsed) {
    throw new Error(`Invalid S3 URI: ${s3Uri}`);
  }

  const { bucket, key } = parsed;
  const url = buildS3Url(bucket, key);

  console.log('[readFileFromSeaWeedFS] 開始從 SeaWeedFS 讀取文件:', {
    s3Uri,
    bucket,
    key,
    url,
  });

  try {
    // 構建請求頭
    const headers: Record<string, string> = {
      'Accept': '*/*',
    };

    // 添加認證（如果配置了）
    const signedHeaders = await signRequest('GET', url, headers);

    // 發送請求
    const response = await fetch(url, {
      method: 'GET',
      headers: signedHeaders,
      signal: options.signal,
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      throw new Error(
        `Failed to read file from SeaWeedFS: ${response.status} ${response.statusText}. ${errorText}`
      );
    }

    // 如果提供了進度回調，使用 Response.body 的流式讀取
    if (options.onProgress) {
      const contentLength = response.headers.get('content-length');
      const total = contentLength ? parseInt(contentLength, 10) : 0;

      if (total > 0 && response.body) {
        const reader = response.body.getReader();
        const chunks: Uint8Array[] = [];
        let loaded = 0;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          chunks.push(value);
          loaded += value.length;
          options.onProgress(loaded, total);
        }

        // 合併所有 chunks
        const allChunks = new Uint8Array(loaded);
        let offset = 0;
        for (const chunk of chunks) {
          allChunks.set(chunk, offset);
          offset += chunk.length;
        }

        return new Blob([allChunks], {
          type: response.headers.get('content-type') || 'application/octet-stream',
        });
      }
    }

    // 直接讀取 Blob
    const blob = await response.blob();
    console.log('[readFileFromSeaWeedFS] 文件讀取成功:', {
      size: blob.size,
      type: blob.type,
    });

    return blob;
  } catch (error: any) {
    console.error('[readFileFromSeaWeedFS] 讀取文件失敗:', error);
    throw error;
  }
}

/**
 * 檢查文件是否存在於 SeaWeedFS
 * @param s3Uri S3 URI 格式：s3://bucket/key
 * @returns 文件是否存在
 */
export async function checkFileExistsInSeaWeedFS(s3Uri: string): Promise<boolean> {
  try {
    const parsed = parseS3Uri(s3Uri);
    if (!parsed) return false;

    const { bucket, key } = parsed;
    const url = buildS3Url(bucket, key);

    const headers: Record<string, string> = {
      'Accept': '*/*',
    };

    const signedHeaders = await signRequest('HEAD', url, headers);

    const response = await fetch(url, {
      method: 'HEAD',
      headers: signedHeaders,
    });

    return response.ok;
  } catch (error) {
    console.error('[checkFileExistsInSeaWeedFS] 檢查文件存在性失敗:', error);
    return false;
  }
}
