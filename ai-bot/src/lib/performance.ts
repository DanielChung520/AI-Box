/**
 * 代碼功能說明: 前端性能監控工具，測量系統載入時間
 * 創建日期: 2025-01-27
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-01-27
 */

export interface PerformanceMetrics {
  // 頁面載入時間
  domContentLoaded: number; // DOMContentLoaded 事件時間（相對於 navigationStart）
  pageLoad: number; // load 事件時間（相對於 navigationStart）

  // 內聯歡迎頁時間
  initialWelcomeShow: number; // 內聯歡迎頁顯示時間（幾乎為 0，因為是內聯的）

  // React 應用啟動時間
  reactAppStart: number; // React 應用開始渲染時間
  reactAppReady: number; // React 應用準備完成時間

  // 歡迎頁時間
  welcomePageMount: number; // 歡迎頁組件掛載時間
  welcomePageContentShow: number; // 歡迎頁內容顯示時間
  welcomePageLogoAnimation: number; // Logo 動畫完成時間

  // 總時間
  totalLoadTime: number; // 從導航開始到內容顯示的總時間
  reactInitTime: number; // React 初始化時間
  welcomePageRenderTime: number; // 歡迎頁渲染時間
  timeToInitialWelcome: number; // 到內聯歡迎頁顯示的時間
}

class PerformanceMonitor {
  private metrics: Partial<PerformanceMetrics> = {};
  private startTime: number = performance.now();
  private navigationStart: number = (performance as any).timeOrigin || performance.now();

  constructor() {
    this.init();
  }

