import { useState, useMemo } from 'react';
import { PanelRightClose, PanelRightOpen } from 'lucide-react';
import AgentCard from './AgentCard';
import AssistantCard from './AssistantCard';
import ChatInput from './ChatInput';
import Tabs from './Tabs';
import { Task } from './Sidebar';
import ChatMessage from './ChatMessage';
import AgentRegistrationModal from './AgentRegistrationModal';
import AssistantMaintenanceModal from './AssistantMaintenanceModal';
import { useTheme } from '../hooks/useTheme';
import { useLanguage, languageNames, languageIcons } from '../contexts/languageContext';

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
  }

  interface ChatAreaProps {
    selectedTask?: Task;
    browseMode?: 'assistants' | 'agents' | null;
    onAssistantSelect?: (assistantId: string) => void;
    onAgentSelect?: (agentId: string) => void;
    resultPanelCollapsed?: boolean;
    onResultPanelToggle?: () => void;
    onAssistantFavorite?: (assistantId: string, isFavorite: boolean, assistantName?: string) => void;
    favoriteAssistants?: Map<string, string> | Set<string>;
    onAgentFavorite?: (agentId: string, isFavorite: boolean, agentName?: string) => void;
    favoriteAgents?: Map<string, string> | Set<string>;
  }

  export default function ChatArea({ selectedTask, browseMode, onAssistantSelect, onAgentSelect, resultPanelCollapsed, onResultPanelToggle, onAssistantFavorite, favoriteAssistants = new Map(), onAgentFavorite, favoriteAgents = new Map(), onTaskUpdate }: ChatAreaProps) {
    const [activeTab, setActiveTab] = useState('human-resource');
    const [activeAssistantTab, setActiveAssistantTab] = useState('human-resource');
    const { theme, toggleTheme } = useTheme();
    const { language, setLanguage, t, updateCounter } = useLanguage();
    const [showLanguageSelector, setShowLanguageSelector] = useState(false);
    const [showAgentRegistrationModal, setShowAgentRegistrationModal] = useState(false);
    const [showAssistantMaintenanceModal, setShowAssistantMaintenanceModal] = useState(false);
    const [maintainingAssistantId, setMaintainingAssistantId] = useState<string | null>(null);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [deletingAssistantId, setDeletingAssistantId] = useState<string | null>(null);

    // Mock数据 - 不同类别的Agent - 使用useMemo和updateCounter确保语言变更时重新渲染
    const agentCategories: AgentCategory[] = useMemo(() => [
      {
        id: 'human-resource',
        name: t('agent.category.humanResource'),
        agents: [
          {
            id: 'hr-1',
             name: t('agent.category.humanResource') + t('agent.hr.assistant'),
             description: t('agent.hr.description.assistant'),
            icon: 'fa-user-tie',
            status: 'online',
            usageCount: 124
          },
          {
            id: 'hr-2',
            name: t('agent.hr.trainingManager'),
            description: t('agent.hr.description.trainingManager'),
            icon: 'fa-graduation-cap',
            status: 'online',
            usageCount: 87
          },
          {
            id: 'hr-3',
            name: t('agent.hr.performanceAnalysis'),
            description: t('agent.hr.description.performanceAnalysis'),
            icon: 'fa-chart-line',
            status: 'maintenance',
            usageCount: 65
          },
          {
            id: 'hr-4',
            name: t('agent.hr.employeeRelations'),
            description: t('agent.hr.description.employeeRelations'),
            icon: 'fa-handshake',
            status: 'online',
            usageCount: 92
          },
          {
            id: 'hr-5',
            name: t('agent.hr.compensationBenefits'),
            description: t('agent.hr.description.compensationBenefits'),
            icon: 'fa-coins',
            status: 'online',
            usageCount: 78
          },
          {
            id: 'hr-6',
            name: t('agent.hr.talentDevelopment'),
            description: t('agent.hr.description.talentDevelopment'),
            icon: 'fa-seedling',
            status: 'online',
            usageCount: 63
          }
        ]
      },
      {
        id: 'logistics',
        name: t('agent.category.logistics'),agents: [
          {
            id: 'log-1',
            name: t('agent.logistics.supplyChainOptimization'),
            description: t('agent.logistics.description.supplyChainOptimization'),
            icon: 'fa-truck',
            status: 'online',
            usageCount: 156
          },
          {
            id: 'log-2',
            name: t('agent.logistics.inventoryManagement'),
            description: t('agent.logistics.description.inventoryManagement'),
            icon: 'fa-warehouse',
            status: 'online',
            usageCount: 98
          },
          {
            id: 'log-3',
            name: t('agent.logistics.routePlanning'),
            description: t('agent.logistics.description.routePlanning'),
            icon: 'fa-route',
            status: 'online',
            usageCount: 129
          },
          {
            id: 'log-4',
            name: t('agent.logistics.dataAnalysis'),
            description: t('agent.logistics.description.dataAnalysis'),
            icon: 'fa-chart-bar',
            status: 'online',
            usageCount: 85
          },
          {
            id: 'log-5',
            name: t('agent.logistics.supplierManagement'),
            description: t('agent.logistics.description.supplierManagement'),
            icon: 'fa-hand-holding-box',
            status: 'online',
            usageCount: 76
          }
        ]
      },
      {
        id: 'finance',
        name: t('agent.category.finance'),
        agents: [
          {
            id: 'fin-1',
            name: t('agent.finance.financialAnalyst'),
            description: t('agent.finance.description.financialAnalyst'),
            icon: 'fa-chart-pie',
            status: 'online',
            usageCount: 203
          },
          {
            id: 'fin-2',
            name: t('agent.finance.budgetPlanning'),
            description: t('agent.finance.description.budgetPlanning'),
            icon: 'fa-money-bill-wave',
            status: 'offline',
            usageCount: 112
          },
          {
            id: 'fin-3',
            name: t('agent.finance.costControl'),
            description: t('agent.finance.description.costControl'),
            icon: 'fa-piggy-bank',
            status: 'online',
            usageCount: 157
          },
          {
            id: 'fin-4',
            name: t('agent.finance.financialReportGeneration'),
            description: t('agent.finance.description.financialReportGeneration'),
            icon: 'fa-file-invoice-dollar',
            status: 'online',
            usageCount: 189
          },
          {
            id: 'fin-5',
            name: t('agent.finance.taxPlanning'),
            description: t('agent.finance.description.taxPlanning'),
            icon: 'fa-receipt',
            status: 'maintenance',
            usageCount: 67
          },
          {
            id: 'fin-6',
            name: t('agent.finance.investmentAnalysis'),
            description: t('agent.finance.description.investmentAnalysis'),
            icon: 'fa-chart-line',
            status: 'online',
            usageCount: 134
          }
        ]
      },
      {
        id: 'mes',
        name: t('agent.category.mes'),
        agents: [
          {
            id: 'mes-1',
            name: t('agent.mes.productionMonitoring'),
            description: t('agent.mes.description.productionMonitoring'),
            icon: 'fa-industry',
            status: 'online',
            usageCount: 256
          },
          {
            id: 'mes-2',
            name: t('agent.mes.qualityControl'),
            description: t('agent.mes.description.qualityControl'),
            icon: 'fa-check-circle',
            status: 'online',
            usageCount: 143
          },
          {
            id: 'mes-3',
            name: t('agent.mes.efficiencyAnalysis'),
            description: t('agent.mes.description.efficiencyAnalysis'),
            icon: 'fa-tachometer-alt',
            status: 'online',
            usageCount: 109
          },
          {
            id: 'mes-4',
            name: t('agent.mes.equipmentMaintenance'),
            description: t('agent.mes.description.equipmentMaintenance'),
            icon: 'fa-tools',
            status: 'online',
            usageCount: 137
          },
          {
            id: 'mes-5',
            name: t('agent.mes.productionScheduling'),
            description: t('agent.mes.description.productionScheduling'),
            icon: 'fa-calendar-alt',
            status: 'online',
            usageCount: 168
          },
          {
            id: 'mes-6',
            name: t('agent.mes.materialManagement'),
            description: t('agent.mes.description.materialManagement'),
            icon: 'fa-box-open',
            status: 'online',
            usageCount: 95
          },
          {
            id: 'mes-7',
            name: t('agent.mes.processOptimization'),
            description: t('agent.mes.description.processOptimization'),
            icon: 'fa-sliders-h',
            status: 'online',
            usageCount: 83
          }
        ]
      }
    ], [language, updateCounter, t]);

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

  // 获取当前选中分类的Agent
  const currentAgents = agentCategories.find(category => category.id === activeTab)?.agents || [];

  // 获取所有Agent（用于聊天输入框的代理选择器）
  const allAgents = useMemo(() => {
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
        <h2 className="text-xl font-bold text-primary">
          {selectedTask ? `${t('chat.task')}${selectedTask.title}` : t('chat.title')}
        </h2>
         <div className="flex items-center space-x-2">
          <button className="p-2 rounded-full hover:bg-tertiary transition-colors">
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
                <div className="p-1 border-b border-primary text-sm font-medium text-primary">{t('language.select')}</div>
                {['zh_TW', 'zh_CN', 'en'].map(lang => (
                  <button
                    key={lang}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-tertiary transition-colors flex items-center ${
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
          <button className="p-2 rounded-full hover:bg-tertiary transition-colors">
            <i className="fa-solid fa-cog text-tertiary"></i>
          </button>
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
      <div className="flex-1 overflow-y-auto p-4">
        {browseMode === 'assistants' ? (
          // 显示助理列表（使用分类 Tabs，与 Agent 相同的方式）
          <>
            {/* 欢迎消息 */}
            <div className="mb-8">
              <div className="flex items-start mb-2">
                <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center mr-3">
                  <i className="fa-solid fa-robot"></i>
                </div>
                <div>
                  <div className="font-medium text-primary">{t('sidebar.browseAssistants')}</div>
                  <div className="text-sm text-tertiary">选择助理来创建任务</div>
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
                    translationKey: `agent.category.${cat.id.replace('-', '')}`
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
                <span className="text-sm font-medium">{t('chat.manage')}</span>
              </button>
            </div>

            {/* Assistant卡片展示区域 */}
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {currentAssistants.map(assistant => {
                // 检查是否收藏 - 兼容 Set 和 Map
                const isFavorite = favoriteAssistants instanceof Map
                  ? favoriteAssistants.has(assistant.id)
                  : favoriteAssistants.has(assistant.id);

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
        ) : selectedTask && selectedTask.messages ? (
          // 显示任务相关的对话
          <div className="space-y-6">
            {selectedTask.messages.map(message => (
              <ChatMessage key={message.id} message={message} />
            ))}
          </div>
        ) : selectedTask ? (
          // 显示任务但还没有消息
          <div className="space-y-6">
            <div className="text-center text-tertiary py-8">
              <i className="fa-solid fa-comments text-4xl mb-4"></i>
              <p>{t('chat.noMessages', '還沒有消息，開始對話吧！')}</p>
            </div>
          </div>
        ) : (
          // 显示默认的Agent列表（带分类 Tabs：HR、Logistics、Finance 等）
          <>
            {/* 欢迎消息 */}
            <div className="mb-8">
              <div className="flex items-start mb-2">
                <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center mr-3">
                  <i className="fa-solid fa-robot"></i>
                </div>
                <div>
                  <div className="font-medium text-primary">{t('chat.aiAssistant')}</div>
                  <div className="text-sm text-tertiary">今天 16:39</div>
                </div>
              </div>
              <div className="bg-secondary p-4 rounded-lg ml-11">
                  <p className="text-secondary">{t('welcome.message')}</p>
              </div>
            </div>

            {/* Agent分类Tabs 和管理按钮 */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex-1">
                <Tabs
                  tabs={agentCategories.map(cat => ({
                    id: cat.id,
                    label: cat.name,
                    translationKey: `agent.category.${cat.id.replace('-', '')}`
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
                <span className="text-sm font-medium">{t('chat.manage')}</span>
              </button>
            </div>

            {/* Agent卡片展示区域 */}
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {currentAgents.map(agent => {
                // 检查是否收藏 - 兼容 Set 和 Map
                const isFavorite = favoriteAgents instanceof Map
                  ? favoriteAgents.has(agent.id)
                  : favoriteAgents.has(agent.id);

                return (
                  <AgentCard
                    key={agent.id}
                    agent={agent}
                    isFavorite={isFavorite}
                    onEdit={(agentId) => {
                      // 可以在这里添加编辑代理的逻辑
                    }}
                    onDelete={(agentId) => {
                      // 可以在这里添加删除代理的逻辑
                    }}
                    onClick={() => {
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
              })}
            </div>
          </>
        )}
      </div>

      {/* 聊天输入区域 */}
      <div className="p-4 border-t border-primary">
        <ChatInput
          agents={allAgents}
          assistants={allAssistants}
          onAgentSelect={onAgentSelect}
          onAssistantSelect={onAssistantSelect}
          selectedAgentId={selectedTask?.executionConfig?.agentId}
          selectedAssistantId={selectedTask?.executionConfig?.assistantId}
          selectedModelId={selectedTask?.executionConfig?.modelId || 'auto'}
          favoriteAgents={favoriteAgents}
          favoriteAssistants={favoriteAssistants}
          onMessageSend={(message) => {
            // 处理消息发送
            console.log('[ChatArea] Message sent:', message);
            // 这里可以添加实际的消息处理逻辑
          }}
          onTaskTitleGenerate={(title) => {
            // 生成任务标题（只在任务标题还是默认值时更新）
            if (selectedTask && (selectedTask.title === '新任務' || selectedTask.title === '新任务' || selectedTask.title === 'New Task')) {
              const updatedTask: Task = {
                ...selectedTask,
                title: title,
              };
              console.log('[ChatArea] Task title generated:', title);
              onTaskUpdate?.(updatedTask);
            }
          }}
        />
      </div>

      {/* Agent 註冊模態框 */}
      <AgentRegistrationModal
        isOpen={showAgentRegistrationModal}
        onClose={() => setShowAgentRegistrationModal(false)}
        onSuccess={() => {
          setShowAgentRegistrationModal(false);
          // 可以在這裡刷新 Agent 列表
        }}
      />

      {/* Assistant 維護模態框 */}
      <AssistantMaintenanceModal
        isOpen={showAssistantMaintenanceModal}
        assistantId={maintainingAssistantId || undefined}
        assistant={maintainingAssistantId ? currentAssistants.find(a => a.id === maintainingAssistantId) : undefined}
        onClose={() => {
          setShowAssistantMaintenanceModal(false);
          setMaintainingAssistantId(null);
        }}
        onSave={(data) => {
          console.log('Assistant maintenance data:', data);
          // TODO: 調用 API 保存助理維護數據
          setShowAssistantMaintenanceModal(false);
          setMaintainingAssistantId(null);
        }}
      />

      {/* 刪除確認對話框 */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowDeleteConfirm(false)}>
          <div
            className="bg-secondary border border-primary rounded-lg p-6 max-w-md w-full mx-4 shadow-xl theme-transition"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-primary mb-4">{t('assistant.delete.title')}</h3>
            <p className="text-sm text-tertiary mb-6">{t('assistant.delete.confirm')}</p>
            <div className="flex justify-end gap-3">
              <button
                className="px-4 py-2 text-sm rounded-lg bg-tertiary hover:bg-hover text-primary transition-colors"
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setDeletingAssistantId(null);
                }}
              >
                {t('assistant.delete.cancelButton')}
              </button>
              <button
                className="px-4 py-2 text-sm rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors"
                onClick={() => {
                  if (deletingAssistantId) {
                    console.log('Delete assistant:', deletingAssistantId);
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
    </div>
  );
}
