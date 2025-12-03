import { useState, useEffect, useRef } from 'react';
import MermaidRenderer from './MermaidRenderer';
import { useLanguage } from '../contexts/languageContext';

interface MarkdownViewerProps {
  content: string;
  fileName: string;
}

export default function MarkdownViewer({ content, fileName }: MarkdownViewerProps) {
  const { t } = useLanguage();
  const [markdownParts, setMarkdownParts] = useState<Array<{type: 'text' | 'mermaid', content: string}>>([]);
  const contentRef = useRef<HTMLDivElement>(null);

  // 解析Markdown内容，识别普通文本和mermaid代码块
  useEffect(() => {
    try {
      // 分割文本和mermaid代码块
      const parts = [];
      const mermaidRegex = /```mermaid\s([\s\S]*?)```/g;
      let lastIndex = 0;
      let match;

      while ((match = mermaidRegex.exec(content)) !== null) {
        // 添加mermaid代码块前的普通文本
        if (match.index > lastIndex) {
          parts.push({
            type: 'text',
            content: content.substring(lastIndex, match.index)
          });
        }

        // 添加mermaid代码块
        parts.push({
          type: 'text',
          content: match[0]  // 保留原始的```mermaid```格式
        });

        lastIndex = match.index + match[0].length;
      }

      // 添加最后一段普通文本
      if (lastIndex < content.length) {
        parts.push({
          type: 'text',
          content: content.substring(lastIndex)
        });
      }

      setMarkdownParts(parts);
    } catch (error) {
      console.error("解析Markdown内容时出错:", error);
      setMarkdownParts([{ type: 'text', content }]);
    }
  }, [content]);

  // 渲染普通Markdown文本
  const renderTextMarkdown = (markdown: string): string => {
    // 标题
    let html = markdown
      .replace(/#{6}\s(.+)/g, '<h6 class="text-lg font-bold mt-4 mb-2">$1</h6>')
      .replace(/#{5}\s(.+)/g, '<h5 class="text-lg font-bold mt-4 mb-2">$1</h5>')
      .replace(/#{4}\s(.+)/g, '<h4 class="text-xl font-bold mt-5 mb-2">$1</h4>')
      .replace(/#{3}\s(.+)/g, '<h3 class="text-xl font-bold mt-6 mb-3">$1</h3>')
      .replace(/#{2}\s(.+)/g, '<h2 class="text-2xl font-bold mt-7 mb-3">$1</h2>')
      .replace(/#{1}\s(.+)/g, '<h1 class="text-3xl font-bold mt-8 mb-4">$1</h1>');

    // 加粗
    html = html.replace(/\*\*(.+)\*\*/g, '<strong>$1</strong>');

    // 斜体
    html = html.replace(/\*(.+)\*/g, '<em>$1</em>');

    // 普通代码块（非mermaid）
    html = html.replace(/```([\s\S]*?)```/g, '<pre class="bg-gray-900 p-4 rounded-md overflow-x-auto my-4 text-sm"><code>$1</code></pre>');

    // 行内代码
    html = html.replace(/`(.+?)`/g, '<code class="bg-gray-900 px-1.5 py-0.5 rounded text-sm">$1</code>');

    // 列表
    html = html.replace(/^\-\s(.+)$/gm, '<li class="list-disc ml-5 mb-1">$1</li>');

    // 水平线
    html = html.replace(/^---$/gm, '<hr class="my-6 border-gray-700">');

    // 段落
    html = html.replace(/^(?!<h|<ul|<ol|<li|<pre|<hr)(.+)$/gm, '<p class="mb-4">$1</p>');

    return html;
  };

  return (
    <div className="p-4 h-full flex flex-col theme-transition">
      {/* 文件标题栏 */}
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-primary">
        <div className="flex items-center">
          <i className="fa-solid fa-file-lines text-blue-400 mr-2"></i>
          <span className="font-medium text-primary">{fileName}</span>
        </div>
        <div className="flex space-x-2">
           <button className="p-1 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary" aria-label={t('markdownViewer.download')}>
            <i className="fa-solid fa-download"></i>
          </button>
           <button className="p-1 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary" aria-label={t('markdownViewer.more')}>
            <i className="fa-solid fa-ellipsis-vertical"></i>
          </button>
        </div>
      </div>

      {/* Markdown内容区域 */}
      <div className="flex-1 overflow-y-auto text-sm markdown-content" ref={contentRef}>
        {markdownParts.map((part, index) => (
          <div key={index}>
            {part.type === 'text' ? (
              <div dangerouslySetInnerHTML={{ __html: renderTextMarkdown(part.content) }} />
            ) : (
              <MermaidRenderer code={part.content.trim()} className="bg-secondary p-4 rounded-lg border border-primary" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
