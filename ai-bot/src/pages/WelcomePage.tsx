/**
 * 代碼功能說明: 歡迎頁面組件，帶動態影像效果
 * 創建日期: 2025-12-05
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-07 17:00
 */

import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { performanceMonitor } from '@/lib/performance';

export default function WelcomePage() {
  const [showContent, setShowContent] = useState(false);
  const [logoAnimationComplete, setLogoAnimationComplete] = useState(false);
  const navigate = useNavigate();
  const pageStartTime = useRef<number>(performance.now());
  const logoImageRef = useRef<HTMLImageElement>(null);
  const animationStartedRef = useRef<boolean>(false);

  useEffect(() => {
    // 記錄歡迎頁組件掛載時間
    performanceMonitor.markWelcomePageMount();

    // 檢查是否有帳號（已登錄）
    const isAuthenticated = localStorage.getItem('isAuthenticated') === 'true';
    const userEmail = localStorage.getItem('userEmail');
    const hasAccount = isAuthenticated && userEmail;

    // 延遲顯示內容，創造淡入效果
    const timer = setTimeout(() => {
      setShowContent(true);
      // 記錄歡迎頁內容顯示時間
      performanceMonitor.markWelcomePageContentShow();
    }, 300);

    // 記錄 Logo 動畫完成時間（動畫持續 1.5 秒，亮光動畫在 1.5 秒後開始，持續 2 秒）
    // 注意：實際的動畫完成處理由 animationend 事件處理，這裡只記錄性能指標
    const logoAnimationTimer = setTimeout(() => {
      performanceMonitor.markLogoAnimationComplete();
      // 輸出性能報告（在亮光動畫完成後）
      setTimeout(() => {
        performanceMonitor.printReport();
      }, 2000); // 亮光動畫持續 2 秒
    }, 1800); // 300ms 延遲 + 1500ms Logo 縮放動畫

    // 根據是否有帳號設置不同的跳轉時間
    // 如果有帳號：至少停留 3 秒後跳轉
    // 如果沒有帳號：10 秒後跳轉或點擊按鈕跳轉
    const minStayTime = hasAccount ? 3000 : 10000;
    const redirectTimer = setTimeout(() => {
      checkAuthAndRedirect();
    }, minStayTime);

    return () => {
      clearTimeout(timer);
      clearTimeout(logoAnimationTimer);
      clearTimeout(redirectTimer);
    };
  }, []);

  // 當動畫完成狀態改變時，確保 DOM 元素保持最終狀態
  useEffect(() => {
    if (logoAnimationComplete && logoImageRef.current) {
      // 強制設置最終狀態，防止任何重新渲染導致動畫重新觸發
      const img = logoImageRef.current;
      // 使用 requestAnimationFrame 確保在下一幀設置，避免與動畫衝突
      requestAnimationFrame(() => {
        if (img) {
          img.style.animation = 'none';
          img.style.transform = 'scale(1)';
          img.style.opacity = '1';
          // 移除 will-change 以優化性能
          img.style.willChange = 'auto';
        }
      });
    }
  }, [logoAnimationComplete]);

  // 監聽 logo 圖片元素，確保動畫完成後立即設置最終狀態
  useEffect(() => {
    if (!logoImageRef.current || animationStartedRef.current) return;
    
    animationStartedRef.current = true;
    
    // 監聽動畫結束事件
    const handleAnimationEnd = () => {
      if (logoImageRef.current) {
        const img = logoImageRef.current;
        img.style.animation = 'none';
        img.style.transform = 'scale(1)';
        img.style.opacity = '1';
        img.style.willChange = 'auto';
        setLogoAnimationComplete(true);
      }
    };

    const img = logoImageRef.current;
    img.addEventListener('animationend', handleAnimationEnd);
    
    return () => {
      if (img) {
        img.removeEventListener('animationend', handleAnimationEnd);
      }
    };
  }, []);

  const checkAuthAndRedirect = () => {
    const isAuthenticated = localStorage.getItem('isAuthenticated') === 'true';
    const userEmail = localStorage.getItem('userEmail');

    if (isAuthenticated && userEmail) {
      navigate('/home');
    } else {
      navigate('/login');
    }
  };

  const handleGetStarted = () => {
    // 檢查是否有帳號
    const isAuthenticated = localStorage.getItem('isAuthenticated') === 'true';
    const userEmail = localStorage.getItem('userEmail');
    const hasAccount = isAuthenticated && userEmail;

    // 如果有帳號，確保至少停留 3 秒
    if (hasAccount) {
      const elapsedTime = performance.now() - pageStartTime.current;
      const minStayTime = 3000;

      if (elapsedTime < minStayTime) {
        // 如果還沒到 3 秒，等待剩餘時間
        setTimeout(() => {
          checkAuthAndRedirect();
        }, minStayTime - elapsedTime);
        return;
      }
    }

    // 如果已經超過 3 秒或沒有帳號，立即跳轉
    checkAuthAndRedirect();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 flex items-center justify-center relative overflow-hidden">
      {/* 動態背景粒子效果 */}
      <div className="absolute inset-0 overflow-hidden">
        {[...Array(50)].map((_, i) => (
          <div
            key={i}
            className="absolute rounded-full bg-white/20 animate-float"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              width: `${Math.random() * 4 + 2}px`,
              height: `${Math.random() * 4 + 2}px`,
              animationDelay: `${Math.random() * 3}s`,
              animationDuration: `${Math.random() * 3 + 2}s`,
            }}
          />
        ))}
      </div>

      {/* 主要內容 */}
      <div className={`relative z-10 text-center px-2 transition-opacity duration-1000 ${showContent ? 'opacity-100' : 'opacity-0'}`}>
        {/* Logo 動畫 */}
        <div className="mb-1">
          <div className="logo-container w-56 h-56 mx-auto flex items-center justify-center p-1 relative">
            <img
              ref={logoImageRef}
              src="/SmartQ.-logo.svg"
              alt="SmartQ Logo"
              className="logo-image object-contain"
            />
            {/* 橫向亮光掃過效果 */}
            <div className="light-beam-container">
              <div className="light-beam"></div>
            </div>
          </div>
        </div>

        {/* 標題 */}

        <h1 className="text-6xl md:text-7xl font-bold text-white mb-4 animate-fade-in-up">
          智慧任務文件編輯
        </h1>
        <p className="text-xl md:text-2xl text-blue-200 mb-2 animate-fade-in-up-delay">
          Smart Task File Editor
        </p>

        {/* 副標題 */}
        <p className="text-lg text-blue-100 mt-8 mb-12 max-w-2xl mx-auto animate-fade-in-up-delay-2">
          智能化的任務管理和文件編輯平台
          <br />
          讓 AI 助手協助您完成工作
        </p>

        {/* 動態圖標展示 */}
        <div className="flex justify-center gap-4 mb-6 animate-fade-in-up-delay-3">
          <div className="text-center">
            <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mb-2 backdrop-blur-sm">
              <i className="fa-solid fa-file-lines text-2xl text-white"></i>
            </div>
            <p className="text-sm text-blue-200">文件管理</p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mb-2 backdrop-blur-sm">
              <i className="fa-solid fa-robot text-2xl text-white"></i>
            </div>
            <p className="text-sm text-blue-200">AI 助手</p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mb-2 backdrop-blur-sm">
              <i className="fa-solid fa-tasks text-2xl text-white"></i>
            </div>
            <p className="text-sm text-blue-200">任務管理</p>
          </div>
        </div>

        {/* 開始按鈕 */}
        <button
          onClick={handleGetStarted}
          className="px-8 py-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white text-lg font-semibold rounded-full shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-300 animate-pulse-slow"
        >
          開始使用
          <i className="fa-solid fa-arrow-right ml-2"></i>
        </button>

        {/* 加載動畫 */}
        <div className="mt-12 flex justify-center">
          <div className="flex gap-2">
            <div className="w-2 h-2 bg-white rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
            <div className="w-2 h-2 bg-white rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            <div className="w-2 h-2 bg-white rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes float {
          0%, 100% {
            transform: translateY(0px) translateX(0px);
            opacity: 0.7;
          }
          50% {
            transform: translateY(-20px) translateX(10px);
            opacity: 1;
          }
        }
        .animate-float {
          animation: float 6s ease-in-out infinite;
        }
        @keyframes bounce-slow {
          0%, 100% {
            transform: translateY(0);
          }
          50% {
            transform: translateY(-10px);
          }
        }
        .animate-bounce-slow {
          animation: bounce-slow 3s ease-in-out infinite;
        }
        @keyframes fade-in-up {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fade-in-up {
          animation: fade-in-up 1s ease-out;
        }
        .animate-fade-in-up-delay {
          animation: fade-in-up 1s ease-out 0.3s both;
        }
        .animate-fade-in-up-delay-2 {
          animation: fade-in-up 1s ease-out 0.6s both;
        }
        .animate-fade-in-up-delay-3 {
          animation: fade-in-up 1s ease-out 0.9s both;
        }
        @keyframes pulse-slow {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.8;
          }
        }
        .animate-pulse-slow {
          animation: pulse-slow 2s ease-in-out infinite;
        }
        /* Logo 縮放動畫 - 從 3 倍縮放到1倍 */
        @keyframes logo-scale-down {
          0% {
            transform: scale(4);
            opacity: 0;
          }
          10% {
            opacity: 1;
          }
          100% {
            transform: scale(1);
            opacity: 1;
          }
        }
        .logo-image {
          animation: logo-scale-down 1.5s cubic-bezier(0.25, 1, 0.5, 1) forwards;
          animation-fill-mode: forwards;
          will-change: transform, opacity;
        }
        /* 動畫完成後通過內聯樣式保持最終狀態，防止重新縮小 */
        .logo-image[style*="animation: none"],
        .logo-image[style*="animation:none"] {
          animation: none !important;
          transform: scale(1) !important;
          opacity: 1 !important;
          will-change: auto !important;
        }
        /* 橫向亮光掃過動畫 */
        .light-beam-container {
          position: absolute;
          top: 50%;
          left: 0;
          width: 100%;
          height: 4px;
          transform: translateY(-50%);
          overflow: hidden;
          pointer-events: none;
        }
        .light-beam {
          position: absolute;
          top: 0;
          left: -100%;
          width: 200%;
          height: 6px;
          z-index: 10;
          background: linear-gradient(90deg,
            rgba(255, 215, 0, 0) 0%,
            rgba(255, 215, 0, 1) 40%,
            rgba(255, 255, 150, 1) 80%,
            rgba(255, 255, 255, 1) 95%,
            rgba(255, 255, 255, 0) 100%
          );
          box-shadow:
            0 0 20px rgba(255, 215, 0, 0.8),
            0 0 50px rgba(255, 200, 0, 0.6),
            0 0 100px rgba(255, 255, 255, 0.5);
          filter: blur(0px);
          border-radius: 50%;
          animation: light-sweep 2s ease-in-out 1.5s forwards;
          opacity: 0;
        }
        @keyframes light-sweep {
          0% {
            left: -200%;
            opacity: 0;
          }
          10% {
            opacity: 1;
          }
          100% {
            left: 100%;
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}
