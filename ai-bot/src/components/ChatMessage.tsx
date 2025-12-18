// 代碼功能說明：聊天消息組件，整合 Markdown 渲染、代碼高亮、Mermaid 圖表等功能
// 創建日期：2025-01-27
// 創建人：Daniel Chung
// 最後修改日期：2025-01-27

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { Message } from './Sidebar';
import CodeBlock from './CodeBlock';
import MermaidToggle from './MermaidToggle';
import MessageActions from './MessageActions';
import { useLanguage } from '../contexts/languageContext';

interface ChatMessageProps {
  message: Message;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const { t } = useLanguage();

  // 自定義代碼塊渲染器
  const components = {
    // 處理代碼塊容器（pre 標籤）
    pre: ({ children, ...props }: any) => {
      // 檢查子元素是否是 code 標籤
      const codeElement = React.Children.toArray(children).find(
        (child: any) => child?.type === 'code'
      ) as any;

      if (codeElement) {
        const className = codeElement.props?.className || '';
      const match = /language-(\w+)/.exec(className || '');
      const language = match ? match[1] : '';
        const codeString = String(codeElement.props?.children || '').replace(/\n$/, '');

      // 如果是 Mermaid 代碼塊
      if (language === 'mermaid') {
        return <MermaidToggle code={codeString} />;
      }

        // 使用 CodeBlock 組件渲染代碼塊
        return <CodeBlock code={codeString} language={language || 'text'} />;
      }

      // 默認處理
      return <pre {...props}>{children}</pre>;
    },
    // 處理行內代碼和代碼塊內的 code 標籤
    code({ node, inline, className, children, ...props }: any) {
      // 如果是行內代碼
      if (inline) {
        return (
          <code className="bg-tertiary px-1.5 py-0.5 rounded text-sm font-mono text-primary" {...props}>
            {children}
          </code>
        );
      }

      // 如果是代碼塊內的 code 標籤，只返回純文本（pre 組件會處理樣式）
      return <code {...props}>{children}</code>;
    },
    // 自定義標題樣式
    h1: ({ node, ...props }: any) => (
      <h1 className="text-3xl font-bold mt-8 mb-4 text-primary" {...props} />
    ),
    h2: ({ node, ...props }: any) => (
      <h2 className="text-2xl font-bold mt-7 mb-3 text-primary" {...props} />
    ),
    h3: ({ node, ...props }: any) => (
      <h3 className="text-xl font-bold mt-6 mb-3 text-primary" {...props} />
    ),
    h4: ({ node, ...props }: any) => (
      <h4 className="text-xl font-bold mt-5 mb-2 text-primary" {...props} />
    ),
    h5: ({ node, ...props }: any) => (
      <h5 className="text-lg font-bold mt-4 mb-2 text-primary" {...props} />
    ),
    h6: ({ node, ...props }: any) => (
      <h6 className="text-lg font-bold mt-4 mb-2 text-primary" {...props} />
    ),
    // 段落 - 保留換行和縮排
    p: ({ node, ...props }: any) => (
      <p className="mb-4 text-primary leading-relaxed whitespace-pre-wrap" {...props} />
    ),
    // 列表 - 支持嵌套縮排
    ul: ({ node, children, ...props }: any) => {
      // 計算嵌套深度
      let depth = 0;
      let parent = node?.parent;
      while (parent) {
        if (parent.type === 'list') {
          depth++;
        }
        parent = parent.parent;
      }

      return (
        <ul
          className="list-disc mb-4 space-y-1 text-primary"
          style={{
            marginLeft: `${depth * 1.5}rem`,
            paddingLeft: depth > 0 ? '0.5rem' : '1.5rem',
            listStylePosition: 'outside'
          }}
          {...props}
        >
          {children}
        </ul>
      );
    },
    ol: ({ node, children, ...props }: any) => {
      // 計算嵌套深度
      let depth = 0;
      let parent = node?.parent;
      while (parent) {
        if (parent.type === 'list') {
          depth++;
        }
        parent = parent.parent;
      }

      return (
        <ol
          className="list-decimal mb-4 space-y-1 text-primary"
          style={{
            marginLeft: `${depth * 1.5}rem`,
            paddingLeft: depth > 0 ? '0.5rem' : '1.5rem',
            listStylePosition: 'outside'
          }}
          {...props}
        >
          {children}
        </ol>
      );
    },
    li: ({ node, ...props }: any) => (
      <li className="mb-1 text-primary leading-relaxed whitespace-normal" {...props} />
    ),
    // 引用
    blockquote: ({ node, ...props }: any) => (
      <blockquote
        className="border-l-4 border-blue-500 pl-4 my-4 italic text-tertiary"
        {...props}
      />
    ),
    // 鏈接
    a: ({ node, ...props }: any) => (
      <a
        className="text-blue-400 hover:text-blue-300 underline"
        target="_blank"
        rel="noopener noreferrer"
        {...props}
      />
    ),
    // 水平線
    hr: ({ node, ...props }: any) => (
      <hr className="my-6 border-primary" {...props} />
    ),
    // 表格
    table: ({ node, ...props }: any) => (
      <div className="overflow-x-auto my-4">
        <table className="min-w-full border-collapse border border-primary" {...props} />
      </div>
    ),
    thead: ({ node, ...props }: any) => (
      <thead className="bg-tertiary" {...props} />
    ),
    tbody: ({ node, ...props }: any) => (
      <tbody {...props} />
    ),
    tr: ({ node, ...props }: any) => (
      <tr className="border-b border-primary" {...props} />
    ),
    th: ({ node, ...props }: any) => (
      <th className="border border-primary px-4 py-2 text-left font-bold text-primary" {...props} />
    ),
    td: ({ node, ...props }: any) => (
      <td className="border border-primary px-4 py-2 text-primary" {...props} />
    ),
    // 強調
    strong: ({ node, ...props }: any) => (
      <strong className="font-bold text-primary" {...props} />
    ),
    em: ({ node, ...props }: any) => (
      <em className="italic text-primary" {...props} />
    ),
  };

  return (
    <div className="mb-6">
      <div className="flex items-start mb-2">
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center mr-3 ${
            message.sender === 'ai' ? 'bg-blue-600' : 'bg-tertiary'
          }`}
        >
          {message.sender === 'ai' ? (
            <i className="fa-solid fa-robot text-white"></i>
          ) : (
            <i className="fa-solid fa-user text-primary"></i>
          )}
        </div>
        <div>
          <div className="font-medium text-primary">
            {message.sender === 'ai' ? t('chat.aiAssistant') : t('chat.user')}
          </div>
          <div className="text-sm text-tertiary">{message.timestamp}</div>
        </div>
      </div>
      <div
        className={`p-4 rounded-lg ml-11 ${
          message.sender === 'ai' ? 'bg-secondary' : 'bg-blue-900/30'
        }`}
      >
        <div
          className="prose prose-invert max-w-none"
          style={{
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word'
          }}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkBreaks]}
            components={components}
          >
            {message.content}
          </ReactMarkdown>
        </div>
        {/* AI 消息下方顯示操作按鈕 */}
        {message.sender === 'ai' && (
          <MessageActions messageId={message.id} messageContent={message.content} />
        )}
      </div>
    </div>
  );
}
