import { useState, useMemo } from 'react';
import { cn } from '../lib/utils';
import { useLanguage } from '../contexts/languageContext';

// 定义消息接口
export interface Message {
  id: string;
  sender: 'user' | 'ai';
  content: string;
  timestamp: string;
  containsMermaid?: boolean;
}

// 定义任务接口
export interface Task {
  id: number;
  title: string;
  status: 'pending' | 'in-progress' | 'completed';
  dueDate: string;
  messages?: Message[];
  executionConfig?: {
    mode: 'free' | 'assistant' | 'agent';
    assistantId?: string;
    agentId?: string;
  };
}

// 定义收藏项接口
export interface FavoriteItem {
  id: string;
  name: string;
  type: 'task' | 'assistant' | 'agent';
  itemId: string;
  icon?: string;
}

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  onTaskSelect?: (task: Task) => void;
  onAgentSelect?: (agentId: string) => void;
  onAssistantSelect?: (assistantId: string) => void;
  onBrowseAssistants?: () => void;
  onBrowseAgents?: () => void;
  selectedTask?: Task;
  browseMode?: 'assistants' | 'agents' | null;
  favorites?: FavoriteItem[];
}

export default function Sidebar({ collapsed, onToggle, onTaskSelect, onAgentSelect, onAssistantSelect, onBrowseAssistants, onBrowseAgents, selectedTask, browseMode, favorites: externalFavorites }: SidebarProps) {
  const [activeSection, setActiveSection] = useState<'favorites' | 'tasks'>('tasks');
  const [activeItemId, setActiveItemId] = useState<string | number | null>(null); // 跟踪当前选中的具体 item ID
  const [showAddTask, setShowAddTask] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const { t, updateCounter, language } = useLanguage();

  // 可收合区域的状态管理
  const [expandedSections, setExpandedSections] = useState({
    tasks: true,
  });

  // 模拟助理数据
  const assistants = useMemo(() => [
    { id: 'assist-1', name: t('sidebar.assistant1') },
    { id: 'assist-2', name: t('sidebar.assistant2') },
    { id: 'assist-3', name: t('sidebar.assistant3') },
  ], [language, updateCounter, t]);

  // 模拟代理数据
  const agents = useMemo(() => [
    { id: 'agent-1', name: t('sidebar.agent1') },
    { id: 'agent-2', name: t('sidebar.agent2') },
    { id: 'agent-3', name: t('sidebar.agent3') },
    { id: 'agent-4', name: t('sidebar.agent4') },
  ], [language, updateCounter, t]);

  // 使用 useMemo 和 language 作为依赖，确保语言变更时重新计算这些数据
  // 如果外部传入了收藏列表，使用外部的；否则使用默认的
  const favorites: FavoriteItem[] = useMemo(() => {
    if (externalFavorites) {
      return externalFavorites;
    }
    // 默认收藏列表（向后兼容）
    return [
      { id: 'fav-1', name: t('sidebar.favorite1'), type: 'task' as const, itemId: '1', icon: 'fa-tasks' },
      { id: 'fav-2', name: t('sidebar.favorite2'), type: 'task' as const, itemId: '2', icon: 'fa-tasks' },
      { id: 'fav-3', name: t('sidebar.favorite3'), type: 'task' as const, itemId: '3', icon: 'fa-tasks' },
      { id: 'fav-4', name: assistants[0].name, type: 'assistant' as const, itemId: assistants[0].id, icon: 'fa-robot' },
      { id: 'fav-5', name: assistants[1].name, type: 'assistant' as const, itemId: assistants[1].id, icon: 'fa-robot' },
      { id: 'fav-6', name: agents[0].name, type: 'agent' as const, itemId: agents[0].id, icon: 'fa-user-tie' },
      { id: 'fav-7', name: agents[1].name, type: 'agent' as const, itemId: agents[1].id, icon: 'fa-user-tie' },
    ];
  }, [externalFavorites, language, updateCounter, t, assistants, agents]);


  // 模拟历史任务数据，包含对话内容
  // 使用 useMemo 确保语言变更时重新计算任务数据
  const tasks: Task[] = useMemo(() => [
    {
       id: 1,
       title: t('sidebar.favorite1'),
      status: 'completed' as const,
      dueDate: '2025-12-01',
      messages: [
        {
          id: '1-1',
          sender: 'user' as const,
          content: t('task.salesReportRequest'),
          timestamp: '2025-12-01 10:15'
        },
        {
          id: '1-2',
          sender: 'ai' as const,
          content: '当然可以！我将为您生成一份包含近三个月销售趋势的分析报告。\n\n以下是您需要的销售数据趋势图：\n```mermaid\ngantt\ntitle 近三个月销售趋势\ndateFormat  YYYY-MM-DD\nsection 销售额\n九月: 2025-09-01, 2025-09-30\n十月: 2025-10-01, 2025-10-31\n十一月: 2025-11-01, 2025-11-30\nsection 订单量\n九月: 2025-09-01, 2025-09-30\n十月: 2025-10-01, 2025-10-31\n十一月: 2025-11-01, 2025-11-30\n```\n\n从图表可以看出，近三个月的销售额和订单量呈现稳步增长趋势，11月份增长最为明显。',
          timestamp: '2025-12-01 10:17',
          containsMermaid: true
        },
        {
          id: '1-3',
          sender: 'user' as const,
          content: '谢谢！请再帮我分析一下各地区的销售占比情况。',
          timestamp: '2025-12-01 10:20'
        },
        {
          id: '1-4',
          sender: 'ai' as const,
          content: '根据数据分析，各地区销售占比如下：\n```mermaid\npie\ntitle 各地区销售占比\n"华东地区" : 38\n"华北地区" : 25\n"华南地区" : 18\n"西部地区" : 12\n"东北地区" : 7\n```\n\n华东地区是我们的主要市场，占比接近40%。建议继续加强该地区的市场推广，同时也可以考虑在西部地区增加投入以提升市场份额。',
          timestamp: '2025-12-01 10:22',
          containsMermaid: true
        }
      ]
    },
    {
       id: 2,
       title: t('sidebar.favorite2'),
      status: 'in-progress' as const,
      dueDate: '2025-12-03',
      messages: [
        {
          id: '2-1',
          sender: 'user' as const,
          content: '我需要为下周的周会准备演示材料，主要内容是项目进度和团队工作分配。',
          timestamp: '2025-12-02 14:30'
        },
        {
          id: '2-2',
          sender: 'ai' as const,
          content: '好的，我可以帮您准备周会演示材料。以下是项目进度流程图：\n```mermaid\ngraph LR\nA[需求分析] --> B[设计阶段]\nB --> C[开发阶段]\nC --> D[测试阶段]\nD --> E[部署上线]\nE --> F[运维监控]\n\nsubgraph 目前进度\nC\nend\n```\n\n以及团队工作分配图：\n```mermaid\nflowchart TD\n    subgraph 团队成员\n        PM[项目经理]\n        Dev1[开发工程师1]\n        Dev2[开发工程师2]\n        QA[测试工程师]\n        Designer[设计师]\n    end\n    \n    subgraph 任务分配\n        Task1[需求文档完善]\n        Task2[数据库设计]\n        Task3[前端开发]\n        Task4[后端开发]\n        Task5[UI设计]\n        Task6[测试计划]\n    end\n    \n    PM --> Task1\n    Dev1 --> Task2\n    Dev1 --> Task4\n    Dev2 --> Task3\n    Designer --> Task5\n    QA --> Task6\n```\n\n这些图表可以帮助您直观地展示项目进度和团队工作分配情况。',
          timestamp: '2025-12-02 14:33',
          containsMermaid: true
        }
      ]
    },
    {
       id: 3,
       title: t('sidebar.favorite3'),
      status: 'pending' as const,
      dueDate: '2025-12-05',
      messages: [
        {
          id: '3-1',
          sender: 'user' as const,
          content: '我们的客服响应时间太长，需要优化流程。你能帮我分析一下当前流程并提出改进建议吗？',
          timestamp: '2025-12-02 16:45'
        },
        {
          id: '3-2',
          sender: 'ai' as const,
          content: '让我为您分析当前客服响应流程并提出优化建议。\n\n当前客服流程：\n```mermaid\ngraph TD\nA[用户提交请求] --> B[等待客服接收]\nB --> C[客服初步评估]\nC --> D[分配给相应专员]\nD --> E[专员处理]\nE --> F[用户反馈]\nF --> G[流程结束]\n```\n\n优化建议：\n```mermaid\ngraph TD\nA[用户提交请求] --> B{智能分类}\nB -->|常见问题| C[自动回复]\nB -->|复杂问题| D[优先分配]\nC --> E[用户确认]\nD --> F[专员快速处理]\nE -->|解决| G[流程结束]\nE -->|未解决| D\nF --> G\n```\n\n优化后的流程引入了智能分类系统，可以自动处理常见问题，同时对复杂问题进行优先分配，预计可以将平均响应时间缩短60%以上。',
          timestamp: '2025-12-02 16:48',
          containsMermaid: true
        }
      ]
    },
    {
       id: 4,
       title: t('sidebar.assistant3'),
      status: 'pending' as const,
      dueDate: '2025-12-10',
      messages: [
        {
          id: '4-1',
          sender: 'user' as const,
          content: '我们需要更新产品文档，特别是新功能的使用指南部分。',
          timestamp: '2025-12-02 09:10'
        },
        {
          id: '4-2',
          sender: 'ai' as const,
          content: '好的，产品文档更新是非常重要的。我建议按照以下结构组织新功能的使用指南：\n```mermaid\ngraph TD\nA[产品文档] --> B[概述]\nB --> C[快速开始]\nC --> D[功能介绍]\nD --> E[使用教程]\nE --> F[常见问题]\n\nsubgraph 新功能部分\nG[功能A]\nH[功能B]\nI[功能C]\nend\n\nD --> G\nD --> H\nD --> I\n```\n\n每个新功能应该包含：功能说明、配置方法、使用步骤、示例场景和注意事项等内容。这样可以帮助用户快速理解和使用新功能。',
          timestamp: '2025-12-02 09:12',
          containsMermaid: true
        }
      ]
    },
  ], [language, updateCounter]);

  // 使用 useMemo 缓存所有直接使用的翻译文本，确保语言变更时正确更新
  const translations = useMemo(() => {
    return {
      favorites: t('sidebar.favorites'),
      tasks: t('sidebar.tasks'),
      addTask: t('sidebar.addTask'),
      browse: t('sidebar.browse'),
      browseAssistants: t('sidebar.browseAssistants'),
      browseAgents: t('sidebar.browseAgents'),
      toggleExpand: t('sidebar.toggle.expand'),
      toggleCollapse: t('sidebar.toggle.collapse'),
      user: t('sidebar.user'),
      userEmail: t('sidebar.user.email'),
      inputPlaceholder: t('sidebar.input.placeholder'),
      buttonAdd: t('sidebar.button.add'),
      buttonCancel: t('sidebar.button.cancel'),
    };
  }, [language, updateCounter]);



  // 获取任务状态对应的图标和颜色
  const getTaskStatusInfo = (status: Task['status']) => {
    switch (status) {
      case 'pending':
        return { icon: 'fa-clock', color: 'text-yellow-500' };
      case 'in-progress':
        return { icon: 'fa-spinner', color: 'text-blue-500' };
      case 'completed':
        return { icon: 'fa-check', color: 'text-green-500' };
      default:
        return { icon: 'fa-question', color: 'text-gray-500' };
    }
  };

  // 添加新任务
  const handleAddTask = () => {
    if (newTaskTitle.trim()) {
      // 这里可以添加实际添加任务的逻辑
      console.log('添加新任务:', newTaskTitle);
      setNewTaskTitle('');
      setShowAddTask(false);
    }
  };

  // 处理任务点击
  const handleTaskClick = (task: Task) => {
    setActiveSection('tasks');
    setActiveItemId(task.id); // 设置选中的任务 ID
    if (onTaskSelect) {
      onTaskSelect(task);
    }
  };

  // 处理收藏项点击
  const handleFavoriteClick = (favorite: FavoriteItem) => {
    setActiveSection('favorites');
    setActiveItemId(favorite.id);

    switch (favorite.type) {
      case 'task':
        // 查找对应的任务
        const task = tasks.find(t => t.id.toString() === favorite.itemId);
        if (task) {
          handleTaskClick(task);
        }
        break;
      case 'assistant':
        // 调用助理选择回调
        if (onAssistantSelect) {
          onAssistantSelect(favorite.itemId);
        }
        break;
      case 'agent':
        // 调用代理选择回调
        if (onAgentSelect) {
          onAgentSelect(favorite.itemId);
        }
        break;
    }
  };

  // 切换区域展开/收合状态
  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  return (
    <div className={cn(
      "h-full bg-secondary border-r border-primary flex flex-col transition-all duration-300 theme-transition",
      collapsed ? "w-16" : "w-64"
    )}>
      {/* 侧边栏头部 */}
      <div className="p-4 border-b border-primary flex items-center justify-between">
        {!collapsed && (
          <div className="flex items-center bg-transparent">
            <img
              src={
                browseMode === 'assistants'
                  ? "/SmartQ-LAS.svg"
                  : browseMode === 'agents'
                  ? "/SmartQ.-HCI.svg"
                  : "/SmartQ-IEE.svg" // 默认显示 SmartQ-IEE（一般情况）
              }
              alt={
                browseMode === 'assistants'
                  ? "SmartQ-LAS Logo"
                  : browseMode === 'agents'
                  ? "SmartQ-HCI Logo"
                  : "SmartQ-IEE Logo"
              }
              className="h-8 transition-opacity duration-300"
              style={{
                backgroundColor: 'transparent',
                mixBlendMode: 'normal',
                display: 'block'
              }}
            />
          </div>
        )}
        <button
          onClick={onToggle}
          className="p-2 rounded-full hover:bg-tertiary transition-colors"
          aria-label={collapsed ? translations.toggleExpand : translations.toggleCollapse}
          title={collapsed ? translations.toggleExpand : translations.toggleCollapse}
        >
          <i className={`fa-solid ${collapsed ? 'fa-chevron-right' : 'fa-chevron-left'}`}></i>
        </button>
      </div>

      {/* 侧边栏内容 */}
      <div className="flex-1 overflow-y-auto p-2">
        {/* 收藏夹 */}
        <div className="mb-4" key={`favorites-section-${language}-${updateCounter}`}>
          <div className="flex items-center mb-2">
           {!collapsed && (
             <span key={`favorites-label-${language}-${updateCounter}`} className="text-sm font-medium text-yellow-400/80">
               {translations.favorites}
             </span>
           )}
            <i className="fa-solid fa-bookmark ml-2 text-yellow-500"></i>
          </div>
           {favorites.map(item => {
              // 根据类型确定图标和颜色
              const getIcon = () => {
                if (item.icon) {
                  return `fa-solid ${item.icon}`;
                }
                switch (item.type) {
                  case 'task':
                    return 'fa-solid fa-tasks';
                  case 'assistant':
                    return 'fa-solid fa-robot';
                  case 'agent':
                    return 'fa-solid fa-user-tie';
                  default:
                    return 'fa-solid fa-star';
                }
              };

              const getColorClass = () => {
                switch (item.type) {
                  case 'task':
                    return 'text-orange-400';
                  case 'assistant':
                    return 'text-purple-400';
                  case 'agent':
                    return 'text-green-400';
                  default:
                    return 'text-yellow-400';
                }
              };

              return (
              <button
                key={item.id}
                className={`w-full text-left p-2 rounded-lg flex items-center transition-all duration-200 mb-1
                  ${activeSection === 'favorites' && activeItemId === item.id
                    ? 'bg-yellow-500/20 text-yellow-400 border-l-2 border-yellow-500 shadow-sm'
                    : 'hover:bg-yellow-500/10 hover:text-yellow-300 hover:border-l-2 hover:border-yellow-500/50'}`}
                  onClick={() => handleFavoriteClick(item)}
              >
                {!collapsed ? (
                    <>
                      <i className={`${getIcon()} mr-2 ${getColorClass()}`}></i>
                  <span className="text-sm">{item.name}</span>
                    </>
                ) : (
                    <i className={`${getIcon()} ${getColorClass()}`}></i>
                )}
              </button>
              );
            })}

            {/* 浏览区域 */}
            {!collapsed && (
              <div className="mt-3 pt-3 border-t border-primary/30">
                <div className="text-xs text-tertiary mb-2 px-2">{t('sidebar.browse')}</div>
                <button
                  className="w-full text-left p-2 rounded-lg flex items-center transition-all duration-200 mb-1 hover:bg-yellow-500/10 hover:text-yellow-300 hover:border-l-2 hover:border-yellow-500/50 hover:shadow-lg hover:shadow-yellow-500/20"
                  onClick={() => {
                    if (onBrowseAssistants) {
                      onBrowseAssistants();
                    }
                  }}
                >
                  <i className="fa-solid fa-robot mr-2 text-purple-400"></i>
                  <span className="text-sm">{t('sidebar.browseAssistants')}</span>
                </button>
                <button
                  className="w-full text-left p-2 rounded-lg flex items-center transition-all duration-200 mb-1 hover:bg-yellow-500/10 hover:text-yellow-300 hover:border-l-2 hover:border-yellow-500/50 hover:shadow-lg hover:shadow-yellow-500/20"
                  onClick={() => {
                    if (onBrowseAgents) {
                      onBrowseAgents();
                    }
                  }}
                >
                  <i className="fa-solid fa-user-tie mr-2 text-green-400"></i>
                  <span className="text-sm">{t('sidebar.browseAgents')}</span>
                </button>
              </div>
            )}
        </div>

        {/* 任务区块 - 可收合 */}
        <div className="mb-4" key={`tasks-section-${language}-${updateCounter}`}>
          <button
            className="w-full flex items-center justify-between mb-2 p-2 rounded-lg hover:bg-orange-500/10 hover:text-orange-300 transition-all duration-200"
            onClick={() => {
              toggleSection('tasks');
              setActiveSection('tasks'); // 点击任务区域标题时，设置 activeSection 为 'tasks'
            }}
          >
             <div className="flex items-center">
               {!collapsed && <span key={`tasks-label-${language}-${updateCounter}`} className="text-sm font-medium text-orange-400/80">{translations.tasks}</span>}
               <i className="fa-solid fa-tasks ml-2 text-orange-500"></i>
             </div>
            {!collapsed && (
              <i className={`fa-solid fa-chevron-down transition-transform ${expandedSections.tasks ? 'rotate-0' : 'rotate-180'}`}></i>
            )}
          </button>

          {/* 任务区域内容 */}
          {expandedSections.tasks && (
            <>
              {/* 新增任务按钮 */}
              {!collapsed && (
                <button
                  className="w-full text-left p-2 rounded-lg flex items-center justify-between hover:bg-orange-500/10 hover:text-orange-300 transition-all duration-200 mb-2"
                  onClick={() => setShowAddTask(!showAddTask)}
                >
                   <div className="flex items-center">
                     <i className="fa-solid fa-plus-circle mr-2 text-orange-500"></i>
                     <span className="text-sm">{translations.addTask}</span>
                   </div>
                  <i className={`fa-solid fa-chevron-down transition-transform ${showAddTask ? 'rotate-180' : ''}`}></i>
                </button>
              )}

              {/* 新增任务输入框 */}
              {!collapsed && showAddTask && (
                <div className="bg-tertiary rounded-lg p-2 mb-2">
                     <input
                    type="text"
                    placeholder={translations.inputPlaceholder}
                    value={newTaskTitle}
                    onChange={(e) => setNewTaskTitle(e.target.value)}
                    className="w-full bg-secondary border border-primary rounded p-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') handleAddTask();
                    }}
                    autoFocus
                  />
                  <div className="flex justify-end mt-1.5">
                    <button
                      className="px-2 py-1 text-xs bg-green-600 hover:bg-green-700 rounded mr-1"
                       onClick={handleAddTask}
                    >
                      {translations.buttonAdd}
                    </button>
                    <button
                      className="px-2 py-1 text-xs bg-tertiary hover:bg-hover rounded"
                      onClick={() => {
                        setNewTaskTitle('');
                        setShowAddTask(false);
                       }}
                    >
                      {translations.buttonCancel}
                    </button>
                  </div>
                </div>
              )}

              {/* 历史任务列表 */}
              {tasks.map(task => {
                const statusInfo = getTaskStatusInfo(task.status);
                return (
                  <button
                    key={task.id}
                    className={`w-full text-left p-2 rounded-lg flex items-center transition-all duration-200 mb-1 cursor-pointer
                      ${activeSection === 'tasks' && activeItemId === task.id
                        ? 'bg-orange-500/20 text-orange-300 border-l-2 border-orange-500 shadow-sm'
                        : 'hover:bg-orange-500/10 hover:text-orange-300 hover:border-l-2 hover:border-orange-500/50'}`}
                    onClick={() => handleTaskClick(task)}
                  >
                    {!collapsed ? (
                      <>
                        <i className={`fa-solid ${statusInfo.icon} mr-2 ${statusInfo.color}`}></i>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm truncate">{task.title}</div>
                          <div className="text-xs text-tertiary">{task.dueDate}</div>
                        </div>
                      </>
                    ) : (
                      <i className={`fa-solid ${statusInfo.icon} ${statusInfo.color}`}></i>
                    )}
                  </button>
                );
              })}
            </>
          )}
        </div>

      </div>

      {/* 侧边栏底部 */}
      <div className="p-4 border-t border-primary" key={`sidebar-footer-${language}-${updateCounter}`}>
        <div className="flex items-center">
           {!collapsed && <div key={`user-info-${language}-${updateCounter}`}>
               <div className="text-sm font-medium">{translations.user}</div>
               <div className="text-xs text-tertiary">{translations.userEmail}</div>
            </div>}
          <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center ml-auto">
            <i className="fa-solid fa-user"></i>
          </div>
        </div>
      </div>
    </div>
  );
}
