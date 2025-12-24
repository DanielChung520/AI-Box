// 代碼功能說明: IEE Editor 頁面測試
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import IEEEditor from '../../../src/pages/IEEEditor';
import { useDraftStore } from '../../../src/stores/draftStore';
import * as apiModule from '../../../src/lib/api';

// Mock API
vi.mock('../../../src/lib/api', () => ({
  previewFile: vi.fn(),
  downloadFile: vi.fn(),
  saveFile: vi.fn(),
}));

// Mock toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock Monaco Editor
vi.mock('../../../src/components/MonacoEditor', () => ({
  default: ({ value, onChange, onMount }: any) => {
    if (onMount) {
      setTimeout(() => {
        onMount({
          onDidChangeCursorPosition: vi.fn(() => ({ dispose: vi.fn() })),
        });
      }, 0);
    }
    return (
      <div data-testid="monaco-editor">
        <textarea
          data-testid="editor-textarea"
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
        />
      </div>
    );
  },
}));

// Mock 子組件
vi.mock('../../../src/components/IEEEditor/Toolbar', () => ({
  default: ({ onSave, isSaving, hasUnsavedChanges }: any) => (
    <div data-testid="toolbar">
      <button data-testid="save-button" onClick={onSave} disabled={isSaving}>
        {isSaving ? '保存中...' : '保存'}
      </button>
      {hasUnsavedChanges && <span data-testid="unsaved-indicator">未保存</span>}
    </div>
  ),
}));

vi.mock('../../../src/components/IEEEditor/Sidebar', () => ({
  default: ({ content, editor, currentLine }: any) => (
    <div data-testid="sidebar">
      <div data-testid="sidebar-content">{content}</div>
      <div data-testid="current-line">Line: {currentLine}</div>
    </div>
  ),
}));

vi.mock('../../../src/components/IEEEditor/StatusBar', () => ({
  default: ({ fileName, isSaved, cursorLine, cursorColumn, totalLines, totalChars }: any) => (
    <div data-testid="status-bar">
      <span data-testid="file-name">{fileName}</span>
      <span data-testid="save-status">{isSaved ? '已保存' : '未保存'}</span>
      <span data-testid="cursor-position">{cursorLine}:{cursorColumn}</span>
      <span data-testid="file-stats">{totalLines} lines, {totalChars} chars</span>
    </div>
  ),
}));

describe('IEEEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    const store = useDraftStore.getState();
    store.clearFileState('test-file-1');
  });

  it('應該渲染編輯器頁面', () => {
    render(<IEEEditor fileId="test-file-1" />);
    
    expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
    expect(screen.getByTestId('toolbar')).toBeInTheDocument();
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('status-bar')).toBeInTheDocument();
  });

  it('應該在加載時顯示載入狀態', async () => {
    const mockPreviewFile = vi.mocked(apiModule.previewFile);
    mockPreviewFile.mockImplementation(() => new Promise(() => {})); // 永遠不 resolve

    render(<IEEEditor fileId="test-file-1" />);
    
    expect(screen.getByText('載入中...')).toBeInTheDocument();
  });

  it('應該從 previewFile API 加載文件內容', async () => {
    const mockPreviewFile = vi.mocked(apiModule.previewFile);
    mockPreviewFile.mockResolvedValue({
      success: true,
      data: {
        content: '# 測試文件\n\n這是測試內容',
        filename: 'test.md',
        file_path: '/path/to/test.md',
      },
    });

    render(<IEEEditor fileId="test-file-1" />);

    await waitFor(() => {
      expect(mockPreviewFile).toHaveBeenCalledWith('test-file-1');
    });

    await waitFor(() => {
      const store = useDraftStore.getState();
      expect(store.stableContent['test-file-1']).toBe('# 測試文件\n\n這是測試內容');
    });
  });

  it('應該在 previewFile 失敗時嘗試 downloadFile', async () => {
    const mockPreviewFile = vi.mocked(apiModule.previewFile);
    const mockDownloadFile = vi.mocked(apiModule.downloadFile);
    
    mockPreviewFile.mockResolvedValue({
      success: false,
      data: null,
    });
    
    mockDownloadFile.mockResolvedValue(new Blob(['下載的內容'], { type: 'text/plain' }));

    render(<IEEEditor fileId="test-file-1" />);

    await waitFor(() => {
      expect(mockPreviewFile).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockDownloadFile).toHaveBeenCalledWith('test-file-1');
    });
  });

  it('應該支持編輯器內容變化', async () => {
    const mockPreviewFile = vi.mocked(apiModule.previewFile);
    mockPreviewFile.mockResolvedValue({
      success: true,
      data: {
        content: '原始內容',
        filename: 'test.md',
      },
    });

    render(<IEEEditor fileId="test-file-1" />);

    await waitFor(() => {
      expect(screen.getByTestId('editor-textarea')).toBeInTheDocument();
    });

    const textarea = screen.getByTestId('editor-textarea') as HTMLTextAreaElement;
    
    // 模擬內容變化
    textarea.value = '修改後的內容';
    textarea.dispatchEvent(new Event('change', { bubbles: true }));

    await waitFor(() => {
      const store = useDraftStore.getState();
      expect(store.draftContent['test-file-1']).toBe('修改後的內容');
    });
  });

  it('應該支持手動保存', async () => {
    const mockPreviewFile = vi.mocked(apiModule.previewFile);
    const mockSaveFile = vi.mocked(apiModule.saveFile);
    
    mockPreviewFile.mockResolvedValue({
      success: true,
      data: {
        content: '原始內容',
        filename: 'test.md',
      },
    });
    
    mockSaveFile.mockResolvedValue({ success: true });

    render(<IEEEditor fileId="test-file-1" />);

    await waitFor(() => {
      expect(screen.getByTestId('save-button')).toBeInTheDocument();
    });

    const saveButton = screen.getByTestId('save-button');
    saveButton.click();

    await waitFor(() => {
      expect(mockSaveFile).toHaveBeenCalled();
    });
  });

  it('應該顯示文件統計信息', async () => {
    const mockPreviewFile = vi.mocked(apiModule.previewFile);
    mockPreviewFile.mockResolvedValue({
      success: true,
      data: {
        content: '第一行\n第二行\n第三行',
        filename: 'test.md',
      },
    });

    render(<IEEEditor fileId="test-file-1" />);

    await waitFor(() => {
      expect(screen.getByTestId('file-stats')).toHaveTextContent('3 lines, 11 chars');
    });
  });

  it('應該在沒有 fileId 時正常渲染', () => {
    render(<IEEEditor />);
    
    expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
  });
});
