import React, { useState, useEffect, useRef } from 'react';
import Markdown from 'markdown-to-jsx';
import MermaidRenderer from './MermaidRenderer';
import { useLanguage } from '../contexts/languageContext';
import { FileText, Database, Network, Download, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { getFileVectors, getFileGraph, getProcessingStatus, getKgChunkStatus, downloadFile, regenerateFileData } from '../lib/api';
import KnowledgeGraphViewer from './KnowledgeGraphViewer';

interface MarkdownViewerProps {
  content: string;
  fileName: string;
  fileId?: string; // 文件 ID，用於獲取向量和圖譜數據
}

type PreviewMode = 'text' | 'vector' | 'graph';

export default function MarkdownViewer({ content, fileName, fileId }: MarkdownViewerProps) {
  const { t } = useLanguage();
  const [mode, setMode] = useState<PreviewMode>('text'); // 默認為文件模式
  const [markdownParts, setMarkdownParts] = useState<Array<{type: 'text' | 'mermaid', content: string}>>([]);
  const [vectorData, setVectorData] = useState<any>(null);
  const [graphData, setGraphData] = useState<any>(null);
  const [processingStatus, setProcessingStatus] = useState<any>(null);
  const [kgChunkStatus, setKgChunkStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [textAvailable, setTextAvailable] = useState<boolean>(false);
  const [vectorAvailable, setVectorAvailable] = useState<boolean>(false);
  const [graphAvailable, setGraphAvailable] = useState<boolean>(false);
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null);
  const [regenerationJobId, setRegenerationJobId] = useState<string | null>(null);
  const [regenerationStartTime, setRegenerationStartTime] = useState<number | null>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  // 修改時間：2025-12-14 14:20:04 (UTC+8) - 判斷是否為草稿檔（尚未提交後端）
  const isDraftFile = (id?: string): boolean => {
    return typeof id === 'string' && id.startsWith('draft-');
  };

  // 檢查數據可用性（只在有 fileId 時檢查，避免不必要的 API 調用）
  useEffect(() => {
    if (fileId) {
      // 延遲檢查，避免在組件加載時立即發起多個請求
      const timer = setTimeout(() => {
        checkDataAvailability();
      }, 100);
      return () => clearTimeout(timer);
    } else {
      setTextAvailable(!!content);
    }
  }, [fileId, content]);

  // 清理刷新定時器
  useEffect(() => {
    return () => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
        setRefreshInterval(null);
      }
    };
  }, [refreshInterval]);

  const refreshProcessingStatus = async () => {
    if (!fileId || isDraftFile(fileId)) return; // 修改時間：2025-12-14 14:20:04 (UTC+8) - 草稿檔跳過
    try {
      const resp = await getProcessingStatus(fileId);
      if (resp?.success && resp.data) {
        setProcessingStatus(resp.data);
      }
    } catch {
      // ignore
    }
  };

  const refreshKgChunkStatus = async () => {
    if (!fileId || isDraftFile(fileId)) return; // 修改時間：2025-12-14 14:20:04 (UTC+8) - 草稿檔跳過
    try {
      const resp = await getKgChunkStatus(fileId);
      if (resp?.success && resp.data) {
        setKgChunkStatus(resp.data);
      }
    } catch {
      // ignore
    }
  };

  // 修改時間：2025-12-14 14:20:04 (UTC+8) - 當向量/圖譜未生成時，輪詢處理狀態以顯示「產生中」（草稿檔跳過）
  useEffect(() => {
    if (!fileId || isDraftFile(fileId)) return; // 草稿檔不輪詢
    const needsPolling =
      (mode === 'vector' && !vectorAvailable) || (mode === 'graph' && !graphAvailable);
    if (!needsPolling) return;

    let cancelled = false;
    const tick = async () => {
      if (cancelled) return;
      await refreshProcessingStatus();
      if (mode === 'graph' && !graphAvailable) {
        await refreshKgChunkStatus();
      }
      await checkDataAvailability();
    };

    tick();
    const interval = setInterval(tick, 3000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [fileId, mode, vectorAvailable, graphAvailable]);

  const renderChunkBars = () => {
    const totalChunks: number | undefined =
      kgChunkStatus?.total_chunks ?? processingStatus?.kg_extraction?.total_chunks;
    if (!totalChunks || totalChunks <= 0) return null;

    const completedSet = new Set<number>(kgChunkStatus?.completed_chunks || processingStatus?.kg_extraction?.completed_chunks || []);
    const failedSet = new Set<number>(kgChunkStatus?.failed_chunks || processingStatus?.kg_extraction?.failed_chunks || []);
    const failedPermanentSet = new Set<number>(kgChunkStatus?.failed_permanent_chunks || processingStatus?.kg_extraction?.failed_permanent_chunks || []);

    const items = Array.from({ length: totalChunks }, (_, i) => i + 1);

    return (
      <div className="mt-4 text-left max-w-2xl mx-auto">
        <div className="text-xs text-tertiary theme-transition mb-2">
          分塊狀態（綠=完成、灰=待處理、橘=可重試失敗、紅=永久失敗）
        </div>
        <div className="grid grid-cols-10 gap-2">
          {items.map((idx) => {
            const isCompleted = completedSet.has(idx);
            const isPermanentFailed = failedPermanentSet.has(idx);
            const isFailed = failedSet.has(idx);
            const color = isCompleted
              ? 'bg-green-500'
              : isPermanentFailed
                ? 'bg-red-500'
                : isFailed
                  ? 'bg-orange-500'
                  : 'bg-gray-300';

            const chunkInfo = kgChunkStatus?.chunks?.[String(idx)];
            const triples = chunkInfo?.triples;
            const attempts = chunkInfo?.attempts;
            const titleParts = [
              `Chunk ${idx}/${totalChunks}`,
              isCompleted ? 'completed' : isPermanentFailed ? 'failed(permanent)' : isFailed ? 'failed(retryable)' : 'pending',
            ];
            if (typeof triples === 'number') titleParts.push(`triples=${triples}`);
            if (typeof attempts === 'number') titleParts.push(`attempts=${attempts}`);

            return (
              <div key={idx} className="space-y-1" title={titleParts.join(' | ')}>
                <div className="h-2 w-full bg-gray-200 rounded">
                  <div className={`h-2 rounded ${color} ${!isCompleted && !isFailed && !isPermanentFailed ? 'animate-pulse' : ''}`} style={{ width: '100%' }} />
                </div>
                <div className="text-[10px] text-tertiary theme-transition text-center">{idx}</div>
              </div>
            );
          })}
        </div>
        {kgChunkStatus?.errors && Object.keys(kgChunkStatus.errors).length > 0 && (
          <div className="mt-3 text-xs text-tertiary theme-transition">
            <div className="font-medium text-orange-500 mb-1">分塊錯誤（最近幾筆）</div>
            <ul className="space-y-1 max-h-24 overflow-auto bg-secondary border border-primary rounded p-2">
              {Object.entries(kgChunkStatus.errors).slice(0, 5).map(([k, v]: any) => (
                <li key={k}>
                  <span className="font-mono">#{k}</span>：{String(v?.error || '')}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  const checkDataAvailability = async () => {
    if (!fileId) return;

    // 檢查文本內容
    setTextAvailable(!!content);

    // 修改時間：2025-12-14 14:20:04 (UTC+8) - 草稿檔跳過向量和圖譜資料檢查（尚未提交後端）
    if (isDraftFile(fileId)) {
      setVectorAvailable(false);
      setGraphAvailable(false);
      return;
    }

    // 檢查向量數據（靜默處理 404 錯誤，因為文件可能沒有向量數據是正常的）
    try {
      const vectorResponse = await getFileVectors(fileId, 1, 0);
      setVectorAvailable(vectorResponse.success && vectorResponse.data &&
        (vectorResponse.data.vectors?.length > 0 ||
         vectorResponse.data.stats?.vector_count > 0 ||
         vectorResponse.data.total > 0));
    } catch (e: any) {
      // 靜默處理錯誤，特別是 404（文件不存在或沒有向量數據是正常情況）
      if (e.message?.includes('文件不存在') || e.message?.includes('404') || e.message?.includes('Not Found')) {
        setVectorAvailable(false);
      } else {
        // 其他錯誤才記錄
        console.warn('[MarkdownViewer] Failed to check vector availability:', e);
        setVectorAvailable(false);
      }
    }

    // 檢查圖譜數據（靜默處理 404 錯誤，因為文件可能沒有圖譜數據是正常的）
    try {
      const graphResponse = await getFileGraph(fileId, 1, 0);
      const hasGraphData = graphResponse.success && graphResponse.data &&
        (graphResponse.data.nodes?.length > 0 ||
         graphResponse.data.edges?.length > 0 ||
         graphResponse.data.triples?.length > 0 ||
         graphResponse.data.stats?.entities_count > 0 ||
         graphResponse.data.stats?.relations_count > 0 ||
         graphResponse.data.stats?.triples_count > 0);
      setGraphAvailable(hasGraphData);

      // 如果圖譜已生成，清除任務狀態
      if (hasGraphData && regenerationJobId) {
        setRegenerationJobId(null);
        setRegenerationStartTime(null);
        if (refreshInterval) {
          clearInterval(refreshInterval);
          setRefreshInterval(null);
        }
      }
    } catch (e: any) {
      // 靜默處理錯誤，特別是 404（文件不存在或沒有圖譜數據是正常情況）
      if (e.message?.includes('文件不存在') || e.message?.includes('404') || e.message?.includes('Not Found')) {
        setGraphAvailable(false);
      } else {
        // 其他錯誤才記錄
        console.warn('[MarkdownViewer] Failed to check graph availability:', e);
        setGraphAvailable(false);
      }
    }
  };

  const loadDataForMode = async (targetMode: PreviewMode) => {
    if (!fileId) return;

    // 修改時間：2025-12-14 14:20:04 (UTC+8) - 草稿檔不支持向量和圖譜模式
    if (isDraftFile(fileId)) {
      if (targetMode === 'vector' || targetMode === 'graph') {
        setError('草稿檔尚未提交後端，無法查看向量或圖譜資料');
        setLoading(false);
        return;
      }
    }

    setLoading(true);
    setError(null); // 清除錯誤狀態
    try {
      switch (targetMode) {
        case 'vector':
          const vectorResponse = await getFileVectors(fileId, 100, 0);
          if (vectorResponse.success && vectorResponse.data) {
            setVectorData(vectorResponse.data);
          }
          break;
        case 'graph':
          const graphResponse = await getFileGraph(fileId, 100, 0);
          if (graphResponse.success && graphResponse.data) {
            setGraphData(graphResponse.data);
          }
          break;
      }
    } catch (err: any) {
      // 靜默處理 404 錯誤（文件不存在或沒有數據是正常情況）
      if (!err.message?.includes('文件不存在') && !err.message?.includes('404') && !err.message?.includes('Not Found')) {
        console.error('[MarkdownViewer] Failed to load data:', err);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleModeChange = (newMode: PreviewMode) => {
    setMode(newMode);
    if (newMode !== 'text') {
      loadDataForMode(newMode);
    }
  };

  // 解析Markdown内容，识别普通文本和mermaid代码块
  useEffect(() => {
    try {
      // 分割文本和mermaid代码块
      const parts: Array<{ type: 'text' | 'mermaid'; content: string }> = [];
      const mermaidRegex = /```mermaid\s([\s\S]*?)```/g;
      let lastIndex = 0;
      let match;

      while ((match = mermaidRegex.exec(content)) !== null) {
        // 添加mermaid代码块前的普通文本
        if (match.index > lastIndex) {
          parts.push({
            type: 'text',
            content: content.substring(lastIndex, match.index)
          });
        }

        // 添加mermaid代码块（保留原始格式以便後續處理）
        parts.push({
          type: 'mermaid',
          content: match[1] // 只提取 mermaid 代碼內容
        });

        lastIndex = match.index + match[0].length;
      }

      // 添加最后一段普通文本
      if (lastIndex < content.length) {
        parts.push({
          type: 'text',
          content: content.substring(lastIndex)
        });
      }

      // 如果沒有找到任何 mermaid 代碼塊，整個內容都是文本
      if (parts.length === 0) {
        parts.push({ type: 'text', content });
      }

      setMarkdownParts(parts);
    } catch (error) {
      console.error("解析Markdown内容时出错:", error);
      setMarkdownParts([{ type: 'text', content }]);
    }
  }, [content]);

  // 修改時間：2025-01-27 15:00:00 (UTC+8) - 使用 markdown-to-jsx 替代 react-markdown，更好的縮排控制
  // 自定義 Markdown 組件樣式（markdown-to-jsx 格式）
  const markdownOptions = {
    overrides: {
      // 標題
      h1: {
        component: 'h1',
        props: { className: 'text-3xl font-bold mt-8 mb-4 text-primary' }
      },
      h2: {
        component: 'h2',
        props: { className: 'text-2xl font-bold mt-7 mb-3 text-primary' }
      },
      h3: {
        component: 'h3',
        props: { className: 'text-xl font-bold mt-6 mb-3 text-primary' }
      },
      h4: {
        component: 'h4',
        props: { className: 'text-xl font-bold mt-5 mb-2 text-primary' }
      },
      h5: {
        component: 'h5',
        props: { className: 'text-lg font-bold mt-4 mb-2 text-primary' }
      },
      h6: {
        component: 'h6',
        props: { className: 'text-lg font-bold mt-4 mb-2 text-primary' }
      },

      // 段落 - 保留換行和縮排（使用自定義組件）
      p: {
        component: ({ children, ...props }: any) => (
          <p
            className="mb-4 text-primary whitespace-pre-wrap leading-relaxed"
            style={{ whiteSpace: 'pre-wrap' }}
            {...props}
          >
            {children}
          </p>
        )
      },

      // 列表 - 支持嵌套縮排
      ul: {
        component: 'ul',
        props: { className: 'list-disc mb-2 text-primary ml-6' }
      },
      ol: {
        component: 'ol',
        props: { className: 'list-decimal mb-2 text-primary ml-6' }
      },
      li: {
        component: 'li',
        props: { className: 'mb-1 text-primary leading-relaxed' }
      },

      // 代碼塊
      pre: {
        component: 'pre',
        props: { className: 'bg-gray-900 dark:bg-gray-800 p-4 rounded-md overflow-x-auto my-4 text-sm whitespace-pre' }
      },
      code: {
        component: ({ className, children, ...props }: any) => {
          // 檢查是否是代碼塊（有 className 且不是行內代碼）
          const isCodeBlock = className && !className.includes('inline');

          if (isCodeBlock) {
            // 提取語言
            const langMatch = className?.match(/language-(\w+)/);
            const language = langMatch ? langMatch[1] : '';
            const codeContent = String(children || '').replace(/\n$/, '');

            // 如果是 Mermaid，使用 MermaidRenderer
            if (language === 'mermaid') {
              return <MermaidRenderer code={codeContent.trim()} className="bg-secondary p-4 rounded-lg border border-primary" />;
            }

            return (
              <pre className="bg-gray-900 dark:bg-gray-800 p-4 rounded-md overflow-x-auto my-4 text-sm whitespace-pre">
                <code className="text-gray-100">{codeContent}</code>
              </pre>
            );
          }

          // 行內代碼
          return (
            <code className="bg-gray-900 dark:bg-gray-800 px-1.5 py-0.5 rounded text-sm text-gray-100" {...props}>
              {children}
            </code>
          );
        }
      },

    // 水平線
      hr: {
        component: 'hr',
        props: { className: 'my-6 border-primary' }
      },

      // 加粗和斜體
      strong: {
        component: 'strong',
        props: { className: 'font-bold text-primary' }
      },
      em: {
        component: 'em',
        props: { className: 'italic text-primary' }
      },

      // 鏈接
      a: {
        component: 'a',
        props: {
          className: 'text-blue-500 hover:text-blue-600 underline',
          target: '_blank',
          rel: 'noopener noreferrer'
        }
      },

      // 引用
      blockquote: {
        component: 'blockquote',
        props: { className: 'border-l-4 border-primary pl-4 my-4 italic text-tertiary' }
      },

      // 表格
      table: {
        component: ({ children }: any) => (
          <div className="overflow-x-auto my-4">
            <table className="min-w-full border border-primary rounded-lg">
              {children}
            </table>
          </div>
        )
      },
      thead: {
        component: 'thead',
        props: { className: 'bg-tertiary' }
      },
      tbody: {
        component: 'tbody'
      },
      tr: {
        component: 'tr',
        props: { className: 'border-b border-primary' }
      },
      th: {
        component: 'th',
        props: { className: 'px-4 py-2 text-left font-bold text-primary' }
      },
      td: {
        component: 'td',
        props: { className: 'px-4 py-2 text-primary' }
      },
    },
  };

  return (
    <div className="p-4 h-full flex flex-col theme-transition">
      {/* 文件标题栏 */}
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-primary gap-4">
        <div className="flex items-center flex-shrink min-w-0 max-w-[40%]">
          <i className="fa-solid fa-file-lines text-blue-400 mr-2"></i>
          <span className="font-medium text-primary truncate">{fileName}</span>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          {/* 模式切換按鈕組（文件、向量、圖譜） */}
          {fileId && (
            <div className="flex gap-0.5 border border-primary rounded-lg p-0.5 bg-tertiary shadow-sm theme-transition">
              <button
                onClick={() => handleModeChange('text')}
                className={`px-3 py-1.5 rounded-md text-sm flex items-center gap-1.5 transition-all theme-transition ${
                  mode === 'text'
                    ? 'bg-blue-500 text-white shadow-md font-medium hover:bg-blue-600'
                    : 'bg-secondary text-primary hover:bg-hover'
                }`}
                title="文件模式"
              >
                <FileText className="w-4 h-4" />
                <span>文件</span>
                {!textAvailable && mode === 'text' && <span className="text-xs opacity-75">(未生成)</span>}
              </button>
              <button
                onClick={() => handleModeChange('vector')}
                className={`px-3 py-1.5 rounded-md text-sm flex items-center gap-1.5 transition-all theme-transition ${
                  mode === 'vector'
                    ? 'bg-blue-500 text-white shadow-md font-medium hover:bg-blue-600'
                    : 'bg-secondary text-primary hover:bg-hover'
                }`}
                title="向量模式"
              >
                <Database className="w-4 h-4" />
                <span>向量</span>
                {!vectorAvailable && mode === 'vector' && <span className="text-xs opacity-75">(未生成)</span>}
              </button>
              <button
                onClick={() => handleModeChange('graph')}
                className={`px-3 py-1.5 rounded-md text-sm flex items-center gap-1.5 transition-all theme-transition ${
                  mode === 'graph'
                    ? 'bg-blue-500 text-white shadow-md font-medium hover:bg-blue-600'
                    : 'bg-secondary text-primary hover:bg-hover'
                }`}
                title="圖譜模式"
              >
                <Network className="w-4 h-4" />
                <span>圖譜</span>
                {!graphAvailable && mode === 'graph' && <span className="text-xs opacity-75">(未生成)</span>}
              </button>
            </div>
          )}
          {/* 下載按鈕 */}
          {fileId && (
            <button
              onClick={async () => {
                // 修改時間：2025-12-14 14:20:04 (UTC+8) - 草稿檔不支持下載
                if (isDraftFile(fileId)) {
                  alert('草稿檔尚未提交後端，無法下載。請先到「文件助手」預覽並 Apply 提交。');
                  return;
                }
                try {
                  const blob = await downloadFile(fileId);
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = fileName;
                  document.body.appendChild(a);
                  a.click();
                  window.URL.revokeObjectURL(url);
                  document.body.removeChild(a);
                } catch (err: any) {
                  alert(`下載失敗: ${err.message}`);
                }
              }}
              className="p-1 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label={t('markdownViewer.download')}
              title={isDraftFile(fileId) ? '草稿檔尚未提交後端，無法下載' : '下載文件'}
              disabled={isDraftFile(fileId)}
            >
              <Download className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* 內容區域 */}
      <div className="flex-1 overflow-y-auto text-sm markdown-content" ref={contentRef}>
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <i className="fa-solid fa-spinner fa-spin text-4xl text-tertiary"></i>
          </div>
        ) : (
          <>
            {mode === 'text' && (
              <>
                {!textAvailable ? (
                  <div className="text-center py-8 text-tertiary theme-transition">
                    <FileText className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p className="text-lg text-primary theme-transition">未成功生成</p>
                    <p className="text-sm mt-2 text-tertiary theme-transition">文本內容尚未生成或無法加載</p>
                  </div>
                ) : (
                  markdownParts.map((part, index) => (
                    <div key={index}>
                      {part.type === 'text' ? (
                        <div
                          className="markdown-content prose prose-invert max-w-none"
                          style={{
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word'
                          }}
                        >
                          <Markdown options={markdownOptions}>
                            {part.content}
                          </Markdown>
                        </div>
                      ) : (
                        <MermaidRenderer code={part.content.trim()} className="bg-secondary p-4 rounded-lg border border-primary" />
                      )}
                    </div>
                  ))
                )}
              </>
            )}
            {mode === 'vector' && (
              <>
                {!vectorAvailable ? (
                  <div className="text-center py-8 text-tertiary theme-transition">
                    <Database className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p className="text-lg font-semibold text-primary theme-transition">未成功生成</p>
                    <p className="text-sm mt-2 mb-4 text-tertiary theme-transition">向量數據尚未生成或無法加載</p>
                    {(() => {
                      const vectorStage = processingStatus?.vectorization?.status || processingStatus?.status;
                      const vectorProgress = processingStatus?.vectorization?.progress ?? 0;
                      const vectorMessage =
                        processingStatus?.vectorization?.message ||
                        processingStatus?.message ||
                        '向量處理中，請稍候';
                      const isVectorRunning = vectorStage === 'processing' || vectorStage === 'in_progress' || vectorStage === 'pending';
                      const isVectorFailed = vectorStage === 'failed';

                      if (isVectorRunning && !isVectorFailed) {
                        return (
                          <div className="space-y-3">
                            <div className="flex items-center justify-center gap-2 text-sm text-tertiary theme-transition">
                              <RefreshCw className="w-5 h-5 animate-spin text-blue-500" />
                              <span className="font-medium text-primary theme-transition">向量產生中... ({vectorProgress}%)</span>
                            </div>
                            <p className="text-xs text-tertiary theme-transition">{vectorMessage}</p>
                            <button
                              onClick={async () => {
                                setLoading(true);
                                try {
                                  await refreshProcessingStatus();
                                  await checkDataAvailability();
                                  if (vectorAvailable) {
                                    await loadDataForMode('vector');
                                    toast.success('向量生成完成！', { duration: 3000 });
                                  }
                                } finally {
                                  setLoading(false);
                                }
                              }}
                              disabled={loading}
                              className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-50 text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-100 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors mx-auto"
                            >
                              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                              <span>手動刷新</span>
                            </button>
                          </div>
                        );
                      }

                      return (
                      <button
                        onClick={async () => {
                          // 修改時間：2025-12-14 14:20:04 (UTC+8) - 草稿檔不支持重新生成
                          if (isDraftFile(fileId)) {
                            setError('草稿檔尚未提交後端，無法重新生成向量資料');
                            return;
                          }
                          setLoading(true);
                          setError(null);
                          try {
                            if (!fileId) {
                              setError('缺少 fileId，無法重新生成');
                              return;
                            }
                            const result = await regenerateFileData(fileId, 'vector');
                            if (result.success) {
                              // 重新檢查數據可用性
                              await checkDataAvailability();
                              // 重新加載數據
                              await loadDataForMode('vector');
                            } else {
                              setError(result.message || '重新生成失敗');
                            }
                          } catch (err: any) {
                            setError(err.message || '重新生成失敗');
                          } finally {
                            setLoading(false);
                          }
                        }}
                        disabled={loading || isDraftFile(fileId)}
                        className="mt-2 px-6 py-2.5 bg-blue-500 text-white text-base font-medium rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors shadow-md hover:shadow-lg"
                      >
                        {loading ? '生成中...' : '重新生成'}
                      </button>
                      );
                    })()}
                    {error && (
                      <p className="text-sm text-red-500 mt-3">{error}</p>
                    )}
                  </div>
                ) : (
                  <div className="p-4 flex flex-col flex-1 min-h-0">
                    <div className="mb-4 flex-shrink-0">
                      <h3 className="text-lg font-semibold mb-2 text-primary theme-transition">向量數據統計</h3>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-tertiary p-3 rounded theme-transition">
                          <div className="text-sm text-tertiary theme-transition">向量數量</div>
                          <div className="text-2xl font-bold text-primary theme-transition">{vectorData?.stats?.vector_count || vectorData?.total || vectorData?.vectors?.length || 0}</div>
                        </div>
                        {vectorData?.stats?.dimension && (
                          <div className="bg-tertiary p-3 rounded theme-transition">
                            <div className="text-sm text-tertiary theme-transition">向量維度</div>
                            <div className="text-2xl font-bold text-primary theme-transition">{vectorData.stats.dimension.toLocaleString()}</div>
                          </div>
                        )}
                        {vectorData?.stats?.collection_name && (
                          <div className="bg-tertiary p-3 rounded theme-transition">
                            <div className="text-sm text-tertiary theme-transition">集合名稱</div>
                            <div className="text-sm font-mono truncate text-primary theme-transition">{vectorData.stats.collection_name}</div>
                          </div>
                        )}
                        {vectorData?.stats?.total_chars && (
                          <div className="bg-tertiary p-3 rounded theme-transition">
                            <div className="text-sm text-tertiary theme-transition">總字符數</div>
                            <div className="text-xl font-bold text-primary theme-transition">{vectorData.stats.total_chars.toLocaleString()}</div>
                          </div>
                        )}
                        {vectorData?.stats?.avg_chars_per_chunk && (
                          <div className="bg-tertiary p-3 rounded theme-transition">
                            <div className="text-sm text-tertiary theme-transition">平均字符數/塊</div>
                            <div className="text-xl font-bold text-primary theme-transition">{vectorData.stats.avg_chars_per_chunk.toLocaleString()}</div>
                          </div>
                        )}
                        {vectorData?.stats?.total_words && (
                          <div className="bg-tertiary p-3 rounded theme-transition">
                            <div className="text-sm text-tertiary theme-transition">總詞數</div>
                            <div className="text-xl font-bold text-primary theme-transition">{vectorData.stats.total_words.toLocaleString()}</div>
                          </div>
                        )}
                        {vectorData?.stats?.avg_words_per_chunk && (
                          <div className="bg-tertiary p-3 rounded theme-transition">
                            <div className="text-sm text-tertiary theme-transition">平均詞數/塊</div>
                            <div className="text-xl font-bold text-primary theme-transition">{vectorData.stats.avg_words_per_chunk.toLocaleString()}</div>
                          </div>
                        )}
                      </div>
                    </div>
                    {vectorData?.vectors && vectorData.vectors.length > 0 && (
                      <div className="flex flex-col flex-1 min-h-0">
                        <h3 className="text-lg font-semibold mb-2 text-primary theme-transition">向量列表（顯示前 {vectorData.vectors.length} 個，共 {vectorData.total || vectorData.vectors.length} 個）</h3>
                        <div className="space-y-2 flex-1 overflow-auto min-h-0">
                          {vectorData.vectors.map((vector: any, index: number) => (
                            <div key={index} className="bg-tertiary p-3 rounded theme-transition">
                              <div className="text-sm font-mono text-tertiary mb-1 theme-transition">
                                ID: {vector.id || vector._id || `vector_${index}`}
                              </div>
                              {vector.metadata && (
                                <div className="text-xs text-tertiary mb-2 theme-transition">
                                  <div className="font-semibold mb-1">元数据:</div>
                                  {JSON.stringify(vector.metadata, null, 2)}
                                </div>
                              )}
                              {vector.document && (
                                <div className="text-sm text-tertiary mt-2 mb-2 p-2 bg-secondary rounded border theme-transition">
                                  <div className="font-semibold mb-1">文档内容:</div>
                                  <pre className="whitespace-pre-wrap text-xs max-h-40 overflow-auto">
                                    {vector.document}
                                  </pre>
                                </div>
                              )}
                              {vector.embedding && (
                                <div className="text-xs text-tertiary opacity-75 mt-1 theme-transition">
                                  向量維度: {vector.embedding.length}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
            {mode === 'graph' && (
              <>
                {!graphAvailable ? (
                  <div className="text-center py-8 text-tertiary theme-transition">
                    <Network className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p className="text-lg font-semibold text-primary theme-transition">未成功生成</p>
                    <p className="text-sm mt-2 mb-4 text-tertiary theme-transition">圖譜數據尚未生成或無法加載</p>

                    {fileId && (() => {
                      // 檢查是否有正在進行的任務
                      const hasActiveTask = regenerationJobId !== null;
                      // 檢查任務是否超時（超過5分鐘認為失敗）
                      const isTaskTimeout = regenerationStartTime !== null &&
                        Date.now() - regenerationStartTime > 5 * 60 * 1000;

                      const graphStage = processingStatus?.kg_extraction?.status || processingStatus?.status;
                      const graphProgress = processingStatus?.kg_extraction?.progress ?? 0;
                      const graphMessage =
                        processingStatus?.kg_extraction?.message ||
                        processingStatus?.message ||
                        '圖譜處理中，請稍候';
                      const isGraphRunning = graphStage === 'processing' || graphStage === 'in_progress' || graphStage === 'pending';
                      const isGraphFailed = graphStage === 'failed';
                      const totalChunks = processingStatus?.kg_extraction?.total_chunks;
                      const completedChunks = processingStatus?.kg_extraction?.completed_chunks?.length ?? 0;
                      const failedChunks = processingStatus?.kg_extraction?.failed_chunks?.length ?? 0;
                      const failedPermanentChunks = processingStatus?.kg_extraction?.failed_permanent_chunks?.length ?? 0;
                      const nextJobId = processingStatus?.kg_extraction?.next_job_id;

                      return (hasActiveTask && !isTaskTimeout) ? (
                        // 任務進行中：顯示提示和刷新圖標
                        <div className="space-y-3">
                          <div className="flex flex-col items-center gap-3">
                            <div className="flex items-center gap-2 text-sm text-tertiary theme-transition">
                              <RefreshCw className="w-5 h-5 animate-spin text-blue-500" />
                              <span className="font-medium text-primary theme-transition">任務已提交，正在處理中...</span>
                            </div>
                            <p className="text-xs text-tertiary theme-transition">
                              {regenerationJobId ? `任務 ID: ${regenerationJobId}` : '請耐心等候，系統正在生成圖譜'}
                            </p>
                            {typeof totalChunks === 'number' && totalChunks > 0 && (
                              <div className="text-xs text-tertiary theme-transition space-y-1">
                                <div>分塊進度：{completedChunks}/{totalChunks}</div>
                                {(failedChunks > 0 || failedPermanentChunks > 0) && (
                                  <div className="text-orange-500">
                                    失敗分塊：{failedChunks}（永久失敗：{failedPermanentChunks}）
                                  </div>
                                )}
                                {nextJobId && (
                                  <div className="opacity-75">已排程續跑：{nextJobId}</div>
                                )}
                              </div>
                            )}
                            {renderChunkBars()}
                            <button
                              onClick={async () => {
                                setLoading(true);
                                try {
                                  await checkDataAvailability();
                                  if (graphAvailable) {
                                    setRegenerationJobId(null);
                                    setRegenerationStartTime(null);
                                    if (refreshInterval) {
                                      clearInterval(refreshInterval);
                                      setRefreshInterval(null);
                                    }
                                    await loadDataForMode('graph');
                                    toast.success('圖譜生成完成！', { duration: 3000 });
                                  }
                                } finally {
                                  setLoading(false);
                                }
                              }}
                              disabled={loading}
                              className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-50 text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-100 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors theme-transition"
                            >
                              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                              <span>手動刷新</span>
                            </button>
                          </div>
                        </div>
                      ) : (isGraphRunning && !isGraphFailed) ? (
                        <div className="space-y-3">
                          <div className="flex items-center justify-center gap-2 text-sm text-tertiary theme-transition">
                            <RefreshCw className="w-5 h-5 animate-spin text-blue-500" />
                            <span className="font-medium text-primary theme-transition">圖譜產生中... ({graphProgress}%)</span>
                          </div>
                          <p className="text-xs text-tertiary theme-transition">{graphMessage}</p>
                          {typeof totalChunks === 'number' && totalChunks > 0 && (
                            <div className="text-xs text-tertiary theme-transition space-y-1">
                              <div>分塊進度：{completedChunks}/{totalChunks}</div>
                              {(failedChunks > 0 || failedPermanentChunks > 0) && (
                                <div className="text-orange-500">
                                  失敗分塊：{failedChunks}（永久失敗：{failedPermanentChunks}）
                                </div>
                              )}
                              {nextJobId && (
                                <div className="opacity-75">已排程續跑：{nextJobId}</div>
                              )}
                            </div>
                          )}
                          {renderChunkBars()}
                          <button
                            onClick={async () => {
                              setLoading(true);
                              try {
                                await refreshProcessingStatus();
                                await checkDataAvailability();
                                if (graphAvailable) {
                                  await loadDataForMode('graph');
                                  toast.success('圖譜生成完成！', { duration: 3000 });
                                }
                              } finally {
                                setLoading(false);
                              }
                            }}
                            disabled={loading}
                            className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-50 text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-100 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors theme-transition mx-auto"
                          >
                            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                            <span>手動刷新</span>
                          </button>
                        </div>
                      ) : (
                        // 沒有任務或任務失敗：顯示重新生成按鈕
                        <div className="space-y-3">
                          {isTaskTimeout && (
                            <p className="text-sm text-orange-500 mb-2">
                              任務處理時間過長，可能已失敗
                            </p>
                          )}
                      <button
                        onClick={async () => {
                          // 修改時間：2025-12-14 14:20:04 (UTC+8) - 草稿檔不支持重新生成
                          if (isDraftFile(fileId)) {
                            setError('草稿檔尚未提交後端，無法重新生成圖譜資料');
                            return;
                          }
                          setLoading(true);
                          setError(null);
                          try {
                            if (!fileId) {
                              setError('缺少 fileId，無法重新生成');
                              return;
                            }
                            const result = await regenerateFileData(fileId, 'graph');
                            if (result.success) {
                                  const jobId = result.data?.job_id;
                                  const message = result.message || '圖譜重新生成已提交到隊列，請耐心等候';
                                  toast.success(message, {
                                    description: jobId ? `任務 ID: ${jobId}` : '處理將在後台進行',
                                    duration: 5000,
                                  });

                                  // 保存任務信息
                                  setRegenerationJobId(jobId || 'pending');
                                  setRegenerationStartTime(Date.now());

                                  // 啟動自動刷新（每3秒檢查一次）
                                  const checkAndRefresh = async () => {
                              await checkDataAvailability();
                                    // 檢查圖譜是否已生成
                                    const isAvailable = await (async () => {
                                      if (!fileId) return false;
                                      try {
                                        const response = await getFileGraph(fileId);
                                        return response.success && response.data;
                                      } catch {
                                        return false;
                                      }
                                    })();

                                    if (isAvailable) {
                                      // 如果圖譜已生成，停止自動刷新
                                      clearInterval(interval);
                                      setRefreshInterval(null);
                                      setRegenerationJobId(null);
                                      setRegenerationStartTime(null);
                              await loadDataForMode('graph');
                                      toast.success('圖譜生成完成！', { duration: 3000 });
                                    }
                                  };

                                  const interval = setInterval(checkAndRefresh, 3000);
                                  setRefreshInterval(interval);

                                  // 立即檢查一次
                                  await checkAndRefresh();
                            } else {
                              setError(result.message || '重新生成失敗');
                                  setRegenerationJobId(null);
                                  setRegenerationStartTime(null);
                            }
                          } catch (err: any) {
                            setError(err.message || '重新生成失敗');
                                setRegenerationJobId(null);
                                setRegenerationStartTime(null);
                          } finally {
                            setLoading(false);
                          }
                        }}
                        disabled={loading || isDraftFile(fileId)}
                        className="mt-2 px-6 py-2.5 bg-blue-500 text-white text-base font-medium rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors shadow-md hover:shadow-lg"
                      >
                            {loading ? '提交中...' : '重新生成'}
                      </button>
                        </div>
                      );
                    })()}

                    {error && (
                      <p className="text-sm text-red-500 mt-3">{error}</p>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col" style={{ height: 'calc(100vh - 200px)' }}>
                    {/* 統計信息 */}
                    <div className="p-4 border-b bg-tertiary flex-shrink-0 theme-transition">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="text-lg font-semibold text-primary theme-transition">圖譜數據統計</h3>
                        <button
                          onClick={async () => {
                            setLoading(true);
                            try {
                              await checkDataAvailability();
                              await loadDataForMode('graph');
                            } finally {
                              setLoading(false);
                            }
                          }}
                          disabled={loading || isDraftFile(fileId)}
                          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-secondary border border-tertiary rounded-lg hover:bg-tertiary disabled:bg-secondary disabled:cursor-not-allowed transition-colors text-primary theme-transition"
                          title="刷新圖譜數據"
                        >
                          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                          <span>刷新</span>
                        </button>
                      </div>
                      <div className="grid grid-cols-3 gap-4">
                        <div className="bg-secondary p-3 rounded theme-transition">
                          <div className="text-sm text-tertiary theme-transition">實體數量</div>
                          <div className="text-2xl font-bold text-primary theme-transition">{graphData?.stats?.entities_count || graphData?.nodes?.length || 0}</div>
                        </div>
                        <div className="bg-secondary p-3 rounded theme-transition">
                          <div className="text-sm text-tertiary theme-transition">關係數量</div>
                          <div className="text-2xl font-bold text-primary theme-transition">{graphData?.stats?.relations_count || graphData?.edges?.length || 0}</div>
                        </div>
                        <div className="bg-secondary p-3 rounded theme-transition">
                          <div className="text-sm text-tertiary theme-transition">三元組數量</div>
                          <div className="text-2xl font-bold text-primary theme-transition">{graphData?.stats?.triples_count || graphData?.triples?.length || 0}</div>
                        </div>
                      </div>
                    </div>

                    {/* 知識圖譜視圖（包含圖形、節點列表、三元組列表） */}
                    <div className="flex-1 min-h-0" style={{ height: '100%' }}>
                      <KnowledgeGraphViewer
                        triples={graphData?.triples || []}
                        nodes={graphData?.nodes}
                        edges={graphData?.edges}
                        height={400}
                      />
                    </div>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
