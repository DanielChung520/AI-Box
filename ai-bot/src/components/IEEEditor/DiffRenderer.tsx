// 代碼功能說明: Diff 視覺化渲染組件（使用 Monaco Editor Decorations API）
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import { useEffect, useRef } from 'react';
import type { editor } from 'monaco-editor';
import * as monaco from 'monaco-editor';
import type { AIPatch, Range } from '../../types/draft';

interface DiffRendererProps {
  editor: editor.IStandaloneCodeEditor | null;
  patches: AIPatch[];
  content: string;
}

/**
 * 將自定義 Range 轉換為 Monaco Range
 */
function toMonacoRange(range: Range): monaco.IRange {
  return {
    startLineNumber: range.startLine,
    startColumn: range.startColumn,
    endLineNumber: range.endLine,
    endColumn: range.endColumn,
  };
}

/**
 * 計算文本在編輯器中的實際範圍
 * 根據原始文本和修改文本計算需要高亮的範圍
 */
function calculateDiffRanges(
  content: string,
  patch: AIPatch
): {
  deletionRange: monaco.IRange | null;
  additionRange: monaco.IRange | null;
} {
  const lines = content.split('\n');
  const originalRange = toMonacoRange(patch.originalRange);

  // 如果原始範圍超出內容範圍，返回 null
  if (
    originalRange.startLineNumber > lines.length ||
    originalRange.endLineNumber > lines.length
  ) {
    return { deletionRange: null, additionRange: null };
  }

  // 計算刪除範圍（原始文本的位置）
  const deletionRange: monaco.IRange = {
    startLineNumber: originalRange.startLineNumber,
    startColumn: originalRange.startColumn,
    endLineNumber: originalRange.endLineNumber,
    endColumn: originalRange.endColumn,
  };

  // 計算新增範圍（修改後文本的位置）
  // 對於新增內容，我們需要找到插入位置
  // 如果 originalText 和 modifiedText 不同，說明是修改
  // 如果 originalText 為空，說明是純新增
  // 如果 modifiedText 為空，說明是純刪除

  let additionRange: monaco.IRange | null = null;

  if (patch.modifiedText && patch.modifiedText !== patch.originalText) {
    // 計算修改後文本的範圍
    const modifiedLines = patch.modifiedText.split('\n');
    const modifiedLineCount = modifiedLines.length;

    if (modifiedLineCount === 1) {
      // 單行修改
      additionRange = {
        startLineNumber: originalRange.startLineNumber,
        startColumn: originalRange.startColumn,
        endLineNumber: originalRange.startLineNumber,
        endColumn: originalRange.startColumn + modifiedLines[0].length,
      };
    } else {
      // 多行修改
      const lastLine = modifiedLines[modifiedLines.length - 1];
      additionRange = {
        startLineNumber: originalRange.startLineNumber,
        startColumn: originalRange.startColumn,
        endLineNumber: originalRange.startLineNumber + modifiedLineCount - 1,
        endColumn: lastLine.length + 1,
      };
    }
  }

  return { deletionRange, additionRange };
}

/**
 * Diff 視覺化渲染組件
 * 使用 Monaco Editor Decorations API 實現紅/綠色高亮
 */
export default function DiffRenderer({ editor, patches, content }: DiffRendererProps) {
  const decorationIdsRef = useRef<string[]>([]);

  useEffect(() => {
    if (!editor) {
      return;
    }

    // 只處理 pending_review 狀態的 patches
    const pendingPatches = patches.filter((patch) => patch.status === 'pending_review');

    if (pendingPatches.length === 0) {
      // 清除所有裝飾器
      if (decorationIdsRef.current.length > 0) {
        editor.deltaDecorations(decorationIdsRef.current, []);
        decorationIdsRef.current = [];
      }
      return;
    }

    // 定義裝飾器樣式（不再需要，直接使用內聯樣式）

    // 為每個 patch 創建裝飾器
    const decorations: editor.IModelDeltaDecoration[] = [];

    for (const patch of pendingPatches) {
      const { deletionRange, additionRange } = calculateDiffRanges(content, patch);

      // 添加刪除裝飾器（紅色中劃線）
      if (deletionRange) {
        decorations.push({
          range: deletionRange,
          options: {
            className: 'diff-deletion',
            isWholeLine: false,
            inlineClassName: 'diff-deletion-inline',
            overviewRuler: {
              color: '#ff6b6b',
              position: monaco.editor.OverviewRulerLane.Left,
            },
            hoverMessage: {
              value: `刪除: ${patch.originalText.substring(0, 50)}${patch.originalText.length > 50 ? '...' : ''}`,
            },
          },
        });
      }

      // 添加新增裝飾器（綠色背景）
      if (additionRange) {
        decorations.push({
          range: additionRange,
          options: {
            className: 'diff-addition',
            isWholeLine: false,
            inlineClassName: 'diff-addition-inline',
            overviewRuler: {
              color: '#51cf66',
              position: monaco.editor.OverviewRulerLane.Left,
            },
            hoverMessage: {
              value: `新增: ${patch.modifiedText.substring(0, 50)}${patch.modifiedText.length > 50 ? '...' : ''}`,
            },
          },
        });
      }
    }

    // 更新裝飾器
    const newDecorationIds = editor.deltaDecorations(decorationIdsRef.current, decorations);
    decorationIdsRef.current = newDecorationIds;

    // 清理函數
    return () => {
      if (decorationIdsRef.current.length > 0) {
        editor.deltaDecorations(decorationIdsRef.current, []);
        decorationIdsRef.current = [];
      }
    };
  }, [editor, patches, content]);

  // 這個組件不渲染任何 UI，只管理裝飾器
  return null;
}

