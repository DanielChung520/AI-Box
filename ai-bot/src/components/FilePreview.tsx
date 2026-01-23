/**
 * 代碼功能說明: 文件預覽組件
 * 創建日期: 2025-12-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-21 12:30 UTC+8
 */

import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Loader2, FileText, Database, Network, Download, RefreshCw, Edit, ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
import Markdown from 'markdown-to-jsx';
import MermaidRenderer from './MermaidRenderer';
import { previewFile, getFileVectors, getFileGraph, getProcessingStatus, getKgChunkStatus, downloadFile, FileMetadata, regenerateFileData, getSimilarVectors } from '../lib/api';
import PDFViewer from './PDFViewer';
import DOCXViewer from './DOCXViewer';
import ExcelViewer from './ExcelViewer';
import KnowledgeGraphViewer from './KnowledgeGraphViewer';
import { useFileEditing } from '../contexts/fileEditingContext';

// 修改時間：2026-01-21 12:25 UTC+8 - Vector Point 卡片組件（類似 Qdrant Dashboard 的 Open panel）
interface VectorPointCardProps {
  point: any;
  index: number;
  collectionName?: string; // 修改時間：2026-01-21 13:10 UTC+8 - 添加 collectionName 用於生成 Qdrant Dashboard 鏈接
  fileId?: string; // 修改時間：2026-01-21 13:30 UTC+8 - 添加 fileId 用於相似度搜索
}

