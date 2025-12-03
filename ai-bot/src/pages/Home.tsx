import { useState, useEffect, useMemo } from 'react';
import { useLanguage } from '../contexts/languageContext';
import Sidebar from '../components/Sidebar';
import ChatArea from '../components/ChatArea';
import ResultPanel from '../components/ResultPanel';
import ExecutorSelectorModal from '../components/ExecutorSelectorModal';
import { Task, FavoriteItem } from '../components/Sidebar';

export default function Home() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [resultPanelCollapsed, setResultPanelCollapsed] = useState(false);
  const [isMarkdownView, setIsMarkdownView] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | undefined>(undefined);
  const { t, updateCounter, language } = useLanguage();

  // 执行者选择相关状态
  const [showExecutorModal, setShowExecutorModal] = useState(false);
  const [executorModalType, setExecutorModalType] = useState<'assistant' | 'agent'>('assistant');
  const [selectedExecutorId, setSelectedExecutorId] = useState<string>('');
  const [selectedExecutorName, setSelectedExecutorName] = useState<string>('');

  // 浏览模式状态
  const [browseMode, setBrowseMode] = useState<'assistants' | 'agents' | null>(null);

  // 收藏状态管理 - 使用 Map 存储 ID 和名称的映射
  const [favoriteAssistants, setFavoriteAssistants] = useState<Map<string, string>>(() => {
    // 从 localStorage 加载收藏的助理
    const saved = localStorage.getItem('favoriteAssistants');
    if (saved) {
      try {
        const data = JSON.parse(saved);
        // 兼容旧格式（数组）
        if (Array.isArray(data)) {
          return new Map<string, string>();
        }
        // 新格式（对象）
        return new Map(Object.entries(data));
      } catch {
        return new Map();
      }
    }
    return new Map();
  });

  // 更新收藏助理的名称（当语言切换或组件加载时）
  useEffect(() => {
    setFavoriteAssistants(prev => {
      const updated = new Map(prev);
      // 为所有收藏的助理更新名称
      prev.forEach((oldName, id) => {
        const newName = getAssistantName(id);
        if (newName !== id) { // 如果找到了名称，更新它
          updated.set(id, newName);
        }
      });
      return updated;
    });
  }, [language, updateCounter, t]);

  // 保存收藏状态到 localStorage
  useEffect(() => {
    const data = Object.fromEntries(favoriteAssistants);
    localStorage.setItem('favoriteAssistants', JSON.stringify(data));
  }, [favoriteAssistants]);

  // 设置页面标题 - 使用language和updateCounter确保语言变更时更新
  useEffect(() => {
    document.title = t('app.title');
  }, [language, updateCounter, t]);

  // 模拟助理和代理数据（实际应该从 API 或 context 获取）
  // 获取助理名称 - 需要匹配 ChatArea 中的助理 ID
  const getAssistantName = (id: string): string => {
    const assistants: Record<string, string> = {
      // HR 类别
      'assist-hr-1': t('sidebar.assistant1'),
      'assist-hr-2': t('sidebar.assistant2'),
      'assist-hr-3': t('sidebar.assistant3'),
      // Logistics 类别
      'assist-log-1': t('sidebar.assistant1'),
      'assist-log-2': t('sidebar.assistant2'),
      'assist-log-3': t('sidebar.assistant3'),
      // Finance 类别
      'assist-fin-1': t('sidebar.assistant1'),
      'assist-fin-2': t('sidebar.assistant2'),
      'assist-fin-3': t('sidebar.assistant3'),
      // MES 类别
      'assist-mes-1': t('sidebar.assistant1'),
      'assist-mes-2': t('sidebar.assistant2'),
      'assist-mes-3': t('sidebar.assistant3'),
      // 兼容旧 ID
      'assist-1': t('sidebar.assistant1'),
      'assist-2': t('sidebar.assistant2'),
      'assist-3': t('sidebar.assistant3'),
    };
    return assistants[id] || id;
  };

  const getAgentName = (id: string): string => {
    const agents: Record<string, string> = {
      'agent-1': t('sidebar.agent1'),
      'agent-2': t('sidebar.agent2'),
      'agent-3': t('sidebar.agent3'),
      'agent-4': t('sidebar.agent4'),
    };
    return agents[id] || id;
  };

  // 处理任务选择
  const handleTaskSelect = (task: Task) => {
    setSelectedTask(task);
    setBrowseMode(null); // 清除浏览模式
    // 如果正在预览Markdown，切换回聊天视图
    if (isMarkdownView) {
      setIsMarkdownView(false);
    }
  };

  // 处理浏览助理
  const handleBrowseAssistants = () => {
    setSelectedTask(undefined);
    setBrowseMode('assistants');
    if (isMarkdownView) {
      setIsMarkdownView(false);
    }
  };

  // 处理浏览代理
  const handleBrowseAgents = () => {
    setSelectedTask(undefined);
    setBrowseMode('agents');
    if (isMarkdownView) {
      setIsMarkdownView(false);
    }
  };

  // 处理助理选择
  const handleAssistantSelect = (assistantId: string) => {
    setExecutorModalType('assistant');
    setSelectedExecutorId(assistantId);
    setSelectedExecutorName(getAssistantName(assistantId));
    setShowExecutorModal(true);
  };

  // 处理代理选择
  const handleAgentSelect = (agentId: string) => {
    setExecutorModalType('agent');
    setSelectedExecutorId(agentId);
    setSelectedExecutorName(getAgentName(agentId));
    setShowExecutorModal(true);
  };

  // 创建新任务并绑定执行者
  const handleCreateTaskWithExecutor = () => {
    const newTask: Task = {
      id: Date.now(), // 临时 ID，实际应该由后端生成
      title: selectedExecutorName,
      status: 'in-progress',
      dueDate: new Date().toISOString().split('T')[0],
      messages: [],
      executionConfig: {
        mode: executorModalType === 'assistant' ? 'assistant' : 'agent',
        ...(executorModalType === 'assistant'
          ? { assistantId: selectedExecutorId }
          : { agentId: selectedExecutorId }
        ),
      },
    };

    setSelectedTask(newTask);
    setShowExecutorModal(false);
    if (isMarkdownView) {
      setIsMarkdownView(false);
    }
  };

  // 将执行者应用到当前任务
  const handleApplyExecutorToCurrentTask = () => {
    if (selectedTask) {
      const updatedTask: Task = {
        ...selectedTask,
        executionConfig: {
          mode: executorModalType === 'assistant' ? 'assistant' : 'agent',
          ...(executorModalType === 'assistant'
            ? { assistantId: selectedExecutorId }
            : { agentId: selectedExecutorId }
          ),
        },
      };
      setSelectedTask(updatedTask);
    }
    setShowExecutorModal(false);
  };

  // 处理助理收藏
  const handleAssistantFavorite = (assistantId: string, isFavorite: boolean, assistantName?: string) => {
    setFavoriteAssistants(prev => {
      const newMap = new Map(prev);
      if (isFavorite) {
        // 保存时使用传入的名称，如果没有则使用 getAssistantName 获取
        newMap.set(assistantId, assistantName || getAssistantName(assistantId));
      } else {
        newMap.delete(assistantId);
      }
      return newMap;
    });
  };

  // 生成收藏列表（包含收藏的助理）- 使用 useMemo 确保语言切换时更新
  const favorites: FavoriteItem[] = useMemo(() => [
    // 保留原有的任务收藏
    { id: 'fav-1', name: t('sidebar.favorite1'), type: 'task' as const, itemId: '1', icon: 'fa-tasks' },
    { id: 'fav-2', name: t('sidebar.favorite2'), type: 'task' as const, itemId: '2', icon: 'fa-tasks' },
    { id: 'fav-3', name: t('sidebar.favorite3'), type: 'task' as const, itemId: '3', icon: 'fa-tasks' },
    // 添加收藏的助理 - 使用保存的名称，如果名称不存在则尝试获取
    ...Array.from(favoriteAssistants.entries()).map(([assistantId, assistantName]) => ({
      id: `fav-assistant-${assistantId}`,
      name: assistantName || getAssistantName(assistantId),
      type: 'assistant' as const,
      itemId: assistantId,
      icon: 'fa-robot'
    }))
  ], [favoriteAssistants, language, updateCounter, t]);

  return (
    <div className="flex h-screen bg-primary text-primary overflow-hidden theme-transition">
      {/* 左侧边栏 - 当右侧显示Markdown预览时自动收合 */}
      <Sidebar
        collapsed={isMarkdownView || sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        onTaskSelect={handleTaskSelect}
        onAgentSelect={handleAgentSelect}
        onAssistantSelect={handleAssistantSelect}
        onBrowseAssistants={handleBrowseAssistants}
        onBrowseAgents={handleBrowseAgents}
        selectedTask={selectedTask}
        browseMode={browseMode}
        favorites={favorites}
      />

      {/* 中间聊天区域 - 根据右侧是否显示Markdown预览调整宽度 */}
      <div className={`${isMarkdownView ? 'w-1/3' : 'flex-1'} flex flex-col overflow-hidden transition-all duration-300`}>
        <ChatArea
          selectedTask={selectedTask}
          browseMode={browseMode}
          onAssistantSelect={handleAssistantSelect}
          onAgentSelect={handleAgentSelect}
          resultPanelCollapsed={resultPanelCollapsed}
          onResultPanelToggle={() => setResultPanelCollapsed(!resultPanelCollapsed)}
          onAssistantFavorite={handleAssistantFavorite}
          favoriteAssistants={favoriteAssistants}
        />
      </div>

      {/* 右侧结果面板 - 预览文件时完全展开，收合时完全隐藏 */}
      {!resultPanelCollapsed && (
        <div className={`transition-all duration-300 ${isMarkdownView ? 'w-2/3' : 'w-80'}`}>
          <ResultPanel
            collapsed={false}
            onViewChange={(isViewing) => {
              setIsMarkdownView(isViewing);
              // 当进入Markdown预览时，清除选中的任务
              if (isViewing) {
                setSelectedTask(undefined);
              }
            }}
          />
        </div>
      )}

      {/* 执行者选择模态框 */}
      <ExecutorSelectorModal
        isOpen={showExecutorModal}
        type={executorModalType}
        executorId={selectedExecutorId}
        executorName={selectedExecutorName}
        hasCurrentTask={!!selectedTask}
        onClose={() => setShowExecutorModal(false)}
        onCreateTask={handleCreateTaskWithExecutor}
        onApplyToCurrent={handleApplyExecutorToCurrentTask}
      />
    </div>
  );
}
