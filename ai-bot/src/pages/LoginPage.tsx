/**
 * 代碼功能說明: 登錄頁面組件
 * 創建日期: 2025-01-27
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-01-27
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

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

    try {
      // 嘗試調用真實的登錄 API
      try {
        const { apiPost } = await import('../lib/api');
        const response = await apiPost('/auth/login', {
          username: email,
          password: password,
        });

        if (response.success && response.data) {
          // 保存認證 token
          const accessToken = response.data.access_token;
          if (accessToken) {
            localStorage.setItem('access_token', accessToken);
          }

          // 保存認證狀態
          localStorage.setItem('isAuthenticated', 'true');
          localStorage.setItem('userEmail', email);
          localStorage.setItem('userName', 'Daniel');
          localStorage.setItem('loginTime', new Date().toISOString());

          // 觸發自定義事件，通知 App 組件更新認證狀態
          window.dispatchEvent(new CustomEvent('authStateChanged', {
            detail: { isAuthenticated: true }
          }));

          // 短暫延遲後跳轉到主頁，確保狀態已更新
          await new Promise(resolve => setTimeout(resolve, 100));
          navigate('/home', { replace: true });
          return;
        }
      } catch (apiError: any) {
        // API 調用失敗，使用模擬登錄作為後備方案
        console.warn('API login failed, using mock login:', apiError);

        // 模擬登錄驗證（暫時使用硬編碼的憑證）
        if (email === 'daniel@test.com' && password === '1234') {
          // 驗證成功，保存登錄狀態（但不保存 token，因為 API 調用失敗）
          localStorage.setItem('isAuthenticated', 'true');
          localStorage.setItem('userEmail', email);
          localStorage.setItem('userName', 'Daniel');
          localStorage.setItem('loginTime', new Date().toISOString());

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
                帳號
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <i className="fa-solid fa-envelope text-blue-300"></i>
                </div>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent backdrop-blur-sm"
                  placeholder="daniel@test.com"
                  required
                  autoComplete="email"
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
                  required
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
              <p className="font-mono text-xs">daniel@test.com / 1234</p>
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
