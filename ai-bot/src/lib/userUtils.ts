// 代碼功能說明: 用戶工具函數 - 統一的用戶信息獲取和權限檢查
// 創建日期: 2026-01-17 23:40 UTC+8
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-17 23:40 UTC+8

import { User } from '../contexts/authContext';

/**
 * 檢查用戶是否為系統管理員
 *
 * 檢查順序：
 * 1. 優先檢查 currentUser?.roles?.includes('system_admin')
 * 2. 如果 roles 為空，檢查 currentUser?.user_id === 'systemAdmin'
 * 3. 如果 currentUser 為空，檢查 localStorage 中的 user_id
 *
 * @param currentUser 當前用戶對象（可選）
 * @returns 是否為系統管理員
 */
export function isSystemAdmin(currentUser?: User | null): boolean {
  // 優先檢查 roles
  if (currentUser?.roles?.includes('system_admin')) {
    return true;
  }

  // 如果 roles 為空，檢查 user_id
  if (currentUser?.user_id === 'systemAdmin') {
    return true;
  }

  // 如果 currentUser 為空，從 localStorage 檢查
  const userId = localStorage.getItem('user_id');
  if (userId === 'systemAdmin') {
    return true;
  }

  // 也檢查 localStorage 中的 currentUser
  try {
    const storedUserJson = localStorage.getItem('currentUser');
    if (storedUserJson) {
      const storedUser = JSON.parse(storedUserJson) as User;
      if (storedUser?.roles?.includes('system_admin') || storedUser?.user_id === 'systemAdmin') {
        return true;
      }
    }
  } catch (error) {
    // 忽略解析錯誤
  }

  return false;
}

/**
 * 獲取當前用戶 ID（統一接口）
 *
 * 優先順序：
 * 1. currentUser?.user_id
 * 2. localStorage.getItem('user_id')
 * 3. localStorage 中的 currentUser.user_id
 * 4. 從 JWT token 解析（使用 jwtUtils.getCurrentUserId）
 *
 * @param currentUser 當前用戶對象（可選）
 * @returns 用戶 ID 或 null
 */
export function getCurrentUserId(currentUser?: User | null): string | null {
  // 優先使用 currentUser
  if (currentUser?.user_id) {
    return currentUser.user_id;
  }

  // 從 localStorage 讀取 user_id
  const userId = localStorage.getItem('user_id');
  if (userId) {
    return userId;
  }

  // 從 currentUser localStorage 讀取
  try {
    const storedUserJson = localStorage.getItem('currentUser');
    if (storedUserJson) {
      const storedUser = JSON.parse(storedUserJson) as User;
      if (storedUser?.user_id) {
        return storedUser.user_id;
      }
    }
  } catch (error) {
    // 忽略解析錯誤
  }

  // 最後嘗試從 token 解析（使用 jwtUtils 的函數）
  try {
    const jwtUtils = require('./jwtUtils');
    return jwtUtils.getCurrentUserId();
  } catch (error) {
    return null;
  }
}

/**
 * 獲取當前用戶對象
 *
 * 優先順序：
 * 1. 傳入的 currentUser 參數
 * 2. localStorage 中的 currentUser
 * 3. 從 JWT token 構建
 *
 * @param currentUser 當前用戶對象（可選）
 * @returns 用戶對象或 null
 */
export function getCurrentUser(currentUser?: User | null): User | null {
  // 優先使用傳入的 currentUser
  if (currentUser) {
    return currentUser;
  }

  // 從 localStorage 讀取
  try {
    const storedUserJson = localStorage.getItem('currentUser');
    if (storedUserJson) {
      return JSON.parse(storedUserJson) as User;
    }
  } catch (error) {
    // 忽略解析錯誤
  }

  // 從 token 構建（如果可能）
  try {
    const token = localStorage.getItem('access_token');
    if (token) {
      const { parseJwtToken } = require('./jwtUtils');
      const tokenPayload = parseJwtToken(token);
      if (tokenPayload) {
        const user_id = tokenPayload.user_id || tokenPayload.sub;
        if (user_id) {
          return {
            user_id: user_id,
            username: tokenPayload.username,
            email: tokenPayload.email,
            roles: tokenPayload.roles || [],
          };
        }
      }
    }
  } catch (error) {
    // 忽略解析錯誤
  }

  return null;
}
