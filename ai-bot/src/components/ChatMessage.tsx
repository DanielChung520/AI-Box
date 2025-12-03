// 代碼功能說明：聊天消息組件，整合 Markdown 渲染、代碼高亮、Mermaid 圖表等功能
// 創建日期：2025-01-27
// 創建人：Daniel Chung
// 最後修改日期：2025-01-27

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
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
    code({ node, inline, className, children, ...props }: any) {
      const match = /language-(\w+)/.exec(className || '');
      const language = match ? match[1] : '';
      const codeString = String(children).replace(/\n$/, '');

      // 如果是 Mermaid 代碼塊
      if (language === 'mermaid') {
        return <MermaidToggle code={codeString} />;
      }

      // 如果是行內代碼
      if (inline) {
        return (
          <code className="bg-tertiary px-1.5 py-0.5 rounded text-sm font-mono text-primary" {...props}>
            {children}
          </code>
        );
      }

      // 如果是代碼塊
      return <CodeBlock code={codeString} language={language || 'text'} />;
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
    // 段落
    p: ({ node, ...props }: any) => (
      <p className="mb-4 text-primary leading-relaxed" {...props} />
    ),
    // 列表
    ul: ({ node, ...props }: any) => (
      <ul className="list-disc ml-6 mb-4 space-y-1 text-primary" {...props} />
    ),
    ol: ({ node, ...props }: any) => (
      <ol className="list-decimal ml-6 mb-4 space-y-1 text-primary" {...props} />
    ),
    li: ({ node, ...props }: any) => (
      <li className="mb-1 text-primary" {...props} />
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
        <div className="prose prose-invert max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
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
