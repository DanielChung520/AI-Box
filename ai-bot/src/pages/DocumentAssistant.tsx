/**
 * 代碼功能說明: 文件助手頁（生成/局部編輯 md/txt/json，preview-first）
 * 創建日期: 2025-12-14 10:53:05 (UTC+8)
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-14 13:28:13 (UTC+8)
 */

import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Wand2, ArrowLeft, Check, Loader2, History } from 'lucide-react';
import FileTree from '../components/FileTree';
import MarkdownViewer from '../components/MarkdownViewer';
import { previewFile } from '../lib/api';
import {
  applyDocEdit,
  applyDocGeneration,
  createDocEdit,
  createDocGeneration,
  getDocEditState,
  getDocGenerationState,
  listDocVersions,
  rollbackDocVersion,
} from '../lib/api';

type DocTab = 'edit' | 'generate';

export default function DocumentAssistant() {
  const navigate = useNavigate();
  const userId = localStorage.getItem('user_id') || undefined;

  const [tab, setTab] = useState<DocTab>('edit');
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string>('');

  const [baseContent, setBaseContent] = useState<string>('');
  const [baseFileType, setBaseFileType] = useState<string>('');

  const [instruction, setInstruction] = useState<string>('');
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [applyLoading, setApplyLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [editRequestId, setEditRequestId] = useState<string | null>(null);
  const [editStatus, setEditStatus] = useState<string | null>(null);
  const [editPreview, setEditPreview] = useState<any>(null);

  const [genFilename, setGenFilename] = useState<string>('new.md');
  const [genFormat, setGenFormat] = useState<'md' | 'txt' | 'json'>('md');
  const [genRequestId, setGenRequestId] = useState<string | null>(null);
  const [genStatus, setGenStatus] = useState<string | null>(null);
  const [genPreviewContent, setGenPreviewContent] = useState<string>('');

  const [versionsLoading, setVersionsLoading] = useState<boolean>(false);
  const [versions, setVersions] = useState<any[]>([]);
  const [currentDocVersion, setCurrentDocVersion] = useState<number | null>(null);

  // 修改時間：2025-12-14 13:28:13 (UTC+8) - 支援從 FileTree 草稿檔導入 generate 預填
  useEffect(() => {
    const applyPrefill = (payload: any) => {
      const tab = payload?.tab;
      const taskId = typeof payload?.taskId === 'string' ? payload.taskId : null;
      const filename = typeof payload?.filename === 'string' ? payload.filename : null;
      if (tab === 'generate') {
        setTab('generate');
      }
      if (taskId) {
        setSelectedTaskId(taskId);
      }
      if (filename) {
        setGenFilename(filename);
        const lower = filename.toLowerCase();
        if (lower.endsWith('.json')) setGenFormat('json');
        else if (lower.endsWith('.txt')) setGenFormat('txt');
        else setGenFormat('md');
      }
    };

    try {
      const raw = localStorage.getItem('docAssistantPrefill');
      if (raw) {
        const payload = JSON.parse(raw);
        applyPrefill(payload);
        localStorage.removeItem('docAssistantPrefill');
      }
    } catch {
      // ignore
    }

    const handler = (event: CustomEvent) => {
      applyPrefill(event?.detail || {});
    };
    window.addEventListener('docAssistantPrefill', handler as EventListener);
    return () => window.removeEventListener('docAssistantPrefill', handler as EventListener);
  }, []);

  const isMarkdown = useMemo(() => {
    const name = (selectedFileName || '').toLowerCase();
    return name.endsWith('.md') || baseFileType.includes('markdown');
  }, [selectedFileName, baseFileType]);

  const isJson = useMemo(() => {
    const name = (selectedFileName || '').toLowerCase();
    return name.endsWith('.json') || baseFileType.includes('json');
  }, [selectedFileName, baseFileType]);

  useEffect(() => {
    let cancelled = false;

    async function loadPreview() {
      if (!selectedFileId) {
        setBaseContent('');
        setBaseFileType('');
        return;
      }
      try {
        const resp = await previewFile(selectedFileId);
        if (cancelled) return;
        setBaseContent(resp?.data?.content || '');
        setBaseFileType(resp?.data?.file_type || '');
      } catch (e: any) {
        if (cancelled) return;
        setError(e?.message || '讀取文件預覽失敗');
      }
    }

    loadPreview();

    return () => {
      cancelled = true;
    };
  }, [selectedFileId]);

  const refreshVersions = async () => {
    if (!selectedFileId) return;
    setVersionsLoading(true);
    setError(null);
    try {
      const resp = await listDocVersions(selectedFileId);
      const data = (resp as any)?.data;
      setVersions(Array.isArray(data?.versions) ? data.versions : []);
      setCurrentDocVersion(typeof data?.doc_version === 'number' ? data.doc_version : null);
    } catch (e: any) {
      setError(e?.message || '讀取版本列表失敗');
    } finally {
      setVersionsLoading(false);
    }
  };

  const startEditPreview = async () => {
    if (!selectedFileId) {
      setError('請先在左側選擇一個文件');
      return;
    }
    if (!instruction.trim()) {
      setError('請輸入編輯指令');
      return;
    }

    setError(null);
    setPreviewLoading(true);
    setEditPreview(null);

    try {
      const resp = await createDocEdit({
        file_id: selectedFileId,
        instruction,
      });
      const rid = (resp as any)?.data?.request_id as string;
      setEditRequestId(rid);
      setEditStatus('queued');

      // poll
      for (let i = 0; i < 30; i++) {
        const st = await getDocEditState(rid);
        const statusText = (st as any)?.data?.status;
        setEditStatus(statusText);
        if (statusText === 'succeeded') {
          setEditPreview((st as any)?.data?.preview);
          break;
        }
        if (statusText === 'failed' || statusText === 'aborted') {
          setError((st as any)?.data?.error_message || '預覽失敗');
          break;
        }
        await new Promise((r) => setTimeout(r, 500));
      }
    } catch (e: any) {
      setError(e?.message || '建立編輯預覽失敗');
    } finally {
      setPreviewLoading(false);
    }
  };

  const applyEdit = async () => {
    if (!editRequestId) {
      setError('沒有可套用的預覽');
      return;
    }
    setApplyLoading(true);
    setError(null);
    try {
      const resp = await applyDocEdit(editRequestId);
      const newVersion = (resp as any)?.data?.new_version;
      setEditStatus('applied');
      await refreshVersions();
      // reload base content
      if (selectedFileId) {
        const pr = await previewFile(selectedFileId);
        setBaseContent(pr?.data?.content || '');
        setBaseFileType(pr?.data?.file_type || '');
      }
      if (typeof newVersion === 'number') {
        setCurrentDocVersion(newVersion);
      }
    } catch (e: any) {
      setError(e?.message || '套用失敗');
    } finally {
      setApplyLoading(false);
    }
  };

  const startGenerationPreview = async () => {
    if (!selectedTaskId) {
      setError('請先在左側選擇目標任務（Task）');
      return;
    }
    if (!genFilename.trim()) {
      setError('請輸入檔名');
      return;
    }
    if (!instruction.trim()) {
      setError('請輸入生成指令');
      return;
    }

    setError(null);
    setPreviewLoading(true);
    setGenPreviewContent('');

    try {
      const resp = await createDocGeneration({
        task_id: selectedTaskId,
        filename: genFilename,
        doc_format: genFormat,
        instruction,
      });
      const rid = (resp as any)?.data?.request_id as string;
      setGenRequestId(rid);
      setGenStatus('queued');

      for (let i = 0; i < 30; i++) {
        const st = await getDocGenerationState(rid);
        const statusText = (st as any)?.data?.status;
        setGenStatus(statusText);
        if (statusText === 'succeeded') {
          setGenPreviewContent((st as any)?.data?.preview?.content || '');
          break;
        }
        if (statusText === 'failed' || statusText === 'aborted') {
          setError((st as any)?.data?.error_message || '生成預覽失敗');
          break;
        }
        await new Promise((r) => setTimeout(r, 500));
      }
    } catch (e: any) {
      setError(e?.message || '建立生成預覽失敗');
    } finally {
      setPreviewLoading(false);
    }
  };

  const applyGeneration = async () => {
    if (!genRequestId) {
      setError('沒有可套用的生成預覽');
      return;
    }
    setApplyLoading(true);
    setError(null);
    try {
      const resp = await applyDocGeneration(genRequestId);
      const fileId = (resp as any)?.data?.file_id as string;
      if (fileId) {
        setSelectedFileId(fileId);
        setSelectedFileName(genFilename);
        setTab('edit');
        await refreshVersions();
      }
      setGenStatus('applied');
    } catch (e: any) {
      setError(e?.message || '建立文件失敗');
    } finally {
      setApplyLoading(false);
    }
  };

  const doRollback = async (toVersion: number) => {
    if (!selectedFileId) return;
    setApplyLoading(true);
    setError(null);
    try {
      await rollbackDocVersion(selectedFileId, toVersion);
      await refreshVersions();
      const pr = await previewFile(selectedFileId);
      setBaseContent(pr?.data?.content || '');
      setBaseFileType(pr?.data?.file_type || '');
    } catch (e: any) {
      setError(e?.message || '回滾失敗');
    } finally {
      setApplyLoading(false);
    }
  };

  useEffect(() => {
    // auto refresh versions when file changes
    refreshVersions().catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFileId]);

  return (
    <div className="h-screen flex flex-col">
      <div className="border-b bg-white p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileText className="w-6 h-6 text-blue-500" />
            <h1 className="text-2xl font-semibold">文件助手（Preview-first）</h1>
            {currentDocVersion !== null && (
              <span className="text-sm text-gray-500">版本 v{currentDocVersion}</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/files')}
              className="px-4 py-2 border rounded-lg hover:bg-gray-50 flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              返回文件管理
            </button>
          </div>
        </div>

        <div className="mt-3 flex items-center gap-2">
          <button
            onClick={() => setTab('edit')}
            className={`px-3 py-2 rounded-lg border ${tab === 'edit' ? 'bg-blue-50 border-blue-500' : 'hover:bg-gray-50'}`}
          >
            局部編輯
          </button>
          <button
            onClick={() => setTab('generate')}
            className={`px-3 py-2 rounded-lg border ${tab === 'generate' ? 'bg-blue-50 border-blue-500' : 'hover:bg-gray-50'}`}
          >
            生成新文件
          </button>
          <button
            onClick={() => refreshVersions()}
            className="px-3 py-2 rounded-lg border hover:bg-gray-50 flex items-center gap-2"
            disabled={!selectedFileId || versionsLoading}
            title="刷新版本"
          >
            <History className="w-4 h-4" />
            {versionsLoading ? '更新中' : '版本'}
          </button>
        </div>

        {error && (
          <div className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">
            {error}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-hidden flex">
        <div className="w-80 border-r border-gray-200 bg-white flex-shrink-0 overflow-auto">
          <FileTree
            userId={userId}
            selectedTaskId={selectedTaskId}
            onTaskSelect={(taskId) => {
              setSelectedTaskId(taskId);
            }}
            onFileSelect={(fileId, fileName) => {
              setSelectedFileId(fileId);
              setSelectedFileName(fileName || '');
              setTab('edit');
            }}
          />
        </div>

        <div className="flex-1 overflow-auto p-4 space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="border rounded-lg bg-white p-4">
              <div className="font-medium mb-2">指令</div>
              <textarea
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                className="w-full min-h-[120px] border rounded p-2"
                placeholder={tab === 'edit' ? '例如：把第 2 段改成…' : '例如：生成一份會議紀錄模板…'}
              />

              {tab === 'generate' && (
                <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-2">
                  <input
                    value={genFilename}
                    onChange={(e) => setGenFilename(e.target.value)}
                    className="border rounded p-2"
                    placeholder="new.md"
                  />
                  <select
                    value={genFormat}
                    onChange={(e) => setGenFormat(e.target.value as any)}
                    className="border rounded p-2"
                  >
                    <option value="md">md</option>
                    <option value="txt">txt</option>
                    <option value="json">json</option>
                  </select>
                  <div className="text-sm text-gray-500 flex items-center">
                    目標 task：{selectedTaskId || '未選擇'}
                  </div>
                </div>
              )}

              <div className="mt-4 flex gap-2">
                <button
                  onClick={tab === 'edit' ? startEditPreview : startGenerationPreview}
                  className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 flex items-center gap-2"
                  disabled={previewLoading}
                >
                  {previewLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
                  產生 Preview
                </button>
                <button
                  onClick={tab === 'edit' ? applyEdit : applyGeneration}
                  className="px-4 py-2 rounded bg-green-600 text-white hover:bg-green-700 flex items-center gap-2"
                  disabled={applyLoading || (tab === 'edit' ? !editPreview : !genPreviewContent)}
                >
                  {applyLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  Apply
                </button>
              </div>

              {tab === 'edit' && editStatus && (
                <div className="mt-3 text-sm text-gray-600">狀態：{editStatus}</div>
              )}
              {tab === 'generate' && genStatus && (
                <div className="mt-3 text-sm text-gray-600">狀態：{genStatus}</div>
              )}
            </div>

            <div className="border rounded-lg bg-white p-4">
              <div className="font-medium mb-2">版本與回滾</div>
              {!selectedFileId ? (
                <div className="text-sm text-gray-500">選擇文件後可查看版本與回滾</div>
              ) : versions.length === 0 ? (
                <div className="text-sm text-gray-500">尚無版本快照（首次 Apply 後會產生）</div>
              ) : (
                <div className="space-y-2">
                  {versions.slice().reverse().map((v, idx) => {
                    const ver = v?.version;
                    return (
                      <div key={idx} className="flex items-center justify-between border rounded p-2">
                        <div className="text-sm">
                          <div className="font-mono">v{ver}</div>
                          <div className="text-xs text-gray-500 truncate max-w-[280px]">{v?.summary || ''}</div>
                        </div>
                        <button
                          onClick={() => doRollback(Number(ver))}
                          className="px-3 py-1.5 border rounded hover:bg-gray-50"
                          disabled={applyLoading}
                        >
                          回滾到此版本
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {tab === 'edit' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="border rounded-lg bg-white p-4">
                <div className="font-medium mb-2">原文（Preview）</div>
                {!selectedFileId ? (
                  <div className="text-sm text-gray-500">請先選擇文件</div>
                ) : isMarkdown ? (
                  <MarkdownViewer content={baseContent} fileName={selectedFileName || 'document.md'} fileId={selectedFileId} />
                ) : (
                  <pre className="text-xs whitespace-pre-wrap break-words bg-gray-50 border rounded p-2 max-h-[520px] overflow-auto">
                    {baseContent}
                  </pre>
                )}
              </div>

              <div className="border rounded-lg bg-white p-4">
                <div className="font-medium mb-2">Patch Preview</div>
                {!editPreview ? (
                  <div className="text-sm text-gray-500">請先產生 Preview</div>
                ) : editPreview.patch_kind === 'json_patch' ? (
                  <pre className="text-xs whitespace-pre-wrap break-words bg-gray-50 border rounded p-2 max-h-[520px] overflow-auto">
                    {JSON.stringify(editPreview.patch, null, 2)}
                  </pre>
                ) : (
                  <pre className="text-xs whitespace-pre-wrap break-words bg-gray-50 border rounded p-2 max-h-[520px] overflow-auto">
                    {String(editPreview.patch || '')}
                  </pre>
                )}
                {editPreview?.summary ? (
                  <div className="mt-2 text-xs text-gray-600">摘要：{editPreview.summary}</div>
                ) : null}
                {isJson && editPreview?.patch_kind === 'json_patch' ? (
                  <div className="mt-2 text-xs text-gray-500">提示：JSON 會以 JSON Patch 方式套用，並在後端重新格式化（indent=2）</div>
                ) : null}
              </div>
            </div>
          )}

          {tab === 'generate' && (
            <div className="border rounded-lg bg-white p-4">
              <div className="font-medium mb-2">生成 Preview</div>
              {!genPreviewContent ? (
                <div className="text-sm text-gray-500">請先產生 Preview</div>
              ) : genFormat === 'md' ? (
                <MarkdownViewer content={genPreviewContent} fileName={genFilename || 'new.md'} />
              ) : (
                <pre className="text-xs whitespace-pre-wrap break-words bg-gray-50 border rounded p-2 max-h-[520px] overflow-auto">
                  {genPreviewContent}
                </pre>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
