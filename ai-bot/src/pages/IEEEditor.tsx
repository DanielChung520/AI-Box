// 代碼功能說明: IEE 編輯器主頁面
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import { useState, useEffect, useCallback } from 'react';
import MonacoEditor from '../components/MonacoEditor';
import Toolbar from '../components/IEEEditor/Toolbar';
import Sidebar from '../components/IEEEditor/Sidebar';
import StatusBar from '../components/IEEEditor/StatusBar';
import DiffRenderer from '../components/IEEEditor/DiffRenderer';
import GutterActions from '../components/IEEEditor/GutterActions';
import MermaidPreview from '../components/IEEEditor/MermaidPreview';
import ReviewModal from '../components/IEEEditor/ReviewModal';
import MarkdownViewer from '../components/MarkdownViewer';
import { useDraftStore } from '../stores/draftStore';
import { useAutoSave } from '../hooks/useAutoSave';
import { previewFile, downloadFile } from '../lib/api';
import type { editor } from 'monaco-editor';
import * as monaco from 'monaco-editor';
import { toast } from 'sonner';

interface IEEEditorProps {
  fileId?: string;
  onClose?: () => void;
}

export default function IEEEditor({ fileId }: IEEEditorProps) {
  const [editorInstance, setEditorInstance] = useState<editor.IStandaloneCodeEditor | null>(null);
  const [currentLine, setCurrentLine] = useState<number>(1);
  const [currentColumn, setCurrentColumn] = useState<number>(1);
  const [fileName, setFileName] = useState<string>('');
  const [filePath, setFilePath] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [showPreview, setShowPreview] = useState<boolean>(false); // 是否显示预览面板
  const [isReviewModalOpen, setIsReviewModalOpen] = useState<boolean>(false);

  const {
    draftContent,
    stableContent,
    setStableContent,
    setDraftContent,
    hasUnsavedChanges,
    setAutoSaveStatus,
    clearFileState,
    patches,
    applyPatch,
    rejectPatch,
  } = useDraftStore();

  const { manualSave } = useAutoSave({
    fileId: fileId || null,
    delay: 2000,
  });

  // 加载文件内容
  const loadFile = useCallback(async (id: string) => {
    if (!id) return;

    setIsLoading(true);
    try {
      // 尝试使用 previewFile API 获取文件内容
      const preview = await previewFile(id);
      if (preview.success && preview.data) {
        const content = preview.data.content || '';
        setStableContent(id, content);
        setFileName(preview.data.filename || '');
        // file_path 可能不存在，使用空字符串
        setFilePath('');
      } else {
        // 如果 preview 失败，尝试下载文件
        try {
          const blob = await downloadFile(id);
          const text = await blob.text();
          setStableContent(id, text);
        } catch (error) {
          console.error('Failed to load file:', error);
          toast.error('無法載入文件');
        }
      }
    } catch (error) {
      console.error('Failed to load file:', error);
      toast.error('無法載入文件');
    } finally {
      setIsLoading(false);
    }
  }, [setStableContent]);

  // 初始化加载文件
  useEffect(() => {
    if (fileId) {
      loadFile(fileId);
    }

    // 清理函数
    return () => {
      if (fileId) {
        clearFileState(fileId);
      }
    };
  }, [fileId, loadFile, clearFileState]);

  // 监听编辑器光标位置变化
  useEffect(() => {
    if (!editorInstance) return;

    const disposable = editorInstance.onDidChangeCursorPosition((e) => {
      setCurrentLine(e.position.lineNumber);
      setCurrentColumn(e.position.column);
    });

    return () => {
      disposable.dispose();
    };
  }, [editorInstance]);

  // 处理编辑器内容变化
  const handleEditorChange = useCallback(
    (value: string) => {
      if (fileId) {
        setDraftContent(fileId, value);
      }
    },
    [fileId, setDraftContent]
  );

  // 处理编辑器挂载
  const handleEditorMount = useCallback((editor: editor.IStandaloneCodeEditor) => {
    setEditorInstance(editor);

    // 注册键盘快捷键
    // Accept: Ctrl+Enter
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      if (!fileId) return;
      const pendingPatches = patches[fileId]?.filter((p) => p.status === 'pending_review') || [];
      if (pendingPatches.length > 0) {
        // 接受当前光标所在行的第一个 patch
        const position = editor.getPosition();
        if (position) {
          const linePatches = pendingPatches.filter(
            (p) => p.originalRange.startLine === position.lineNumber
          );
          if (linePatches.length > 0) {
            applyPatch(fileId, linePatches[0].id);
            toast.success('修改已接受');
          } else {
            // 如果没有当前行的 patch，接受第一个
            applyPatch(fileId, pendingPatches[0].id);
            toast.success('修改已接受');
          }
        } else {
          applyPatch(fileId, pendingPatches[0].id);
          toast.success('修改已接受');
        }
      }
    });

    // Reject: Ctrl+Shift+Enter
    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.Enter,
      () => {
        if (!fileId) return;
        const pendingPatches = patches[fileId]?.filter((p) => p.status === 'pending_review') || [];
        if (pendingPatches.length > 0) {
          // 拒绝当前光标所在行的第一个 patch
          const position = editor.getPosition();
          if (position) {
            const linePatches = pendingPatches.filter(
              (p) => p.originalRange.startLine === position.lineNumber
            );
            if (linePatches.length > 0) {
              rejectPatch(fileId, linePatches[0].id);
              toast.success('修改已拒絕');
            } else {
              // 如果没有当前行的 patch，拒绝第一个
              rejectPatch(fileId, pendingPatches[0].id);
              toast.success('修改已拒絕');
            }
          } else {
            rejectPatch(fileId, pendingPatches[0].id);
            toast.success('修改已拒絕');
          }
        }
      }
    );
  }, [fileId, patches, applyPatch, rejectPatch]);

  // 处理保存
  const handleSave = useCallback(async () => {
    if (!fileId) return;

    try {
      setAutoSaveStatus(fileId, 'saving');
      await manualSave();
      toast.success('文件已保存');
    } catch (error) {
      console.error('Failed to save file:', error);
      toast.error('保存失敗');
    }
  }, [fileId, manualSave, setAutoSaveStatus]);

  // 处理审查
  const handleReview = useCallback(() => {
    if (!fileId) return;
    setIsReviewModalOpen(true);
  }, [fileId]);

  // 处理提交（从 Review Modal 触发）
  const handleCommit = useCallback(() => {
    // TODO: 实现提交逻辑（将在任务 5.2 中实现）
    toast.info('提交功能即将实现');
  }, []);

  // 处理关闭（暂时不使用，保留以备将来使用）
  // const handleClose = useCallback(() => {
  //   if (fileId && hasUnsavedChanges(fileId)) {
  //     if (!confirm('有未保存的變更，確定要關閉嗎？')) {
  //       return;
  //     }
  //   }
  //   if (onClose) {
  //     onClose();
  //   }
  // }, [fileId, hasUnsavedChanges, onClose]);

  // 获取当前文件内容
  const currentContent = fileId ? draftContent[fileId] || stableContent[fileId] || '' : '';
  const isSaved = fileId ? !hasUnsavedChanges(fileId) : true;
  const isSaving = fileId ? useDraftStore.getState().autoSaveStatus[fileId] === 'saving' : false;

  // 计算文件统计信息
  const totalLines = currentContent.split('\n').length;
  const totalChars = currentContent.length;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-gray-600 dark:text-gray-400">載入中...</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full w-full bg-white dark:bg-gray-900">
      <Toolbar
        onSave={handleSave}
        onReview={handleReview}
        onCommit={handleCommit}
        isSaving={isSaving}
        hasUnsavedChanges={!isSaved}
        showPreview={showPreview}
        onTogglePreview={() => setShowPreview(!showPreview)}
      />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          content={currentContent}
          editor={editorInstance}
          currentLine={currentLine}
        />
        <div className="flex-1 flex flex-col relative">
          <div className={`flex flex-1 overflow-hidden ${showPreview ? 'flex-row' : ''}`}>
            {/* 编辑器区域 */}
            <div className={`flex flex-col ${showPreview ? 'w-1/2 border-r border-gray-300 dark:border-gray-700' : 'flex-1'}`}>
              <div className="flex-1 relative">
                <MonacoEditor
                  value={currentContent}
                  onChange={handleEditorChange}
                  onMount={handleEditorMount}
                  language="markdown"
                  height="100%"
                  readOnly={false}
                  options={{
                    wordWrap: 'on',
                    lineNumbers: 'on',
                    minimap: { enabled: true },
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    formatOnPaste: true,
                    formatOnType: true,
                  }}
                />
                {fileId && (
                  <>
                    <DiffRenderer
                      editor={editorInstance}
                      patches={patches[fileId] || []}
                      content={currentContent}
                    />
                    <GutterActions
                      editor={editorInstance}
                      patches={patches[fileId] || []}
                      onAccept={(patchId) => {
                        if (fileId) {
                          applyPatch(fileId, patchId);
                          toast.success('修改已接受');
                        }
                      }}
                      onReject={(patchId) => {
                        if (fileId) {
                          rejectPatch(fileId, patchId);
                          toast.success('修改已拒絕');
                        }
                      }}
                    />
                    <MermaidPreview editor={editorInstance} content={currentContent} />
                  </>
                )}
              </div>
            </div>
            {/* 预览面板 */}
            {showPreview && (
              <div className="w-1/2 flex flex-col bg-white dark:bg-gray-900 overflow-hidden">
                <div className="p-2 border-b border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                  <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">Markdown 預覽</h3>
                </div>
                <div className="flex-1 overflow-y-auto p-4">
                  <MarkdownViewer
                    content={currentContent}
                    fileName={fileName || 'document.md'}
                    fileId={fileId}
                  />
                </div>
              </div>
            )}
          </div>
          {/* 状态栏 */}
          <StatusBar
            fileName={fileName}
            filePath={filePath}
            isSaved={isSaved}
            isSaving={isSaving}
            cursorLine={currentLine}
            cursorColumn={currentColumn}
            totalLines={totalLines}
            totalChars={totalChars}
          />
        </div>
      </div>
      {/* Review Modal */}
      {fileId && (
        <ReviewModal
          isOpen={isReviewModalOpen}
          onClose={() => setIsReviewModalOpen(false)}
          fileId={fileId}
          modifiedContent={currentContent}
          onCommit={handleCommit}
        />
      )}
    </div>
  );
}
