import { useState, useEffect, useRef } from 'react';
import MermaidRenderer from './MermaidRenderer';
import { useLanguage } from '../contexts/languageContext';
import { FileText, Database, Network, Download } from 'lucide-react';
import { getFileVectors, getFileGraph, downloadFile, regenerateFileData } from '../lib/api';
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [textAvailable, setTextAvailable] = useState<boolean>(false);
  const [vectorAvailable, setVectorAvailable] = useState<boolean>(false);
  const [graphAvailable, setGraphAvailable] = useState<boolean>(false);
  const contentRef = useRef<HTMLDivElement>(null);

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

  const checkDataAvailability = async () => {
    if (!fileId) return;
    
    // 檢查文本內容
    setTextAvailable(!!content);

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
      setGraphAvailable(graphResponse.success && graphResponse.data && 
        (graphResponse.data.nodes?.length > 0 || 
         graphResponse.data.edges?.length > 0 ||
         graphResponse.data.triples?.length > 0 ||
         graphResponse.data.stats?.entities_count > 0 ||
         graphResponse.data.stats?.relations_count > 0 ||
         graphResponse.data.stats?.triples_count > 0));
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
      const parts = [];
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

        // 添加mermaid代码块
        parts.push({
          type: 'text',
          content: match[0]  // 保留原始的```mermaid```格式
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

      setMarkdownParts(parts);
    } catch (error) {
      console.error("解析Markdown内容时出错:", error);
      setMarkdownParts([{ type: 'text', content }]);
    }
  }, [content]);

  // 渲染普通Markdown文本
  const renderTextMarkdown = (markdown: string): string => {
    // 标题
    let html = markdown
      .replace(/#{6}\s(.+)/g, '<h6 class="text-lg font-bold mt-4 mb-2">$1</h6>')
      .replace(/#{5}\s(.+)/g, '<h5 class="text-lg font-bold mt-4 mb-2">$1</h5>')
      .replace(/#{4}\s(.+)/g, '<h4 class="text-xl font-bold mt-5 mb-2">$1</h4>')
      .replace(/#{3}\s(.+)/g, '<h3 class="text-xl font-bold mt-6 mb-3">$1</h3>')
      .replace(/#{2}\s(.+)/g, '<h2 class="text-2xl font-bold mt-7 mb-3">$1</h2>')
      .replace(/#{1}\s(.+)/g, '<h1 class="text-3xl font-bold mt-8 mb-4">$1</h1>');

    // 加粗
    html = html.replace(/\*\*(.+)\*\*/g, '<strong>$1</strong>');

    // 斜体
    html = html.replace(/\*(.+)\*/g, '<em>$1</em>');

    // 普通代码块（非mermaid）
    html = html.replace(/```([\s\S]*?)```/g, '<pre class="bg-gray-900 p-4 rounded-md overflow-x-auto my-4 text-sm"><code>$1</code></pre>');

    // 行内代码
    html = html.replace(/`(.+?)`/g, '<code class="bg-gray-900 px-1.5 py-0.5 rounded text-sm">$1</code>');

    // 列表
    html = html.replace(/^\-\s(.+)$/gm, '<li class="list-disc ml-5 mb-1">$1</li>');

    // 水平线
    html = html.replace(/^---$/gm, '<hr class="my-6 border-gray-700">');

    // 段落
    html = html.replace(/^(?!<h|<ul|<ol|<li|<pre|<hr)(.+)$/gm, '<p class="mb-4">$1</p>');

    return html;
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
              className="p-1 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
              aria-label={t('markdownViewer.download')}
              title="下載文件"
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
                        <div dangerouslySetInnerHTML={{ __html: renderTextMarkdown(part.content) }} />
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
                    {fileId && (
                      <button
                        onClick={async () => {
                          setLoading(true);
                          setError(null);
                          try {
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
                        disabled={loading}
                        className="mt-2 px-6 py-2.5 bg-blue-500 text-white text-base font-medium rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors shadow-md hover:shadow-lg"
                      >
                        {loading ? '生成中...' : '重新生成'}
                      </button>
                    )}
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
                    {fileId && (
                      <button
                        onClick={async () => {
                          setLoading(true);
                          setError(null);
                          try {
                            const result = await regenerateFileData(fileId, 'graph');
                            if (result.success) {
                              // 重新檢查數據可用性
                              await checkDataAvailability();
                              // 重新加載數據
                              await loadDataForMode('graph');
                            } else {
                              setError(result.message || '重新生成失敗');
                            }
                          } catch (err: any) {
                            setError(err.message || '重新生成失敗');
                          } finally {
                            setLoading(false);
                          }
                        }}
                        disabled={loading}
                        className="mt-2 px-6 py-2.5 bg-blue-500 text-white text-base font-medium rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors shadow-md hover:shadow-lg"
                      >
                        {loading ? '生成中...' : '重新生成'}
                      </button>
                    )}
                    {error && (
                      <p className="text-sm text-red-500 mt-3">{error}</p>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col" style={{ height: 'calc(100vh - 200px)' }}>
                    {/* 統計信息 */}
                    <div className="p-4 border-b bg-tertiary flex-shrink-0 theme-transition">
                      <h3 className="text-lg font-semibold mb-2 text-primary theme-transition">圖譜數據統計</h3>
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

                    {/* 圖形視圖（上半部分） */}
                    <div className="flex-shrink-0 border-b" style={{ height: '480px' }}>
                      <KnowledgeGraphViewer
                        triples={graphData?.triples || []}
                        nodes={graphData?.nodes}
                        edges={graphData?.edges}
                        height={480}
                      />
                    </div>

                    {/* 三元組列表（下半部分） */}
                    <div className="flex-1 min-h-0 overflow-auto p-4">
                      <h3 className="text-lg font-semibold mb-3 text-primary theme-transition">三元組列表</h3>
                      {graphData?.triples && graphData.triples.length > 0 ? (
                        <div className="space-y-2">
                          {graphData.triples.map((triple: any, index: number) => (
                            <div key={index} className="bg-tertiary p-3 rounded border border-primary theme-transition hover:bg-hover transition-colors">
                              <div className="text-sm text-primary theme-transition">
                                <span className="font-semibold text-blue-400">
                                  {triple.subject || triple.subject_type || 'Unknown'}
                                </span>
                                {triple.subject_type && (
                                  <span className="text-xs text-tertiary ml-1 theme-transition">({triple.subject_type})</span>
                                )}
                                {' → '}
                                <span className="text-green-400 font-medium">{triple.relation}</span>
                                {' → '}
                                <span className="font-semibold text-purple-400">
                                  {triple.object || triple.object_type || 'Unknown'}
                                </span>
                                {triple.object_type && (
                                  <span className="text-xs text-tertiary ml-1 theme-transition">({triple.object_type})</span>
                                )}
                              </div>
                              {triple.confidence !== undefined && (
                                <div className="text-xs text-tertiary mt-1 theme-transition">
                                  置信度: {typeof triple.confidence === 'number' ? triple.confidence.toFixed(2) : triple.confidence}
                                </div>
                              )}
                              {triple.context && (
                                <div className="text-xs text-tertiary opacity-75 mt-1 italic truncate theme-transition">
                                  上下文: {triple.context}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : graphData?.edges && graphData.edges.length > 0 ? (
                        // 如果沒有 triples，從 edges 構建顯示
                        <div className="space-y-2">
                          {graphData.edges.map((edge: any, index: number) => {
                            const from = edge._from || edge.from || edge.source || '';
                            const to = edge._to || edge.to || edge.target || '';
                            const type = edge.type || edge.label || edge.relation || '';
                            return (
                              <div key={index} className="bg-tertiary p-3 rounded border border-primary theme-transition hover:bg-hover transition-colors">
                                <div className="text-sm text-primary theme-transition">
                                  <span className="font-semibold text-blue-400">
                                    {from.split('/').pop() || from}
                                  </span>
                                  {' → '}
                                  <span className="text-green-400 font-medium">{type}</span>
                                  {' → '}
                                  <span className="font-semibold text-purple-400">
                                    {to.split('/').pop() || to}
                                  </span>
                                </div>
                                {edge.confidence !== undefined && (
                                  <div className="text-xs text-tertiary mt-1 theme-transition">
                                    置信度: {typeof edge.confidence === 'number' ? edge.confidence.toFixed(2) : edge.confidence}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="text-center py-8 text-tertiary theme-transition">
                          <p>暫無三元組數據</p>
                      </div>
                    )}
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
