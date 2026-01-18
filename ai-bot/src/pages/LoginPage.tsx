/**
 * 代碼功能說明: 登錄頁面組件
 * 創建日期: 2025-01-27
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-17 23:30 UTC+8
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
// 修改時間：2025-12-08 08:46:00 UTC+8 - 添加 JWT token 解析功能導入
import { getUserIdFromToken } from '../lib/jwtUtils';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    // 驗證輸入不為空（但不限制格式）
    if (!email.trim()) {
      setError('請輸入帳號（用戶名或郵箱）');
      setIsLoading(false);
      return;
    }

    if (!password.trim()) {
      setError('請輸入密碼');
      setIsLoading(false);
      return;
    }

    try {
      // 嘗試調用真實的登錄 API
      try {
        const { apiPost } = await import('../lib/api');
        const response = await apiPost('/auth/login', {
          username: email.trim(), // 使用 trim() 去除首尾空格
          password: password,
        });

        if (response.success && response.data) {
          // 修改時間：2025-12-09 - 修復 token 保存和後續請求的時序問題
          // 保存認證 token（必須先保存，確保後續請求能使用）
          const accessToken = response.data.access_token;
          const refreshToken = response.data.refresh_token;

          if (!accessToken) {
            console.error('[Login] No access_token in response:', response);
            setError('登錄失敗：服務器未返回認證令牌');
            setIsLoading(false);
            return;
          }

          // 立即保存 token 到 localStorage（同步操作，確保後續請求能讀取到）
          localStorage.setItem('access_token', accessToken);
          if (refreshToken) {
            localStorage.setItem('refresh_token', refreshToken);
          }
          console.log('[Login] Token saved to localStorage');

          // 從 token 中解析並保存 user_id
          const userId = getUserIdFromToken(accessToken);
          if (userId) {
            localStorage.setItem('user_id', userId);
            console.log('[Login] Saved user_id from token:', userId);
          } else {
            console.warn('[Login] Failed to parse user_id from token');
          }

          // 從 token 中解析用戶信息（包括 roles）
          const { parseJwtToken } = await import('../lib/jwtUtils');
          const tokenPayload = parseJwtToken(accessToken);

          // 構建 currentUser 對象
          const user_id = tokenPayload?.user_id || tokenPayload?.sub || userId;
          let roles = tokenPayload?.roles || [];

          // 如果 user_id 是 systemAdmin 但 roles 為空，自動添加 system_admin 角色
          if (user_id === 'systemAdmin' && (!roles || roles.length === 0)) {
            roles = ['system_admin'];
            console.log('[Login] Auto-added system_admin role for systemAdmin user');
          }

          const currentUser = {
            user_id: user_id,
            username: tokenPayload?.username || email,
            email: tokenPayload?.email || email,
            roles: roles,
          };

          // 保存完整的用戶信息到 localStorage
          localStorage.setItem('currentUser', JSON.stringify(currentUser));
          console.log('[Login] Saved currentUser to localStorage:', currentUser);

          // 保存認證狀態
          localStorage.setItem('isAuthenticated', 'true');
          localStorage.setItem('userEmail', currentUser.email || email);
          localStorage.setItem('userName', currentUser.username || 'Daniel');
          localStorage.setItem('loginTime', new Date().toISOString());

          // 修改時間：2025-12-09 - 確保 token 已保存後再觸發同步
          // 觸發文件樹同步事件（通知其他組件從後台加載數據）
          window.dispatchEvent(new CustomEvent('userLoggedIn', {
            detail: { userId: userId || email }
          }));

          // 觸發任務同步事件（延遲執行，確保 token 已完全保存）
          // 注意：如果同步失敗（401），可能是時序問題，稍後會自動重試
          setTimeout(async () => {
            try {
              // 再次確認 token 存在
              const savedToken = localStorage.getItem('access_token');
              if (!savedToken) {
                console.error('[Login] Token not found when syncing tasks. Login may have failed.');
                return;
              }

              console.log('[Login] Starting task sync with token length:', savedToken.length);
              const { syncTasksBidirectional } = await import('../lib/taskStorage');
              await syncTasksBidirectional();
              console.log('[Login] Tasks synced successfully');
            } catch (error: any) {
              // 如果是 401 錯誤且在登錄後短時間內，可能是時序問題
              if (error?.status === 401) {
                const loginTime = localStorage.getItem('loginTime');
                const isRecentLogin = loginTime && (Date.now() - new Date(loginTime).getTime()) < 5000;
                if (isRecentLogin) {
                  console.warn('[Login] Task sync failed with 401 shortly after login. This may be a timing issue. Will retry later.');
                  // 稍後重試（2 秒後）
                  setTimeout(async () => {
                    try {
                      const { syncTasksBidirectional } = await import('../lib/taskStorage');
                      await syncTasksBidirectional();
                      console.log('[Login] Tasks synced successfully on retry');
                    } catch (retryError) {
                      console.error('[Login] Task sync failed on retry:', retryError);
                    }
                  }, 2000);
                  return;
                }
              }
              console.error('[Login] Failed to sync tasks:', error);
            }
          }, 1500); // 增加延遲到 1.5 秒，確保 token 保存完成並給後端處理時間

          // 觸發自定義事件，通知 App 組件更新認證狀態
          window.dispatchEvent(new CustomEvent('authStateChanged', {
            detail: {
              isAuthenticated: true,
              currentUser: currentUser
            }
          }));

          // 短暫延遲後跳轉到主頁，確保狀態已更新
          await new Promise(resolve => setTimeout(resolve, 100));
          navigate('/home', { replace: true });
          return;
        }
      } catch (apiError: any) {
        // API 調用失敗，使用模擬登錄作為後備方案
        console.warn('API login failed, using mock login:', apiError);

        // 修改時間：2025-12-08 08:46:00 UTC+8 - 模擬登錄時也保存 user_id 並觸發登錄事件
        // 模擬登錄驗證（暫時使用硬編碼的憑證）
        if (email === 'daniel@test.com' && password === '1234') {
          // 驗證成功，保存登錄狀態（但不保存 token，因為 API 調用失敗）
          // 使用 email 作為臨時的 user_id（僅用於模擬登錄）
          localStorage.setItem('isAuthenticated', 'true');
          localStorage.setItem('userEmail', email);
          localStorage.setItem('user_id', email); // 模擬登錄時使用 email 作為 user_id
          localStorage.setItem('userName', 'Daniel');
          localStorage.setItem('loginTime', new Date().toISOString());

          // 修改時間：2025-12-08 09:04:21 UTC+8 - 模擬登錄時也觸發任務同步
          // 觸發文件樹同步事件
          window.dispatchEvent(new CustomEvent('userLoggedIn', {
            detail: { userId: email }
          }));

          // 觸發任務同步事件（異步執行）
          setTimeout(async () => {
            try {
              const { syncTasksBidirectional } = await import('../lib/taskStorage');
              await syncTasksBidirectional();
              console.log('[Login] Tasks synced successfully');
            } catch (error) {
              console.error('[Login] Failed to sync tasks:', error);
            }
          }, 500);

          // 觸發自定義事件，通知 App 組件更新認證狀態
          window.dispatchEvent(new CustomEvent('authStateChanged', {
            detail: { isAuthenticated: true }
          }));

          // 短暫延遲後跳轉到主頁，確保狀態已更新
          await new Promise(resolve => setTimeout(resolve, 100));
          navigate('/home', { replace: true });
          return;
        } else {
          // 驗證失敗
          setError('帳號或密碼錯誤');
          setIsLoading(false);
          return;
        }
      }
    } catch (error) {
      setError('登錄過程中發生錯誤，請稍後再試');
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 flex items-center justify-center relative overflow-hidden">
      {/* 動態背景 */}
      <div className="absolute inset-0 overflow-hidden">
        {[...Array(30)].map((_, i) => (
          <div
            key={i}
            className="absolute rounded-full bg-white/10 animate-float"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              width: `${Math.random() * 3 + 1}px`,
              height: `${Math.random() * 3 + 1}px`,
              animationDelay: `${Math.random() * 2}s`,
              animationDuration: `${Math.random() * 2 + 2}s`,
            }}
          />
        ))}
      </div>

      {/* 登錄表單 */}
      <div className="relative z-10 w-full max-w-md px-6">
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-8 border border-white/20">
          {/* Logo */}
          <div className="text-center mb-8">
            <div className="w-20 h-20 mx-auto flex items-center justify-center mb-4 p-1">
              <img
                src="/SmartQ.-logo.svg"
                alt="SmartQ Logo"
                className="object-contain"
              />
            </div>
            <p className="text-xl font-bold text-white mb-2">SmartQ IEE</p>
            <h1 className="text-3xl font-bold text-white mb-2">智慧任務文件編輯</h1>
            <p className="text-blue-200">請登錄您的帳號</p>
          </div>

          {/* 表單 */}
          <form onSubmit={handleLogin} className="space-y-6">
            {/* 錯誤訊息 */}
            {error && (
              <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg text-sm flex items-center">
                <i className="fa-solid fa-circle-exclamation mr-2"></i>
                {error}
              </div>
            )}

            {/* 帳號輸入 */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-blue-200 mb-2">
                帳號（用戶名或郵箱）
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <i className="fa-solid fa-user text-blue-300"></i>
                </div>
                <input
                  id="email"
                  type="text"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent backdrop-blur-sm"
                  placeholder="systemAdmin 或 daniel@test.com"
                  autoComplete="username"
                  pattern=".*"
                  title="請輸入用戶名或郵箱地址"
                />
              </div>
            </div>

            {/* 密碼輸入 */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-blue-200 mb-2">
                密碼
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <i className="fa-solid fa-lock text-blue-300"></i>
                </div>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent backdrop-blur-sm"
                  placeholder="請輸入密碼"
                  autoComplete="current-password"
                />
              </div>
            </div>

            {/* 登錄按鈕 */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {isLoading ? (
                <>
                  <i className="fa-solid fa-spinner fa-spin mr-2"></i>
                  登錄中...
                </>
              ) : (
                <>
                  登錄
                  <i className="fa-solid fa-arrow-right ml-2"></i>
                </>
              )}
            </button>

            {/* 提示訊息 */}
            <div className="text-center text-sm text-blue-300 pt-4 border-t border-white/10">
              <p className="mb-2">測試帳號：</p>
              <p className="font-mono text-xs mb-1">daniel@test.com / 1234</p>
              <p className="font-mono text-xs">systemAdmin / systemAdmin@2026</p>
            </div>
          </form>
        </div>

        {/* 返回按鈕 */}
        <button
          onClick={() => navigate('/')}
          className="mt-6 w-full text-center text-blue-200 hover:text-white transition-colors text-sm"
        >
          <i className="fa-solid fa-arrow-left mr-2"></i>
          返回歡迎頁面
        </button>
      </div>

      <style>{`
        @keyframes float {
          0%, 100% {
            transform: translateY(0px) translateX(0px);
            opacity: 0.5;
          }
          50% {
            transform: translateY(-15px) translateX(5px);
            opacity: 0.8;
          }
        }
        .animate-float {
          animation: float 4s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}
