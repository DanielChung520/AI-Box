/**
 * 代碼功能說明: FileEditStatus 組件單元測試
 * 創建日期: 2026-01-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-06
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import FileEditStatus from '../../../src/components/FileEditStatus';

describe('FileEditStatus', () => {
  const mockOnAccept = vi.fn();
  const mockOnReject = vi.fn();
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該渲染三個操作按鈕', () => {
    render(
      <FileEditStatus
        onAccept={mockOnAccept}
        onReject={mockOnReject}
        onSubmit={mockOnSubmit}
      />
    );

    expect(screen.getByText('接受')).toBeInTheDocument();
    expect(screen.getByText('拒絕')).toBeInTheDocument();
    expect(screen.getByText('提交')).toBeInTheDocument();
  });

  it('應該在點擊接受按鈕時調用 onAccept', async () => {
    const user = userEvent.setup();
    render(
      <FileEditStatus
        onAccept={mockOnAccept}
        onReject={mockOnReject}
        onSubmit={mockOnSubmit}
      />
    );

    const acceptButton = screen.getByLabelText('接受修改');
    await user.click(acceptButton);

    expect(mockOnAccept).toHaveBeenCalledTimes(1);
    expect(mockOnReject).not.toHaveBeenCalled();
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('應該在點擊拒絕按鈕時調用 onReject', async () => {
    const user = userEvent.setup();
    render(
      <FileEditStatus
        onAccept={mockOnAccept}
        onReject={mockOnReject}
        onSubmit={mockOnSubmit}
      />
    );

    const rejectButton = screen.getByLabelText('拒絕修改');
    await user.click(rejectButton);

    expect(mockOnReject).toHaveBeenCalledTimes(1);
    expect(mockOnAccept).not.toHaveBeenCalled();
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('應該在點擊提交按鈕時調用 onSubmit', async () => {
    const user = userEvent.setup();
    render(
      <FileEditStatus
        onAccept={mockOnAccept}
        onReject={mockOnReject}
        onSubmit={mockOnSubmit}
      />
    );

    const submitButton = screen.getByLabelText('提交修改到後端');
    await user.click(submitButton);

    expect(mockOnSubmit).toHaveBeenCalledTimes(1);
    expect(mockOnAccept).not.toHaveBeenCalled();
    expect(mockOnReject).not.toHaveBeenCalled();
  });

  it('應該在提交中時顯示加載狀態', () => {
    render(
      <FileEditStatus
        onAccept={mockOnAccept}
        onReject={mockOnReject}
        onSubmit={mockOnSubmit}
        isSubmitting={true}
      />
    );

    expect(screen.getByText('提交中...')).toBeInTheDocument();
    const submitButton = screen.getByLabelText('提交修改到後端');
    expect(submitButton).toBeDisabled();
  });

  it('應該在未提交時顯示正常提交按鈕', () => {
    render(
      <FileEditStatus
        onAccept={mockOnAccept}
        onReject={mockOnReject}
        onSubmit={mockOnSubmit}
        isSubmitting={false}
      />
    );

    expect(screen.getByText('提交')).toBeInTheDocument();
    const submitButton = screen.getByLabelText('提交修改到後端');
    expect(submitButton).not.toBeDisabled();
  });

  it('應該正確設置按鈕的 aria-label', () => {
    render(
      <FileEditStatus
        onAccept={mockOnAccept}
        onReject={mockOnReject}
        onSubmit={mockOnSubmit}
      />
    );

    expect(screen.getByLabelText('接受修改')).toBeInTheDocument();
    expect(screen.getByLabelText('拒絕修改')).toBeInTheDocument();
    expect(screen.getByLabelText('提交修改到後端')).toBeInTheDocument();
  });
});