  private init() {
    // 記錄內聯歡迎頁顯示時間（幾乎為 0，因為是內聯的）
    this.metrics.initialWelcomeShow = performance.now() - this.startTime;
    this.logMetric('Initial Welcome Show', this.metrics.initialWelcomeShow);

    // 記錄 DOMContentLoaded 時間
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        this.metrics.domContentLoaded = performance.now() - this.startTime;
        this.logMetric('DOMContentLoaded', this.metrics.domContentLoaded);
      });
    } else {
      this.metrics.domContentLoaded = performance.now() - this.startTime;
    }

    // 記錄 load 事件時間
    if (document.readyState !== 'complete') {
      window.addEventListener('load', () => {
        this.metrics.pageLoad = performance.now() - this.startTime;
        this.logMetric('Page Load', this.metrics.pageLoad);
      });
    } else {
      this.metrics.pageLoad = performance.now() - this.startTime;
    }
  }

  /**
   * 記錄 React 應用啟動時間
   */
  markReactAppStart() {
    this.metrics.reactAppStart = performance.now() - this.startTime;
    this.logMetric('React App Start', this.metrics.reactAppStart);
  }

  /**
   * 記錄 React 應用準備完成時間
   */
  markReactAppReady() {
    this.metrics.reactAppReady = performance.now() - this.startTime;
    this.metrics.reactInitTime = (this.metrics.reactAppReady || 0) - (this.metrics.reactAppStart || 0);
    this.logMetric('React App Ready', this.metrics.reactAppReady);
    this.logMetric('React Init Time', this.metrics.reactInitTime);
  }

  /**
   * 記錄歡迎頁組件掛載時間
   */
  markWelcomePageMount() {
    this.metrics.welcomePageMount = performance.now() - this.startTime;
    this.logMetric('Welcome Page Mount', this.metrics.welcomePageMount);
  }

  /**
   * 記錄歡迎頁內容顯示時間
   */
  markWelcomePageContentShow() {
    this.metrics.welcomePageContentShow = performance.now() - this.startTime;
    this.metrics.welcomePageRenderTime = (this.metrics.welcomePageContentShow || 0) - (this.metrics.welcomePageMount || 0);
    this.logMetric('Welcome Page Content Show', this.metrics.welcomePageContentShow);
    this.logMetric('Welcome Page Render Time', this.metrics.welcomePageRenderTime);
  }

  /**
   * 記錄 Logo 動畫完成時間
   */
  markLogoAnimationComplete() {
    this.metrics.welcomePageLogoAnimation = performance.now() - this.startTime;
    this.logMetric('Logo Animation Complete', this.metrics.welcomePageLogoAnimation);
  }

  /**
   * 計算總載入時間
   */
  calculateTotalLoadTime() {
    const contentShowTime = this.metrics.welcomePageContentShow || this.metrics.welcomePageMount || 0;
    this.metrics.totalLoadTime = contentShowTime;
    this.metrics.timeToInitialWelcome = this.metrics.initialWelcomeShow || 0;
    this.logMetric('Total Load Time', this.metrics.totalLoadTime);
    this.logMetric('Time to Initial Welcome', this.metrics.timeToInitialWelcome);
  }

  /**
   * 獲取所有性能指標
   */
  getMetrics(): PerformanceMetrics {
    this.calculateTotalLoadTime();
    return {
      domContentLoaded: this.metrics.domContentLoaded || 0,
      pageLoad: this.metrics.pageLoad || 0,
      initialWelcomeShow: this.metrics.initialWelcomeShow || 0,
      reactAppStart: this.metrics.reactAppStart || 0,
      reactAppReady: this.metrics.reactAppReady || 0,
      welcomePageMount: this.metrics.welcomePageMount || 0,
      welcomePageContentShow: this.metrics.welcomePageContentShow || 0,
      welcomePageLogoAnimation: this.metrics.welcomePageLogoAnimation || 0,
      totalLoadTime: this.metrics.totalLoadTime || 0,
      reactInitTime: this.metrics.reactInitTime || 0,
      welcomePageRenderTime: this.metrics.welcomePageRenderTime || 0,
      timeToInitialWelcome: this.metrics.timeToInitialWelcome || 0,
    };
  }

  /**
   * 輸出性能報告
   */
  printReport() {
    const metrics = this.getMetrics();
    console.group('🚀 系統性能監控報告');
    console.log('📊 頁面載入時間:');
    console.log(`  - DOMContentLoaded: ${metrics.domContentLoaded.toFixed(2)}ms`);
    console.log(`  - Page Load: ${metrics.pageLoad.toFixed(2)}ms`);
    console.log('');
    console.log('🎬 內聯歡迎頁:');
    console.log(`  - Initial Welcome Show: ${metrics.initialWelcomeShow.toFixed(2)}ms`);
    console.log(`  - Time to Initial Welcome: ${metrics.timeToInitialWelcome.toFixed(2)}ms`);
    console.log('');
    console.log('⚛️  React 應用時間:');
    console.log(`  - React App Start: ${metrics.reactAppStart.toFixed(2)}ms`);
    console.log(`  - React App Ready: ${metrics.reactAppReady.toFixed(2)}ms`);
    console.log(`  - React Init Time: ${metrics.reactInitTime.toFixed(2)}ms`);
    console.log('');
    console.log('👋 歡迎頁時間:');
    console.log(`  - Welcome Page Mount: ${metrics.welcomePageMount.toFixed(2)}ms`);
    console.log(`  - Content Show: ${metrics.welcomePageContentShow.toFixed(2)}ms`);
    console.log(`  - Logo Animation: ${metrics.welcomePageLogoAnimation.toFixed(2)}ms`);
    console.log(`  - Render Time: ${metrics.welcomePageRenderTime.toFixed(2)}ms`);
    console.log('');
    console.log('⏱️  總時間:');
    console.log(`  - Total Load Time: ${metrics.totalLoadTime.toFixed(2)}ms`);
    console.groupEnd();
  }

  /**
   * 記錄單個指標
   */
  private logMetric(name: string, value: number) {
    if (process.env.NODE_ENV === 'development') {
      console.log(`⏱️  ${name}: ${value.toFixed(2)}ms`);
    }
  }
}

// 創建全局實例
export const performanceMonitor = new PerformanceMonitor();

// 在開發環境中，將監控器暴露到 window 對象，方便調試
if (process.env.NODE_ENV === 'development' && typeof window !== 'undefined') {
  (window as any).performanceMonitor = performanceMonitor;
}
