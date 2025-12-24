// 代碼功能說明: Monaco Editor 組件
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import { useRef } from 'react';
import Editor from '@monaco-editor/react';
import type { editor } from 'monaco-editor';

export interface MonacoEditorProps {
  value: string;
  onChange?: (value: string) => void;
  language?: string;
  theme?: string;
  readOnly?: boolean;
  onMount?: (editor: editor.IStandaloneCodeEditor) => void;
  height?: string;
  options?: editor.IStandaloneEditorConstructionOptions;
}

export default function MonacoEditor({
  value,
  onChange,
  language = 'markdown',
  theme = 'vs-dark',
  readOnly = false,
  onMount,
  height = '100%',
  options,
}: MonacoEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);

  const handleEditorDidMount = (editor: editor.IStandaloneCodeEditor) => {
    editorRef.current = editor;
    if (onMount) {
      onMount(editor);
    }
  };

  const defaultOptions: editor.IStandaloneEditorConstructionOptions = {
    fontSize: 14,
    lineNumbers: 'on',
    wordWrap: 'on',
    tabSize: 2,
    insertSpaces: true,
    minimap: { enabled: true },
    scrollBeyondLastLine: false,
    automaticLayout: true,
    ...options,
  };

  return (
    <Editor
      height={height}
      language={language}
      theme={theme}
      value={value}
      onChange={(newValue) => {
        if (onChange) {
          onChange(newValue || '');
        }
      }}
      onMount={handleEditorDidMount}
      options={{
        ...defaultOptions,
        readOnly,
      }}
    />
  );
}
