import { useState, useMemo, useRef, useEffect, useContext } from 'react';
import { PanelRightClose, PanelRightOpen, BookOpen } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import AgentCard from './AgentCard';
import AssistantCard from './AssistantCard';
import ChatInput from './ChatInput';
import Tabs from './Tabs';
import { Task } from './Sidebar';
import ChatMessage from './ChatMessage';
import AgentRegistrationModal from './AgentRegistrationModal';
import AgentDisplayConfigModal from './AgentDisplayConfigModal';
import DeleteAgentConfirmModal from './DeleteAgentConfirmModal';
import AssistantMaintenanceModal from './AssistantMaintenanceModal';
import ChatSearchModal from './ChatSearchModal';
import KnowledgeBaseModal from './KnowledgeBaseModal';
import { useTheme } from '../hooks/useTheme';
import { useLanguage, languageNames, languageIcons } from '../contexts/languageContext';
import { useFileEditing } from '../contexts/fileEditingContext';
import { useStreamingEdit } from '../hooks/useStreamingEdit';
import { startEditingSession, submitEditingCommand, deleteAgentConfig } from '../lib/api';
import { useAgentDisplayConfig } from '../hooks/useAgentDisplayConfig';
import { AuthContext } from '../contexts/authContext';
import { isSystemAdmin } from '../lib/userUtils';

  // 定义Agent分类和卡片数据
  interface AgentCategory {
    id: string;
    name: string;
    agents: Agent[];
  }

  interface Agent {
    id: string;
    name: string;
    description: string;
    icon: string;
    status: 'registering' | 'online' | 'maintenance' | 'deprecated';
    usageCount: number;
  }

  // 定义Assistant分类和卡片数据
  interface AssistantCategory {
    id: string;
    name: string;
    assistants: Assistant[];
  }

  interface Assistant {
    id: string;
    name: string;
    description: string;
    icon: string;
    status: 'registering' | 'online' | 'maintenance' | 'deprecated';
    usageCount: number;
    allowedTools?: string[]; // 可使用的工具列表
  }

  interface ChatAreaProps {
    selectedTask: Task | undefined;
    browseMode?: 'assistants' | 'agents' | null;
    onAssistantSelect: (id: string) => void;
    onAgentSelect: (id: string) => void;
    onModelSelect: (id: string) => void;
    onMessageSend: (raw: string) => void;
    resultPanelCollapsed: boolean;
    onResultPanelToggle: () => void;
    onAssistantFavorite: (id: string, isFavorite: boolean, name?: string) => void;
    favoriteAssistants?: Map<string, string>;
    onAgentFavorite: (id: string, isFavorite: boolean, name?: string) => void;
    favoriteAgents?: Map<string, string>;
    onTaskUpdate: (task: Task) => void;
    currentTaskId?: string;
    onTaskCreate: (task: Task) => void;
    onTaskDelete: (taskId: number) => void;
    isPreviewMode?: boolean;
  }

  export default function ChatArea({ selectedTask, browseMode, onAssistantSelect, onAgentSelect, onModelSelect, onMessageSend, resultPanelCollapsed, onResultPanelToggle, onAssistantFavorite, favoriteAssistants = new Map(), onAgentFavorite, favoriteAgents = new Map(), onTaskUpdate, currentTaskId, onTaskCreate, onTaskDelete, isPreviewMode = false }: ChatAreaProps) {
    const location = useLocation();
    const navigate = useNavigate();
    const { currentUser } = useContext(AuthContext);
    // 使用統一的系統管理員檢查函數
    const isAdmin = isSystemAdmin(currentUser);

    const [activeTab, setActiveTab] = useState('human-resource');
    const [activeAssistantTab, setActiveAssistantTab] = useState('human-resource');
    const { theme, toggleTheme } = useTheme();
    const { language, setLanguage, t, updateCounter } = useLanguage();
    const [showLanguageSelector, setShowLanguageSelector] = useState(false);
    const [showSystemMenu, setShowSystemMenu] = useState(false);
    const [showAgentRegistrationModal, setShowAgentRegistrationModal] = useState(false);
    const [showAssistantMaintenanceModal, setShowAssistantMaintenanceModal] = useState(false);
    const [maintainingAssistantId, setMaintainingAssistantId] = useState<string | null>(null);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [deletingAssistantId, setDeletingAssistantId] = useState<string | null>(null);
    const [showSearchModal, setShowSearchModal] = useState(false);
    // 修改時間：2026-01-13 - 添加 Agent Display Config 編輯相關狀態
    const [maintainingAgentId, setMaintainingAgentId] = useState<string | null>(null);
    const [showAgentEditModal, setShowAgentEditModal] = useState(false);
    // 修改時間：2026-01-13 - 添加 Agent 刪除相關狀態
    const [deletingAgentId, setDeletingAgentId] = useState<string | null>(null);
    const [deletingAgentName, setDeletingAgentName] = useState<string>('');
    const [showDeleteAgentModal, setShowDeleteAgentModal] = useState(false);
    // 修改時間：2026-02-12 - 知識庫管理 Modal 狀態
    const [showKnowledgeBaseModal, setShowKnowledgeBaseModal] = useState(false);

    // 修改時間：2026-01-06 - 文件編輯相關狀態
    const { editingFileId, setEditingFile, setPatches, clearEditing, setCurrentRequestId: setEditingRequestId } = useFileEditing();
    const { connect: connectStreamingEdit, disconnect, patches: streamingPatches, isStreaming, error: streamingError } = useStreamingEdit();
    const editingSessionIdRef = useRef<string | null>(null);

    // 處理點擊外部區域關閉系統管理菜單
    useEffect(() => {
      const handleClickOutside = (e: MouseEvent) => {
        const target = e.target as HTMLElement;
        if (showSystemMenu && !target.closest('.system-menu-container')) {
          setShowSystemMenu(false);
        }
      };

      if (showSystemMenu) {
        document.addEventListener('mousedown', handleClickOutside);
        return () => {
          document.removeEventListener('mousedown', handleClickOutside);
        };
      }
    }, [showSystemMenu]);

    // 處理 ESC 鍵關閉系統管理菜單
    useEffect(() => {
      const handleEscape = (e: KeyboardEvent) => {
        if (e.key === 'Escape' && showSystemMenu) {
          setShowSystemMenu(false);
        }
      };

      document.addEventListener('keydown', handleEscape);
      return () => {
        document.removeEventListener('keydown', handleEscape);
      };
    }, [showSystemMenu]);

    // 修改時間：2026-01-06 - 監聽文件選擇事件
    useEffect(() => {
      const handleFileSelected = (event: CustomEvent) => {
        const { fileId } = event.detail;
        if (fileId) {
          setEditingFile(fileId);
          // 啟動編輯 Session
          startEditingSession({ doc_id: fileId })
            .then((response) => {
              if (response.success && response.data?.session_id) {
                editingSessionIdRef.current = response.data.session_id;
                console.log('[ChatArea] Editing session started:', response.data.session_id);
              }
            })
            .catch((error) => {
              console.error('[ChatArea] Failed to start editing session:', error);
            });
        } else {
          clearEditing();
          editingSessionIdRef.current = null;
        }
      };

      window.addEventListener('fileSelectedForEditing', handleFileSelected as EventListener);
      return () => {
        window.removeEventListener('fileSelectedForEditing', handleFileSelected as EventListener);
      };
    }, [setEditingFile, clearEditing]);

    // 修改時間：2026-01-06 - 監聽消息發送事件，檢測文件編輯消息
    useEffect(() => {
      if (!editingFileId || !editingSessionIdRef.current) {
        return;
      }

      const handleMessageSent = async (event: Event) => {
        const customEvent = event as CustomEvent;
        const { message, fileId } = customEvent.detail;
        if (fileId === editingFileId && message) {
          // 提交編輯指令
          try {
            const response = await submitEditingCommand({
              session_id: editingSessionIdRef.current!,
              command: message,
            });

              if (response.success && response.data?.request_id) {
                // 存儲 request_id 到 Context
                setEditingRequestId(response.data.request_id);
                // 連接流式編輯端點
                connectStreamingEdit(editingSessionIdRef.current!, response.data.request_id);
              }
          } catch (error) {
            console.error('[ChatArea] Failed to submit editing command:', error);
          }
        }
      };

      window.addEventListener('messageSentForFileEditing', handleMessageSent);
      return () => {
        window.removeEventListener('messageSentForFileEditing', handleMessageSent);
      };
      }, [editingFileId, connectStreamingEdit, setEditingRequestId]);

    // 修改時間：2026-01-06 - 將流式 patches 更新到 Context
    useEffect(() => {
      if (streamingPatches && streamingPatches.length > 0) {
        setPatches(streamingPatches);
        // patches 更新後會自動觸發 applyPatches（在 Context 中）
      }
    }, [streamingPatches, setPatches]);

    // DEBUG: 追蹤 KnowledgeBaseModal 狀態
    useEffect(() => {
      console.log('[KnowledgeBaseModal DEBUG] showKnowledgeBaseModal changed:', showKnowledgeBaseModal);
    }, [showKnowledgeBaseModal]);

    // 修改時間：2026-01-06 - 組件卸載時斷開連接
    useEffect(() => {
      return () => {
        disconnect();
      };
    }, [disconnect]);

    // 用於自動滾動到底部的 ref
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const messagesContainerRef = useRef<HTMLDivElement>(null);
    // 用於消息定位的 ref map
    const messageRefs = useRef<Map<string, HTMLDivElement>>(new Map());

    // 定位到指定消息
    const scrollToMessage = (messageId: string) => {
      const messageElement = document.getElementById(`message-${messageId}`);
      if (messageElement && messagesContainerRef.current) {
        // 滚动到消息位置
        messageElement.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        });
        // 高亮显示（可选）
        messageElement.classList.add('ring-2', 'ring-blue-500', 'ring-opacity-50');
        setTimeout(() => {
          messageElement.classList.remove('ring-2', 'ring-blue-500', 'ring-opacity-50');
        }, 2000);
      }
    };

    // 當消息更新時，自動滾動到底部
    useEffect(() => {
      if (selectedTask?.messages && selectedTask.messages.length > 0 && messagesEndRef.current) {
        // 使用 requestAnimationFrame 確保 DOM 已經更新後再滾動
        requestAnimationFrame(() => {
          setTimeout(() => {
            messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
          }, 50);
        });
      }
    }, [selectedTask?.messages]);

    // 從後端獲取代理展示配置 - 修改時間：2026-01-13 - 使用 API 替代硬編碼
    const { agentCategories, loading: agentConfigLoading, error: agentConfigError, refetch: refetchAgentConfig } = useAgentDisplayConfig();

    // 當配置加載完成後，確保 activeTab 指向有效的分類
    useEffect(() => {
      if (!agentConfigLoading && agentCategories.length > 0) {
        const categoryIds = agentCategories.map(cat => cat.id);
        if (!categoryIds.includes(activeTab)) {
          // 如果當前 activeTab 不在新的分類列表中，切換到第一個分類
          setActiveTab(categoryIds[0]);
        }
      }
    }, [agentConfigLoading, agentCategories, activeTab]);

  // Mock数据 - 不同类别的Assistant - 使用useMemo和updateCounter确保语言变更时重新渲染
  const assistantCategories: AssistantCategory[] = useMemo(() => [
    {
      id: 'human-resource',
      name: t('agent.category.humanResource'),
      assistants: [
        {
          id: 'assist-hr-1',
          name: t('sidebar.assistant1'),
          description: t('agent.hr.description.assistant'),
          icon: 'fa-robot',
          status: 'online',
          usageCount: 124
        },
        {
          id: 'assist-hr-2',
          name: t('sidebar.assistant2'),
          description: '专业的内容创作助理，适用于HR文档编写',
          icon: 'fa-pen-to-square',
          status: 'online',
          usageCount: 87
        },
        {
          id: 'assist-hr-3',
          name: t('sidebar.assistant3'),
          description: '数据分析专家，适用于HR数据分析',
          icon: 'fa-chart-simple',
          status: 'online',
          usageCount: 65
        }
      ]
    },
    {
      id: 'logistics',
      name: t('agent.category.logistics'),
      assistants: [
        {
          id: 'assist-log-1',
          name: t('sidebar.assistant1'),
          description: '通用助理，适用于物流场景',
          icon: 'fa-robot',
          status: 'online',
          usageCount: 156
        },
        {
          id: 'assist-log-2',
          name: t('sidebar.assistant2'),
          description: '内容创作助理，适用于物流文档',
          icon: 'fa-pen-to-square',
          status: 'online',
          usageCount: 98
        },
        {
          id: 'assist-log-3',
          name: t('sidebar.assistant3'),
          description: '数据分析专家，适用于物流数据分析',
          icon: 'fa-chart-simple',
          status: 'online',
          usageCount: 129
        }
      ]
    },
    {
      id: 'finance',
      name: t('agent.category.finance'),
      assistants: [
        {
          id: 'assist-fin-1',
          name: t('sidebar.assistant1'),
          description: '通用助理，适用于财务场景',
          icon: 'fa-robot',
          status: 'online',
          usageCount: 203
        },
        {
          id: 'assist-fin-2',
          name: t('sidebar.assistant2'),
          description: '内容创作助理，适用于财务报告编写',
          icon: 'fa-pen-to-square',
          status: 'online',
          usageCount: 112
        },
        {
          id: 'assist-fin-3',
          name: t('sidebar.assistant3'),
          description: '数据分析专家，适用于财务数据分析',
          icon: 'fa-chart-simple',
          status: 'online',
          usageCount: 157
        }
      ]
    },
    {
      id: 'mes',
      name: t('agent.category.mes'),
      assistants: [
        {
          id: 'assist-mes-1',
          name: t('sidebar.assistant1'),
          description: '通用助理，适用于生产管理场景',
          icon: 'fa-robot',
          status: 'online',
          usageCount: 256
        },
        {
          id: 'assist-mes-2',
          name: t('sidebar.assistant2'),
          description: '内容创作助理，适用于生产文档',
          icon: 'fa-pen-to-square',
          status: 'online',
          usageCount: 143
        },
        {
          id: 'assist-mes-3',
          name: t('sidebar.assistant3'),
          description: '数据分析专家，适用于生产数据分析',
          icon: 'fa-chart-simple',
          status: 'online',
          usageCount: 109
        }
      ]
    }
  ], [language, updateCounter, t]);

  // 获取当前选中分类的Agent - 修改時間：2026-01-13 - 使用從 API 獲取的數據
  const currentAgents = useMemo(() => {
    if (!agentCategories || agentCategories.length === 0) {
      return [];
    }
    return agentCategories.find(category => category.id === activeTab)?.agents || [];
  }, [agentCategories, activeTab]);

  // 获取所有Agent（用于聊天输入框的代理选择器） - 修改時間：2026-01-13 - 使用從 API 獲取的數據
  const allAgents = useMemo(() => {
    if (!agentCategories || agentCategories.length === 0) {
      return [];
    }
    return agentCategories.flatMap(category => category.agents);
  }, [agentCategories]);

  // 获取所有Assistant（用于聊天输入框的助理选择器）
  const allAssistants = useMemo(() => {
    return assistantCategories.flatMap(category => category.assistants);
  }, [assistantCategories]);

  // 获取当前选中分类的Assistant
  const currentAssistants = assistantCategories.find(category => category.id === activeAssistantTab)?.assistants || [];

  return (
    <div className="flex-1 flex flex-col h-full bg-primary theme-transition">
       {/* 聊天区域头部 */}
      <div className="p-4 border-b border-primary flex items-center justify-between">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <h2 className="text-base font-bold text-primary flex-shrink-0">
            {selectedTask ? `${t('chat.task')}${selectedTask.title}` : t('chat.title')}
          </h2>
          {/* 修改時間：2026-01-21 12:45 UTC+8 - 顯示當前頁面 URL */}
          <span className="text-xs text-tertiary font-mono truncate flex-1 min-w-0" title={window.location.href}>
            {window.location.origin}{location.pathname}{location.hash}
          </span>
        </div>
         <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowSearchModal(true)}
            className="p-2 rounded-full hover:bg-tertiary transition-colors"
            title={t('chat.search.title', '搜索聊天記錄')}
            aria-label={t('chat.search.title', '搜索聊天記錄')}
          >
            <i className="fa-solid fa-search text-tertiary"></i>
          </button>
          <button
            className="p-2 rounded-full hover:bg-tertiary transition-all duration-300 relative group"
            onClick={toggleTheme}
            title={`切换到${theme === 'dark' ? '浅色' : '深色'}主题`}
            aria-label={`切换到${theme === 'dark' ? '浅色' : '深色'}主题`}
          >
            <i className={`fa-solid ${theme === 'dark' ? 'fa-sun' : 'fa-moon'} text-tertiary group-hover:text-yellow-400 transition-all duration-300 transform group-hover:scale-110`}></i>
            {/* 显示当前主题状态的小圆点 */}
            <span className={`absolute -top-1 -right-1 w-3 h-3 rounded-full border-2 border-secondary ${theme === 'dark' ? 'bg-yellow-400' : 'bg-blue-400'}`}></span>
          </button>
          <div className="relative">
            <button
              className="p-2 rounded-full hover:bg-tertiary transition-all duration-300 relative group"
              onClick={() => setShowLanguageSelector(!showLanguageSelector)}
              title="选择语言"
              aria-label="选择语言"
            >
              <i className={`fa-solid ${languageIcons[language]} text-tertiary group-hover:text-blue-400 transition-all duration-300 transform group-hover:scale-110`}></i>
            </button>
            {/* 语言选择下拉菜单 */}
            {showLanguageSelector && (
              <div className="absolute right-0 top-full mt-1 w-40 bg-secondary border border-primary rounded-lg shadow-lg z-20 theme-transition transform transition-all duration-200 origin-top-right">
                <div className="p-1 border-b border-primary text-[11.2px] font-medium text-primary">{t('language.select')}</div>
                {['zh_TW', 'zh_CN', 'en'].map(lang => (
                  <button
                    key={lang}
                    className={`w-full text-left px-4 py-2 text-[11.2px] hover:bg-tertiary transition-colors flex items-center ${
                      language === lang ? 'text-blue-400 bg-blue-900/20' : 'text-secondary'
                    }`}
                  onClick={() => {
                    // 安全地切换语言
                    const langKey = lang as 'zh_TW' | 'zh_CN' | 'en';
                    setLanguage(langKey);
                    setShowLanguageSelector(false);
                  }}
                  >
                    <i className={`fa-solid ${languageIcons[lang as 'zh_TW' | 'zh_CN' | 'en']} mr-2`}></i>
                    {languageNames[lang as 'zh_TW' | 'zh_CN' | 'en']}
                    {language === lang && (
                      <i className="fa-solid fa-check ml-auto text-green-400"></i>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
          {/* 知識庫管理按鈕 - 修改時間：2026-02-12 */}
          <button
            className="p-2 rounded-full hover:bg-tertiary transition-colors relative group"
            onClick={() => setShowKnowledgeBaseModal(true)}
            title="知識庫管理"
            aria-label="知識庫管理"
          >
            <BookOpen className="w-5 h-5 text-tertiary group-hover:text-blue-400 transition-colors" />
          </button>

          {/* 系統管理菜單（僅 system_admin 可見） */}
          {isAdmin && (
            <div className="relative system-menu-container">
              <button
                className="p-2 rounded-full hover:bg-tertiary transition-colors relative group"
                onClick={() => setShowSystemMenu(!showSystemMenu)}
                title="系統管理"
                aria-label="系統管理"
              >
                <i className="fa-solid fa-cog text-tertiary group-hover:text-blue-400 transition-colors"></i>
              </button>
              {/* 系統管理下拉菜單 */}
              {showSystemMenu && (
                <div className="absolute right-0 top-full mt-1 w-56 bg-secondary border border-primary rounded-lg shadow-lg z-30 theme-transition">
                  <div className="p-1 border-b border-primary text-xs font-medium text-primary px-3 py-2">
                    系統管理
                  </div>
                  <button
                    className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-tertiary transition-colors flex items-center gap-3"
                    onClick={() => {
                      navigate('/admin/services');
                      setShowSystemMenu(false);
                    }}
                  >
                    <i className="fa-solid fa-server w-4 text-center"></i>
                    <span>系統服務狀態</span>
                  </button>
                  <button
                    className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-tertiary transition-colors flex items-center gap-3"
                    onClick={() => {
                      navigate('/admin/accounts');
                      setShowSystemMenu(false);
                    }}
                  >
                    <i className="fa-solid fa-users-cog w-4 text-center"></i>
                    <span>賬號/安全群組設置</span>
                  </button>
                  <button
                    className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-tertiary transition-colors flex items-center gap-3"
                    onClick={() => {
                      navigate('/admin/agent-requests');
                      setShowSystemMenu(false);
                    }}
                  >
                    <i className="fa-solid fa-clipboard-check w-4 text-center"></i>
                    <span>Agent 申請審查</span>
                  </button>
                  <div className="border-t border-primary my-1"></div>
                  <button
                    className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-tertiary transition-colors flex items-center gap-3"
                    onClick={() => {
                      navigate('/admin/settings');
                      setShowSystemMenu(false);
                    }}
                  >
                    <i className="fa-solid fa-sliders-h w-4 text-center"></i>
                    <span>系統設置</span>
                  </button>
                </div>
              )}
            </div>
          )}
          {/* 普通設置按鈕（非 system_admin 用戶） */}
          {!isAdmin && (
            <button className="p-2 rounded-full hover:bg-tertiary transition-colors">
              <i className="fa-solid fa-cog text-tertiary"></i>
            </button>
          )}
          {onResultPanelToggle && (
            <button
              onClick={onResultPanelToggle}
              className="p-2 rounded-full hover:bg-tertiary transition-colors"
              title={resultPanelCollapsed ? t('chat.expandPanel') : t('chat.collapsePanel')}
              aria-label={resultPanelCollapsed ? t('chat.expandPanel') : t('chat.collapsePanel')}
            >
              {resultPanelCollapsed ? (
                <PanelRightOpen className="w-5 h-5 text-tertiary" />
              ) : (
                <PanelRightClose className="w-5 h-5 text-tertiary" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* 聊天内容区域 */}
      <div className="flex-1 overflow-y-auto p-4" ref={messagesContainerRef}>
        {/* 優先顯示任務內容：如果有選中的任務，優先顯示任務內容，而不是瀏覽頁面 */}
        {selectedTask && selectedTask.messages ? (
          // 显示任务相关的对话
          <div className="space-y-6">
            {selectedTask.messages.map(message => (
              <ChatMessage
                key={message.id}
                message={message}
                ref={(el) => {
                  if (el) {
                    messageRefs.current.set(message.id, el);
                  } else {
                    messageRefs.current.delete(message.id);
                  }
                }}
              />
            ))}
            {/* 用於滾動到底部的錨點 */}
            <div ref={messagesEndRef} />
          </div>
        ) : selectedTask ? (
          // 显示任务但还没有消息
          <div className="space-y-6">
            <div className="text-center text-tertiary py-8">
              <i className="fa-solid fa-comments text-[28.8px] mb-4"></i>
              <p className="text-[12.8px]">{t('chat.noMessages', '還沒有消息，開始對話吧！')}</p>
            </div>
          </div>
        ) : browseMode === 'assistants' ? (
          // 显示助理列表（使用分类 Tabs，与 Agent 相同的方式）
          <>
            {/* 欢迎消息 */}
            <div className="mb-8">
              <div className="flex items-start mb-2">
                <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center mr-3">
                  <i className="fa-solid fa-robot"></i>
                </div>
                <div>
                  <div className="font-medium text-primary text-[12.8px]">{t('sidebar.browseAssistants')}</div>
                  <div className="text-[11.2px] text-tertiary">选择助理来创建任务</div>
                </div>
              </div>
            </div>

            {/* Assistant分类Tabs 和管理按钮 */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex-1">
                <Tabs
                  tabs={assistantCategories.map(cat => ({
                    id: cat.id,
                    label: cat.name,
                    // 移除 translationKey，直接使用從 API 獲取的多語言文本（如果 Assistant 也改用 API）
                    // translationKey: `agent.category.${cat.id.replace('-', '')}`
                  }))}
                  activeTab={activeAssistantTab}
                  onTabChange={setActiveAssistantTab}
                />
              </div>
              <button
                className="ml-4 px-4 py-2 rounded-full bg-purple-600/20 hover:bg-purple-600/30 text-purple-400 border border-purple-500/30 hover:border-purple-500/50 transition-all duration-200 flex items-center"
                title={t('chat.manageAssistants')}
                aria-label={t('chat.manageAssistants')}
                onClick={() => {
                  setMaintainingAssistantId(null);
                  setShowAssistantMaintenanceModal(true);
                }}
              >
                <i className="fa-solid fa-cog mr-2"></i>
                <span className="text-[11.2px] font-medium">{t('chat.manage')}</span>
              </button>
            </div>

            {/* Assistant卡片展示区域 */}
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {currentAssistants.map(assistant => {
                // 检查是否收藏 - 兼容 Set 和 Map
                const isFavorite = favoriteAssistants?.has(assistant.id) ?? false;

                return (
                  <AssistantCard
                    key={assistant.id}
                    assistant={assistant}
                    isFavorite={isFavorite}
                    onEdit={(assistantId) => {
                      setMaintainingAssistantId(assistantId);
                      setShowAssistantMaintenanceModal(true);
                    }}
                    onDelete={(assistantId) => {
                      setDeletingAssistantId(assistantId);
                      setShowDeleteConfirm(true);
                    }}
                    onClick={() => {
                      if (onAssistantSelect) {
                        onAssistantSelect(assistant.id);
                      }
                    }}
                    onFavorite={(assistantId, isFav) => {
                      // 传递助理名称
                      onAssistantFavorite?.(assistantId, isFav, assistant.name);
                    }}
                  />
                );
              })}
            </div>
          </>
        ) : browseMode === 'agents' ? (
          // 显示代理列表（带分类 Tabs：HR、Logistics、Finance 等）
          <>
            {/* 欢迎消息 */}
            <div className="mb-8">
              <div className="flex items-start mb-2">
                <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center mr-3">
                  <i className="fa-solid fa-robot"></i>
                </div>
                <div>
                  <div className="font-medium text-primary text-[12.8px]">{t('chat.aiAssistant')}</div>
                  <div className="text-[11.2px] text-tertiary">今天 16:39</div>
                </div>
              </div>
              <div className="bg-secondary p-4 rounded-lg ml-11">
                  <p className="text-secondary text-[12.8px]">{t('welcome.message')}</p>
              </div>
            </div>

            {/* 加载状态 */}
            {agentConfigLoading && (
              <div className="flex items-center justify-center py-12">
                <div className="text-center">
                  <i className="fa-solid fa-spinner fa-spin text-[28.8px] text-tertiary mb-4"></i>
                  <p className="text-[12.8px] text-tertiary">{t('common.loading', '載入中...')}</p>
                </div>
              </div>
            )}

            {/* 错误状态 */}
            {agentConfigError && !agentConfigLoading && (
              <div className="flex items-center justify-center py-12">
                <div className="text-center">
                  <i className="fa-solid fa-exclamation-triangle text-[28.8px] text-yellow-400 mb-4"></i>
                  <p className="text-[12.8px] text-tertiary mb-4">
                    {t('common.error', '載入代理配置失敗')}: {agentConfigError.message}
                  </p>
                  <button
                    onClick={() => window.location.reload()}
                    className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-[11.2px] transition-colors"
                  >
                    {t('common.retry', '重試')}
                  </button>
                </div>
              </div>
            )}

            {/* Agent分类Tabs 和管理按钮 - 只在非加载且无错误时显示 */}
            {!agentConfigLoading && !agentConfigError && (
              <>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex-1">
                    <Tabs
                      tabs={agentCategories.map(cat => ({
                        id: cat.id,
                        label: cat.name,
                        // 移除 translationKey，直接使用從 API 獲取的多語言文本
                        // translationKey: `agent.category.${cat.id.replace('-', '')}`
                      }))}
                      activeTab={activeTab}
                      onTabChange={setActiveTab}
                    />
                  </div>
                  <button
                    className="ml-4 px-4 py-2 rounded-full bg-green-600/20 hover:bg-green-600/30 text-green-400 border border-green-500/30 hover:border-green-500/50 transition-all duration-200 flex items-center"
                    title={t('chat.manageAgents')}
                    aria-label={t('chat.manageAgents')}
                    onClick={() => setShowAgentRegistrationModal(true)}
                  >
                    <i className="fa-solid fa-cog mr-2"></i>
                    <span className="text-[11.2px] font-medium">{t('chat.manage')}</span>
                  </button>
                </div>

                {/* Agent卡片展示区域 */}
                <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {currentAgents.length > 0 ? (
                    currentAgents.map(agent => {
                      // 检查是否收藏 - 兼容 Set 和 Map
                      const isFavorite = favoriteAgents?.has(agent.id) ?? false;

                      return (
                        <AgentCard
                          key={agent.id}
                          agent={agent}
                          isFavorite={isFavorite}
                          onEdit={(agentId) => {
                            // 修改時間：2026-01-13 - 實現 Agent Display Config 編輯功能
                            setMaintainingAgentId(agentId);
                            setShowAgentEditModal(true);
                          }}
                          onDelete={(agentId) => {
                            // 修改時間：2026-01-13 - 打開刪除確認 Modal
                            const agent = currentAgents.find(a => a.id === agentId);
                            if (agent) {
                              setDeletingAgentId(agentId);
                              setDeletingAgentName(agent.name);
                              setShowDeleteAgentModal(true);
                            }
                          }}
                          onClick={() => {
                            // 審查中的 Agent 無法啟動對話
                            if (agent.status === 'registering') {
                              return;
                            }
                            if (onAgentSelect) {
                              onAgentSelect(agent.id);
                            }
                          }}
                          onFavorite={(agentId, isFav) => {
                            // 传递代理名称
                            onAgentFavorite?.(agentId, isFav, agent.name);
                          }}
                        />
                      );
                    })
                  ) : (
                    <div className="col-span-full text-center py-12">
                      <p className="text-[12.8px] text-tertiary">{t('common.empty', '暫無代理')}</p>
                    </div>
                  )}
                </div>
              </>
            )}
          </>
        ) : null}
      </div>

      {/* 聊天输入区域 - 在代理浏览或助理浏览模式下，只有建立task后才显示 */}
      {/* 当没有选中任务时，如果browseMode为null但显示的是代理列表时，也应该隐藏 */}
      {selectedTask !== undefined && (
      <div className="p-4 border-t border-primary">
        <ChatInput
          agents={allAgents}
          assistants={allAssistants}
          onAgentSelect={onAgentSelect}
          onAssistantSelect={onAssistantSelect}
          onModelSelect={onModelSelect}
          selectedAgentId={selectedTask?.executionConfig?.agentId}
          selectedAssistantId={selectedTask?.executionConfig?.assistantId}
          selectedModelId={selectedTask?.executionConfig?.modelId || 'auto'}
          currentTaskId={currentTaskId}
          selectedTask={selectedTask}
          onTaskCreate={onTaskCreate}
          onTaskDelete={onTaskDelete}
          isPreviewMode={isPreviewMode}
          onMessageSend={onMessageSend}
          onTaskTitleGenerate={(title) => {
            // 生成任务标题（只在任务标题还是默认值时更新）
            if (selectedTask && (selectedTask.title === '新任務' || selectedTask.title === '新任务' || selectedTask.title === 'New Task')) {
              const updatedTask: Task = {
                ...selectedTask,
                title: title,
              };
              onTaskUpdate?.(updatedTask);
            }
          }}
        />
      </div>
      )}

      {/* Agent 註冊模態框 */}
      <AgentRegistrationModal
        isOpen={showAgentRegistrationModal}
        onClose={() => setShowAgentRegistrationModal(false)}
        onSuccess={() => {
          setShowAgentRegistrationModal(false);
          // 可以在這裡刷新 Agent 列表
          refetchAgentConfig();
        }}
        categoryName={agentCategories.find(cat => cat.id === activeTab)?.name}
        categoryId={activeTab}
      />

      {/* Assistant 維護模態框 */}
      <AssistantMaintenanceModal
        isOpen={showAssistantMaintenanceModal}
        assistantId={maintainingAssistantId || undefined}
        assistant={maintainingAssistantId ? currentAssistants.find(a => a.id === maintainingAssistantId) : undefined}
        key={maintainingAssistantId || 'new-assistant'} // 添加 key 确保组件正确更新
        onClose={() => {
          setShowAssistantMaintenanceModal(false);
          setMaintainingAssistantId(null);
        }}
        onSave={(data) => {
          console.log('[ChatArea] 🎯 onSave callback received!', {
            maintainingAssistantId,
            dataId: data.id,
            dataAllowedTools: data.allowedTools,
            dataAllowedToolsLength: data.allowedTools?.length,
            hasWebSearch: data.allowedTools?.includes('web_search'),
            fullData: data,
          });

          // 保存助理的 allowedTools 到 localStorage
          // 优先使用 data.id（从 AssistantMaintenanceModal 传递），然后是 maintainingAssistantId
          const assistantIdToSave = data.id || maintainingAssistantId;

          console.log('[ChatArea] Assistant ID resolution:', {
            dataId: data.id,
            maintainingAssistantId,
            assistantIdToSave,
            hasAllowedTools: !!data.allowedTools,
            allowedToolsCount: data.allowedTools?.length || 0,
          });

          if (data.allowedTools && assistantIdToSave) {
            try {
              const storageKey = `assistant_${assistantIdToSave}_allowedTools`;
              localStorage.setItem(storageKey, JSON.stringify(data.allowedTools));
              console.log('[ChatArea] ✅ Saved assistant allowedTools to localStorage:', {
                assistantId: assistantIdToSave,
                storageKey,
                allowedTools: data.allowedTools,
                allowedToolsCount: data.allowedTools.length,
                hasWebSearch: data.allowedTools.includes('web_search'),
                webSearchIndex: data.allowedTools.indexOf('web_search'),
              });

              // 验证保存是否成功
              const verify = localStorage.getItem(storageKey);
              console.log('[ChatArea] Verification - localStorage value:', {
                storageKey,
                stored: verify,
                parsed: verify ? JSON.parse(verify) : null,
              });

              // 触发自定义事件，通知其他组件更新
              window.dispatchEvent(new CustomEvent('assistantToolsUpdated', {
                detail: {
                  assistantId: assistantIdToSave,
                  allowedTools: data.allowedTools,
                }
              }));
            } catch (error) {
              console.error('[ChatArea] ❌ Failed to save assistant allowedTools:', error);
            }
          } else {
            console.warn('[ChatArea] ⚠️ Cannot save allowedTools:', {
              hasAllowedTools: !!data.allowedTools,
              allowedTools: data.allowedTools,
              hasAssistantId: !!assistantIdToSave,
              maintainingAssistantId,
            });
          }
          // TODO: 調用 API 保存助理維護數據
          setShowAssistantMaintenanceModal(false);
          setMaintainingAssistantId(null);
        }}
      />

      {/* 搜索 Modal */}
      {selectedTask && selectedTask.messages && (
        <ChatSearchModal
          isOpen={showSearchModal}
          onClose={() => setShowSearchModal(false)}
          messages={selectedTask.messages}
          onSelectMessage={scrollToMessage}
        />
      )}

      {/* 刪除確認對話框 */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowDeleteConfirm(false)}>
          <div
            className="bg-secondary border border-primary rounded-lg p-6 max-w-md w-full mx-4 shadow-xl theme-transition"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-sm font-semibold text-primary mb-4">{t('assistant.delete.title')}</h3>
            <p className="text-[11.2px] text-tertiary mb-6">{t('assistant.delete.confirm')}</p>
            <div className="flex justify-end gap-3">
              <button
                className="px-4 py-2 text-[11.2px] rounded-lg bg-tertiary hover:bg-hover text-primary transition-colors"
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setDeletingAssistantId(null);
                }}
              >
                {t('assistant.delete.cancelButton')}
              </button>
              <button
                className="px-4 py-2 text-[11.2px] rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors"
                onClick={() => {
                  if (deletingAssistantId) {
                    // TODO: 調用 API 刪除助理
                    setShowDeleteConfirm(false);
                    setDeletingAssistantId(null);
                  }
                }}
              >
                {t('assistant.delete.confirmButton')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Agent Display Config 編輯模態框 - 修改時間：2026-01-13 */}
      <AgentDisplayConfigModal
        isOpen={showAgentEditModal}
        agentId={maintainingAgentId || undefined}
        onClose={() => {
          setShowAgentEditModal(false);
          setMaintainingAgentId(null);
        }}
        onSuccess={() => {
          setShowAgentEditModal(false);
          setMaintainingAgentId(null);
          // 刷新代理配置列表
          if (refetchAgentConfig) {
            refetchAgentConfig();
          }
        }}
      />

      {/* 刪除代理確認模態框 - 修改時間：2026-01-13 */}
      <DeleteAgentConfirmModal
        isOpen={showDeleteAgentModal}
        agentId={deletingAgentId || ''}
        agentName={deletingAgentName}
        onClose={() => {
          setShowDeleteAgentModal(false);
          setDeletingAgentId(null);
          setDeletingAgentName('');
        }}
        onConfirm={async () => {
          if (!deletingAgentId) return;
          await deleteAgentConfig(deletingAgentId);
          // 刪除成功後刷新代理配置列表
          if (refetchAgentConfig) {
            refetchAgentConfig();
          }
        }}
      />

      {/* 知識庫管理 Modal - 修改時間：2026-02-12 */}
      <KnowledgeBaseModal
        isOpen={showKnowledgeBaseModal}
        onClose={() => setShowKnowledgeBaseModal(false)}
      />
    </div>
  );
}
