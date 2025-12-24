// 代碼功能說明: JWT Token 解析工具
// 創建日期: 2025-01-27
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-08 08:46:00 UTC+8

/**
 * JWT Token 解析工具
 * 用於從 JWT token 中解析用戶信息
 */

/**
 * 解析 JWT token 的 payload（不驗證簽名）
 * @param token JWT token 字符串
 * @returns Token payload 對象，如果解析失敗則返回 null
 */
export function parseJwtToken(token: string): Record<string, any> | null {
  try {
    // JWT token 格式：header.payload.signature
    const parts = token.split('.');
    if (parts.length !== 3) {
      console.error('[JWT] Invalid token format');
      return null;
    }

    // 解碼 payload（base64url）
    const payload = parts[1];
    // 將 base64url 轉換為 base64
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    // 添加 padding（如果需要）
    const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
    // 解碼 base64
    const decoded = atob(padded);
    // 解析 JSON
    return JSON.parse(decoded);
  } catch (error) {
    console.error('[JWT] Failed to parse token:', error);
    return null;
  }
}

/**
 * 從 JWT token 中獲取 user_id
 * @param token JWT token 字符串
 * @returns user_id，如果解析失敗則返回 null
 */
export function getUserIdFromToken(token: string): string | null {
  const payload = parseJwtToken(token);
  if (!payload) {
    return null;
  }

  // 嘗試從 payload 中獲取 user_id（優先使用 sub，因為這是 JWT 標準）
  return payload.sub || payload.user_id || null;
}

/**
 * 從 localStorage 中獲取當前用戶的 user_id
 * @returns user_id，如果不存在則返回 null
 */
export function getCurrentUserId(): string | null {
  const token = localStorage.getItem('access_token');
  if (!token) {
    return null;
  }

  return getUserIdFromToken(token);
}