function VectorPointCard({ point, index, collectionName, fileId: propFileId }: VectorPointCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showModal, setShowModal] = useState(false); // 修改時間：2026-01-21 13:10 UTC+8 - 添加 modal 狀態
  const [viewMode, setViewMode] = useState<'details' | 'graph' | 'similar'>('details'); // 修改時間：2026-01-21 13:40 UTC+8 - 添加 similar 視圖模式
  const [similarVectors, setSimilarVectors] = useState<any[] | null>(null); // 修改時間：2026-01-21 13:30 UTC+8 - 相似向量結果
  const [loadingSimilar, setLoadingSimilar] = useState(false); // 修改時間：2026-01-21 13:30 UTC+8 - 加載狀態

  const pointId = point.id || point._id || `point_${index}`;
  const payload = point.payload || {};
  const vector = point.vector;

  // 從 payload 提取常見字段
  const chunkText = payload.chunk_text || payload.text || payload.document || '';
  const chunkIndex = payload.chunk_index !== undefined ? payload.chunk_index : payload.index;
  const fileId = propFileId || payload.file_id; // 修改時間：2026-01-21 13:30 UTC+8 - 優先使用 prop 傳入的 fileId
  const taskId = payload.task_id;

  // 修改時間：2026-01-21 13:30 UTC+8 - 查找相似向量
  const handleFindSimilar = async () => {
    if (!fileId || !pointId) {
      toast.error('無法查找相似向量：缺少必要信息');
      return;
    }

    // 如果還沒有打開 modal，先打開
    if (!showModal) {
      setShowModal(true);
    }

    setLoadingSimilar(true);
    setSimilarVectors(null);
    setViewMode('similar'); // 切換到相似向量視圖
    try {
      const response = await getSimilarVectors(fileId, pointId, 10);
      if (response.success && response.data?.similar_vectors) {
        setSimilarVectors(response.data.similar_vectors);
        toast.success(`找到 ${response.data.similar_vectors.length} 個相似向量`);
      } else {
        toast.error(response.message || '查找相似向量失敗');
        setViewMode('details'); // 失敗時回到 details 視圖
      }
    } catch (error: any) {
      console.error('[VectorPointCard] Failed to find similar vectors:', error);
      toast.error(`查找相似向量失敗: ${error.message || '未知錯誤'}`);
      setViewMode('details'); // 失敗時回到 details 視圖
    } finally {
      setLoadingSimilar(false);
    }
  };

  // 修改時間：2026-01-21 13:10 UTC+8 - 生成 Qdrant Dashboard 鏈接
  // 注意：Qdrant Dashboard 可能無法直接通過 URL 打開特定 point
  // 所以我們提供 collection 視圖，用戶可以在那裡選擇 point
  const qdrantCollectionUrl = collectionName
    ? `http://localhost:6333/dashboard#/collections/${collectionName}`
    : null;
  const qdrantGraphUrl = collectionName
    ? `http://localhost:6333/dashboard#/collections/${collectionName}/graph`
    : null;
  // 修改時間：2026-01-21 13:25 UTC+8 - 嘗試使用 points 視圖（可能需要手動選擇 point）
  const qdrantPointUrl = collectionName
    ? `http://localhost:6333/dashboard#/collections/${collectionName}/points`
    : null;

  return (
    <>
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
        {/* Point Header（可點擊展開/收起） */}
        <div className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-3 flex-1 min-w-0 text-left"
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-500 dark:text-gray-400 flex-shrink-0" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500 dark:text-gray-400 flex-shrink-0" />
            )}
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <div className="font-mono text-sm text-gray-900 dark:text-gray-100 flex-shrink-0">
                ID: {pointId}
              </div>
              {/* 修改時間：2026-01-21 13:45 UTC+8 - 顯示 chunk_text 預覽（最多 10 字符） */}
              {chunkText && (
                <div className="text-xs text-gray-600 dark:text-gray-400 truncate flex-1 min-w-0" title={chunkText}>
                  {chunkText.length > 10 ? `${chunkText.substring(0, 20)}...` : chunkText}
                </div>
              )}
            </div>
            {chunkIndex !== undefined && (
              <div className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">
                Chunk #{chunkIndex}
              </div>
            )}
          </button>
          <div className="flex items-center gap-2 flex-shrink-0 ml-2">
            {/* 修改時間：2026-01-21 13:30 UTC+8 - 添加 "尋找相似" 按鈕 */}
            {fileId && (
              <button
                onClick={handleFindSimilar}
                disabled={loadingSimilar}
                className="px-3 py-1.5 text-xs bg-purple-600 text-white rounded hover:bg-purple-700 transition-colors flex items-center gap-1 disabled:bg-gray-400 disabled:cursor-not-allowed"
                title="查找相似的向量"
              >
                {loadingSimilar ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Network className="w-3 h-3" />
                )}
                <span>尋找相似</span>
              </button>
            )}
            {/* 修改時間：2026-01-21 13:10 UTC+8 - 添加 "Open Panel" 按鈕 */}
            <button
              onClick={() => setShowModal(true)}
              className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors flex items-center gap-1"
              title="打開詳細面板"
            >
              <ExternalLink className="w-3 h-3" />
              <span>Open Panel</span>
            </button>
            {vector && (
              <div className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">
                Vector: {Array.isArray(vector) ? vector.length : 'N/A'} dims
              </div>
            )}
          </div>
        </div>

      {/* Point Details（展開時顯示） */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
          {/* Payload 信息 */}
          <div className="mt-3 space-y-3">
            {/* Chunk Text（如果有） */}
            {chunkText && (
              <div>
                <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">
                  Chunk Text
                </div>
                <div className="bg-white dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-700">
                  <pre className="whitespace-pre-wrap text-sm text-gray-900 dark:text-gray-100 max-h-60 overflow-auto">
                    {chunkText}
                  </pre>
                </div>
              </div>
            )}

            {/* Metadata 信息 */}
            <div>
              <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">
                Payload
              </div>
              <div className="bg-white dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-700">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {fileId && (
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">file_id:</span>{' '}
                      <span className="font-mono text-gray-900 dark:text-gray-100">{fileId}</span>
                    </div>
                  )}
                  {taskId && (
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">task_id:</span>{' '}
                      <span className="font-mono text-gray-900 dark:text-gray-100">{taskId}</span>
                    </div>
                  )}
                  {chunkIndex !== undefined && (
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">chunk_index:</span>{' '}
                      <span className="font-mono text-gray-900 dark:text-gray-100">{chunkIndex}</span>
                    </div>
                  )}
                </div>
                {/* 完整的 Payload JSON（可折疊） */}
                <details className="mt-2">
                  <summary className="cursor-pointer text-xs text-blue-600 dark:text-blue-400 hover:underline">
                    查看完整 Payload JSON
                  </summary>
                  <pre className="mt-2 p-2 bg-gray-50 dark:bg-gray-950 rounded text-xs overflow-auto max-h-40">
                    {JSON.stringify(payload, null, 2)}
                  </pre>
                </details>
              </div>
            </div>

            {/* Vector 信息（如果有） */}
            {vector && Array.isArray(vector) && (
              <div>
                <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">
                  Vector ({vector.length} dimensions)
                </div>
                <div className="bg-white dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-700">
                  <details>
                    <summary className="cursor-pointer text-xs text-blue-600 dark:text-blue-400 hover:underline">
                      查看向量數據（前 10 維度 + ...）
                    </summary>
                    <pre className="mt-2 text-xs text-gray-600 dark:text-gray-400 font-mono overflow-auto max-h-40">
                      {JSON.stringify(vector.slice(0, 10), null, 2)}
                      {vector.length > 10 && `\n... (${vector.length - 10} more dimensions)`}
                    </pre>
                  </details>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>

    {/* 修改時間：2026-01-21 13:10 UTC+8 - Point 詳細信息 Modal（類似 Qdrant Dashboard 的 Open panel） */}
    {showModal && (
      <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
          {/* Modal Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
            <div className="flex items-center gap-3">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {viewMode === 'details' ? 'Point Details' : viewMode === 'graph' ? 'Graph View' : 'Similar Vectors'}
              </h3>
              <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">ID: {pointId}</span>
            </div>
            <div className="flex items-center gap-2">
              {/* 視圖切換按鈕 */}
              <div className="flex items-center gap-2 border border-gray-300 dark:border-gray-600 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('details')}
                  className={`px-3 py-1.5 text-xs rounded transition-colors ${
                    viewMode === 'details'
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  Details
                </button>
                <button
                  onClick={handleFindSimilar}
                  disabled={loadingSimilar}
                  className={`px-3 py-1.5 text-xs rounded transition-colors flex items-center gap-1 ${
                    viewMode === 'similar'
                      ? 'bg-purple-600 text-white'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {loadingSimilar ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Network className="w-3 h-3" />
                  )}
                  <span>Similar</span>
                </button>
                {qdrantGraphUrl && (
                  <button
                    onClick={() => setViewMode('graph')}
                    className={`px-3 py-1.5 text-xs rounded transition-colors ${
                      viewMode === 'graph'
                        ? 'bg-green-600 text-white'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    Graph
                  </button>
                )}
              </div>
              {/* Qdrant Dashboard 鏈接 */}
              {qdrantCollectionUrl && (
                <a
                  href={qdrantCollectionUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors flex items-center gap-1"
                  title="在新窗口中打開 Qdrant Dashboard Collection 視圖（可查看所有 Points）"
                >
                  <ExternalLink className="w-3 h-3" />
                  <span>Open Collection</span>
                </a>
              )}
              {qdrantPointUrl && (
                <a
                  href={qdrantPointUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700 transition-colors flex items-center gap-1"
                  title="在新窗口中打開 Qdrant Dashboard Points 視圖（可搜索和選擇 Point）"
                >
                  <Database className="w-3 h-3" />
                  <span>View Points</span>
                </a>
              )}
              <button
                onClick={() => setShowModal(false)}
                className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Modal Content */}
          <div className="flex-1 overflow-auto p-6">
            {viewMode === 'similar' ? (
              // 修改時間：2026-01-21 13:40 UTC+8 - 相似向量視圖
              <div className="h-full flex flex-col">
                <div className="flex items-center justify-between mb-4 flex-shrink-0">
                  <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    相似向量 {similarVectors ? `(${similarVectors.length})` : ''}
                  </h4>
                  <button
                    onClick={() => setViewMode('details')}
                    className="px-3 py-1.5 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
                  >
                    ← 回到 Details
                  </button>
                </div>
                {loadingSimilar ? (
                  <div className="flex-1 flex items-center justify-center">
                    <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
                    <span className="ml-3 text-gray-600 dark:text-gray-400">正在查找相似向量...</span>
                  </div>
                ) : similarVectors && similarVectors.length > 0 ? (
                  <div className="flex-1 overflow-auto space-y-3">
                    {similarVectors.map((similar, idx) => {
                      const similarPointId = similar.id;
                      const similarPayload = similar.payload || {};
                      const similarChunkText = similarPayload.chunk_text || similarPayload.text || similarPayload.document || '';
                      const similarChunkIndex = similarPayload.chunk_index !== undefined ? similarPayload.chunk_index : similarPayload.index;
                      const similarityScore = similar.score !== undefined ? (similar.score * 100).toFixed(1) : 'N/A';

                      return (
                        <div
                          key={similarPointId || idx}
                          className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center gap-3 flex-1 min-w-0">
                              <div className="font-mono text-sm text-gray-900 dark:text-gray-100">
                                ID: {similarPointId}
                              </div>
                              {similarChunkIndex !== undefined && (
                                <div className="text-xs text-gray-500 dark:text-gray-400">
                                  Chunk #{similarChunkIndex}
                                </div>
                              )}
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              <span className="px-2 py-1 text-xs font-semibold bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 rounded">
                                相似度: {similarityScore}%
                              </span>
                            </div>
                          </div>
                          {similarChunkText && (
                            <div className="mt-2">
                              <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Chunk Text:</div>
                              <div className="bg-gray-50 dark:bg-gray-900 p-2 rounded text-sm text-gray-700 dark:text-gray-300 line-clamp-3">
                                {similarChunkText.substring(0, 200)}
                                {similarChunkText.length > 200 ? '...' : ''}
                              </div>
                            </div>
                          )}
                          <details className="mt-2">
                            <summary className="cursor-pointer text-xs text-blue-600 dark:text-blue-400 hover:underline">
                              查看完整 Payload
                            </summary>
                            <pre className="mt-2 p-2 bg-gray-50 dark:bg-gray-950 rounded text-xs overflow-auto max-h-40 font-mono">
                              {JSON.stringify(similarPayload, null, 2)}
                            </pre>
                          </details>
                        </div>
                      );
                    })}
                  </div>
                ) : similarVectors && similarVectors.length === 0 ? (
                  <div className="flex-1 flex items-center justify-center">
                    <div className="text-center text-gray-500 dark:text-gray-400">
                      <Network className="w-16 h-16 mx-auto mb-4 opacity-50" />
                      <p>沒有找到相似的向量</p>
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex items-center justify-center">
                    <div className="text-center text-gray-500 dark:text-gray-400">
                      <Network className="w-16 h-16 mx-auto mb-4 opacity-50" />
                      <p>點擊上方 "Similar" 按鈕查找相似向量</p>
                    </div>
                  </div>
                )}
              </div>
            ) : viewMode === 'graph' && qdrantGraphUrl ? (
              // 修改時間：2026-01-21 13:20 UTC+8 - 由於 X-Frame-Options 限制，顯示提示並提供打開按鈕
              <div className="h-full w-full flex flex-col items-center justify-center border border-gray-200 dark:border-gray-700 rounded-lg p-8 space-y-4">
                <Network className="w-16 h-16 text-gray-400 dark:text-gray-500" />
                <div className="text-center">
                  <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                    Qdrant Dashboard Graph View
                  </h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                    由於安全策略限制，無法在當前窗口中嵌入 Qdrant Dashboard。
                    <br />
                    請點擊下方按鈕在新窗口中打開 Graph 視圖。
                  </p>
                  <a
                    href={qdrantGraphUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                  >
                    <Network className="w-5 h-5" />
                    <span>在新窗口中打開 Graph 視圖</span>
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
                <div className="mt-4 text-xs text-gray-500 dark:text-gray-400 space-y-2">
                  <p>Graph URL: <code className="font-mono bg-gray-100 dark:bg-gray-900 px-2 py-1 rounded">{qdrantGraphUrl}</code></p>
                  {qdrantPointUrl && (
                    <p>Points URL: <code className="font-mono bg-gray-100 dark:bg-gray-900 px-2 py-1 rounded">{qdrantPointUrl}</code></p>
                  )}
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
                    注意：在 Qdrant Dashboard 中，您需要手動選擇 Point ID <code className="font-mono bg-gray-200 dark:bg-gray-800 px-1 rounded">{pointId}</code> 來查看詳細信息
                  </p>
                </div>
              </div>
            ) : (
              // Details 視圖
              <div className="space-y-4">
                {/* Point Info */}
                <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800 mb-4">
                  <p className="text-sm text-blue-800 dark:text-blue-300">
                    <strong>提示：</strong> 由於 Qdrant Dashboard 的安全限制，無法直接通過 URL 打開特定 Point。
                    <br />
                    請使用上方按鈕打開 Collection 視圖，然後在 Points 列表中搜索或選擇 Point ID: <code className="font-mono bg-blue-100 dark:bg-blue-900 px-2 py-1 rounded">{pointId}</code>
                  </p>
                </div>
                <div className="grid grid-cols-3 gap-4">
              <div className="bg-gray-50 dark:bg-gray-900 p-3 rounded border border-gray-200 dark:border-gray-700">
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Point ID</div>
                <div className="text-sm font-mono text-gray-900 dark:text-gray-100 truncate" title={pointId}>
                  {pointId}
                </div>
              </div>
              {chunkIndex !== undefined && (
                <div className="bg-gray-50 dark:bg-gray-900 p-3 rounded border border-gray-200 dark:border-gray-700">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Chunk Index</div>
                  <div className="text-sm font-mono text-gray-900 dark:text-gray-100">{chunkIndex}</div>
                </div>
              )}
              {vector && Array.isArray(vector) && (
                <div className="bg-gray-50 dark:bg-gray-900 p-3 rounded border border-gray-200 dark:border-gray-700">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Vector Dimensions</div>
                  <div className="text-sm font-mono text-gray-900 dark:text-gray-100">{vector.length}</div>
                </div>
              )}
            </div>

            {/* Chunk Text */}
            {chunkText && (
              <div>
                <div className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Chunk Text
                </div>
                <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded border border-gray-200 dark:border-gray-700">
                  <pre className="whitespace-pre-wrap text-sm text-gray-900 dark:text-gray-100 max-h-60 overflow-auto">
                    {chunkText}
                  </pre>
                </div>
              </div>
            )}

            {/* Payload */}
            <div>
              <div className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Payload
              </div>
              <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded border border-gray-200 dark:border-gray-700">
                <div className="grid grid-cols-2 gap-3 text-sm mb-3">
                  {fileId && (
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">file_id:</span>{' '}
                      <span className="font-mono text-gray-900 dark:text-gray-100">{fileId}</span>
                    </div>
                  )}
                  {taskId && (
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">task_id:</span>{' '}
                      <span className="font-mono text-gray-900 dark:text-gray-100">{taskId}</span>
                    </div>
                  )}
                  {chunkIndex !== undefined && (
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">chunk_index:</span>{' '}
                      <span className="font-mono text-gray-900 dark:text-gray-100">{chunkIndex}</span>
                    </div>
                  )}
                </div>
                <details className="mt-2">
                  <summary className="cursor-pointer text-sm text-blue-600 dark:text-blue-400 hover:underline">
                    查看完整 Payload JSON
                  </summary>
                  <pre className="mt-2 p-3 bg-gray-100 dark:bg-gray-950 rounded text-xs overflow-auto max-h-60 font-mono">
                    {JSON.stringify(payload, null, 2)}
                  </pre>
                </details>
              </div>
            </div>

            {/* Vector */}
            {vector && Array.isArray(vector) && (
              <div>
                <div className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Vector ({vector.length} dimensions)
                </div>
                <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded border border-gray-200 dark:border-gray-700">
                  <details>
                    <summary className="cursor-pointer text-sm text-blue-600 dark:text-blue-400 hover:underline">
                      查看向量數據（前 20 維度 + ...）
                    </summary>
                    <pre className="mt-2 text-xs text-gray-600 dark:text-gray-400 font-mono overflow-auto max-h-60">
                      {JSON.stringify(vector.slice(0, 20), null, 2)}
                      {vector.length > 20 && `\n... (${vector.length - 20} more dimensions)`}
                    </pre>
                  </details>
                </div>
              </div>
            )}
              </div>
            )}
          </div>
        </div>
      </div>
    )}
  </>
  );
}

interface FilePreviewProps {
  file: FileMetadata;
  isOpen: boolean;
  onClose: () => void;
  inline?: boolean; // 是否内嵌显示（非模态框）
}

type PreviewMode = 'text' | 'vector' | 'graph';

export default function FilePreview({ file, isOpen, onClose, inline = false }: FilePreviewProps) {
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

  // 修改時間：2026-01-06 - 從 Context 獲取流式編輯 patches
  const { editingFileId, patches, modifiedContent, setOriginalContent, setEditingFile } = useFileEditing();
  const shouldShowPatches = editingFileId === file.file_id && patches.length > 0;
  // 如果有修改後的內容，使用修改後的內容；否則使用原始內容
  const displayContent = (editingFileId === file.file_id && modifiedContent) ? modifiedContent : content;

  // 輔助函數：轉義正則表達式特殊字符
  const escapeRegExp = (string: string) => {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  };

  // 修改時間：2026-01-21 12:40 UTC+8 - 應用 Search-and-Replace patches 到內容（用於 Markdown 流式編輯）
  const applyPatches = useMemo(() => {
    if (!shouldShowPatches || patches.length === 0) {
      return displayContent;
    }

    let patchedContent = displayContent;
    for (const patch of patches) {
      const { search_block, replace_block } = patch;
      // 使用全局替換（因為可能有多個相同的 search_block）
      patchedContent = patchedContent.replace(new RegExp(escapeRegExp(search_block), 'g'), replace_block);
    }
    return patchedContent;
  }, [displayContent, patches, shouldShowPatches, escapeRegExp]);

  // 修改時間：2026-01-21 12:40 UTC+8 - 解析 Markdown 內容，識別普通文本和 mermaid 代碼塊
  const markdownParts = useMemo(() => {
    const contentToParse = applyPatches;
    try {
      const parts: Array<{type: 'text' | 'mermaid', content: string}> = [];
      const mermaidRegex = /```mermaid\n([\s\S]*?)```/g;
      let lastIndex = 0;
      let match;

      while ((match = mermaidRegex.exec(contentToParse)) !== null) {
        // 添加 mermaid 代碼塊之前的文本
        if (match.index > lastIndex) {
          parts.push({
            type: 'text',
            content: contentToParse.substring(lastIndex, match.index)
          });
        }

        // 添加 mermaid 代碼塊
        parts.push({
          type: 'mermaid',
          content: match[1] // 只提取 mermaid 代碼內容
        });

        lastIndex = match.index + match[0].length;
      }

      // 添加最後一段普通文本
      if (lastIndex < contentToParse.length) {
        parts.push({
          type: 'text',
          content: contentToParse.substring(lastIndex)
        });
      }

      // 如果沒有找到任何 mermaid 代碼塊，整個內容都是文本
      if (parts.length === 0) {
        parts.push({ type: 'text', content: contentToParse });
      }

      return parts;
    } catch (error) {
      console.error("解析Markdown内容时出错:", error);
      return [{ type: 'text', content: contentToParse }];
    }
  }, [applyPatches]);

  // 修改時間：2026-01-21 12:40 UTC+8 - 自定義 Markdown 組件樣式（markdown-to-jsx 格式）
  const markdownOptions = useMemo(() => ({
    overrides: {
      // 標題
      h1: {
        component: 'h1',
        props: { className: 'text-3xl font-bold mt-8 mb-4 text-primary theme-transition' }
      },
      h2: {
        component: 'h2',
        props: { className: 'text-2xl font-bold mt-7 mb-3 text-primary theme-transition' }
      },
      h3: {
        component: 'h3',
        props: { className: 'text-xl font-bold mt-6 mb-3 text-primary theme-transition' }
      },
      h4: {
        component: 'h4',
        props: { className: 'text-xl font-bold mt-5 mb-2 text-primary theme-transition' }
      },
      h5: {
        component: 'h5',
        props: { className: 'text-lg font-bold mt-4 mb-2 text-primary theme-transition' }
      },
      h6: {
        component: 'h6',
        props: { className: 'text-lg font-bold mt-4 mb-2 text-primary theme-transition' }
      },
      // 段落 - 保留換行和縮排
      p: {
        component: ({ children, ...props }: any) => (
          <p
            className="mb-4 text-primary whitespace-pre-wrap leading-relaxed theme-transition"
            style={{ whiteSpace: 'pre-wrap' }}
            {...props}
          >
            {children}
          </p>
        )
      },
      // 列表
      ul: {
        component: 'ul',
        props: { className: 'list-disc mb-2 text-primary ml-6 theme-transition' }
      },
      ol: {
        component: 'ol',
        props: { className: 'list-decimal mb-2 text-primary ml-6 theme-transition' }
      },
      li: {
        component: 'li',
        props: { className: 'mb-1 text-primary leading-relaxed theme-transition' }
      },
      // 代碼塊
      pre: {
        component: 'pre',
        props: { className: 'bg-gray-900 dark:bg-gray-800 p-4 rounded-md overflow-x-auto my-4 text-sm whitespace-pre' }
      },
      code: {
        component: ({ className, children, ...props }: any) => {
          const isCodeBlock = className && !className.includes('inline');
          if (isCodeBlock) {
            const langMatch = className?.match(/language-(\w+)/);
            const language = langMatch ? langMatch[1] : '';
            const codeContent = String(children || '').replace(/\n$/, '');
            // 如果是 Mermaid，使用 MermaidRenderer（但這不會被觸發，因為我們已經解析了 mermaid 代碼塊）
            if (language === 'mermaid') {
              return <MermaidRenderer code={codeContent.trim()} className="bg-secondary p-4 rounded-lg border border-primary theme-transition" />;
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
        props: { className: 'my-6 border-primary theme-transition' }
      },
      // 引用
      blockquote: {
        component: 'blockquote',
        props: { className: 'border-l-4 border-primary pl-4 italic my-4 text-tertiary theme-transition' }
      },
      // 鏈接
      a: {
        component: 'a',
        props: { className: 'text-blue-500 hover:text-blue-600 underline', target: '_blank', rel: 'noopener noreferrer' }
      },
      // 圖片
      img: {
        component: 'img',
        props: { className: 'max-w-full h-auto rounded my-4' }
      },
      // 表格
      table: {
        component: 'table',
        props: { className: 'min-w-full border-collapse border border-primary my-4' }
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
        props: { className: 'px-4 py-2 text-left font-semibold text-primary border-r border-primary theme-transition' }
      },
      td: {
        component: 'td',
        props: { className: 'px-4 py-2 text-primary border-r border-primary theme-transition' }
      },
      // 強調
      strong: {
        component: 'strong',
        props: { className: 'font-bold text-primary theme-transition' }
      },
      em: {
        component: 'em',
        props: { className: 'italic text-primary theme-transition' }
      }
    }
  } as any), []);

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

      // 修改時間：2026-01-06 - 如果是 Markdown 文件且是當前編輯的文件，獲取原始內容
      const isMarkdown = file.filename.toLowerCase().endsWith('.md') ||
                        file.filename.toLowerCase().endsWith('.markdown') ||
                        file.file_type === 'text/markdown';
      if (isMarkdown && editingFileId === file.file_id) {
        // 設置編輯文件（確保 Context 知道當前編輯的文件）
        setEditingFile(file.file_id);
        // 獲取原始內容並存儲到 Context
        previewFile(file.file_id)
          .then((response) => {
            if (response.success && response.data?.content) {
              setOriginalContent(response.data.content);
            }
          })
          .catch((error) => {
            console.error('[FilePreview] Failed to load original content:', error);
          });
      }
    }

    // 清理刷新定時器
    return () => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
        setRefreshInterval(null);
      }
    };
  }, [isOpen, file, editingFileId, setOriginalContent, setEditingFile]);

  const refreshProcessingStatus = async () => {
    try {
      const resp = await getProcessingStatus(file.file_id);
      console.log('[FilePreview] refreshProcessingStatus response:', resp);
      if (resp?.success && resp.data) {
        setProcessingStatus(resp.data);
      } else {
        // 如果 API 返回 null 或失败，设置为 null
        setProcessingStatus(null);
      }
    } catch (err) {
      console.warn('[FilePreview] Failed to refresh processing status:', err);
      setProcessingStatus(null);
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
    // 修改時間：2026-01-21 12:50 UTC+8 - 只要 collection 存在就認為可用（即使 vector_count 為 0）
    try {
      const vectorResponse = await getFileVectors(file.file_id, 1, 0);
      // 只要 collection 存在（有 collection_name），就認為可用，即使 vector_count 為 0
      const hasCollection = vectorResponse.success && vectorResponse.data &&
        (vectorResponse.data.stats?.collection_name ||
         vectorResponse.data.collection_name);
      setVectorAvailable(hasCollection || false);

      // 如果 collection 存在，且當前是向量模式，立即加載數據
      if (hasCollection && mode === 'vector') {
        loadDataForMode('vector');
      }
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
            console.log('[FilePreview] Vector data loaded:', vectorResponse.data);
            setVectorData(vectorResponse.data);
          } else {
            console.warn('[FilePreview] Failed to load vector data:', vectorResponse);
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

        // 修改時間：2026-01-06 - 如果是 Markdown 文件且是當前編輯的文件，更新原始內容到 Context
        const isMarkdown = file.filename.toLowerCase().endsWith('.md') ||
                          file.filename.toLowerCase().endsWith('.markdown') ||
                          file.file_type === 'text/markdown';
        if (isMarkdown && editingFileId === file.file_id) {
          setOriginalContent(response.data.content);
        }
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
        // 修改時間：2026-01-21 12:15 UTC+8 - inline 模式下不顯示 Viewer 的 Header
        if (file.file_type === 'application/pdf' || file.filename.toLowerCase().endsWith('.pdf')) {
          return <PDFViewer fileId={file.file_id} fileName={file.filename} fileMetadata={file} showHeader={!inline} />;
        }

        // DOCX 文件使用 DOCXViewer
        // 修改時間：2026-01-21 12:15 UTC+8 - inline 模式下不顯示 Viewer 的 Header
        if (
          file.file_type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
          file.file_type === 'application/msword' ||
          file.filename.toLowerCase().endsWith('.docx') ||
          file.filename.toLowerCase().endsWith('.doc')
        ) {
          return <DOCXViewer fileId={file.file_id} fileName={file.filename} fileMetadata={file} showHeader={!inline} />;
        }

        // XLSX 文件使用 ExcelViewer
        // 修改時間：2026-01-21 12:15 UTC+8 - inline 模式下不顯示 Viewer 的 Header
        if (
          file.file_type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
          file.file_type === 'application/vnd.ms-excel' ||
          file.filename.toLowerCase().endsWith('.xlsx') ||
          file.filename.toLowerCase().endsWith('.xls')
        ) {
          return <ExcelViewer fileId={file.file_id} fileName={file.filename} fileMetadata={file} showHeader={!inline} />;
        }

        // Markdown 文件直接渲染（不再使用 MarkdownViewer 避免重複 Header）
        // 修改時間：2026-01-21 12:40 UTC+8 - 整合 Markdown 和 Mermaid 渲染到 FilePreview
        if (file.file_type === 'text/markdown' || file.filename.endsWith('.md')) {
          return (
            <div className="p-4 flex-1 overflow-auto min-h-0">
              <div className="prose prose-invert max-w-none">
                {markdownParts.map((part, index) => (
                  <div key={index}>
                    {part.type === 'text' ? (
                      <div
                        className="markdown-content"
                        style={{
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word'
                        }}
                      >
                        <Markdown options={markdownOptions as any}>
                          {part.content}
                        </Markdown>
                      </div>
                    ) : (
                      <MermaidRenderer
                        code={part.content.trim()}
                        className="bg-secondary p-4 rounded-lg border border-primary theme-transition my-4"
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
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
        // 修改時間：2026-01-21 12:55 UTC+8 - 即使 vectorAvailable 為 false，如果已經有 vectorData，也顯示數據
        // 優先檢查是否有已加載的 vectorData（即使 vector_count 為 0，也應該顯示 Collection 信息）
        console.log('[FilePreview] Vector mode - vectorAvailable:', vectorAvailable, 'vectorData:', vectorData);
        const hasCollectionName = vectorData?.stats?.collection_name || vectorData?.collection_name;
        console.log('[FilePreview] hasCollectionName:', hasCollectionName);
        if (vectorData && hasCollectionName) {
          console.log('[FilePreview] Showing Qdrant-style interface with vectorData');
          // 有 vectorData 且 collection 存在，直接顯示（即使 vector_count 為 0）
          const vectorCount = vectorData?.stats?.vector_count || vectorData?.total || vectorData?.vectors?.length || 0;
          const collectionName = vectorData?.stats?.collection_name;
          const collectionStatus = vectorData?.stats?.status;

          const qdrantDashboardUrl = collectionName
            ? `http://localhost:6333/dashboard#/collections/${collectionName}`
            : null;

          return (
            <div className="h-full flex flex-col p-4 bg-white dark:bg-gray-900">
              <div className="mb-4 flex-shrink-0 border-b border-gray-200 dark:border-gray-700 pb-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Collection Info</h3>
                  {qdrantDashboardUrl && (
                    <a
                      href={qdrantDashboardUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
                      title="在 Qdrant Dashboard 中打開"
                    >
                      <ExternalLink className="w-4 h-4" />
                      <span>打開 Dashboard</span>
                    </a>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-700">
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Collection Name</div>
                    <div className="text-sm font-mono text-gray-900 dark:text-gray-100 truncate" title={collectionName}>
                      {collectionName || '-'}
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-700">
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Points Count</div>
                    <div className="text-xl font-bold text-gray-900 dark:text-gray-100">{vectorCount.toLocaleString()}</div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-700">
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Status</div>
                    <div className="text-sm text-gray-900 dark:text-gray-100 capitalize">
                      {collectionStatus || 'unknown'}
                    </div>
                  </div>
                </div>
              </div>

              {vectorData?.vectors && vectorData.vectors.length > 0 ? (
                <div className="flex-1 flex flex-col min-h-0">
                  <div className="flex items-center justify-between mb-3 flex-shrink-0">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                      Points（顯示 {vectorData.vectors.length} / {vectorData.total || vectorCount}）
                    </h3>
                  </div>
                  <div className="flex-1 overflow-auto min-h-0 space-y-2">
                    {vectorData.vectors.map((point: any, index: number) => (
                      <VectorPointCard
                        key={point.id || index}
                        point={point}
                        index={index}
                        collectionName={collectionName} // 修改時間：2026-01-21 13:10 UTC+8 - 傳遞 collectionName
                        fileId={file.file_id} // 修改時間：2026-01-21 13:30 UTC+8 - 傳遞 fileId 用於相似度搜索
                      />
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center text-gray-500 dark:text-gray-400">
                  <div className="text-center">
                    <Database className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p>沒有找到 Points（Collection 存在但尚未有向量數據）</p>
                    {collectionStatus === 'error' && (
                      <p className="text-sm text-red-500 mt-2">Collection 狀態：錯誤</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        }

        // 修改時間：2026-01-21 12:55 UTC+8 - 如果 vectorAvailable 為 false，但沒有 vectorData，顯示"未成功生成"
        if (!vectorAvailable) {
          console.log('[FilePreview] vectorAvailable is false, showing "未成功生成" interface');
          console.log('[FilePreview] file.status:', file.status, 'file.storage_path:', file.storage_path, 'processingStatus:', processingStatus);

          // 修改時間：2026-01-21 13:05 UTC+8 - 如果 storage_path 有值，表示文件已存在，認為處理已完成
          const hasStoragePath = file.storage_path && file.storage_path.trim().length > 0;
          const fileStatusCompleted = file.status === 'completed';
          const hasProcessingStatus = processingStatus !== null && processingStatus !== undefined;

          // 如果 storage_path 存在，認為文件已上傳/處理完成
          const fileExists = hasStoragePath || fileStatusCompleted;

          const vectorStage = processingStatus?.vectorization?.status || processingStatus?.status;
          const vectorProgress = processingStatus?.vectorization?.progress ?? 0;
          const vectorMessage =
            processingStatus?.vectorization?.message ||
            processingStatus?.message ||
            '向量處理中，請稍候';
          const isVectorRunning = vectorStage === 'processing' || vectorStage === 'in_progress' || vectorStage === 'pending';
          const isVectorFailed = vectorStage === 'failed';

          // 如果文件已存在（storage_path 有值或 status = completed），但 processing_status 為 null，認為處理已完成（可能 TTL 過期）
          // 這種情況下，應該顯示"未成功生成"但提供"重新生成"按鈕，而不是顯示"生成中"
          // 只有在 processing_status 存在且狀態為 running 時，才顯示"生成中"
          const shouldShowGenerating = hasProcessingStatus && isVectorRunning && !isVectorFailed && !fileExists;
          console.log('[FilePreview] shouldShowGenerating:', shouldShowGenerating, 'fileExists:', fileExists, 'hasStoragePath:', hasStoragePath, 'fileStatusCompleted:', fileStatusCompleted, 'hasProcessingStatus:', hasProcessingStatus);
          return (
            <div className="text-center py-8 text-gray-500">
              <Database className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-semibold">未成功生成</p>
              <p className="text-sm mt-2 mb-4">
                {fileExists && !hasProcessingStatus
                  ? '文件已上傳，但向量數據可能尚未生成或已過期'
                  : '向量數據尚未生成或無法加載'}
              </p>
              {shouldShowGenerating ? (
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
        // 修改時間：2026-01-21 12:35 UTC+8 - 處理 vectorData 為 null 的情況
        if (!vectorData) {
          console.log('[FilePreview] vectorData is null, showing loading interface');
          return (
            <div className="h-full flex items-center justify-center p-4">
              <div className="text-center text-gray-500 dark:text-gray-400">
                <Database className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p>正在加載向量數據...</p>
              </div>
            </div>
          );
        }

        // 修改時間：2026-01-21 12:25 UTC+8 - 實現方案2：顯示類似 Qdrant Dashboard 的格式
        console.log('[FilePreview] Showing Qdrant-style interface (vectorAvailable=true, vectorData exists)');
        const vectorCount = vectorData?.stats?.vector_count || vectorData?.total || vectorData?.vectors?.length || 0;
        const collectionName = vectorData?.stats?.collection_name;
        const collectionStatus = vectorData?.stats?.status;

        // Qdrant Dashboard URL（可選，用於跳轉）
        const qdrantDashboardUrl = collectionName
          ? `http://localhost:6333/dashboard#/collections/${collectionName}`
          : null;

        return (
          <div className="h-full flex flex-col p-4 bg-white dark:bg-gray-900">
            {/* Collection Info（類似 Qdrant Dashboard 的 Info 面板） */}
            <div className="mb-4 flex-shrink-0 border-b border-gray-200 dark:border-gray-700 pb-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Collection Info</h3>
                {qdrantDashboardUrl && (
                  <a
                    href={qdrantDashboardUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
                    title="在 Qdrant Dashboard 中打開"
                  >
                    <ExternalLink className="w-4 h-4" />
                    <span>打開 Dashboard</span>
                  </a>
                )}
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-700">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Collection Name</div>
                  <div className="text-sm font-mono text-gray-900 dark:text-gray-100 truncate" title={collectionName}>
                    {collectionName || '-'}
                  </div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-700">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Points Count</div>
                  <div className="text-xl font-bold text-gray-900 dark:text-gray-100">{vectorCount.toLocaleString()}</div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-700">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Status</div>
                  <div className="text-sm text-gray-900 dark:text-gray-100 capitalize">
                    {collectionStatus || 'unknown'}
                  </div>
                </div>
              </div>
            </div>

            {/* Points 列表（類似 Qdrant Dashboard 的 Points 面板） */}
            {vectorData?.vectors && vectorData.vectors.length > 0 ? (
              <div className="flex-1 flex flex-col min-h-0">
                <div className="flex items-center justify-between mb-3 flex-shrink-0">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    Points（顯示 {vectorData.vectors.length} / {vectorData.total || vectorCount}）
                  </h3>
                </div>
                <div className="flex-1 overflow-auto min-h-0 space-y-2">
                  {vectorData.vectors.map((point: any, index: number) => (
                    <VectorPointCard
                      key={point.id || index}
                      point={point}
                      index={index}
                      collectionName={collectionName} // 修改時間：2026-01-21 13:10 UTC+8 - 傳遞 collectionName
                      fileId={file.file_id} // 修改時間：2026-01-21 13:30 UTC+8 - 傳遞 fileId 用於相似度搜索
                    />
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-500 dark:text-gray-400">
                <div className="text-center">
                  <Database className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>沒有找到 Points</p>
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
          <div className="flex flex-col h-full">
            {/* 統計信息 */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 flex-shrink-0">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">圖譜數據統計</h3>
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
                  className="flex items-center gap-2 px-3 py-1.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:bg-gray-100 dark:disabled:bg-gray-900 disabled:cursor-not-allowed transition-colors text-gray-700 dark:text-gray-200"
                  title="刷新圖譜數據"
                >
                  <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                  <span>刷新</span>
                </button>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-white dark:bg-gray-800 p-3 rounded shadow-sm border border-gray-200 dark:border-gray-700">
                  <div className="text-sm text-gray-600 dark:text-gray-400">實體數量</div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{entitiesCount}</div>
                </div>
                <div className="bg-white dark:bg-gray-800 p-3 rounded shadow-sm border border-gray-200 dark:border-gray-700">
                  <div className="text-sm text-gray-600 dark:text-gray-400">關係數量</div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{relationsCount}</div>
                </div>
                <div className="bg-white dark:bg-gray-800 p-3 rounded shadow-sm border border-gray-200 dark:border-gray-700">
                  <div className="text-sm text-gray-600 dark:text-gray-400">三元組數量</div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{triplesCount}</div>
                </div>
              </div>
            </div>

            {/* 圖形視圖（包含節點列表和三元組列表） */}
            <div className="flex-1 min-h-0 overflow-hidden bg-white dark:bg-gray-950">
              <KnowledgeGraphViewer
                triples={triples}
                nodes={graphData?.nodes}
                edges={graphData?.edges}
                height={600}
              />
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  // 如果是内嵌模式，使用不同的布局
  if (inline) {
    return (
      <div className="h-full w-full flex flex-col bg-white dark:bg-gray-900 theme-transition">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-primary flex-shrink-0 gap-2">
          <div className="flex items-center gap-2 flex-shrink min-w-0">
            <h2 className="text-lg font-semibold truncate text-primary flex-shrink min-w-0">{file.filename}</h2>
            <span className="text-xs text-tertiary whitespace-nowrap flex-shrink-0">
              {file.file_size} bytes · {file.file_type}
            </span>
            {file.storage_path && (
              <span className="text-xs text-blue-500 dark:text-blue-400 font-mono truncate max-w-md" title={file.storage_path}>
                · {file.storage_path}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            {/* 模式切換按鈕組（文件、向量、圖譜） */}
            <div className="flex gap-0.5 border border-primary rounded-lg p-0.5 bg-tertiary shadow-sm">
              <button
                onClick={() => handleModeChange('text')}
                className={`px-3 py-1.5 rounded-md text-sm flex items-center gap-1.5 transition-all ${
                  mode === 'text'
                    ? 'bg-primary text-secondary shadow-md font-medium'
                    : 'bg-secondary text-primary hover:bg-tertiary'
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
                    ? 'bg-primary text-secondary shadow-md font-medium'
                    : 'bg-secondary text-primary hover:bg-tertiary'
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
                    ? 'bg-primary text-secondary shadow-md font-medium'
                    : 'bg-secondary text-primary hover:bg-tertiary'
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
                className="p-2 hover:bg-tertiary rounded transition-colors text-primary"
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
              className="p-2 hover:bg-tertiary rounded transition-colors text-primary"
              title="下載文件"
            >
              <Download className="w-5 h-5" />
            </button>
            {/* 關閉按鈕 */}
            <button
              onClick={onClose}
              className="p-2 hover:bg-tertiary rounded transition-colors text-primary"
              title="關閉"
            >
              <X className="w-5 h-5" />
            </button>
                        </div>
                    </div>

        {/* Content */}
        <div className="flex-1 overflow-auto min-h-0">
          {renderContent()}
        </div>
      </div>
    );
  }

  // 模态框模式（原有实现）
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b gap-2">
          <div className="flex items-center gap-2 flex-shrink min-w-0">
            <h2 className="text-lg font-semibold truncate flex-shrink min-w-0">{file.filename}</h2>
            <span className="text-xs text-gray-500 whitespace-nowrap flex-shrink-0">
              {file.file_size} bytes · {file.file_type}
            </span>
            {file.storage_path && (
              <span className="text-xs text-blue-500 dark:text-blue-400 font-mono truncate max-w-md" title={file.storage_path}>
                · {file.storage_path}
              </span>
            )}
          </div>
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
                  // 修改時間：2026-01-21 11:57 UTC+8 - 傳遞 fileMetadata 以支持 SeaWeedFS 直接訪問
                  const blob = await downloadFile(file.file_id, file);
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
      </div>
    </div>
  );
}
