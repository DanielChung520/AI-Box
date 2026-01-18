// 代碼功能說明: 用戶個人中心浮動菜單組件
// 創建日期: 2026-01-17 22:54 UTC+8
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-17 23:26 UTC+8

import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../contexts/authContext';
import { useContext } from 'react';
import UserProfileModal from './UserProfileModal';
import ChangePasswordModal from './ChangePasswordModal';

interface UserMenuProps {
  isOpen: boolean;
  onClose: () => void;
  position?: 'top' | 'bottom';
}

export default function UserMenu({ isOpen, onClose, position = 'bottom' }: UserMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);
  const firstMenuItemRef = useRef<HTMLButtonElement>(null);
  const navigate = useNavigate();
  const { logout } = useContext(AuthContext);
  const [showUserProfileModal, setShowUserProfileModal] = useState(false);
  const [showChangePasswordModal, setShowChangePasswordModal] = useState(false);

  // 處理點擊外部區域關閉菜單
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isOpen, onClose]);

  // 處理 ESC 鍵關閉菜單和鍵盤導航
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      // ESC 鍵關閉菜單
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }

      // Tab 鍵導航（在菜單項之間）
      if (e.key === 'Tab') {
        const menuItems = menuRef.current?.querySelectorAll('[role="menuitem"]');
        if (!menuItems || menuItems.length === 0) return;

        const currentIndex = Array.from(menuItems).findIndex(
          (item) => item === document.activeElement
        );

        // Shift+Tab：向上導航
        if (e.shiftKey) {
          e.preventDefault();
          if (currentIndex <= 0) {
            // 回到第一個菜單項
            (menuItems[menuItems.length - 1] as HTMLElement)?.focus();
          } else {
            (menuItems[currentIndex - 1] as HTMLElement)?.focus();
          }
        } else {
          // Tab：向下導航
          if (currentIndex >= menuItems.length - 1) {
            // 回到第一個菜單項（循環）
            e.preventDefault();
            (menuItems[0] as HTMLElement)?.focus();
          }
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  // 當菜單打開時，將焦點移到第一個菜單項
  useEffect(() => {
    if (isOpen && firstMenuItemRef.current) {
      // 使用 setTimeout 確保 DOM 已更新
      setTimeout(() => {
        firstMenuItemRef.current?.focus();
      }, 0);
    }
  }, [isOpen]);

  // 處理登出
  const handleLogout = () => {
    logout();
    navigate('/login');
    onClose();
  };

  // 處理我的賬戶
  const handleMyAccount = () => {
    setShowUserProfileModal(true);
    onClose();
  };

  // 處理變更密碼
  const handleChangePassword = () => {
    setShowChangePasswordModal(true);
    onClose();
  };

  if (!isOpen) return null;

  // 處理鍵盤選擇（Enter/Space）
  const handleMenuItemKeyDown = (
    e: React.KeyboardEvent,
    handler: () => void
  ) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handler();
    }
  };

  return (
    <div
      ref={menuRef}
      role="menu"
      aria-label="用戶菜單"
      className={`bg-secondary border border-primary rounded-lg shadow-lg py-1 min-w-[200px] max-w-[250px] w-full sm:w-auto theme-transition ${
        position === 'top' ? 'mb-2' : 'mt-2'
      } ${
        isOpen ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-2'
      } transition-all duration-200`}
      style={{
        animation: isOpen ? 'fadeInSlide 200ms ease-out' : 'none',
        zIndex: 1000,
      }}
    >
      {/* 我的賬戶 */}
      <button
        ref={firstMenuItemRef}
        role="menuitem"
        aria-label="我的賬戶"
        tabIndex={0}
        className="w-full text-left px-4 py-3 text-sm text-primary hover:bg-tertiary focus:bg-tertiary focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset theme-transition flex items-center gap-3 transition-colors duration-200"
        onClick={handleMyAccount}
        onKeyDown={(e) => handleMenuItemKeyDown(e, handleMyAccount)}
      >
        <i className="fa-solid fa-user w-4 text-center" aria-hidden="true"></i>
        <span>我的賬戶</span>
      </button>

      <div className="border-t border-primary my-1"></div>

      {/* 變更密碼 */}
      <button
        role="menuitem"
        aria-label="變更密碼"
        tabIndex={0}
        className="w-full text-left px-4 py-3 text-sm text-primary hover:bg-tertiary focus:bg-tertiary focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset theme-transition flex items-center gap-3 transition-colors duration-200"
        onClick={handleChangePassword}
        onKeyDown={(e) => handleMenuItemKeyDown(e, handleChangePassword)}
      >
        <i className="fa-solid fa-key w-4 text-center" aria-hidden="true"></i>
        <span>變更密碼</span>
      </button>

      <div className="border-t border-primary my-1" role="separator" aria-orientation="horizontal"></div>

      {/* 登出 */}
      <button
        role="menuitem"
        aria-label="登出"
        tabIndex={0}
        className="w-full text-left px-4 py-3 text-sm text-red-400 hover:bg-red-500/20 hover:text-red-300 focus:bg-red-500/20 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-inset theme-transition flex items-center gap-3 transition-colors duration-200"
        onClick={handleLogout}
        onKeyDown={(e) => handleMenuItemKeyDown(e, handleLogout)}
      >
        <i className="fa-solid fa-sign-out-alt w-4 text-center" aria-hidden="true"></i>
        <span>登出</span>
      </button>

      <style>{`
        @keyframes fadeInSlide {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>

      {/* 我的賬戶 Modal */}
      <UserProfileModal
        isOpen={showUserProfileModal}
        onClose={() => setShowUserProfileModal(false)}
      />

      {/* 變更密碼 Modal */}
      <ChangePasswordModal
        isOpen={showChangePasswordModal}
        onClose={() => setShowChangePasswordModal(false)}
      />
    </div>
  );
}
