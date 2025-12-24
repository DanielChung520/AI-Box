/**
 * 代碼功能說明: 文件預覽組件
 * 創建日期: 2025-12-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-13
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Loader2, FileText, Database, Network, Download, RefreshCw, Edit } from 'lucide-react';
import { toast } from 'sonner';
import { previewFile, getFileVectors, getFileGraph, getProcessingStatus, getKgChunkStatus, downloadFile, FileMetadata, regenerateFileData } from '../lib/api';
import PDFViewer from './PDFViewer';
import MarkdownViewer from './MarkdownViewer';
import DOCXViewer from './DOCXViewer';
import ExcelViewer from './ExcelViewer';
import KnowledgeGraphViewer from './KnowledgeGraphViewer';

interface FilePreviewProps {
  file: FileMetadata;
  isOpen: boolean;
  onClose: () => void;
}

type PreviewMode = 'text' | 'vector' | 'graph';

export default function FilePreview({ file, isOpen, onClose }: FilePreviewProps) {
  const navigate = useNavigate();
  const [mode, setMode] = useState<PreviewMode>('text'); // 默認為文件模式
  const [content, setContent] = useState<string>('');
  const [vectorData, setVectorData] = useState<any>(null);
  const [graphData, setGraphData] = useState<any>(null);
  const [processingStatus, setProcessingStatus] = useState<any>(null);
  const [kgChunkStatus, setKgChunkStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isTruncated, setIsTruncated] = useState(false);
  const [textAvailable, setTextAvailable] = useState<boolean>(false);
  const [vectorAvailable, setVectorAvailable] = useState<boolean>(false);
  const [graphAvailable, setGraphAvailable] = useState<boolean>(false);
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null);
  const [regenerationJobId, setRegenerationJobId] = useState<string | null>(null);
  const [regenerationStartTime, setRegenerationStartTime] = useState<number | null>(null);

  const handleOpenInIEE = () => {
    // 檢查文件類型是否為 Markdown
    const fileName = file.filename.toLowerCase();
    const isMarkdown = fileName.endsWith('.md') || fileName.endsWith('.markdown');
    if (!isMarkdown) {
      toast.error('IEE 編輯器目前僅支持 Markdown 文件');
      return;
    }
    // 關閉預覽窗口
    onClose();
    // 導航到 IEE 編輯器頁面
    navigate(`/iee-editor?fileId=${encodeURIComponent(file.file_id)}`);
  };

  useEffect(() => {
    if (isOpen && file) {
      setMode('text'); // 重置為文件模式
      checkDataAvailability();
      loadDataForMode('text');
      // 重置任務狀態
      setRegenerationJobId(null);
      setRegenerationStartTime(null);
    }

    // 清理刷新定時器
    return () => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
        setRefreshInterval(null);
      }
    };
  }, [isOpen, file]);

  const refreshProcessingStatus = async () => {
    try {
      const resp = await getProcessingStatus(file.file_id);
      if (resp?.success && resp.data) {
        setProcessingStatus(resp.data);
      }
    } catch {
      // ignore
    }
  };

  const refreshKgChunkStatus = async () => {
    try {
      const resp = await getKgChunkStatus(file.file_id);
      if (resp?.success && resp.data) {
        setKgChunkStatus(resp.data);
      }
    } catch {
      // ignore
    }
  };

  // 修改時間：2025-12-13 (UTC+8) - 當向量/圖譜未生成時，輪詢處理狀態以顯示「產生中」
  useEffect(() => {
    if (!isOpen) return;
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
  }, [isOpen, mode, vectorAvailable, graphAvailable]);

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
        <div className="text-xs text-gray-600 mb-2">
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
                <div className="text-[10px] text-gray-500 text-center">{idx}</div>
              </div>
            );
          })}
        </div>

        {kgChunkStatus?.errors && Object.keys(kgChunkStatus.errors).length > 0 && (
          <div className="mt-3 text-xs text-gray-600">
            <div className="font-medium text-orange-600 mb-1">分塊錯誤（最近幾筆）</div>
            <ul className="space-y-1 max-h-24 overflow-auto bg-gray-50 border border-gray-200 rounded p-2">
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

  // 判斷文件類型是否支持 previewFile API（不支持的文件類型使用專門的 Viewer）
  const isFileTypeWithCustomViewer = (fileType: string, filename: string): boolean => {
    const lowerFilename = filename.toLowerCase();
    return (
      // PDF
      fileType === 'application/pdf' || lowerFilename.endsWith('.pdf') ||
      // DOCX/DOC
      fileType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
      fileType === 'application/msword' ||
      lowerFilename.endsWith('.docx') || lowerFilename.endsWith('.doc') ||
      // XLSX/XLS
      fileType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
      fileType === 'application/vnd.ms-excel' ||
      lowerFilename.endsWith('.xlsx') || lowerFilename.endsWith('.xls')
    );
  };

  const checkDataAvailability = async () => {
    // 檢查文本內容
    // 對於有專門 Viewer 的文件類型（PDF、DOCX、XLSX），不需要調用 previewFile API
    if (isFileTypeWithCustomViewer(file.file_type, file.filename)) {
      // 這些文件類型有專門的 Viewer 組件，直接設置為可用
      setTextAvailable(true);
    } else {
      // 其他文件類型（如 Markdown、TXT）使用 previewFile API
      try {
        const textResponse = await previewFile(file.file_id);
        setTextAvailable(!!(textResponse.success && textResponse.data?.content));
      } catch (e) {
        setTextAvailable(false);
      }
    }

    // 檢查向量數據
    try {
      const vectorResponse = await getFileVectors(file.file_id, 1, 0);
      setVectorAvailable(vectorResponse.success && vectorResponse.data &&
        (vectorResponse.data.vectors?.length > 0 ||
         vectorResponse.data.stats?.vector_count > 0 ||
         vectorResponse.data.total > 0));
    } catch (e) {
      setVectorAvailable(false);
    }

    // 檢查圖譜數據
    try {
      const graphResponse = await getFileGraph(file.file_id, 1, 0);
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
    } catch (e) {
      setGraphAvailable(false);
    }
  };

  const loadDataForMode = async (targetMode: PreviewMode) => {
    setLoading(true);
    setError(null);

    try {
      switch (targetMode) {
        case 'text':
          await loadPreview();
          break;

        case 'vector':
          const vectorResponse = await getFileVectors(file.file_id, 100, 0);
          if (vectorResponse.success && vectorResponse.data) {
            setVectorData(vectorResponse.data);
          } else {
            setError('無法加載向量數據');
          }
          break;

        case 'graph':
          const graphResponse = await getFileGraph(file.file_id, 100, 0);
          if (graphResponse.success && graphResponse.data) {
            setGraphData(graphResponse.data);
          } else {
            setError('無法加載圖譜數據');
          }
          break;
      }
    } catch (err: any) {
      setError(err.message || '加載數據失敗');
    } finally {
      setLoading(false);
    }
  };

  const handleModeChange = (newMode: PreviewMode) => {
    setMode(newMode);
    setError(null); // 切換模式時清除錯誤狀態
    loadDataForMode(newMode);
  };

  const loadPreview = async () => {
    // 對於有專門 Viewer 的文件類型，不需要加載預覽內容
    if (isFileTypeWithCustomViewer(file.file_type, file.filename)) {
      // 這些文件類型由專門的 Viewer 組件處理，不需要預覽內容
      setContent('');
      setIsTruncated(false);
      return;
    }

    // 其他文件類型使用 previewFile API
    try {
      const response = await previewFile(file.file_id);
      if (response.success && response.data) {
        setContent(response.data.content);
        setIsTruncated(response.data.is_truncated);
      } else {
        setError('預覽失敗');
      }
    } catch (err: any) {
      // 對於不支持預覽的文件類型，不顯示錯誤（因為有專門的 Viewer）
      if (err.message?.includes('不支持預覽此文件類型')) {
        setTextAvailable(true); // 設置為可用，讓專門的 Viewer 處理
        setContent('');
      } else {
        setError(err.message || '預覽失敗');
      }
    }
  };

  if (!isOpen) return null;

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      );
    }

    // 注意：錯誤狀態不會覆蓋"未成功生成"的顯示
    // 因為在 vector 和 graph 模式下，如果數據不可用，會顯示"重新生成"按鈕
    // 錯誤消息會在按鈕下方顯示

    switch (mode) {
      case 'text':
        if (!textAvailable) {
          return (
            <div className="text-center py-8 text-gray-500">
              <FileText className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg">未成功生成</p>
              <p className="text-sm mt-2">文本內容尚未生成或無法加載</p>
            </div>
          );
        }
        // PDF 文件使用 PDFViewer
        if (file.file_type === 'application/pdf' || file.filename.toLowerCase().endsWith('.pdf')) {
          return <PDFViewer fileId={file.file_id} fileName={file.filename} />;
        }

        // DOCX 文件使用 DOCXViewer
        if (
          file.file_type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
          file.file_type === 'application/msword' ||
          file.filename.toLowerCase().endsWith('.docx') ||
          file.filename.toLowerCase().endsWith('.doc')
        ) {
          return <DOCXViewer fileId={file.file_id} fileName={file.filename} />;
        }

        // XLSX 文件使用 ExcelViewer
        if (
          file.file_type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
          file.file_type === 'application/vnd.ms-excel' ||
          file.filename.toLowerCase().endsWith('.xlsx') ||
          file.filename.toLowerCase().endsWith('.xls')
        ) {
          return <ExcelViewer fileId={file.file_id} fileName={file.filename} />;
        }

        // Markdown 文件使用 MarkdownViewer
        if (file.file_type === 'text/markdown' || file.filename.endsWith('.md')) {
          return <MarkdownViewer content={content} fileName={file.filename} fileId={file.file_id} />;
        }

        // 其他文本文件直接显示
        return (
          <div className="p-4">
            <pre className="whitespace-pre-wrap font-mono text-sm bg-gray-50 p-4 rounded max-h-[60vh] overflow-auto">
              {content}
            </pre>
            {isTruncated && (
              <div className="mt-2 text-sm text-gray-500">
                文件內容已截斷（僅顯示前 100KB）
              </div>
            )}
          </div>
        );

      case 'vector':
        if (!vectorAvailable) {
          const vectorStage = processingStatus?.vectorization?.status || processingStatus?.status;
          const vectorProgress = processingStatus?.vectorization?.progress ?? 0;
          const vectorMessage =
            processingStatus?.vectorization?.message ||
            processingStatus?.message ||
            '向量處理中，請稍候';
          const isVectorRunning = vectorStage === 'processing' || vectorStage === 'in_progress' || vectorStage === 'pending';
          const isVectorFailed = vectorStage === 'failed';
          return (
            <div className="text-center py-8 text-gray-500">
              <Database className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-semibold">未成功生成</p>
              <p className="text-sm mt-2 mb-4">向量數據尚未生成或無法加載</p>
              {isVectorRunning && !isVectorFailed ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-center gap-2 text-sm text-gray-600">
                    <RefreshCw className="w-5 h-5 animate-spin text-blue-500" />
                    <span className="font-medium">向量產生中... ({vectorProgress}%)</span>
                  </div>
                  <p className="text-xs text-gray-500">{vectorMessage}</p>
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
              ) : (
              <button
                onClick={async () => {
                  setLoading(true);
                  setError(null);
                  try {
                    const result = await regenerateFileData(file.file_id, 'vector');
                    if (result.success) {
                      // 修改時間：2025-12-12 - 添加成功提示，顯示任務已提交
                      const jobId = result.data?.job_id;
                      const message = result.message || '向量重新生成已提交到隊列';
                      toast.success(message, {
                        description: jobId ? `任務 ID: ${jobId}` : '處理將在後台進行',
                        duration: 5000,
                      });

                      // 重新檢查數據可用性
                      await checkDataAvailability();
                      // 重新加載數據
                      await loadDataForMode('vector');
                    } else {
                      const errorMsg = result.message || '重新生成失敗';
                      setError(errorMsg);
                      toast.error(errorMsg);
                    }
                  } catch (err: any) {
                    const errorMsg = err.message || '重新生成失敗';
                    setError(errorMsg);
                    toast.error(errorMsg);
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
          );
        }
        const vectorCount = vectorData?.stats?.vector_count || vectorData?.total || vectorData?.vectors?.length || 0;
        const collectionName = vectorData?.stats?.collection_name;
        return (
          <div className="p-4">
            <div className="mb-4">
              <h3 className="text-lg font-semibold mb-2">向量數據統計</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-3 rounded">
                  <div className="text-sm text-gray-600">向量數量</div>
                  <div className="text-2xl font-bold">{vectorCount}</div>
                </div>
                {collectionName && (
                  <div className="bg-gray-50 p-3 rounded">
                    <div className="text-sm text-gray-600">集合名稱</div>
                    <div className="text-sm font-mono truncate">{collectionName}</div>
                  </div>
                )}
              </div>
            </div>
            {vectorData?.vectors && vectorData.vectors.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-2">向量列表（顯示前 {vectorData.vectors.length} 個，共 {vectorData.total || vectorCount} 個）</h3>
                <div className="space-y-2 max-h-[40vh] overflow-auto">
                  {vectorData.vectors.map((vector: any, index: number) => (
                    <div key={index} className="bg-gray-50 p-3 rounded">
                      <div className="text-sm font-mono text-gray-600 mb-1">
                        ID: {vector.id || vector._id || `vector_${index}`}
                      </div>
                      {vector.metadata && (
                        <div className="text-xs text-gray-500 mb-2">
                          <div className="font-semibold mb-1">元数据:</div>
                          {JSON.stringify(vector.metadata, null, 2)}
                        </div>
                      )}
                      {vector.document && (
                        <div className="text-sm text-gray-700 mt-2 mb-2 p-2 bg-white rounded border">
                          <div className="font-semibold mb-1">文档内容:</div>
                          <pre className="whitespace-pre-wrap text-xs max-h-40 overflow-auto">
                            {vector.document}
                          </pre>
                        </div>
                      )}
                      {vector.embedding && (
                        <div className="text-xs text-gray-400 mt-1">
                          向量維度: {vector.embedding.length}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );

      case 'graph':
        if (!graphAvailable) {
          // 檢查是否有正在進行的任務
          const hasActiveTask = regenerationJobId !== null;
          // 檢查任務是否超時（超過5分鐘認為失敗）
          const isTaskTimeout = regenerationStartTime !== null &&
            Date.now() - regenerationStartTime > 5 * 60 * 1000;
          const graphStage = processingStatus?.kg_extraction?.status || processingStatus?.status;
          const graphProgress = processingStatus?.kg_extraction?.progress ?? 0;
          const totalChunks = processingStatus?.kg_extraction?.total_chunks;
          const completedChunks = processingStatus?.kg_extraction?.completed_chunks?.length ?? 0;
          const failedChunks = processingStatus?.kg_extraction?.failed_chunks?.length ?? 0;
          const failedPermanentChunks = processingStatus?.kg_extraction?.failed_permanent_chunks?.length ?? 0;
          const nextJobId = processingStatus?.kg_extraction?.next_job_id;
          const graphMessage =
            processingStatus?.kg_extraction?.message ||
            processingStatus?.message ||
            '圖譜處理中，請稍候';
          const isGraphRunning = graphStage === 'processing' || graphStage === 'in_progress' || graphStage === 'pending';
          const isGraphFailed = graphStage === 'failed';

          return (
            <div className="text-center py-8 text-gray-500">
              <Network className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-semibold">未成功生成</p>
              <p className="text-sm mt-2 mb-4">圖譜數據尚未生成或無法加載</p>

              {hasActiveTask && !isTaskTimeout ? (
                // 任務進行中：顯示提示和刷新圖標
                <div className="space-y-3">
                  <div className="flex flex-col items-center gap-3">
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <RefreshCw className="w-5 h-5 animate-spin text-blue-500" />
                      <span className="font-medium">任務已提交，正在處理中...</span>
                    </div>
                    <p className="text-xs text-gray-500">
                      {regenerationJobId ? `任務 ID: ${regenerationJobId}` : '請耐心等候，系統正在生成圖譜'}
                    </p>
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
                      className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-50 text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-100 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
                    >
                      <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                      <span>手動刷新</span>
                    </button>
                  </div>
                </div>
              ) : isGraphRunning && !isGraphFailed ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-center gap-2 text-sm text-gray-600">
                    <RefreshCw className="w-5 h-5 animate-spin text-blue-500" />
                    <span className="font-medium">圖譜產生中... ({graphProgress}%)</span>
                  </div>
                  <p className="text-xs text-gray-500">{graphMessage}</p>
                  {typeof totalChunks === 'number' && totalChunks > 0 && (
                    <div className="text-xs text-gray-600 space-y-1">
                      <div>分塊進度：{completedChunks}/{totalChunks}</div>
                      {(failedChunks > 0 || failedPermanentChunks > 0) && (
                        <div className="text-orange-600">
                          失敗分塊：{failedChunks}（永久失敗：{failedPermanentChunks}）
                        </div>
                      )}
                      {nextJobId && (
                        <div className="text-gray-500">已排程續跑：{nextJobId}</div>
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
                    className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-50 text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-100 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors mx-auto"
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
                  setLoading(true);
                  setError(null);
                  try {
                    const result = await regenerateFileData(file.file_id, 'graph');
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
                              try {
                                const response = await getFileGraph(file.file_id);
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
                          const errorMsg = result.message || '重新生成失敗';
                          setError(errorMsg);
                          setRegenerationJobId(null);
                          setRegenerationStartTime(null);
                          toast.error(errorMsg);
                    }
                  } catch (err: any) {
                        const errorMsg = err.message || '重新生成失敗';
                        setError(errorMsg);
                        setRegenerationJobId(null);
                        setRegenerationStartTime(null);
                        toast.error(errorMsg);
                  } finally {
                    setLoading(false);
                  }
                }}
                disabled={loading}
                className="mt-2 px-6 py-2.5 bg-blue-500 text-white text-base font-medium rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors shadow-md hover:shadow-lg"
              >
                    {loading ? '提交中...' : '重新生成'}
              </button>
                </div>
              )}

              {error && (
                <p className="text-sm text-red-500 mt-3">{error}</p>
              )}
            </div>
          );
        }
        const stats = graphData?.stats || {};
        const entitiesCount = stats.entities_count || graphData?.nodes?.length || 0;
        const relationsCount = stats.relations_count || graphData?.edges?.length || 0;
        const triplesCount = stats.triples_count || graphData?.triples?.length || 0;

        // 提取三元組數據（優先使用 triples，否則從 nodes 和 edges 構建）
        const triples = graphData?.triples || [];

        return (
          <div className="flex flex-col" style={{ height: 'calc(100vh - 200px)' }}>
            {/* 統計信息 */}
            <div className="p-4 border-b bg-gray-50 flex-shrink-0">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-semibold">圖譜數據統計</h3>
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
                  disabled={loading}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors"
                  title="刷新圖譜數據"
                >
                  <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                  <span>刷新</span>
                </button>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-white p-3 rounded shadow-sm">
                  <div className="text-sm text-gray-600">實體數量</div>
                  <div className="text-2xl font-bold">{entitiesCount}</div>
                </div>
                <div className="bg-white p-3 rounded shadow-sm">
                  <div className="text-sm text-gray-600">關係數量</div>
                  <div className="text-2xl font-bold">{relationsCount}</div>
                </div>
                <div className="bg-white p-3 rounded shadow-sm">
                  <div className="text-sm text-gray-600">三元組數量</div>
                  <div className="text-2xl font-bold">{triplesCount}</div>
                </div>
              </div>
            </div>

            {/* 圖形視圖（上半部分） */}
            <div className="flex-shrink-0 border-b" style={{ height: '480px' }}>
              <KnowledgeGraphViewer
                triples={triples}
                nodes={graphData?.nodes}
                edges={graphData?.edges}
                height={480}
              />
            </div>

            {/* 三元組列表（下半部分） */}
            <div className="flex-1 min-h-0 overflow-auto p-4">
              <h3 className="text-lg font-semibold mb-3">三元組列表</h3>
              {triples.length > 0 ? (
                <div className="space-y-2">
                  {triples.map((triple: any, index: number) => (
                    <div key={index} className="bg-gray-50 p-3 rounded border border-gray-200 hover:bg-gray-100 transition-colors">
                      <div className="text-sm">
                        <span className="font-semibold text-blue-600">
                          {triple.subject || triple.subject_type || 'Unknown'}
                        </span>
                        {triple.subject_type && (
                          <span className="text-xs text-gray-500 ml-1">({triple.subject_type})</span>
                        )}
                        {' → '}
                        <span className="text-green-600 font-medium">{triple.relation}</span>
                        {' → '}
                        <span className="font-semibold text-purple-600">
                          {triple.object || triple.object_type || 'Unknown'}
                        </span>
                        {triple.object_type && (
                          <span className="text-xs text-gray-500 ml-1">({triple.object_type})</span>
                        )}
                      </div>
                      {triple.confidence !== undefined && (
                        <div className="text-xs text-gray-500 mt-1">
                          置信度: {typeof triple.confidence === 'number' ? triple.confidence.toFixed(2) : triple.confidence}
                        </div>
                      )}
                      {triple.context && (
                        <div className="text-xs text-gray-400 mt-1 italic truncate">
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
                      <div key={index} className="bg-gray-50 p-3 rounded border border-gray-200 hover:bg-gray-100 transition-colors">
                        <div className="text-sm">
                          <span className="font-semibold text-blue-600">
                            {from.split('/').pop() || from}
                          </span>
                          {' → '}
                          <span className="text-green-600 font-medium">{type}</span>
                          {' → '}
                          <span className="font-semibold text-purple-600">
                            {to.split('/').pop() || to}
                          </span>
                        </div>
                        {edge.confidence !== undefined && (
                          <div className="text-xs text-gray-500 mt-1">
                            置信度: {typeof edge.confidence === 'number' ? edge.confidence.toFixed(2) : edge.confidence}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <p>暫無三元組數據</p>
              </div>
            )}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b gap-4">
          <h2 className="text-lg font-semibold truncate flex-shrink min-w-0 max-w-[40%]">{file.filename}</h2>
          <div className="flex items-center gap-3 flex-shrink-0">
            {/* 模式切換按鈕組（文件、向量、圖譜） */}
            <div className="flex gap-0.5 border border-gray-300 rounded-lg p-0.5 bg-gray-100 shadow-sm">
              <button
                onClick={() => handleModeChange('text')}
                className={`px-3 py-1.5 rounded-md text-sm flex items-center gap-1.5 transition-all ${
                  mode === 'text'
                    ? 'bg-blue-500 text-white shadow-md font-medium'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
                title="文件模式"
              >
                <FileText className="w-4 h-4" />
                <span>文件</span>
                {!textAvailable && mode === 'text' && <span className="text-xs opacity-75">(未生成)</span>}
              </button>
              <button
                onClick={() => handleModeChange('vector')}
                className={`px-3 py-1.5 rounded-md text-sm flex items-center gap-1.5 transition-all ${
                  mode === 'vector'
                    ? 'bg-blue-500 text-white shadow-md font-medium'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
                title="向量模式"
              >
                <Database className="w-4 h-4" />
                <span>向量</span>
                {!vectorAvailable && mode === 'vector' && <span className="text-xs opacity-75">(未生成)</span>}
              </button>
              <button
                onClick={() => handleModeChange('graph')}
                className={`px-3 py-1.5 rounded-md text-sm flex items-center gap-1.5 transition-all ${
                  mode === 'graph'
                    ? 'bg-blue-500 text-white shadow-md font-medium'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
                title="圖譜模式"
              >
                <Network className="w-4 h-4" />
                <span>圖譜</span>
                {!graphAvailable && mode === 'graph' && <span className="text-xs opacity-75">(未生成)</span>}
              </button>
            </div>
            {/* IEE 編輯器按鈕（僅 Markdown 文件顯示） */}
            {(file.filename.toLowerCase().endsWith('.md') || file.filename.toLowerCase().endsWith('.markdown')) && (
              <button
                onClick={handleOpenInIEE}
                className="p-2 hover:bg-blue-100 rounded transition-colors text-blue-600"
                title="使用 IEE 編輯器打開"
              >
                <Edit className="w-5 h-5" />
              </button>
            )}
            {/* 下載按鈕 */}
            <button
              onClick={async () => {
                try {
                  const blob = await downloadFile(file.file_id);
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = file.filename;
                  document.body.appendChild(a);
                  a.click();
                  window.URL.revokeObjectURL(url);
                  document.body.removeChild(a);
                } catch (err: any) {
                  alert(`下載失敗: ${err.message}`);
                }
              }}
              className="p-2 hover:bg-gray-100 rounded transition-colors"
              title="下載文件"
            >
              <Download className="w-5 h-5" />
            </button>
            {/* 關閉按鈕 */}
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded transition-colors"
              title="關閉"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto">
          {renderContent()}
        </div>

        {/* Footer */}
        <div className="p-4 border-t text-sm text-gray-500">
          <div className="flex justify-between">
            <span>文件大小: {file.file_size} bytes</span>
            <span>類型: {file.file_type}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
