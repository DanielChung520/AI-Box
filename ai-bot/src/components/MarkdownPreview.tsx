/**
 * 代碼功能說明: Markdown 文件預覽組件
 * 創建日期: 2026-02-13
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-02-13
 * 
 * 注意：此組件完全獨立，不依賴其他預覽器
 */

import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';

type PreviewMode = 'text' | 'vector' | 'graph';

interface MarkdownPreviewProps {
  fileId?: string;
  fileName: string;
}

export default function MarkdownPreview({ fileId, fileName }: MarkdownPreviewProps) {
  const [mode, setMode] = useState<PreviewMode>('text');
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [vectorData, setVectorData] = useState<any>(null);
  const [graphData, setGraphData] = useState<any>(null);
  const [vectorAvailable, setVectorAvailable] = useState(false);
  const [graphAvailable, setGraphAvailable] = useState(false);

  useEffect(() => {
    if (!fileId) return;
    setLoading(true);
    fetch(`/api/v1/files/${fileId}/preview`)
      .then(res => res.json())
      .then(data => {
        setContent(data.data?.content || '');
        setError(null);
      })
      .catch(err => {
        setError('加载失败');
        console.error(err);
      })
      .finally(() => setLoading(false));
  }, [fileId]);

  useEffect(() => {
    if (!fileId || mode !== 'vector') return;
    fetch(`/api/v1/files/${fileId}/vectors?limit=10`)
      .then(res => res.json())
      .then(data => {
        if (data.success && data.data?.points?.length > 0) {
          setVectorData(data.data);
          setVectorAvailable(true);
        }
      })
      .catch(console.error);
  }, [fileId, mode]);

  useEffect(() => {
    if (!fileId || mode !== 'graph') return;
    fetch(`/api/v1/files/${fileId}/graph`)
      .then(res => res.json())
      .then(data => {
        if (data.success && data.data) {
          setGraphData(data.data);
          setGraphAvailable(true);
        }
      })
      .catch(console.error);
  }, [fileId, mode]);

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 px-4 py-2 border-b bg-gray-50">
        <button onClick={() => setMode('text')} className={`px-3 py-1 rounded text-sm ${mode === 'text' ? 'bg-blue-500 text-white' : 'hover:bg-gray-200'}`}>
          文件
        </button>
        <button onClick={() => setMode('vector')} className={`px-3 py-1 rounded text-sm ${mode === 'vector' ? 'bg-blue-500 text-white' : 'hover:bg-gray-200'}`}>
          向量 {vectorAvailable && '✓'}
        </button>
        <button onClick={() => setMode('graph')} className={`px-3 py-1 rounded text-sm ${mode === 'graph' ? 'bg-blue-500 text-white' : 'hover:bg-gray-200'}`}>
          圖譜 {graphAvailable && '✓'}
        </button>
      </div>
      <div className="flex-1 overflow-auto p-4">
        {loading && <div className="flex items-center justify-center h-full"><Loader2 className="w-8 h-8 animate-spin text-blue-500" /></div>}
        {error && <div className="text-red-500 text-center">{error}</div>}
        {!loading && !error && mode === 'text' && <pre className="whitespace-pre-wrap font-mono text-sm">{content}</pre>}
        {!loading && !error && mode === 'vector' && (
          <div className="space-y-2">
            {vectorData?.points?.map((p: any, i: number) => (
              <div key={i} className="p-2 border rounded bg-gray-50 text-sm">
                <p className="text-xs text-gray-500 mb-1">Chunk {i + 1}</p>
                <p>{p.payload?.text?.substring(0, 200)}...</p>
              </div>
            )) || <p className="text-gray-400">暂无向量数据</p>}
          </div>
        )}
        {!loading && !error && mode === 'graph' && (
          <div className="text-gray-400">
            {graphData ? <pre className="text-sm">{JSON.stringify(graphData, null, 2)}</pre> : <p>暂无图谱数据</p>}
          </div>
        )}
      </div>
    </div>
  );
}
