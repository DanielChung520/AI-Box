import { useState, useEffect, useMemo, useRef } from 'react';
import { useLanguage } from '../contexts/languageContext';
import Sidebar from '../components/Sidebar';
import ChatArea from '../components/ChatArea';
import ResultPanel from '../components/ResultPanel';
import ExecutorSelectorModal from '../components/ExecutorSelectorModal';
import { Task, FavoriteItem, FileNode } from '../components/Sidebar';
import { saveTask, deleteTask, getTask } from '../lib/taskStorage';
import '../lib/debugStorage'; // 加載調試工具
import '../lib/checkFiles'; // 加載文件檢查工具

export default function Home() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [resultPanelCollapsed, setResultPanelCollapsed] = useState(false);
  const [isMarkdownView, setIsMarkdownView] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | undefined>(undefined);
  const prevResultPanelCollapsedRef = useRef<boolean>(false);
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

  // 代理收藏状态管理 - 使用 Map 存储 ID 和名称的映射
  const [favoriteAgents, setFavoriteAgents] = useState<Map<string, string>>(() => {
    // 从 localStorage 加载收藏的代理
    const saved = localStorage.getItem('favoriteAgents');
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

  // 更新收藏代理的名称（当语言切换或组件加载时）
  useEffect(() => {
    setFavoriteAgents(prev => {
      const updated = new Map(prev);
      // 为所有收藏的代理更新名称
      prev.forEach((oldName, id) => {
        const newName = getAgentName(id);
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
    // 触发自定义事件，通知其他组件更新
    window.dispatchEvent(new CustomEvent('favoritesUpdated', {
      detail: { type: 'favoriteAssistants' }
    }));
  }, [favoriteAssistants]);

  // 保存代理收藏状态到 localStorage
  useEffect(() => {
    const data = Object.fromEntries(favoriteAgents);
    localStorage.setItem('favoriteAgents', JSON.stringify(data));
    // 触发自定义事件，通知其他组件更新
    window.dispatchEvent(new CustomEvent('favoritesUpdated', {
      detail: { type: 'favoriteAgents' }
    }));
  }, [favoriteAgents]);

  // 设置页面标题 - 使用language和updateCounter确保语言变更时更新
  useEffect(() => {
    document.title = t('app.title');
  }, [language, updateCounter, t]);

  // 追蹤 resultPanelCollapsed 的變化
  useEffect(() => {
    prevResultPanelCollapsedRef.current = resultPanelCollapsed;
  }, [resultPanelCollapsed]);

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
    // HR 类别
    if (id === 'hr-1') {
      return t('agent.category.humanResource') + t('agent.hr.assistant');
    }
    if (id === 'hr-2') {
      return t('agent.hr.trainingManager');
    }
    if (id === 'hr-3') {
      return t('agent.hr.performanceAnalysis');
    }
    if (id === 'hr-4') {
      return t('agent.hr.employeeRelations');
    }
    if (id === 'hr-5') {
      return t('agent.hr.compensationBenefits');
    }
    if (id === 'hr-6') {
      return t('agent.hr.talentDevelopment');
    }

    // Logistics 类别
    if (id === 'log-1') {
      return t('agent.logistics.supplyChainOptimization');
    }
    if (id === 'log-2') {
      return t('agent.logistics.inventoryManagement');
    }
    if (id === 'log-3') {
      return t('agent.logistics.routePlanning');
    }
    if (id === 'log-4') {
      return t('agent.logistics.dataAnalysis');
    }
    if (id === 'log-5') {
      return t('agent.logistics.supplierManagement');
    }

    // Finance 类别
    if (id === 'fin-1') {
      return t('agent.finance.financialAnalyst');
    }
    if (id === 'fin-2') {
      return t('agent.finance.budgetPlanning');
    }
    if (id === 'fin-3') {
      return t('agent.finance.costControl');
    }
    if (id === 'fin-4') {
      return t('agent.finance.financialReportGeneration');
    }
    if (id === 'fin-5') {
      return t('agent.finance.taxPlanning');
    }
    if (id === 'fin-6') {
      return t('agent.finance.investmentAnalysis');
    }

    // MES 类别
    if (id === 'mes-1') {
      return t('agent.mes.productionMonitoring');
    }
    if (id === 'mes-2') {
      return t('agent.mes.qualityControl');
    }
    if (id === 'mes-3') {
      return t('agent.mes.efficiencyAnalysis');
    }
    if (id === 'mes-4') {
      return t('agent.mes.equipmentMaintenance');
    }
    if (id === 'mes-5') {
      return t('agent.mes.productionScheduling');
    }
    if (id === 'mes-6') {
      return t('agent.mes.materialManagement');
    }
    if (id === 'mes-7') {
      return t('agent.mes.processOptimization');
    }

    // 兼容旧 ID
    const legacyAgents: Record<string, string> = {
      'agent-1': t('sidebar.agent1'),
      'agent-2': t('sidebar.agent2'),
      'agent-3': t('sidebar.agent3'),
      'agent-4': t('sidebar.agent4'),
    };

    return legacyAgents[id] || id;
  };

  // 处理任务选择
  const handleTaskSelect = (task: Task) => {
    // 從 localStorage 重新加載任務數據，確保文件樹是最新的
    const savedTask = getTask(task.id);
    const taskToSelect = savedTask || task;

    setSelectedTask(taskToSelect);
    setBrowseMode(null); // 清除浏览模式
    // 如果正在预览Markdown，切换回聊天视图
    if (isMarkdownView) {
      setIsMarkdownView(false);
    }
    // 任務的文件目錄會自動從 task.fileTree 恢復
  };

  // 處理任務創建（用於文件上傳時創建新任務）
  const handleTaskCreate = (task: Task) => {
    setSelectedTask(task);
    // 保存任務到 localStorage
    saveTask(task);
    // 觸發事件通知 Sidebar 更新焦點
    window.dispatchEvent(new CustomEvent('taskCreated', {
      detail: { taskId: task.id }
    }));
  };

  // 處理任務刪除（用於文件上傳失敗時清除任務）
  const handleTaskDelete = (taskId: number) => {
    if (selectedTask && selectedTask.id === taskId) {
      setSelectedTask(undefined);
      // 從 localStorage 刪除任務
      deleteTask(taskId);
      // 觸發事件通知 Sidebar 清除焦點
      window.dispatchEvent(new CustomEvent('taskDeleted', {
        detail: { taskId: taskId }
      }));
    }
  };

  // 處理文件樹變化
  const handleFileTreeChange = (fileTree: FileNode[]) => {
    if (selectedTask) {
      // 更新當前任務的文件樹
      setSelectedTask({
        ...selectedTask,
        fileTree: fileTree,
      });
    }
  };

  // 監聽文件上傳事件（包括模擬和真實上傳）
  useEffect(() => {
    const handleFilesUploaded = (event: CustomEvent) => {
      const { taskId, files } = event.detail;


      // 使用函數式更新，確保獲取最新的 selectedTask
      setSelectedTask((currentTask) => {
        if (!currentTask) {
          return currentTask;
        }

        // 檢查任務ID是否匹配（支持字符串和數字比較）
        const taskIdMatch = String(currentTask.id) === String(taskId);

        if (taskIdMatch) {
          // 將文件轉換為 FileNode 格式
          const newFileNodes: FileNode[] = files.map((file: any) => ({
            id: file.file_id,
            name: file.filename,
            type: 'file' as const,
          }));

          // 更新任務的文件樹
          const updatedFileTree = currentTask.fileTree ? [...currentTask.fileTree, ...newFileNodes] : newFileNodes;
          const updatedTask = {
            ...currentTask,
            fileTree: updatedFileTree,
          };

          // 同時更新 localStorage 中的任務數據
          saveTask(updatedTask);

          return updatedTask;
        } else {
          return currentTask;
        }
      });
    };

    const handleMockFilesUploaded = (event: CustomEvent) => {
      const { taskId, files } = event.detail;


      // 使用函數式更新，確保獲取最新的 selectedTask
      setSelectedTask((currentTask) => {
        if (!currentTask) {
          return currentTask;
        }

        // 檢查任務ID是否匹配（支持字符串和數字比較）
        const taskIdMatch = String(currentTask.id) === String(taskId);

        if (taskIdMatch) {
          // 將模擬文件轉換為 FileNode 格式
          const newFileNodes: FileNode[] = files.map((file: any) => ({
            id: file.file_id,
            name: file.filename,
            type: 'file' as const,
          }));

          // 更新任務的文件樹
          const updatedFileTree = currentTask.fileTree ? [...currentTask.fileTree, ...newFileNodes] : newFileNodes;
          const updatedTask = {
            ...currentTask,
            fileTree: updatedFileTree,
          };

          // 同時更新 localStorage 中的任務數據
          saveTask(updatedTask);

          return updatedTask;
        } else {
          return currentTask;
        }
      });
    };

    window.addEventListener('filesUploaded', handleFilesUploaded as EventListener);
    window.addEventListener('mockFilesUploaded', handleMockFilesUploaded as EventListener);

    return () => {
      window.removeEventListener('filesUploaded', handleFilesUploaded as EventListener);
      window.removeEventListener('mockFilesUploaded', handleMockFilesUploaded as EventListener);
    };
  }, []); // 移除 selectedTask 依賴，使用函數式更新

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
    // 如果已经有选中的任务，直接更新任务的执行配置，不打开模态框
    if (selectedTask) {
      setSelectedTask({
        ...selectedTask,
        executionConfig: {
          ...selectedTask.executionConfig,
          mode: 'assistant',
          assistantId: assistantId,
          agentId: undefined, // 清除代理ID
        }
      });
      // 清除浏览模式（如果正在浏览）
      if (browseMode) {
        setBrowseMode(null);
      }
      return;
    }

    // 如果没有选中的任务，直接创建新任务并设置助理（不打开模态框）
    const newTask: Task = {
      id: Date.now(), // 临时 ID，实际应该由后端生成
      title: getAssistantName(assistantId), // 使用助理名称作为初始标题
      status: 'in-progress',
      dueDate: new Date().toISOString().split('T')[0],
      messages: [],
      executionConfig: {
        mode: 'assistant',
        assistantId: assistantId,
      },
      fileTree: [], // 新增任務時清空文件目錄
    };

    setSelectedTask(newTask);
    // 清除浏览模式（从浏览模式创建任务时）
    setBrowseMode(null);

    // 如果正在预览Markdown，切换回聊天视图
    if (isMarkdownView) {
      setIsMarkdownView(false);
    }
  };

  // 处理代理选择
  const handleAgentSelect = (agentId: string) => {
    // 如果已经有选中的任务，直接更新任务的执行配置，不打开模态框
    if (selectedTask) {
      setSelectedTask({
        ...selectedTask,
        executionConfig: {
          ...selectedTask.executionConfig,
          mode: 'agent',
          agentId: agentId,
          assistantId: undefined, // 清除助理ID
        }
      });
      // 清除浏览模式（如果正在浏览）
      if (browseMode) {
        setBrowseMode(null);
      }
      return;
    }

    // 如果没有选中的任务，直接创建新任务并设置代理（不打开模态框）
    const newTask: Task = {
      id: Date.now(), // 临时 ID，实际应该由后端生成
      title: getAgentName(agentId), // 使用代理名称作为初始标题
      status: 'in-progress',
      dueDate: new Date().toISOString().split('T')[0],
      messages: [],
      executionConfig: {
        mode: 'agent',
        agentId: agentId,
      },
      fileTree: [], // 新增任務時清空文件目錄
    };

    setSelectedTask(newTask);
    // 清除浏览模式（从浏览模式创建任务时）
    setBrowseMode(null);

    // 如果正在预览Markdown，切换回聊天视图
    if (isMarkdownView) {
      setIsMarkdownView(false);
    }
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

  // 处理代理收藏
  const handleAgentFavorite = (agentId: string, isFavorite: boolean, agentName?: string) => {
    setFavoriteAgents(prev => {
      const newMap = new Map(prev);
      if (isFavorite) {
        // 保存时使用传入的名称，如果没有则使用 getAgentName 获取
        newMap.set(agentId, agentName || getAgentName(agentId));
      } else {
        newMap.delete(agentId);
      }
      return newMap;
    });
  };

  // 生成收藏列表（包含收藏的助理和代理）- 使用 useMemo 确保语言切换时更新
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
    })),
    // 添加收藏的代理 - 使用保存的名称，如果名称不存在则尝试获取
    ...Array.from(favoriteAgents.entries()).map(([agentId, agentName]) => ({
      id: `fav-agent-${agentId}`,
      name: agentName || getAgentName(agentId),
      type: 'agent' as const,
      itemId: agentId,
      icon: 'fa-user-tie'
    }))
  ], [favoriteAssistants, favoriteAgents, language, updateCounter, t]);

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

      {/* 中间聊天区域 - 根据右侧是否显示Markdown预览和面板收拢状态调整宽度 */}
      <div className={`${resultPanelCollapsed || !isMarkdownView ? 'flex-1' : 'w-1/3'} flex flex-col overflow-hidden transition-all duration-300`}>
        <ChatArea
          selectedTask={selectedTask}
          browseMode={browseMode}
          onAssistantSelect={handleAssistantSelect}
          onAgentSelect={handleAgentSelect}
          resultPanelCollapsed={resultPanelCollapsed}
          onResultPanelToggle={() => {
            const newCollapsed = !resultPanelCollapsed;
            setResultPanelCollapsed(newCollapsed);
            // 當收攏面板時，重置預覽狀態
            if (newCollapsed) {
              setIsMarkdownView(false);
            }
          }}
          onAssistantFavorite={handleAssistantFavorite}
          favoriteAssistants={favoriteAssistants}
          onAgentFavorite={handleAgentFavorite}
          favoriteAgents={favoriteAgents}
          onTaskUpdate={(updatedTask: Task) => {
            // 更新任务（包括标题）
            setSelectedTask(updatedTask);
          }}
          currentTaskId={selectedTask ? String(selectedTask.id) : undefined}
          onTaskCreate={handleTaskCreate}
          onTaskDelete={handleTaskDelete}
        />
      </div>

      {/* 右侧结果面板 - 预览文件时完全展开，收合时完全隐藏。在代理浏览或助理浏览模式下，只有建立task后才显示 */}
      {!resultPanelCollapsed && selectedTask !== undefined && (
        <div className={`transition-all duration-300 ${isMarkdownView ? 'w-2/3' : 'w-80'}`}>
          <ResultPanel
            collapsed={false}
            wasCollapsed={prevResultPanelCollapsedRef.current}
            onToggle={() => {
              setResultPanelCollapsed(true);
            }}
            onViewChange={(isViewing) => {
              setIsMarkdownView(isViewing);
              // 注意：不應該在預覽文件時清除選中的任務
              // 預覽文件時應該保持任務選中狀態，這樣聊天區域才能正常顯示
              // 但是需要清除瀏覽模式，確保顯示任務內容而不是瀏覽頁面
              if (isViewing && browseMode) {
                setBrowseMode(null);
              }
            }}
            fileTree={selectedTask?.fileTree}
            onFileTreeChange={handleFileTreeChange}
            taskId={(() => {
              // 邏輯說明：
              // 1. 如果任務已經有 fileTree（從 prop 傳入），不傳遞 taskId，FileTree 會使用 fileTree prop
              // 2. 如果任務沒有 fileTree 但需要從後端獲取，傳遞 taskId
              // 3. 新任務（剛創建，沒有文件、沒有消息、標題為"新任務"）不傳遞 taskId，避免不必要的 API 調用
              if (!selectedTask) {
                console.log('[Home] No selectedTask, taskId = undefined');
                return undefined;
              }

              // 如果已經有 fileTree，不調用 API，使用 prop
              if (selectedTask.fileTree?.length) {
                console.log('[Home] Task has fileTree, taskId = undefined', { taskId: selectedTask.id, fileTreeLength: selectedTask.fileTree.length });
                return undefined;
              }

                // 檢查是否為新任務：標題為"新任務"且沒有消息和文件
              const isNewTask = (
                (selectedTask.title === '新任務' || selectedTask.title === '新任务' || selectedTask.title === 'New Task') &&
                (!selectedTask.messages || selectedTask.messages.length === 0) &&
                (!selectedTask.fileTree || selectedTask.fileTree.length === 0)
              );

              if (isNewTask) {
                console.log('[Home] New task detected, taskId = undefined', { taskId: selectedTask.id });
                return undefined;
              }

              // 其他情況都傳遞 taskId，讓 FileTree 從後端獲取文件
              const taskId = String(selectedTask.id);
              console.log('[Home] Passing taskId to ResultPanel', { taskId, taskTitle: selectedTask.title });
              return taskId;
            })()}
            userId={localStorage.getItem('userEmail') || undefined}
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
