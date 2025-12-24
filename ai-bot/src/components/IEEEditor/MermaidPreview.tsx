// 代碼功能說明: Mermaid 即時預覽組件
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import { useEffect, useRef, useState, useMemo } from 'react';
import type { editor } from 'monaco-editor';
import * as monaco from 'monaco-editor';

interface MermaidBlock {
  id: string;
  startLine: number;
  endLine: number;
  code: string;
}

interface MermaidPreviewProps {
  editor: editor.IStandaloneCodeEditor | null;
  content: string;
}

/**
 * 檢測 Markdown 中的 Mermaid 代碼塊
 */
function detectMermaidBlocks(content: string): MermaidBlock[] {
  const blocks: MermaidBlock[] = [];
  const lines = content.split('\n');
  let currentBlock: { startLine: number; code: string } | null = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmedLine = line.trim();

    // 檢測 Mermaid 代碼塊開始
    if (trimmedLine.startsWith('```mermaid') || trimmedLine === '```mermaid') {
      currentBlock = {
        startLine: i + 1, // Monaco Editor 使用 1-based 行號
        code: '',
      };
    }
    // 檢測代碼塊結束
    else if (trimmedLine === '```' && currentBlock) {
      blocks.push({
        id: `mermaid-${currentBlock.startLine}`,
        startLine: currentBlock.startLine,
        endLine: i + 1,
        code: currentBlock.code.trim(),
      });
      currentBlock = null;
    }
    // 收集代碼內容
    else if (currentBlock) {
      currentBlock.code += line + '\n';
    }
  }

  return blocks;
}

/**
 * Mermaid 即時預覽組件
 * 在編輯器中檢測 Mermaid 代碼塊並顯示即時預覽
 */
export default function MermaidPreview({ editor, content }: MermaidPreviewProps) {
  const widgetRefsRef = useRef<Map<string, editor.IContentWidget>>(new Map());
  const [mermaidBlocks, setMermaidBlocks] = useState<MermaidBlock[]>([]);
  const [lastSuccessfulRender, setLastSuccessfulRender] = useState<Map<string, string>>(new Map());

  // 檢測 Mermaid 代碼塊（使用防抖）
  const debouncedBlocks = useMemo(() => {
    const timer = setTimeout(() => {
      const blocks = detectMermaidBlocks(content);
      setMermaidBlocks(blocks);
    }, 500); // 500ms 防抖

    return () => clearTimeout(timer);
  }, [content]);

  useEffect(() => {
    return debouncedBlocks;
  }, [debouncedBlocks]);

  useEffect(() => {
    if (!editor) {
      return;
    }

    // 清理舊的 widgets
    widgetRefsRef.current.forEach((widget) => {
      editor.removeContentWidget(widget);
    });
    widgetRefsRef.current.clear();

    if (mermaidBlocks.length === 0) {
      return;
    }

    // 為每個 Mermaid 代碼塊創建 Content Widget
    for (const block of mermaidBlocks) {
      if (!block.code.trim()) {
        continue;
      }

      const widget: editor.IContentWidget = {
        getId: () => `mermaid-preview-${block.id}`,
        getDomNode: () => {
          const container = document.createElement('div');
          container.className = 'mermaid-preview-widget';
          container.style.marginTop = '8px';
          container.style.marginBottom = '8px';
          container.style.padding = '12px';
          container.style.backgroundColor = 'var(--vscode-editor-background, #1e1e1e)';
          container.style.border = '1px solid var(--vscode-panel-border, #3e3e3e)';
          container.style.borderRadius = '8px';
          container.style.overflow = 'auto';
          container.style.maxWidth = '100%';

          // 創建渲染容器
          const renderContainer = document.createElement('div');
          renderContainer.id = `mermaid-preview-${block.id}-container`;

          // 使用 React 渲染 Mermaid（需要異步處理）
          // 由於 Content Widget 是純 DOM，我們需要手動渲染
          const renderMermaid = async () => {
            try {
              // 動態導入 Mermaid
              const mermaid = (await import('mermaid')).default;

              // 初始化 Mermaid（如果尚未初始化）
              const theme = document.documentElement.classList.contains('dark') ? 'dark' : 'default';
              mermaid.initialize({
                startOnLoad: false,
                theme,
                securityLevel: 'loose',
              });

              // 生成唯一 ID
              const chartId = `mermaid-chart-${block.id}-${Date.now()}`;

              // 創建臨時元素
              const tempDiv = document.createElement('div');
              tempDiv.id = chartId;
              tempDiv.className = 'mermaid';
              tempDiv.textContent = block.code.trim();

              // 渲染圖表
              if (typeof mermaid.run === 'function') {
                await mermaid.run({
                  nodes: [tempDiv],
                  suppressErrors: false,
                });
                renderContainer.innerHTML = tempDiv.innerHTML;
                // 保存成功渲染的結果
                setLastSuccessfulRender((prev) => {
                  const newMap = new Map(prev);
                  newMap.set(block.id, tempDiv.innerHTML);
                  return newMap;
                });
              } else {
                throw new Error('Mermaid API 不可用');
              }
            } catch (error) {
              console.error('Mermaid 渲染錯誤:', error);
              // 顯示錯誤信息
              const errorDiv = document.createElement('div');
              errorDiv.className = 'mermaid-error';
              errorDiv.style.color = '#ff6b6b';
              errorDiv.style.padding = '8px';
              errorDiv.style.borderRadius = '4px';
              errorDiv.style.backgroundColor = 'rgba(255, 107, 107, 0.1)';
              errorDiv.innerHTML = `
                <div style="font-weight: 600; margin-bottom: 4px;">圖表渲染錯誤</div>
                <div style="font-size: 12px;">${error instanceof Error ? error.message : '渲染失敗'}</div>
                ${lastSuccessfulRender.has(block.id) ? '<div style="margin-top: 8px; font-size: 11px; opacity: 0.7;">顯示最近一次成功的渲染:</div>' : ''}
              `;

              // 如果有最近成功的渲染，顯示它
              if (lastSuccessfulRender.has(block.id)) {
                const successDiv = document.createElement('div');
                successDiv.style.marginTop = '8px';
                successDiv.innerHTML = lastSuccessfulRender.get(block.id) || '';
                errorDiv.appendChild(successDiv);
              }

              renderContainer.innerHTML = '';
              renderContainer.appendChild(errorDiv);
            }
          };

          // 異步渲染
          renderMermaid();

          container.appendChild(renderContainer);
          return container;
        },
        getPosition: () => {
          return {
            position: {
              lineNumber: block.endLine + 1,
              column: 1,
            },
            preference: [monaco.editor.ContentWidgetPositionPreference.BELOW],
          };
        },
      };

      editor.addContentWidget(widget);
      widgetRefsRef.current.set(block.id, widget);
    }

    // 清理函數
    return () => {
      widgetRefsRef.current.forEach((widget) => {
        editor.removeContentWidget(widget);
      });
      widgetRefsRef.current.clear();
    };
  }, [editor, mermaidBlocks, lastSuccessfulRender]);

  // 這個組件不渲染任何 UI，只管理 Content Widgets
  return null;
}

