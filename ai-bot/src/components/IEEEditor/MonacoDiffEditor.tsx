// 代碼功能說明: Monaco Diff Editor 封裝組件
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import { useRef } from 'react';
import { DiffEditor } from '@monaco-editor/react';
import type { editor } from 'monaco-editor';

export interface MonacoDiffEditorProps {
  original: string;
  modified: string;
  language?: string;
  theme?: string;
  onMount?: (editor: editor.IStandaloneDiffEditor) => void;
  height?: string;
  options?: editor.IStandaloneDiffEditorConstructionOptions;
}

export default function MonacoDiffEditor({
  original,
  modified,
  language = 'markdown',
  theme = 'vs-dark',
  onMount,
  height = '100%',
  options,
}: MonacoDiffEditorProps) {
  const editorRef = useRef<editor.IStandaloneDiffEditor | null>(null);

  const handleEditorDidMount = (editor: editor.IStandaloneDiffEditor) => {
    editorRef.current = editor;

    // 配置同步滾動（Monaco Diff Editor 默認啟用同步滾動）
    const originalEditor = editor.getOriginalEditor();
    const modifiedEditor = editor.getModifiedEditor();

    // 確保兩個編輯器使用相同的滾動設置
    originalEditor.updateOptions({ scrollBeyondLastLine: false });
    modifiedEditor.updateOptions({ scrollBeyondLastLine: false });

    if (onMount) {
      onMount(editor);
    }
  };

  const defaultOptions: editor.IStandaloneDiffEditorConstructionOptions = {
    fontSize: 14,
    lineNumbers: 'on',
    wordWrap: 'on',
    readOnly: true,
    renderSideBySide: true,
    enableSplitViewResizing: true,
    automaticLayout: true,
    scrollBeyondLastLine: false,
    minimap: { enabled: true },
    ...options,
  };

  return (
    <DiffEditor
      height={height}
      language={language}
      theme={theme}
      original={original}
      modified={modified}
      options={defaultOptions}
      onMount={handleEditorDidMount}
    />
  );
}
