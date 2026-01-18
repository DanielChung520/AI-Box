// 代碼功能說明: 用戶個人中心 - 我的賬戶 Modal 組件
// 創建日期: 2026-01-17 23:07 UTC+8
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-17 23:26 UTC+8

import { useState, useEffect, useContext, useRef } from 'react';
import { AuthContext } from '../contexts/authContext';
import { getCurrentUser, updateUserProfile, type UserProfile } from '../lib/api';

interface UserProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function UserProfileModal({ isOpen, onClose }: UserProfileModalProps) {
  const { currentUser, setCurrentUser } = useContext(AuthContext);
  const modalRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // 表單字段
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);

  // 表單驗證錯誤
  const [usernameError, setUsernameError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);

  // 加載用戶信息
  useEffect(() => {
    if (isOpen) {
      loadUserProfile();
    }
  }, [isOpen]);

  // 處理 ESC 鍵關閉 Modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isSubmitting && !isLoading) {
        handleCancel();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, isSubmitting, isLoading]);

  // 當 Modal 打開時，將焦點移到關閉按鈕
  useEffect(() => {
    if (isOpen && closeButtonRef.current) {
      setTimeout(() => {
        closeButtonRef.current?.focus();
      }, 0);
    }
  }, [isOpen]);

  // 當用戶信息加載完成後，填充表單
  useEffect(() => {
    if (userProfile) {
      setUsername(userProfile.username || '');
      setEmail(userProfile.email || '');
      setUsernameError(null);
      setEmailError(null);
      setError(null);
      setSuccessMessage(null);
    }
  }, [userProfile]);

  const loadUserProfile = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const profile = await getCurrentUser();
      setUserProfile(profile);
    } catch (err: any) {
      setError(err?.message || '獲取用戶信息失敗');
      console.error('Failed to load user profile:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // 驗證用戶名格式
  const validateUsername = (value: string): boolean => {
    if (!value.trim()) {
      setUsernameError('用戶名為必填項');
      return false;
    }
    if (value.length < 3 || value.length > 50) {
      setUsernameError('用戶名長度必須在 3-50 字符之間');
      return false;
    }
    // 檢查格式：字母、數字、下劃線、連字符
    if (!/^[a-zA-Z0-9_-]+$/.test(value)) {
      setUsernameError('用戶名只能包含字母、數字、下劃線和連字符');
      return false;
    }
    setUsernameError(null);
    return true;
  };

  // 驗證郵箱格式
  const validateEmail = (value: string): boolean => {
    if (!value.trim()) {
      setEmailError('郵箱地址為必填項');
      return false;
    }
    // 基本的郵箱格式驗證
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) {
      setEmailError('請輸入有效的郵箱地址');
      return false;
    }
    setEmailError(null);
    return true;
  };

  // 處理用戶名輸入
  const handleUsernameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setUsername(value);
    // 實時驗證格式
    if (value && value !== userProfile?.username) {
      validateUsername(value);
    } else {
      setUsernameError(null);
    }
  };

  // 處理郵箱輸入
  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setEmail(value);
    // 實時驗證格式
    if (value && value !== userProfile?.email) {
      validateEmail(value);
    } else {
      setEmailError(null);
    }
  };

  // 處理用戶名失焦（可選：檢查唯一性）
  const handleUsernameBlur = () => {
    if (username && username !== userProfile?.username) {
      validateUsername(username);
    }
  };

  // 處理郵箱失焦（可選：檢查唯一性）
  const handleEmailBlur = () => {
    if (email && email !== userProfile?.email) {
      validateEmail(email);
    }
  };

  // 驗證表單
  const validateForm = (): boolean => {
    const isUsernameValid = validateUsername(username);
    const isEmailValid = validateEmail(email);
    return isUsernameValid && isEmailValid;
  };

  // 處理保存
  const handleSave = async () => {
    setError(null);
    setSuccessMessage(null);

    // 驗證表單
    if (!validateForm()) {
      return;
    }

    // 檢查是否有變更
    const hasChanges = username !== userProfile?.username || email !== userProfile?.email;
    if (!hasChanges) {
      setSuccessMessage('沒有需要保存的變更');
      setTimeout(() => {
        onClose();
      }, 1000);
      return;
    }

    setIsSubmitting(true);

    try {
      // 構建更新數據（只包含變更的字段）
      const updateData: { username?: string; email?: string } = {};
      if (username !== userProfile?.username) {
        updateData.username = username;
      }
      if (email !== userProfile?.email) {
        updateData.email = email;
      }

      // 調用 API 更新用戶信息
      const updatedProfile = await updateUserProfile(updateData);

      // 更新 AuthContext
      if (setCurrentUser) {
        setCurrentUser({
          user_id: updatedProfile.user_id,
          username: updatedProfile.username,
          email: updatedProfile.email,
          roles: updatedProfile.roles,
        });
      }

      // 更新 localStorage
      localStorage.setItem('userName', updatedProfile.username);
      localStorage.setItem('userEmail', updatedProfile.email);
      localStorage.setItem('currentUser', JSON.stringify({
        user_id: updatedProfile.user_id,
        username: updatedProfile.username,
        email: updatedProfile.email,
        roles: updatedProfile.roles,
      }));

      // 觸發認證狀態更新事件
      window.dispatchEvent(new CustomEvent('authStateChanged'));

      setSuccessMessage('用戶信息更新成功');
      setUserProfile(updatedProfile);

      // 1.5 秒後關閉 Modal
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err: any) {
      // 處理錯誤
      const errorMessage = err?.message || '更新用戶信息失敗';

      // 檢查是否為唯一性錯誤
      if (errorMessage.includes('already exists') || errorMessage.includes('已存在')) {
        if (errorMessage.includes('username') || errorMessage.includes('用戶名')) {
          setUsernameError('該用戶名已被使用');
        } else if (errorMessage.includes('email') || errorMessage.includes('郵箱')) {
          setEmailError('該郵箱地址已被使用');
        }
        setError('用戶名或郵箱地址已被其他用戶使用');
      } else {
        setError(errorMessage);
      }
      console.error('Failed to update user profile:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // 處理取消
  const handleCancel = () => {
    if (!isSubmitting && !isLoading) {
      // 恢復原始值
      if (userProfile) {
        setUsername(userProfile.username || '');
        setEmail(userProfile.email || '');
      }
      setUsernameError(null);
      setEmailError(null);
      setError(null);
      setSuccessMessage(null);
      onClose();
    }
  };

  // 格式化日期時間
  const formatDateTime = (dateString?: string): string => {
    if (!dateString) return '-';
    try {
      const date = new Date(dateString);
      return date.toLocaleString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return dateString;
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition p-4"
      onClick={(e) => {
        // 點擊背景關閉 Modal
        if (e.target === e.currentTarget && !isSubmitting && !isLoading) {
          handleCancel();
        }
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="user-profile-modal-title"
    >
      <div
        ref={modalRef}
        className="bg-secondary border border-primary rounded-lg shadow-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto theme-transition custom-scrollbar"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal 標題 */}
        <div className="p-6 border-b border-primary flex items-center justify-between sticky top-0 bg-secondary z-10">
          <h2 id="user-profile-modal-title" className="text-xl font-semibold text-primary theme-transition">
            我的賬戶
          </h2>
          <button
            ref={closeButtonRef}
            onClick={handleCancel}
            className="p-2 rounded-full hover:bg-tertiary focus:bg-tertiary focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
            aria-label="關閉"
            disabled={isSubmitting || isLoading}
          >
            <i className="fa-solid fa-times text-primary" aria-hidden="true"></i>
          </button>
        </div>

        {/* Modal 內容 */}
        <div className="p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <i className="fa-solid fa-spinner fa-spin text-2xl text-primary"></i>
              <span className="ml-3 text-primary">加載中...</span>
            </div>
          ) : userProfile ? (
            <div className="space-y-6">
              {/* 錯誤/成功提示 */}
              {error && (
                <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 text-red-400 text-sm" role="alert" aria-live="polite">
                  <i className="fa-solid fa-exclamation-circle mr-2" aria-hidden="true"></i>
                  {error}
                </div>
              )}
              {successMessage && (
                <div className="bg-green-500/10 border border-green-500/50 rounded-lg p-4 text-green-400 text-sm" role="alert" aria-live="polite">
                  <i className="fa-solid fa-check-circle mr-2" aria-hidden="true"></i>
                  {successMessage}
                </div>
              )}

              {/* 基本信息區塊 */}
              <div>
                <h3 className="text-lg font-medium text-primary mb-4 theme-transition">基本信息</h3>
                <div className="space-y-4">
                  {/* 用戶名 */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2 theme-transition">
                      用戶名 <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="text"
                      value={username}
                      onChange={handleUsernameChange}
                      onBlur={handleUsernameBlur}
                      disabled={isSubmitting || isLoading}
                      className={`w-full px-4 py-2 bg-tertiary border rounded-lg text-primary placeholder-tertiary focus:outline-none focus:ring-2 theme-transition ${
                        usernameError ? 'border-red-500 focus:ring-red-500/50' : 'border-primary focus:ring-blue-500/50'
                      } disabled:opacity-50 disabled:cursor-not-allowed`}
                      placeholder="請輸入用戶名"
                    />
                    {usernameError && (
                      <p className="mt-1 text-sm text-red-400">{usernameError}</p>
                    )}
                  </div>

                  {/* 郵箱 */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2 theme-transition">
                      郵箱地址 <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="email"
                      value={email}
                      onChange={handleEmailChange}
                      onBlur={handleEmailBlur}
                      disabled={isSubmitting || isLoading}
                      className={`w-full px-4 py-2 bg-tertiary border rounded-lg text-primary placeholder-tertiary focus:outline-none focus:ring-2 theme-transition ${
                        emailError ? 'border-red-500 focus:ring-red-500/50' : 'border-primary focus:ring-blue-500/50'
                      } disabled:opacity-50 disabled:cursor-not-allowed`}
                      placeholder="請輸入郵箱地址"
                    />
                    {emailError && (
                      <p className="mt-1 text-sm text-red-400">{emailError}</p>
                    )}
                  </div>

                  {/* 用戶 ID（只讀） */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2 theme-transition">
                      用戶 ID
                    </label>
                    <input
                      type="text"
                      value={userProfile.user_id || '-'}
                      disabled
                      className="w-full px-4 py-2 bg-tertiary/50 border border-primary rounded-lg text-tertiary cursor-not-allowed theme-transition"
                    />
                    <p className="mt-1 text-xs text-tertiary">系統自動生成，不可修改</p>
                  </div>
                </div>
              </div>

              {/* 角色與權限區塊（只讀） */}
              <div>
                <h3 className="text-lg font-medium text-primary mb-4 theme-transition">角色與權限</h3>
                <div className="space-y-4">
                  {/* 角色列表 */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2 theme-transition">
                      角色
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {userProfile.roles && userProfile.roles.length > 0 ? (
                        userProfile.roles.map((role) => (
                          <span
                            key={role}
                            className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg text-sm border border-blue-500/50"
                          >
                            {role}
                          </span>
                        ))
                      ) : (
                        <span className="text-tertiary text-sm">無</span>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-tertiary">由系統管理員分配，用戶無法修改</p>
                  </div>

                  {/* 權限列表（可選） */}
                  {userProfile.permissions && userProfile.permissions.length > 0 && (
                    <div>
                      <label className="block text-sm font-medium text-primary mb-2 theme-transition">
                        權限
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {userProfile.permissions.map((permission) => (
                          <span
                            key={permission}
                            className="px-3 py-1 bg-purple-500/20 text-purple-400 rounded-lg text-sm border border-purple-500/50"
                          >
                            {permission}
                          </span>
                        ))}
                      </div>
                      <p className="mt-1 text-xs text-tertiary">由角色決定，用戶無法修改</p>
                    </div>
                  )}
                </div>
              </div>

              {/* 賬戶狀態區塊（只讀） */}
              <div>
                <h3 className="text-lg font-medium text-primary mb-4 theme-transition">賬戶狀態</h3>
                <div className="space-y-4">
                  {/* 賬戶狀態 */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2 theme-transition">
                      狀態
                    </label>
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-3 h-3 rounded-full ${
                          userProfile.is_active ? 'bg-green-500' : 'bg-red-500'
                        }`}
                      ></div>
                      <span className="text-primary">
                        {userProfile.is_active ? '啟用' : '禁用'}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-tertiary">由系統管理員控制</p>
                  </div>

                  {/* 創建時間 */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2 theme-transition">
                      創建時間
                    </label>
                    <input
                      type="text"
                      value={formatDateTime(userProfile.created_at)}
                      disabled
                      className="w-full px-4 py-2 bg-tertiary/50 border border-primary rounded-lg text-tertiary cursor-not-allowed theme-transition"
                    />
                  </div>

                  {/* 最後登錄時間 */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2 theme-transition">
                      最後登錄
                    </label>
                    <input
                      type="text"
                      value={formatDateTime(userProfile.last_login_at)}
                      disabled
                      className="w-full px-4 py-2 bg-tertiary/50 border border-primary rounded-lg text-tertiary cursor-not-allowed theme-transition"
                    />
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-tertiary">
              <i className="fa-solid fa-exclamation-circle text-2xl mb-2"></i>
              <p>無法加載用戶信息</p>
            </div>
          )}
        </div>

        {/* Modal 底部按鈕 */}
        <div className="p-6 border-t border-primary flex justify-end gap-3 sticky bottom-0 bg-secondary">
          <button
            onClick={handleCancel}
            disabled={isSubmitting || isLoading}
            className="px-4 py-2 bg-tertiary hover:bg-hover text-primary rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={isSubmitting || isLoading || !!usernameError || !!emailError}
            className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isSubmitting && (
              <i className="fa-solid fa-spinner fa-spin"></i>
            )}
            {isSubmitting ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
