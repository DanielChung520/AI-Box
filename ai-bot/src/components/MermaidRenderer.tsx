import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { useTheme } from '../hooks/useTheme';

interface MermaidRendererProps {
  code: string;
  className?: string;
}

export default function MermaidRenderer({ code, className = '' }: MermaidRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isClient, setIsClient] = useState(false);
  const [renderError, setRenderError] = useState<string | null>(null);
  const [isRendering, setIsRendering] = useState(false);
  const { theme } = useTheme();

  // 确保在客户端环境
  useEffect(() => {
    const checkClientEnvironment = () => {
      setIsClient(
        typeof window !== 'undefined' &&
        typeof document !== 'undefined' &&
        typeof document.createElementNS === 'function'
      );
    };

    // 立即检查
    checkClientEnvironment();

    // 监听窗口加载完成事件，确保DOM完全可用
    window.addEventListener('load', checkClientEnvironment);

    return () => {
      window.removeEventListener('load', checkClientEnvironment);
    };
  }, []);

  // 初始化 Mermaid
  useEffect(() => {
    if (!isClient) return;

    try {
      mermaid.initialize({
        startOnLoad: false,
        theme: theme === 'dark' ? 'dark' : 'default',
        themeVariables: {
          primaryColor: theme === 'dark' ? '#1e3a8a' : '#bfdbfe',
          primaryTextColor: theme === 'dark' ? '#e2e8f0' : '#1f2937',
          primaryBorderColor: '#3b82f6',
          lineColor: theme === 'dark' ? '#94a3b8' : '#4b5563',
          secondaryColor: theme === 'dark' ? '#1f2937' : '#f3f4f6',
          tertiaryColor: theme === 'dark' ? '#374151' : '#e5e7eb'
        },
        gantt: {
          dateFormat: 'YYYY-MM-DD'
        },
        securityLevel: 'loose',
        fontFamily: 'inherit'
      } as any);
    } catch (error) {
      console.error('Mermaid 初始化错误:', error);
    }
  }, [isClient, theme]);

  // 渲染Mermaid图表
  useEffect(() => {
    // 确保所有条件都满足才进行渲染
    if (!isClient || !containerRef.current || !code.trim() || isRendering) return;

    setIsRendering(true);
    setRenderError(null);

    // 清空之前的内容
    const container = containerRef.current;
    container.innerHTML = '';

    // 生成唯一ID
    const chartId = `mermaid-${Math.random().toString(36).substring(2, 10)}`;

    // 创建临时元素用于渲染
    const tempDiv = document.createElement('div');
    tempDiv.id = chartId;
    tempDiv.className = 'mermaid';
    tempDiv.textContent = code.trim();
    container.appendChild(tempDiv);

    // 使用 mermaid 渲染（mermaid 10.x API）
    const renderChart = async () => {
      try {
        // 尝试使用 mermaid.run() (mermaid 10.x)
        if (typeof mermaid.run === 'function') {
          await mermaid.run({
            nodes: [tempDiv],
            suppressErrors: false
          });
        }
        // 尝试使用 mermaid.contentLoaded() (旧版本兼容)
        else if (typeof mermaid.contentLoaded === 'function') {
          mermaid.contentLoaded();
          // 等待一小段时间让 mermaid 处理
          await new Promise(resolve => setTimeout(resolve, 100));
        }
        // 尝试使用 mermaid.render() (如果存在)
        else if (typeof mermaid.render === 'function') {
          const result = await mermaid.render(chartId, code.trim());
          if (result && result.svg) {
            tempDiv.innerHTML = result.svg;
          }
        }
        else {
          throw new Error('Mermaid API 不可用，请检查 mermaid 版本');
        }
        setIsRendering(false);
      } catch (error) {
        console.error('Mermaid渲染错误:', error);
        setRenderError(error instanceof Error ? error.message : '渲染失败');
        container.innerHTML = '';
        setIsRendering(false);
      }
    };

    // 延迟执行以确保 DOM 已更新
    setTimeout(() => {
      renderChart();
    }, 50);

    // 清理函数
    return () => {
      if (container) {
        container.innerHTML = '';
      }
      setIsRendering(false);
    };
  }, [isClient, code, theme]);

  // 显示加载状态
  if (!isClient || isRendering) {
    return (
      <div className={`my-4 p-4 bg-secondary border border-primary rounded-lg ${className}`}>
        <div className="flex items-center text-tertiary">
          <i className="fa-solid fa-spinner fa-spin mr-2"></i>
          <span>图表加载中...</span>
        </div>
      </div>
    );
  }

  // 显示错误信息
  if (renderError) {
    return (
      <div className={`my-4 p-4 bg-red-900/20 border border-red-700/30 rounded-lg ${className}`}>
        <div className="text-red-400 text-sm font-medium mb-1">图表渲染错误</div>
        <pre className="text-xs text-red-300 whitespace-pre-wrap">{renderError}</pre>
        <details className="mt-2">
          <summary className="text-xs text-red-300 cursor-pointer">查看原始代码</summary>
          <pre className="text-xs text-red-200 mt-2 whitespace-pre-wrap bg-red-900/30 p-2 rounded">{code}</pre>
        </details>
      </div>
    );
  }

  // 渲染结果
  return (
    <div
      ref={containerRef}
      className={`my-4 overflow-x-auto ${className}`}
    />
  );
}
