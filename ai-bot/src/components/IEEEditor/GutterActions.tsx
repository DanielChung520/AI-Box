// 代碼功能說明: 側邊欄 Accept/Reject 按鈕組件
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import { useEffect, useRef } from 'react';
import type { editor } from 'monaco-editor';
import * as monaco from 'monaco-editor';
import type { AIPatch } from '../../types/draft';

interface GutterActionsProps {
  editor: editor.IStandaloneCodeEditor | null;
  patches: AIPatch[];
  onAccept: (patchId: string) => void;
  onReject: (patchId: string) => void;
}

/**
 * 側邊欄操作按鈕組件
 * 在 Gutter（側邊欄）顯示 Accept/Reject 圖標
 */
export default function GutterActions({
  editor,
  patches,
  onAccept,
  onReject,
}: GutterActionsProps) {
  const decorationIdsRef = useRef<string[]>([]);
  const widgetRefsRef = useRef<Map<string, editor.IContentWidget>>(new Map());

  useEffect(() => {
    if (!editor) {
      return;
    }

    // 只處理 pending_review 狀態的 patches
    const pendingPatches = patches.filter((patch) => patch.status === 'pending_review');

    // 清理舊的 widgets
    widgetRefsRef.current.forEach((widget) => {
      editor.removeContentWidget(widget);
    });
    widgetRefsRef.current.clear();

    // 清除舊的裝飾器
    if (decorationIdsRef.current.length > 0) {
      editor.deltaDecorations(decorationIdsRef.current, []);
      decorationIdsRef.current = [];
    }

    if (pendingPatches.length === 0) {
      return;
    }

    // 為每個 patch 創建 Content Widget 用於顯示按鈕
    for (const patch of pendingPatches) {
      const startLine = patch.originalRange.startLine;

      // 創建 Content Widget
      const widget: editor.IContentWidget = {
        getId: () => `gutter-action-${patch.id}`,
        getDomNode: () => {
          const container = document.createElement('div');
          container.className = 'gutter-action-container';
          container.style.display = 'flex';
          container.style.gap = '4px';
          container.style.alignItems = 'center';
          container.style.padding = '2px 4px';
          container.style.backgroundColor = 'var(--vscode-editor-background, #1e1e1e)';
          container.style.border = '1px solid var(--vscode-panel-border, #3e3e3e)';
          container.style.borderRadius = '4px';
          container.style.cursor = 'pointer';
          container.style.zIndex = '1000';

          // Accept 按鈕
          const acceptBtn = document.createElement('button');
          acceptBtn.className = 'gutter-action-btn gutter-action-accept';
          acceptBtn.innerHTML = '✓';
          acceptBtn.title = '接受修改 (Ctrl+Enter)';
          acceptBtn.style.cssText = `
            background: #51cf66;
            color: white;
            border: none;
            border-radius: 3px;
            width: 20px;
            height: 20px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            transition: opacity 0.2s;
          `;
          acceptBtn.onmouseenter = () => {
            acceptBtn.style.opacity = '0.8';
          };
          acceptBtn.onmouseleave = () => {
            acceptBtn.style.opacity = '1';
          };
          acceptBtn.onclick = (e) => {
            e.stopPropagation();
            e.preventDefault();
            onAccept(patch.id);
          };

          // Reject 按鈕
          const rejectBtn = document.createElement('button');
          rejectBtn.className = 'gutter-action-btn gutter-action-reject';
          rejectBtn.innerHTML = '✗';
          rejectBtn.title = '拒絕修改 (Ctrl+Shift+Enter)';
          rejectBtn.style.cssText = `
            background: #ff6b6b;
            color: white;
            border: none;
            border-radius: 3px;
            width: 20px;
            height: 20px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            transition: opacity 0.2s;
          `;
          rejectBtn.onmouseenter = () => {
            rejectBtn.style.opacity = '0.8';
          };
          rejectBtn.onmouseleave = () => {
            rejectBtn.style.opacity = '1';
          };
          rejectBtn.onclick = (e) => {
            e.stopPropagation();
            e.preventDefault();
            onReject(patch.id);
          };

          container.appendChild(acceptBtn);
          container.appendChild(rejectBtn);

          return container;
        },
        getPosition: () => {
          return {
            position: {
              lineNumber: startLine,
              column: 1,
            },
            preference: [
              monaco.editor.ContentWidgetPositionPreference.ABOVE,
            ] as editor.ContentWidgetPositionPreference[],
          };
        },
      };

      editor.addContentWidget(widget);
      widgetRefsRef.current.set(patch.id, widget);
    }

    // 清理函數
    return () => {
      // 移除所有 widgets
      widgetRefsRef.current.forEach((widget) => {
        editor.removeContentWidget(widget);
      });
      widgetRefsRef.current.clear();

      // 清除裝飾器
      if (decorationIdsRef.current.length > 0) {
        editor.deltaDecorations(decorationIdsRef.current, []);
        decorationIdsRef.current = [];
      }
    };
  }, [editor, patches, onAccept, onReject]);

  // 這個組件不渲染任何 UI，只管理 Gutter 操作
  return null;
}

