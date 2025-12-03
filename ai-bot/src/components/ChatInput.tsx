import { useState, useRef, useEffect, useMemo } from 'react';
import { useLanguage } from '../contexts/languageContext';

interface Agent {
  id: string;
  name: string;
  description: string;
  icon: string;
  status: 'registering' | 'online' | 'maintenance' | 'deprecated';
  usageCount: number;
}

interface ChatInputProps {
  agents?: Agent[];
  onAgentSelect?: (agentId: string) => void;
  onModelSelect?: (modelId: string) => void;
  selectedAgentId?: string;
  selectedModelId?: string;
}

export default function ChatInput({
  agents = [],
  onAgentSelect,
  onModelSelect,
  selectedAgentId,
  selectedModelId = 'auto'
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [showAssistantSelector, setShowAssistantSelector] = useState(false);
  const [showAgentSelector, setShowAgentSelector] = useState(false);
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [showMentionMenu, setShowMentionMenu] = useState(false);
  const assistantSelectorRef = useRef<HTMLDivElement>(null);
  const agentSelectorRef = useRef<HTMLDivElement>(null);
  const modelSelectorRef = useRef<HTMLDivElement>(null);
  const mentionMenuRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { t } = useLanguage();

  // LLM 模型列表 - 使用 useMemo 确保 t 函数可用
  const llmModels = useMemo(() => [
    { id: 'auto', name: t('chatInput.model.auto', 'Auto'), provider: 'auto' },
    { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', provider: 'chatgpt' },
    { id: 'gpt-4', name: 'GPT-4', provider: 'chatgpt' },
    { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'chatgpt' },
    { id: 'gemini-pro', name: 'Gemini Pro', provider: 'gemini' },
    { id: 'gemini-ultra', name: 'Gemini Ultra', provider: 'gemini' },
    { id: 'qwen-turbo', name: 'Qwen Turbo', provider: 'qwen' },
    { id: 'qwen-plus', name: 'Qwen Plus', provider: 'qwen' },
    { id: 'grok-beta', name: 'Grok Beta', provider: 'grok' },
    { id: 'llama2', name: 'Llama 2', provider: 'ollama' },
    { id: 'qwen3-coder:30b', name: 'Qwen3 Coder 30B', provider: 'ollama' },
    { id: 'gpt-oss:20b', name: 'GPT-OSS 20B', provider: 'ollama' },
  ], [t]);

  // 点击外部关闭下拉菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (assistantSelectorRef.current && !assistantSelectorRef.current.contains(event.target as Node)) {
        setShowAssistantSelector(false);
      }
      if (agentSelectorRef.current && !agentSelectorRef.current.contains(event.target as Node)) {
        setShowAgentSelector(false);
      }
      if (modelSelectorRef.current && !modelSelectorRef.current.contains(event.target as Node)) {
        setShowModelSelector(false);
      }
      if (mentionMenuRef.current && !mentionMenuRef.current.contains(event.target as Node)) {
        setShowMentionMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // 监听输入框中的 @ 符号
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const handleInput = (e: Event) => {
      const target = e.target as HTMLTextAreaElement;
      const cursorPos = target.selectionStart;
      const textBeforeCursor = target.value.substring(0, cursorPos);
      const lastAt = textBeforeCursor.lastIndexOf('@');

      // 如果输入了 @ 且后面没有空格，显示提及菜单
      if (lastAt !== -1 && lastAt === cursorPos - 1) {
        setShowMentionMenu(true);
      } else if (lastAt !== -1) {
        const textAfterAt = textBeforeCursor.substring(lastAt + 1);
        // 如果 @ 后面有空格或换行，关闭菜单
        if (textAfterAt.includes(' ') || textAfterAt.includes('\n')) {
          setShowMentionMenu(false);
        }
      }
    };

    textarea.addEventListener('input', handleInput);
    return () => {
      textarea.removeEventListener('input', handleInput);
    };
  }, []);

  // 提及选项（类似 Cursor 的功能）- 使用 useMemo 确保 t 函数可用
  const mentionOptions = useMemo(() => [
    { id: 'file', label: t('chatInput.mention.file', '文件'), icon: 'fa-file', description: t('chatInput.mention.fileDesc', '提及文件') },
    { id: 'code', label: t('chatInput.mention.code', '代码'), icon: 'fa-code', description: t('chatInput.mention.codeDesc', '提及代码片段') },
    { id: 'context', label: t('chatInput.mention.context', '上下文'), icon: 'fa-layer-group', description: t('chatInput.mention.contextDesc', '提及上下文') },
    { id: 'variable', label: t('chatInput.mention.variable', '变量'), icon: 'fa-tag', description: t('chatInput.mention.variableDesc', '提及变量') },
    { id: 'function', label: t('chatInput.mention.function', '函数'), icon: 'fa-function', description: t('chatInput.mention.functionDesc', '提及函数') },
  ], [t]);

  // 插入提及到输入框
  const insertMention = (option: { id: string; label: string; icon: string; description: string }) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const cursorPos = textarea.selectionStart;
    const textBeforeCursor = textarea.value.substring(0, cursorPos);
    const textAfterCursor = textarea.value.substring(cursorPos);
    const lastAt = textBeforeCursor.lastIndexOf('@');

    if (lastAt !== -1) {
      // 替换 @ 到光标位置的内容为 @选项名
      const newText = textarea.value.substring(0, lastAt) + `@${option.label} ` + textAfterCursor;
      setMessage(newText);

      // 设置光标位置
      setTimeout(() => {
        const newCursorPos = lastAt + option.label.length + 2; // +2 for @ and space
        textarea.setSelectionRange(newCursorPos, newCursorPos);
        textarea.focus();
      }, 0);
    } else {
      // 如果没有找到 @，直接在光标位置插入
      const newText = textBeforeCursor + `@${option.label} ` + textAfterCursor;
      setMessage(newText);

      setTimeout(() => {
        const newCursorPos = cursorPos + option.label.length + 2;
        textarea.setSelectionRange(newCursorPos, newCursorPos);
        textarea.focus();
      }, 0);
    }

    setShowMentionMenu(false);
  };

  // 处理 @ 按钮点击
  const handleMentionClick = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      const cursorPos = textarea.selectionStart;
      const textBeforeCursor = textarea.value.substring(0, cursorPos);
      const textAfterCursor = textarea.value.substring(cursorPos);

      // 在光标位置插入 @
      setMessage(textBeforeCursor + '@' + textAfterCursor);

      setTimeout(() => {
        textarea.setSelectionRange(cursorPos + 1, cursorPos + 1);
        textarea.focus();
        setShowMentionMenu(true);
      }, 0);
    }
  };

  // 获取选中的代理名称
  const selectedAgent = agents.find(a => a.id === selectedAgentId);
  const selectedAgentName = selectedAgent ? selectedAgent.name : t('chatInput.agent', '代理');

  // 获取选中的模型名称
  const selectedModel = llmModels.find(m => m.id === selectedModelId);
  const selectedModelName = selectedModel ? selectedModel.name : t('chatInput.model.auto', 'Auto');

  const handleSend = () => {
    if (message.trim()) {
      // 这里可以添加发送消息的逻辑
      console.log('发送消息:', message);
      setMessage('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="bg-secondary rounded-xl overflow-hidden theme-transition">
      {/* 工具栏 */}
      <div className="flex items-center p-2 border-b border-primary">
        <button
          className="p-2 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
          aria-label="使用互联网"
        >
          <i className="fa-solid fa-globe"></i>
        </button>
        <button
          className="p-2 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
          aria-label="深度思考"
        >
          <i className="fa-solid fa-brain"></i>
        </button>
        {/* 助理选择器 */}
        <div className="relative ml-2" ref={assistantSelectorRef}>
          <button
            className="px-3 py-1 rounded bg-tertiary hover:bg-hover transition-colors text-sm flex items-center text-secondary"
            onClick={() => {
              setShowAssistantSelector(!showAssistantSelector);
              setShowAgentSelector(false);
              setShowModelSelector(false);
            }}
          >
            <i className="fa-solid fa-robot mr-2"></i>
            {t('chatInput.assistant')}
            <i className={`fa-solid fa-chevron-down ml-2 transition-transform ${showAssistantSelector ? 'rotate-180' : ''}`}></i>
          </button>

          {showAssistantSelector && (
            <div className="absolute left-0 top-full mt-1 w-48 bg-secondary border border-primary rounded-lg shadow-lg z-20 theme-transition">
              <div className="p-2 border-b border-primary text-sm font-medium text-primary">{t('chatInput.selectAssistant')}</div>
              <button className="w-full text-left px-4 py-2 text-sm hover:bg-tertiary transition-colors flex items-center text-secondary">
                <i className="fa-solid fa-comment-dots mr-2 text-blue-400"></i>
                {t('assistant.general')}
              </button>
              <button className="w-full text-left px-4 py-2 text-sm hover:bg-tertiary transition-colors flex items-center text-secondary">
                <i className="fa-solid fa-pen-to-square mr-2 text-green-400"></i>
                {t('assistant.creative')}
              </button>
              <button className="w-full text-left px-4 py-2 text-sm hover:bg-tertiary transition-colors flex items-center text-secondary">
                <i className="fa-solid fa-chart-simple mr-2 text-purple-400"></i>
                {t('assistant.analyst')}
              </button>
            </div>
          )}
        </div>

        {/* 代理选择器 */}
        <div className="relative ml-2" ref={agentSelectorRef}>
          <button
            className="px-3 py-1 rounded bg-tertiary hover:bg-hover transition-colors text-sm flex items-center text-secondary"
            onClick={() => {
              setShowAgentSelector(!showAgentSelector);
              setShowAssistantSelector(false);
              setShowModelSelector(false);
            }}
          >
            <i className="fa-solid fa-user-tie mr-2"></i>
            <span className="max-w-[100px] truncate">{selectedAgentName}</span>
            <i className={`fa-solid fa-chevron-down ml-2 transition-transform ${showAgentSelector ? 'rotate-180' : ''}`}></i>
          </button>

          {showAgentSelector && agents.length > 0 && (
            <div className="absolute left-0 top-full mt-1 w-64 bg-secondary border border-primary rounded-lg shadow-lg z-20 theme-transition max-h-96 overflow-y-auto">
              <div className="p-2 border-b border-primary text-sm font-medium text-primary sticky top-0 bg-secondary">
                {t('chatInput.selectAgent', '選擇代理')}
              </div>
              {agents.map(agent => (
                <button
                  key={agent.id}
                  className={`w-full text-left px-4 py-2 text-sm hover:bg-tertiary transition-colors flex items-center ${
                    selectedAgentId === agent.id ? 'bg-tertiary' : ''
                  }`}
                  onClick={() => {
                    onAgentSelect?.(agent.id);
                    setShowAgentSelector(false);
                  }}
                >
                  <i className={`fa-solid ${agent.icon} mr-2 ${
                    agent.status === 'online' ? 'text-green-400' :
                    agent.status === 'maintenance' ? 'text-yellow-400' :
                    agent.status === 'deprecated' ? 'text-red-400' :
                    'text-gray-400'
                  }`}></i>
                  <div className="flex-1 min-w-0">
                    <div className="text-secondary truncate">{agent.name}</div>
                    <div className="text-xs text-tertiary truncate">{agent.description}</div>
                  </div>
                  {selectedAgentId === agent.id && (
                    <i className="fa-solid fa-check text-blue-400 ml-2"></i>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 模型选择器 */}
        <div className="relative ml-2" ref={modelSelectorRef}>
          <button
            className="px-3 py-1 rounded bg-tertiary hover:bg-hover transition-colors text-sm flex items-center text-secondary"
            onClick={() => {
              setShowModelSelector(!showModelSelector);
              setShowAssistantSelector(false);
              setShowAgentSelector(false);
            }}
          >
            <i className="fa-solid fa-brain mr-2"></i>
            <span className="max-w-[120px] truncate">{selectedModelName}</span>
            <i className={`fa-solid fa-chevron-down ml-2 transition-transform ${showModelSelector ? 'rotate-180' : ''}`}></i>
          </button>

          {showModelSelector && (
            <div className="absolute left-0 top-full mt-1 w-56 bg-secondary border border-primary rounded-lg shadow-lg z-20 theme-transition max-h-96 overflow-y-auto">
              <div className="p-2 border-b border-primary text-sm font-medium text-primary sticky top-0 bg-secondary">
                {t('chatInput.selectModel', '選擇模型')}
              </div>
              {llmModels.map(model => (
                <button
                  key={model.id}
                  className={`w-full text-left px-4 py-2 text-sm hover:bg-tertiary transition-colors flex items-center ${
                    selectedModelId === model.id ? 'bg-tertiary' : ''
                  }`}
                  onClick={() => {
                    onModelSelect?.(model.id);
                    setShowModelSelector(false);
                  }}
                >
                  <i className={`fa-solid ${
                    model.id === 'auto' ? 'fa-magic' :
                    model.provider === 'chatgpt' ? 'fa-robot' :
                    model.provider === 'gemini' ? 'fa-gem' :
                    model.provider === 'qwen' ? 'fa-code' :
                    model.provider === 'grok' ? 'fa-bolt' :
                    'fa-server'
                  } mr-2 ${
                    model.id === 'auto' ? 'text-purple-400' :
                    model.provider === 'chatgpt' ? 'text-green-400' :
                    model.provider === 'gemini' ? 'text-blue-400' :
                    model.provider === 'qwen' ? 'text-orange-400' :
                    model.provider === 'grok' ? 'text-yellow-400' :
                    'text-gray-400'
                  }`}></i>
                  <span className="text-secondary flex-1">{model.name}</span>
                  {selectedModelId === model.id && (
                    <i className="fa-solid fa-check text-blue-400 ml-2"></i>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="ml-auto flex items-center space-x-1">
          <button
            className="p-2 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
            aria-label="上传文件"
          >
            <i className="fa-solid fa-paperclip"></i>
          </button>
          <button
            className="p-2 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
            aria-label="表情"
          >
            <i className="fa-solid fa-smile"></i>
          </button>
          <button
            className="p-2 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
            aria-label="语音输入"
          >
            <i className="fa-solid fa-microphone"></i>
          </button>
        </div>
      </div>

      {/* 输入框 */}
      <div className="flex items-end p-3 relative">
        <textarea
          ref={textareaRef}
          className="flex-1 bg-transparent border border-primary rounded-lg p-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-primary"
          placeholder={t('chatInput.placeholder')}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          rows={3}
        />

        {/* @ 提及按钮 */}
        <button
          onClick={handleMentionClick}
          className="ml-2 p-2 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
          title={t('chatInput.mention.title', '提及 (@)')}
          aria-label={t('chatInput.mention.title', '提及 (@)')}
        >
          <span className="text-lg font-semibold">@</span>
        </button>

        {/* 提及菜单 */}
        {showMentionMenu && (
          <div
            ref={mentionMenuRef}
            className="absolute bottom-full right-0 mb-2 w-64 bg-secondary border border-primary rounded-lg shadow-lg z-30 theme-transition max-h-80 overflow-y-auto"
          >
            <div className="p-2 border-b border-primary text-sm font-medium text-primary sticky top-0 bg-secondary">
              {t('chatInput.mention.title', '提及')}
            </div>
            {mentionOptions.map(option => (
              <button
                key={option.id}
                className="w-full text-left px-4 py-2 text-sm hover:bg-tertiary transition-colors flex items-center gap-3"
                onClick={() => insertMention(option)}
              >
                <i className={`fa-solid ${option.icon} text-blue-400 w-5`}></i>
                <div className="flex-1 min-w-0">
                  <div className="text-secondary font-medium">{option.label}</div>
                  <div className="text-xs text-tertiary truncate">{option.description}</div>
                </div>
              </button>
            ))}
          </div>
        )}

        <button
          className="ml-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center"
          onClick={handleSend}
        >
          <span>{t('chatInput.send')}</span>
          <i className="fa-solid fa-paper-plane ml-2"></i>
        </button>
      </div>
    </div>
  );
}
