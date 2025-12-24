// 代碼功能說明: Monaco Editor 組件測試
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import MonacoEditor from '../../../src/components/MonacoEditor';

// Mock Monaco Editor
const mockEditorInstance = {
  revealLineInCenter: vi.fn(),
  setPosition: vi.fn(),
  focus: vi.fn(),
  onDidChangeCursorPosition: vi.fn(() => ({ dispose: vi.fn() })),
  dispose: vi.fn(),
};

vi.mock('@monaco-editor/react', () => ({
  default: ({ value, onChange, onMount, language, theme, height, options }: any) => {
    // 模擬編輯器掛載
    if (onMount) {
      setTimeout(() => {
        onMount(mockEditorInstance);
      }, 0);
    }
    
    return (
      <div data-testid="monaco-editor" data-language={language} data-theme={theme} data-height={height}>
        <textarea
          data-testid="monaco-editor-textarea"
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          readOnly={options?.readOnly}
        />
      </div>
    );
  },
}));

describe('MonacoEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該渲染編輯器', () => {
    render(<MonacoEditor value="測試內容" />);
    
    expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
  });

  it('應該顯示初始內容', () => {
    render(<MonacoEditor value="初始內容" />);
    
    const textarea = screen.getByTestId('monaco-editor-textarea') as HTMLTextAreaElement;
    expect(textarea.value).toBe('初始內容');
  });

  it('應該使用默認語言和主題', () => {
    render(<MonacoEditor value="內容" />);
    
    const editor = screen.getByTestId('monaco-editor');
    expect(editor).toHaveAttribute('data-language', 'markdown');
    expect(editor).toHaveAttribute('data-theme', 'vs-dark');
  });

  it('應該支持自定義語言和主題', () => {
    render(<MonacoEditor value="內容" language="javascript" theme="vs-light" />);
    
    const editor = screen.getByTestId('monaco-editor');
    expect(editor).toHaveAttribute('data-language', 'javascript');
    expect(editor).toHaveAttribute('data-theme', 'vs-light');
  });

  it('應該在掛載時調用 onMount 回調', async () => {
    const handleMount = vi.fn();
    render(<MonacoEditor value="內容" onMount={handleMount} />);
    
    await waitFor(() => {
      expect(handleMount).toHaveBeenCalledWith(mockEditorInstance);
    });
  });

  it('應該支持只讀模式', () => {
    render(<MonacoEditor value="內容" readOnly={true} />);
    
    const textarea = screen.getByTestId('monaco-editor-textarea') as HTMLTextAreaElement;
    expect(textarea.readOnly).toBe(true);
  });

  it('應該支持編輯模式', () => {
    render(<MonacoEditor value="內容" readOnly={false} />);
    
    const textarea = screen.getByTestId('monaco-editor-textarea') as HTMLTextAreaElement;
    expect(textarea.readOnly).toBe(false);
  });

  it('應該支持自定義高度', () => {
    render(<MonacoEditor value="內容" height="500px" />);
    
    const editor = screen.getByTestId('monaco-editor');
    expect(editor).toHaveAttribute('data-height', '500px');
  });
});
