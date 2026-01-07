/**
 * 代碼功能說明: 文件數據預覽組件（文本、向量、圖譜）
 * 創建日期: 2025-12-09
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-06
 */

import { useState, useEffect, useCallback } from 'react';
import { X, Loader2, FileText, Database, Network, Download } from 'lucide-react';
import { previewFile, getFileVectors, getFileGraph, downloadFile, FileMetadata } from '../lib/api';

interface FileDataPreviewProps {
  file: FileMetadata;
  initialMode?: 'text' | 'vector' | 'graph';
  isOpen: boolean;
  onClose: () => void;
}

type PreviewMode = 'text' | 'vector' | 'graph';

export default function FileDataPreview({
  file,
  initialMode = 'text', // 默認為文件模式
  isOpen,
  onClose
}: FileDataPreviewProps) {
  const [mode, setMode] = useState<PreviewMode>(initialMode);
  const [textContent, setTextContent] = useState<string>('');
  const [vectorData, setVectorData] = useState<any>(null);
  const [graphData, setGraphData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [textAvailable, setTextAvailable] = useState<boolean>(false);
  const [vectorAvailable, setVectorAvailable] = useState<boolean>(false);
  const [graphAvailable, setGraphAvailable] = useState<boolean>(false);

  const checkDataAvailability = useCallback(async () => {
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
  }, [file]);

  const loadDataForMode = useCallback(async (targetMode: PreviewMode) => {
    setLoading(true);
    setError(null);

    try {
      switch (targetMode) {
        case 'text':
          const textResponse = await previewFile(file.file_id);
          if (textResponse.success && textResponse.data) {
            setTextContent(textResponse.data.content || '');
          } else {
            setError('無法加載文本內容');
          }
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
  }, [file]);

  useEffect(() => {
    if (isOpen && file) {
      setMode(initialMode);
      // 重置狀態
      setTextContent('');
      setVectorData(null);
      setGraphData(null);
      setError(null);
      setLoading(false);
      // 檢查各類數據是否可用
      void checkDataAvailability();
      // 根據模式加載數據
      void loadDataForMode(initialMode);
    }
  }, [isOpen, file, initialMode, checkDataAvailability, loadDataForMode]);

  const handleModeChange = (newMode: PreviewMode) => {
    setMode(newMode);
    loadDataForMode(newMode);
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

    if (error) {
      return (
        <div className="text-center py-8 text-red-500">
          {error}
        </div>
      );
    }

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
        return (
          <div className="p-4">
            <pre className="whitespace-pre-wrap font-mono text-sm bg-gray-50 p-4 rounded max-h-[60vh] overflow-auto">
              {textContent}
            </pre>
          </div>
        );

      case 'vector':
        if (!vectorAvailable) {
          return (
            <div className="text-center py-8 text-gray-500">
              <Database className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg">未成功生成</p>
              <p className="text-sm mt-2">向量數據尚未生成或無法加載</p>
            </div>
          );
        }
        const vectorCount = vectorData?.stats?.vector_count || vectorData?.total || vectorData?.vectors?.length || 0;
        const collectionName = vectorData?.stats?.collection_name;

        return (
          <div className="h-full flex flex-col p-4">
            <div className="mb-4 flex-shrink-0">
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
              <div className="flex-1 flex flex-col min-h-0">
                <h3 className="text-lg font-semibold mb-2 flex-shrink-0">向量列表（顯示前 {vectorData.vectors.length} 個，共 {vectorData.total || vectorCount} 個）</h3>
                <div className="flex-1 space-y-2 overflow-auto min-h-0">
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
              <p className="text-lg">未成功生成</p>
              <p className="text-sm mt-2">圖譜數據尚未生成或無法加載</p>
            </div>
          );
        }
        const stats = graphData?.stats || {};
        const entitiesCount = stats.entities_count || graphData?.nodes?.length || 0;
        const relationsCount = stats.relations_count || graphData?.edges?.length || 0;
        const triplesCount = stats.triples_count || graphData?.triples?.length || stats.triples_count || 0;

        return (
          <div className="p-4">
            <div className="mb-4">
              <h3 className="text-lg font-semibold mb-2">圖譜數據統計</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gray-50 p-3 rounded">
                  <div className="text-sm text-gray-600">實體數量</div>
                  <div className="text-2xl font-bold">{entitiesCount}</div>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <div className="text-sm text-gray-600">關係數量</div>
                  <div className="text-2xl font-bold">{relationsCount}</div>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <div className="text-sm text-gray-600">三元組數量</div>
                  <div className="text-2xl font-bold">{triplesCount}</div>
                </div>
              </div>
            </div>
            {graphData?.nodes && graphData.nodes.length > 0 && (
              <div className="mb-4">
                <h3 className="text-lg font-semibold mb-2">實體列表（顯示前 {graphData.nodes.length} 個，共 {entitiesCount} 個）</h3>
                <div className="space-y-2 max-h-[30vh] overflow-auto">
                  {graphData.nodes.slice(0, 20).map((entity: any, index: number) => (
                    <div key={index} className="bg-gray-50 p-3 rounded">
                      <div className="font-semibold">{entity.name || entity.text || entity.label}</div>
                      <div className="text-sm text-gray-600">類型: {entity.type || entity._key}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {graphData?.edges && graphData.edges.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-2">關係列表（顯示前 {graphData.edges.length} 個，共 {relationsCount} 個）</h3>
                <div className="space-y-2 max-h-[30vh] overflow-auto">
                  {graphData.edges.slice(0, 20).map((relation: any, index: number) => {
                    const from = relation._from || relation.from || relation.subject || '';
                    const to = relation._to || relation.to || relation.object || '';
                    const type = relation.type || relation.predicate || '';
                    return (
                      <div key={index} className="bg-gray-50 p-3 rounded">
                        <div className="text-sm">
                          <span className="font-semibold">{from.split('/').pop() || from}</span>
                          {' → '}
                          <span className="text-blue-600">{type}</span>
                          {' → '}
                          <span className="font-semibold">{to.split('/').pop() || to}</span>
                        </div>
                        {relation.confidence && (
                          <div className="text-xs text-gray-500 mt-1">置信度: {relation.confidence.toFixed(2)}</div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            {graphData?.triples && graphData.triples.length > 0 && (
              <div className="mt-4">
                <h3 className="text-lg font-semibold mb-2">三元組列表（顯示前 {graphData.triples.length} 個，共 {triplesCount} 個）</h3>
                <div className="space-y-2 max-h-[30vh] overflow-auto">
                  {graphData.triples.slice(0, 20).map((triple: any, index: number) => (
                    <div key={index} className="bg-gray-50 p-3 rounded">
                      <div className="text-sm">
                        <span className="font-semibold">{triple.subject || triple._from}</span>
                        {' → '}
                        <span className="text-blue-600">{triple.predicate || triple.type}</span>
                        {' → '}
                        <span className="font-semibold">{triple.object || triple._to}</span>
                      </div>
                      {triple.confidence && (
                        <div className="text-xs text-gray-500 mt-1">置信度: {triple.confidence.toFixed(2)}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl max-h-[90vh] flex flex-col">
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
