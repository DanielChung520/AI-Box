/**
 * 代碼功能說明: 文件預覽組件
 * 創建日期: 2025-12-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-09
 */

import React, { useState, useEffect } from 'react';
import { X, Loader2, FileText, Database, Network, Download } from 'lucide-react';
import { previewFile, getFileVectors, getFileGraph, downloadFile, FileMetadata, regenerateFileData, API_URL } from '../lib/api';
import PDFViewer from './PDFViewer';
import MarkdownViewer from './MarkdownViewer';
import KnowledgeGraphViewer from './KnowledgeGraphViewer';

interface FilePreviewProps {
  file: FileMetadata;
  isOpen: boolean;
  onClose: () => void;
}

type PreviewMode = 'text' | 'vector' | 'graph';

export default function FilePreview({ file, isOpen, onClose }: FilePreviewProps) {
  const [mode, setMode] = useState<PreviewMode>('text'); // 默認為文件模式
  const [content, setContent] = useState<string>('');
  const [vectorData, setVectorData] = useState<any>(null);
  const [graphData, setGraphData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isTruncated, setIsTruncated] = useState(false);
  const [textAvailable, setTextAvailable] = useState<boolean>(false);
  const [vectorAvailable, setVectorAvailable] = useState<boolean>(false);
  const [graphAvailable, setGraphAvailable] = useState<boolean>(false);

  useEffect(() => {
    if (isOpen && file) {
      setMode('text'); // 重置為文件模式
      checkDataAvailability();
      loadDataForMode('text');
    }
  }, [isOpen, file]);

  const checkDataAvailability = async () => {
    // 檢查文本內容
    try {
      const textResponse = await previewFile(file.file_id);
      setTextAvailable(!!(textResponse.success && textResponse.data?.content));
    } catch (e) {
      setTextAvailable(false);
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
      setGraphAvailable(graphResponse.success && graphResponse.data && 
        (graphResponse.data.nodes?.length > 0 || 
         graphResponse.data.edges?.length > 0 ||
         graphResponse.data.triples?.length > 0 ||
         graphResponse.data.stats?.entities_count > 0 ||
         graphResponse.data.stats?.relations_count > 0 ||
         graphResponse.data.stats?.triples_count > 0));
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
    try {
      const response = await previewFile(file.file_id);
      if (response.success && response.data) {
        setContent(response.data.content);
        setIsTruncated(response.data.is_truncated);
      } else {
        setError('預覽失敗');
      }
    } catch (err: any) {
      setError(err.message || '預覽失敗');
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
        if (file.file_type === 'application/pdf') {
          // 構建文件下載 URL
          const fileUrl = `${API_URL}/files/${file.file_id}/download`;
          return <PDFViewer fileUrl={fileUrl} fileName={file.filename} />;
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
          return (
            <div className="text-center py-8 text-gray-500">
              <Database className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-semibold">未成功生成</p>
              <p className="text-sm mt-2 mb-4">向量數據尚未生成或無法加載</p>
              <button
                onClick={async () => {
                  setLoading(true);
                  setError(null);
                  try {
                    const result = await regenerateFileData(file.file_id, 'vector');
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
          return (
            <div className="text-center py-8 text-gray-500">
              <Network className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-semibold">未成功生成</p>
              <p className="text-sm mt-2 mb-4">圖譜數據尚未生成或無法加載</p>
              <button
                onClick={async () => {
                  setLoading(true);
                  setError(null);
                  try {
                    const result = await regenerateFileData(file.file_id, 'graph');
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
              <h3 className="text-lg font-semibold mb-2">圖譜數據統計</h3>
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
