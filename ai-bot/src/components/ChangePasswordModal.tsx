// 代碼功能說明: 用戶個人中心 - 變更密碼 Modal 組件
// 創建日期: 2026-01-17 23:15 UTC+8
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-17 23:26 UTC+8

import { useState, useEffect, useRef } from 'react';
import { changePassword, type ChangePasswordRequest } from '../lib/api';

interface ChangePasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ChangePasswordModal({ isOpen, onClose }: ChangePasswordModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const firstInputRef = useRef<HTMLInputElement>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // 表單字段
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // 密碼顯示/隱藏狀態
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // 表單驗證錯誤
  const [currentPasswordError, setCurrentPasswordError] = useState<string | null>(null);
  const [newPasswordError, setNewPasswordError] = useState<string | null>(null);
  const [confirmPasswordError, setConfirmPasswordError] = useState<string | null>(null);

  // 密碼強度（可選功能）
  const [passwordStrength, setPasswordStrength] = useState<'weak' | 'medium' | 'strong' | null>(null);

  // 重置表單
  const resetForm = () => {
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setCurrentPasswordError(null);
    setNewPasswordError(null);
    setConfirmPasswordError(null);
    setError(null);
    setSuccessMessage(null);
    setPasswordStrength(null);
  };

  // 當 Modal 關閉時重置表單
  const handleClose = () => {
    if (!isSubmitting) {
      resetForm();
      onClose();
    }
  };

  // 處理 ESC 鍵關閉 Modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isSubmitting) {
        handleClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, isSubmitting]);

  // 當 Modal 打開時，將焦點移到第一個輸入框
  useEffect(() => {
    if (isOpen && firstInputRef.current) {
      setTimeout(() => {
        firstInputRef.current?.focus();
      }, 0);
    }
  }, [isOpen]);

  // 驗證當前密碼
  const validateCurrentPassword = (value: string): boolean => {
    if (!value.trim()) {
      setCurrentPasswordError('當前密碼為必填項');
      return false;
    }
    setCurrentPasswordError(null);
    return true;
  };

  // 驗證新密碼
  const validateNewPassword = (value: string): boolean => {
    if (!value.trim()) {
      setNewPasswordError('新密碼為必填項');
      return false;
    }
    if (value.length < 8) {
      setNewPasswordError('新密碼長度必須至少 8 個字符');
      return false;
    }
    // 檢查是否與當前密碼相同
    if (value === currentPassword) {
      setNewPasswordError('新密碼不能與當前密碼相同');
      return false;
    }
    setNewPasswordError(null);

    // 計算密碼強度（可選）
    const strength = calculatePasswordStrength(value);
    setPasswordStrength(strength);

    return true;
  };

  // 驗證確認密碼
  const validateConfirmPassword = (value: string): boolean => {
    if (!value.trim()) {
      setConfirmPasswordError('確認密碼為必填項');
      return false;
    }
    if (value !== newPassword) {
      setConfirmPasswordError('確認密碼與新密碼不一致');
      return false;
    }
    setConfirmPasswordError(null);
    return true;
  };

  // 計算密碼強度（可選功能）
  const calculatePasswordStrength = (password: string): 'weak' | 'medium' | 'strong' => {
    let strength = 0;
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^a-zA-Z0-9]/.test(password)) strength++;

    if (strength <= 2) return 'weak';
    if (strength <= 4) return 'medium';
    return 'strong';
  };

  // 處理當前密碼輸入
  const handleCurrentPasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setCurrentPassword(value);
    if (currentPasswordError) {
      validateCurrentPassword(value);
    }
  };

  // 處理新密碼輸入
  const handleNewPasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setNewPassword(value);
    if (newPasswordError) {
      validateNewPassword(value);
    }
    // 如果確認密碼已輸入，重新驗證確認密碼
    if (confirmPassword) {
      validateConfirmPassword(confirmPassword);
    }
  };

  // 處理確認密碼輸入
  const handleConfirmPasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setConfirmPassword(value);
    if (confirmPasswordError) {
      validateConfirmPassword(value);
    }
  };

  // 處理表單提交
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);

    // 驗證所有字段
    const isCurrentPasswordValid = validateCurrentPassword(currentPassword);
    const isNewPasswordValid = validateNewPassword(newPassword);
    const isConfirmPasswordValid = validateConfirmPassword(confirmPassword);

    if (!isCurrentPasswordValid || !isNewPasswordValid || !isConfirmPasswordValid) {
      return;
    }

    setIsSubmitting(true);

    try {
      const requestData: ChangePasswordRequest = {
        current_password: currentPassword,
        new_password: newPassword,
      };

      await changePassword(requestData);

      setSuccessMessage('密碼修改成功！');

      // 3 秒後關閉 Modal
      setTimeout(() => {
        handleClose();
      }, 2000);
    } catch (err: any) {
      const errorMessage = err?.message || '密碼修改失敗';
      setError(errorMessage);

      // 根據錯誤類型設置具體的錯誤提示
      if (errorMessage.includes('當前密碼') || errorMessage.includes('INVALID_PASSWORD')) {
        setCurrentPasswordError('當前密碼錯誤');
      } else if (errorMessage.includes('長度') || errorMessage.includes('PASSWORD_TOO_SHORT')) {
        setNewPasswordError('新密碼長度必須至少 8 個字符');
      } else if (errorMessage.includes('相同') || errorMessage.includes('PASSWORD_SAME_AS_CURRENT')) {
        setNewPasswordError('新密碼不能與當前密碼相同');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition p-4"
      onClick={(e) => {
        // 點擊背景關閉 Modal
        if (e.target === e.currentTarget && !isSubmitting) {
          handleClose();
        }
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="change-password-modal-title"
    >
      <div
        ref={modalRef}
        className="bg-secondary border border-primary rounded-lg shadow-xl w-full max-w-md theme-transition"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-primary flex items-center justify-between">
          <h2 id="change-password-modal-title" className="text-xl font-semibold text-primary">
            變更密碼
          </h2>
          <button
            onClick={handleClose}
            className="p-2 rounded-full hover:bg-tertiary focus:bg-tertiary focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
            aria-label="關閉"
            disabled={isSubmitting}
          >
            <i className="fa-solid fa-times text-primary" aria-hidden="true"></i>
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSubmit} className="px-6 py-4">
          {/* 錯誤提示 */}
          {error && (
            <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded text-red-400 text-sm" role="alert" aria-live="polite">
              <i className="fa-solid fa-exclamation-circle mr-2" aria-hidden="true"></i>
              {error}
            </div>
          )}

          {/* 成功提示 */}
          {successMessage && (
            <div className="mb-4 p-3 bg-green-500/20 border border-green-500/50 rounded text-green-400 text-sm" role="alert" aria-live="polite">
              <i className="fa-solid fa-check-circle mr-2" aria-hidden="true"></i>
              {successMessage}
            </div>
          )}

          {/* 當前密碼 */}
          <div className="mb-4">
            <label htmlFor="currentPassword" className="block text-sm font-medium text-primary mb-2">
              當前密碼
            </label>
            <div className="relative">
              <input
                ref={firstInputRef}
                type={showCurrentPassword ? 'text' : 'password'}
                id="currentPassword"
                value={currentPassword}
                onChange={handleCurrentPasswordChange}
                onBlur={() => validateCurrentPassword(currentPassword)}
                className={`w-full px-3 py-2 bg-tertiary border ${
                  currentPasswordError ? 'border-red-500' : 'border-primary'
                } rounded text-primary placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 theme-transition`}
                placeholder="請輸入當前密碼"
                disabled={isSubmitting}
                aria-invalid={!!currentPasswordError}
                aria-describedby={currentPasswordError ? 'current-password-error' : undefined}
              />
              <button
                type="button"
                onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-primary transition-colors"
                tabIndex={-1}
              >
                <i className={`fa-solid ${showCurrentPassword ? 'fa-eye-slash' : 'fa-eye'}`}></i>
              </button>
            </div>
            {currentPasswordError && (
              <p id="current-password-error" className="mt-1 text-sm text-red-400" role="alert">
                {currentPasswordError}
              </p>
            )}
          </div>

          {/* 新密碼 */}
          <div className="mb-4">
            <label htmlFor="newPassword" className="block text-sm font-medium text-primary mb-2">
              新密碼
            </label>
            <div className="relative">
              <input
                type={showNewPassword ? 'text' : 'password'}
                id="newPassword"
                value={newPassword}
                onChange={handleNewPasswordChange}
                onBlur={() => validateNewPassword(newPassword)}
                className={`w-full px-3 py-2 bg-tertiary border ${
                  newPasswordError ? 'border-red-500' : 'border-primary'
                } rounded text-primary placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 theme-transition`}
                placeholder="請輸入新密碼（至少 8 個字符）"
                disabled={isSubmitting}
                aria-invalid={!!newPasswordError}
                aria-describedby={newPasswordError ? 'new-password-error' : undefined}
              />
              <button
                type="button"
                onClick={() => setShowNewPassword(!showNewPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-primary transition-colors"
                tabIndex={-1}
              >
                <i className={`fa-solid ${showNewPassword ? 'fa-eye-slash' : 'fa-eye'}`}></i>
              </button>
            </div>
            {newPasswordError && (
              <p id="new-password-error" className="mt-1 text-sm text-red-400" role="alert">
                {newPasswordError}
              </p>
            )}
            {/* 密碼強度指示器（可選） */}
            {newPassword && passwordStrength && (
              <div className="mt-2">
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-tertiary rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${
                        passwordStrength === 'weak'
                          ? 'bg-red-500 w-1/3'
                          : passwordStrength === 'medium'
                          ? 'bg-yellow-500 w-2/3'
                          : 'bg-green-500 w-full'
                      }`}
                    ></div>
                  </div>
                  <span
                    className={`text-xs ${
                      passwordStrength === 'weak'
                        ? 'text-red-400'
                        : passwordStrength === 'medium'
                        ? 'text-yellow-400'
                        : 'text-green-400'
                    }`}
                  >
                    {passwordStrength === 'weak' ? '弱' : passwordStrength === 'medium' ? '中' : '強'}
                  </span>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  建議包含大小寫字母、數字和特殊字符
                </p>
              </div>
            )}
          </div>

          {/* 確認新密碼 */}
          <div className="mb-6">
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-primary mb-2">
              確認新密碼
            </label>
            <div className="relative">
              <input
                type={showConfirmPassword ? 'text' : 'password'}
                id="confirmPassword"
                value={confirmPassword}
                onChange={handleConfirmPasswordChange}
                onBlur={() => validateConfirmPassword(confirmPassword)}
                className={`w-full px-3 py-2 bg-tertiary border ${
                  confirmPasswordError ? 'border-red-500' : 'border-primary'
                } rounded text-primary placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 theme-transition`}
                placeholder="請再次輸入新密碼"
                disabled={isSubmitting}
                aria-invalid={!!confirmPasswordError}
                aria-describedby={confirmPasswordError ? 'confirm-password-error' : undefined}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-primary transition-colors"
                tabIndex={-1}
              >
                <i className={`fa-solid ${showConfirmPassword ? 'fa-eye-slash' : 'fa-eye'}`}></i>
              </button>
            </div>
            {confirmPasswordError && (
              <p id="confirm-password-error" className="mt-1 text-sm text-red-400" role="alert">
                {confirmPasswordError}
              </p>
            )}
          </div>

          {/* Modal Footer */}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-sm font-medium text-primary bg-tertiary border border-primary rounded hover:bg-primary/10 transition-colors theme-transition"
              disabled={isSubmitting}
            >
              取消
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isSubmitting}
            >
              {isSubmitting ? '提交中...' : '確認變更'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
