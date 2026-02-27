// 代碼功能說明：聊天消息組件，整合 Markdown 渲染、代碼高亮、Mermaid 圖表等功能
// 創建日期：2025-01-27
// 創建人：Daniel Chung
// 最後修改日期：2026-01-06

import React, { forwardRef } from 'react';
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

const ChatMessage = forwardRef<HTMLDivElement, ChatMessageProps>(
  ({ message }, ref) => {
  const { t } = useLanguage();

  // 自定義代碼塊渲染器
  const components = {
    // 處理代碼塊（直接處理 code 標籤，通過 inline 屬性區分行內和代碼塊）
    code({ node, inline, className, children, ...props }: any) {
      // 如果是行內代碼
      if (inline) {
        return (
          <code className="bg-tertiary px-1.5 py-0.5 rounded text-[11.2px] font-mono text-primary" {...props}>
            {children}
          </code>
        );
      }

      // 如果是代碼塊（inline === false）
      const match = /language-(\w+)/.exec(className || '');
      const language = match ? match[1] : '';
      const codeString = String(children || '').replace(/\n$/, '');

      // 如果是 Mermaid 代碼塊
      if (language === 'mermaid') {
        return <MermaidToggle code={codeString} />;
      }

      // 使用 CodeBlock 組件渲染代碼塊（帶語法高亮）
      // 如果沒有指定語言，嘗試自動檢測（特別是 Python 代碼）
      let detectedLanguage = language || 'text';
      if (!language && codeString.trim()) {
        // 簡單的語言檢測：檢查常見的 Python 關鍵字
        const pythonKeywords = /^(def|import|from|class|if|elif|else|for|while|try|except|with|async|await)/m;
        if (pythonKeywords.test(codeString)) {
          detectedLanguage = 'python';
        }
      }

      // 調試：記錄代碼塊信息
      if (process.env.NODE_ENV === 'development') {
        console.debug('[ChatMessage] Rendering code block:', {
          language: detectedLanguage,
          codeLength: codeString.length,
          preview: codeString.substring(0, 50),
        });
      }

      return <CodeBlock code={codeString} language={detectedLanguage} />;
    },
    // 處理 pre 標籤（代碼塊的容器）
    pre: ({ children, ...props }: any) => {
      // 如果 children 是我們自定義的 CodeBlock 或 MermaidToggle，直接返回（不使用 pre 包裹）
      const childrenArray = React.Children.toArray(children);
      const firstChild = childrenArray[0] as any;

      // 檢查是否是我們的組件實例
      if (firstChild && React.isValidElement(firstChild)) {
        const componentType = firstChild.type;
        if (componentType === CodeBlock || componentType === MermaidToggle) {
          // 直接返回，不使用 pre 包裹（避免 p > pre > CodeBlock 的嵌套問題）
          return <>{children}</>;
        }
      }

      // 默認處理（fallback）
      return <pre {...props}>{children}</pre>;
    },
    // 自定義標題樣式
    h1: ({ node, ...props }: any) => (
      <h1 className="text-2xl font-bold mt-[5.2px] mb-[3.6px] text-primary" {...props} />
    ),
    h2: ({ node, ...props }: any) => (
      <h2 className="text-[19.2px] font-bold mt-[4.8px] mb-[2.2px] text-primary" {...props} />
    ),
    h3: ({ node, ...props }: any) => (
      <h3 className="text-base font-bold mt-[3.4px] mb-[2.2px] text-primary" {...props} />
    ),
    h4: ({ node, ...props }: any) => (
      <h4 className="text-base font-bold mt-[3px] mb-[2.8px] text-primary" {...props} />
    ),
    h5: ({ node, ...props }: any) => (
      <h5 className="text-sm font-bold mt-[2.6px] mb-[2.7px] text-primary" {...props} />
    ),
    h6: ({ node, ...props }: any) => (
      <h6 className="text-sm font-bold mt-[2.6px] mb-[2.5px] text-primary" {...props} />
    ),
    // 段落 - 保留換行和縮排
    // 如果包含代碼塊（pre 標籤或 code 標籤），使用 div 而不是 p
    p: ({ node, children, ...props }: any) => {
      // 檢查 node.children 是否包含 pre 或 code 節點（代碼塊）
      const hasCodeBlock = node?.children?.some((child: any) => {
        if (child.type === 'element') {
          return child.tagName === 'pre' || (child.tagName === 'code' && !child.properties?.inline);
        }
        return false;
      });

      // 遞歸檢查是否有任何 DOM 元素包含 block-level 元素
      const hasBlockElement = (element: any): boolean => {
        if (element.type === 'element') {
          // pre, div, code block 都是 block-level
          if (element.tagName === 'pre' || element.tagName === 'div' || (element.tagName === 'code' && !element.properties?.inline)) {
            return true;
          }
          // 遞歸檢查 children
          if (element.children) {
            return element.children.some(hasBlockElement);
          }
        }
        return false;
      };

      const hasNestedBlock = node?.children?.some(hasBlockElement);

      // 檢查 React children 是否包含 CodeBlock 或 MermaidToggle 組件
      const checkForBlockComponent = (child: any): boolean => {
        if (React.isValidElement(child)) {
          const componentType = child.type;
          if (componentType === CodeBlock || componentType === MermaidToggle) {
            return true;
          }
          const childProps = child.props as any;
          if (childProps?.children) {
            const nestedChildren = React.Children.toArray(childProps.children);
            return nestedChildren.some(checkForBlockComponent);
          }
        }
        return false;
      };

      const childrenArray = React.Children.toArray(children);
      const hasBlockComponent = childrenArray.some(checkForBlockComponent);

      // 如果包含代碼塊或塊級組件，使用 div 而不是 p
      if (hasCodeBlock || hasNestedBlock || hasBlockComponent) {
        return <div className="mb-2 text-primary leading-[0.81] whitespace-pre-wrap" {...props}>{children}</div>;
      }

      // 否則使用正常的 p 標籤
      return <p className="mb-2 text-primary leading-[0.81] whitespace-pre-wrap" {...props}>{children}</p>;
    },
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
          className="list-disc mb-2 space-y-[0.12px] text-primary"
          style={{
            marginLeft: `${depth * 1.5}rem`,
            paddingLeft: depth > 0 ? '0.35rem' : '1.05rem',
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
          className="list-decimal mb-2 space-y-[0.15px] text-primary"
          style={{
            marginLeft: `${depth * 1.5}rem`,
            paddingLeft: depth > 0 ? '0.35rem' : '1.05rem',
            listStylePosition: 'outside'
          }}
          {...props}
        >
          {children}
        </ol>
      );
    },
    li: ({ node, ...props }: any) => (
      <li className="mb-[0.12px] text-primary leading-[1.4] whitespace-normal" {...props} />
    ),
    // 引用
    blockquote: ({ node, ...props }: any) => (
      <blockquote
        className="border-l-4 border-blue-500 pl-[11.2px] my-2 italic text-tertiary"
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
      <hr className="my-3 border-primary" {...props} />
    ),
    // 表格
    table: ({ node, ...props }: any) => (
      <div className="overflow-x-auto my-2">
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
      <th className="border border-primary px-[11.2px] py-2 text-left font-bold text-primary" {...props} />
    ),
    td: ({ node, ...props }: any) => (
      <td className="border border-primary px-[11.2px] py-1 text-primary" {...props} />
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
      <div ref={ref} className="mb-6" id={`message-${message.id}`}>
        <div className="flex items-start mb-2">
        <div
          className={`message-avatar w-8 h-8 rounded-full flex items-center justify-center mr-3 ${
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
          <div className="text-[11.2px] text-tertiary">{message.timestamp}</div>
        </div>
      </div>
      <div
        className={`message-bubble message-bubble-${message.sender} p-[11.2px] rounded-lg ml-11 ${
          message.sender === 'ai' ? 'bg-[var(--bg-secondary)]' : 'bg-tertiary/50'
        }`}
      >
        <div
          className="prose prose-invert max-w-none [&_pre]:!bg-transparent [&_pre]:!my-0 text-[12.8px]"
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
);

ChatMessage.displayName = 'ChatMessage';

export default ChatMessage;
