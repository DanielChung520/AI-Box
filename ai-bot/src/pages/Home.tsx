// 代碼功能說明: 首頁頁件組件
// 創建日期: 2025-10-25
// 創建人: Daniel Chung
// 最後修改日期: 2026-02-02

import { useState, useEffect, useMemo, useRef } from 'react';
import { useLanguage } from '../contexts/languageContext';
import Sidebar from '../components/Sidebar';
import ChatArea from '../components/ChatArea';
import ResultPanel from '../components/ResultPanel';
import ExecutorSelectorModal from '../components/ExecutorSelectorModal';
import FileEditPreviewModal from '../components/FileEditPreviewModal';
import BrainIcon from '../components/BrainIcon';
import AIStatusWindow from '../components/AIStatusWindow';
import { Task, FavoriteItem, FileNode } from '../components/Sidebar';
import { saveTask, deleteTask, getTask, getFavorites } from '../lib/taskStorage';
// 修改時間：2025-12-13 17:28:02 (UTC+8) - 產品級 Chat：串接 /api/v1/chat
// 修改時間：2025-12-21 - 添加流式 Chat 支持
import { chatProduct, chatProductStream, ChatProductMessage } from '../lib/api';
import { parseFileReference, updateDraftFileContent } from '../lib/fileReference';
import { getDocEditState } from '../lib/api';
import { extractTaskTitle } from '../lib/taskTitleUtils'; // 修改時間：2025-12-21 - 導入任務標題提取工具
import { useAIStatusSSE } from '../hooks/useAIStatusSSE';
import { useAIStatusStore } from '../stores/aiStatusStore';
import '../lib/debugStorage'; // 加載調試工具
import '../lib/checkFiles'; // 加載文件檢查工具

export default function Home() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [resultPanelCollapsed, setResultPanelCollapsed] = useState(false);
  const [isMarkdownView, setIsMarkdownView] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | undefined>(undefined);
  const prevResultPanelCollapsedRef = useRef<boolean>(false);
  const { t, updateCounter, language } = useLanguage();

  // AI 狀態 SSE 追蹤
  const { connect: connectAIStatus, disconnect: disconnectAIStatus } = useAIStatusSSE({
    requestId: null,  // 從 store 讀取，不從 props 傳入
    enabled: true,
  });

  const { currentStatus, setCurrentStatus, setRequestId, requestId } = useAIStatusStore();

  // 當 AI 回覆完成時，清理 request_id
  useEffect(() => {
    if ((currentStatus === 'completed' || currentStatus === 'error') && requestId) {
      const timer = setTimeout(() => {
        setRequestId(null);
        disconnectAIStatus();
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [currentStatus, requestId, disconnectAIStatus, setRequestId]);

  // 調試：記錄 token 狀態
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const userEmail = localStorage.getItem('userEmail');
    const currentUser = localStorage.getItem('currentUser');
    console.log('[Home] Token status:', {
      hasToken: !!token,
      tokenLength: token?.length || 0,
      tokenPreview: token ? token.substring(0, 20) + '...' : 'None',
      userEmail,
      currentUser: currentUser ? JSON.parse(currentUser) : null,
    });
  }, []);

  // 修改時間：2025-12-13 17:28:02 (UTC+8) - 收藏模型 localStorage key（與 api.ts 一致）
  const FAVORITE_MODELS_STORAGE_KEY = 'ai-box-favorite-models';

  const loadFavoriteModelsLocal = (): string[] => {
    try {
      const raw = localStorage.getItem(FAVORITE_MODELS_STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch {
      return [];
    }
  };

  const generateSessionId = (): string => {
    // 優先使用瀏覽器原生 UUID
    // @ts-ignore
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      // @ts-ignore
      return crypto.randomUUID();
    }
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  };

  // 生成唯一消息 ID（使用 UUID 避免重複）
  const generateMessageId = (): string => {
    // @ts-ignore
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      // @ts-ignore
      return `msg-${crypto.randomUUID()}-ai`;
    }
    return `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}-ai`;
  };

  // 执行者选择相关状态
  const [showExecutorModal, setShowExecutorModal] = useState(false);
  const [executorModalType] = useState<'assistant' | 'agent'>('assistant');
  const [selectedExecutorId] = useState<string>('');
  const [selectedExecutorName] = useState<string>('');

  // 修改時間：2025-12-14 14:30:00 (UTC+8) - 檔案編輯預覽 Modal 狀態
  const [editPreviewModal, setEditPreviewModal] = useState<{
    isOpen: boolean;
    fileId: string;
    filename: string;
    requestId: string;
    taskId: string;
  } | null>(null);

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
      prev.forEach((_oldName, id) => {
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
      prev.forEach((_oldName, id) => {
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

  // 修改時間：2026-01-06 - 監聽收藏更新事件，從 localStorage 重新加載收藏狀態
  useEffect(() => {
    const handleFavoriteAssistantsUpdated = () => {
      const saved = localStorage.getItem('favoriteAssistants');
      if (saved) {
        try {
          const data = JSON.parse(saved);
          setFavoriteAssistants(new Map(Object.entries(data)));
          console.log('[Home] Reloaded favorite assistants from localStorage');
        } catch (error) {
          console.error('[Home] Failed to reload favorite assistants:', error);
        }
      }
    };

    const handleFavoriteAgentsUpdated = () => {
      const saved = localStorage.getItem('favoriteAgents');
      if (saved) {
        try {
          const data = JSON.parse(saved);
          setFavoriteAgents(new Map(Object.entries(data)));
          console.log('[Home] Reloaded favorite agents from localStorage');
        } catch (error) {
          console.error('[Home] Failed to reload favorite agents:', error);
        }
      }
    };

    // 監聽自定義事件
    window.addEventListener('favoriteAssistantsUpdated', handleFavoriteAssistantsUpdated);
    window.addEventListener('favoriteAgentsUpdated', handleFavoriteAgentsUpdated);

    // 監聽 localStorage 變化（跨標籤頁同步）
    window.addEventListener('storage', (e) => {
      if (e.key === 'favoriteAssistants') {
        handleFavoriteAssistantsUpdated();
      } else if (e.key === 'favoriteAgents') {
        handleFavoriteAgentsUpdated();
      }
    });

    return () => {
      window.removeEventListener('favoriteAssistantsUpdated', handleFavoriteAssistantsUpdated);
      window.removeEventListener('favoriteAgentsUpdated', handleFavoriteAgentsUpdated);
    };
  }, []);

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
    console.log('[Home] handleTaskSelect called, task.id=' + task.id + ', selectedTask.id=' + (selectedTask?.id || 'null'));

    // 如果選擇的是當前任務，保留內存中的任務（包含最新消息）
    if (selectedTask && selectedTask.id === task.id) {
      console.log('[Home] 選擇當前任務，保留內存中的數據');
      setCurrentStatus('idle'); // 重置 AI 狀態
      setBrowseMode(null);
      if (isMarkdownView) {
        setIsMarkdownView(false);
      }
      return;
    }

    // 從 localStorage 重新加載任務數據
    const savedTask = getTask(task.id);
    const taskToSelect = savedTask || task;

    console.log('[Home] 從 localStorage 加載任務:', {
      taskId: task.id,
      hasSavedTask: !!savedTask,
      messageCount: taskToSelect?.messages?.length || 0,
      lastMessage: taskToSelect?.messages?.slice(-1)[0]?.content?.substring(0, 50) || 'none',
    });

    setSelectedTask(taskToSelect);
    setCurrentStatus('idle'); // 重置 AI 狀態
    setBrowseMode(null); // 清除浏览模式
    // 如果正在预览Markdown，切换回聊天视图
    if (isMarkdownView) {
      setIsMarkdownView(false);
    }
    // 任務的文件目錄會自動從 task.fileTree 恢復
  };

  // 修改時間：2025-12-13 17:28:02 (UTC+8) - 模型選擇寫回 task.executionConfig.modelId 並持久化
  const handleModelSelect = (modelId: string) => {
    if (!selectedTask) {
      return;
    }

    const updatedTask: Task = {
      ...selectedTask,
      executionConfig: {
        ...(selectedTask.executionConfig || { mode: 'free' }),
        modelId,
      },
    };

    setSelectedTask(updatedTask);
    saveTask(updatedTask, true).catch((error) => {
      console.error('[Home] Failed to save task after model select:', error);
    });
  };

  // 修改時間：2025-12-13 17:28:02 (UTC+8) - 送出訊息：呼叫 /api/v1/chat 並把回覆寫回 task.messages
  const handleMessageSend = async (raw: string) => {
    if (!selectedTask) {
      return;
    }

    // 設置 AI 處理狀態
    setCurrentStatus('processing');
    console.log('[Home] AI 狀態設置為: processing');

    // 生成 request_id 並開始追蹤狀態
    const requestId = `req-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    console.log('[Home] 🔧 生成 request_id:', requestId);

    // 【修復】確保 SSE 連接在 /api/v1/agent-status/start 之前建立
    // 時序：1. 先設置 requestId 2. 建立 SSE 連接 3. 啟動狀態追蹤
    setRequestId(requestId);

    // 【關鍵】立即建立 SSE 連接（不使用 setTimeout 延遲）
    console.log('[Home] 🔌 建立 SSE 連接...');
    connectAIStatus();

    // 然後調用 API 開始追蹤狀態
    console.log('[Home] 📡 調用 /api/v1/agent-status/start...');
    fetch('/api/v1/agent-status/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request_id: requestId }),
    })
    .then(response => {
      console.log('[Home] ✅ /api/v1/agent-status/start 響應:', response.status, response.statusText);
      return response.json();
    })
    .then(data => {
      console.log('[Home] ✅ 狀態追蹤啟動成功:', data);
    })
    .catch((error) => {
      console.error('[Home] ❌ 無法啟動狀態追蹤:', error);
    });

    let text = '';
    let fileReferences: Array<any> = [];
    let tools: { web_search?: boolean } = {};
    let assistantId: string | undefined;

    try {
      const parsed = JSON.parse(raw);
      text = String(parsed?.text ?? '').trim();
      fileReferences = Array.isArray(parsed?.fileReferences) ? parsed.fileReferences : [];
      tools = parsed?.tools || {};
      assistantId = parsed?.assistantId;
    } catch {
      text = String(raw ?? '').trim();
    }

    console.log('[Home] 📥 Parsed message:', {
      text: text.substring(0, 100),
      textLength: text.length,
      fileReferencesCount: fileReferences.length,
      tools,
      hasTools: !!tools,
      webSearchEnabled: tools?.web_search,
      assistantId,
      isWebSearchActive: tools?.web_search,
    });

    // 如果 tools 为空但应该启用 web_search，发出警告
    if (!tools?.web_search && text.includes('上網')) {
      console.warn('[Home] ⚠️ User message contains "上網" but web_search tool is not enabled!', {
        tools,
        text: text.substring(0, 100),
      });
    }

    const now = new Date();
    const timestamp = now.toLocaleString();

    const sessionId =
      selectedTask.executionConfig?.sessionId || generateSessionId();
    const modelId = selectedTask.executionConfig?.modelId || 'auto';

    const userMessage = {
      id: `msg-${generateMessageId().split('-')[1]}-user`,  // 使用 generateMessageId 但保持 user 後綴
      sender: 'user' as const,
      content: text || '(no text)',
      timestamp,
    };

    const taskWithUserMessage: Task = {
      ...selectedTask,
      status: 'in-progress',
      messages: [...(selectedTask.messages || []), userMessage],
      executionConfig: {
        ...(selectedTask.executionConfig || { mode: 'free' }),
        sessionId,
        modelId,
      },
    };

    setSelectedTask(taskWithUserMessage);
    // 立即同步保存到 localStorage（確保切換任務時能讀取到）
    try {
      const taskKey = `ai-box-task-${taskWithUserMessage.id}`;
      localStorage.setItem(taskKey, JSON.stringify(taskWithUserMessage));
      console.log('[Home] 已將用戶消息同步保存到 localStorage, key=' + taskKey);
    } catch (error) {
      console.error('[Home] Failed to save task to localStorage:', error);
    }
    // 異步同步到後台
    saveTask(taskWithUserMessage, true).catch((error) => {
      console.error('[Home] Failed to sync task to backend:', error);
    });

    // 修改時間：2025-12-14 14:30:00 (UTC+8) - 檢測是否為編輯草稿檔意圖
    const lastUserMessage = (taskWithUserMessage.messages || []).slice(-1)[0];
    const userText = lastUserMessage?.content || '';
    const fileRef = parseFileReference(userText, String(taskWithUserMessage.id));

    // 如果是草稿檔編輯，直接更新草稿檔內容，不調用後端
    if (fileRef && fileRef.isDraft && fileRef.fileId) {
      // 先發送聊天請求獲取 AI 回復
      const history = (taskWithUserMessage.messages || []).slice(-20);
      const chatMessages: ChatProductMessage[] = history.map((m) => ({
        role: (m.sender === 'ai' ? 'assistant' : 'user'),
        content: m.content,
      }));

      const attachments = fileReferences.map((ref) => ({
        file_id: String(ref.fileId ?? ''),
        file_name: String(ref.fileName ?? ''),
        file_path: ref.filePath ? String(ref.filePath) : undefined,
        task_id: ref.taskId ? String(ref.taskId) : undefined,
      })).filter((a) => a.file_id && a.file_name);

      const favoriteModels = loadFavoriteModelsLocal();
      const mode =
        modelId === 'auto'
          ? 'auto'
          : favoriteModels.includes(modelId)
            ? 'favorite'
            : 'manual';

      const model_selector: any =
        mode === 'auto'
          ? { mode: 'auto' }
          : { mode, model_id: modelId };

      // 构建允许的工具列表
      const allowedTools: string[] = [];
      if (tools?.web_search) {
        allowedTools.push('web_search');
      }

      // 修改時間：2026-01-27 - 添加 agent_id 到草稿檔編輯請求中
      const agentId = taskWithUserMessage.executionConfig?.agentId;
      const assistantId = taskWithUserMessage.executionConfig?.assistantId;

      // 修改時間：2026-01-27 - 添加完整的請求參數日誌（草稿檔編輯）
      const draftEditRequest = {
        messages: chatMessages,
        session_id: sessionId,
        task_id: String(taskWithUserMessage.id),
        model_selector,
        attachments: attachments.length ? attachments : undefined,
        allowed_tools: allowedTools.length > 0 ? allowedTools : undefined,
        assistant_id: assistantId,
        agent_id: agentId,
      };

      console.log('[chatMessage] 📤 發送聊天請求（草稿檔編輯）:', {
        task_id: String(taskWithUserMessage.id),
        assistant_id: assistantId || '未選擇',
        agent_id: agentId || '未選擇',
        model_id: modelId,
        model_selector: draftEditRequest.model_selector,
        web_search: tools?.web_search || false,
        message_count: chatMessages.length,
        last_message: chatMessages[chatMessages.length - 1]?.content?.substring(0, 100),
        allowed_tools: draftEditRequest.allowed_tools || [],
        attachments_count: draftEditRequest.attachments?.length || 0,
        session_id: sessionId,
        timestamp: new Date().toISOString(),
        full_request: draftEditRequest,
      });

      // [send chat message] 攔截日誌
      console.log('[send chat message] 📤 發送請求:', {
        agent_id: draftEditRequest.agent_id,
        assistant_id: draftEditRequest.assistant_id,
        model_selector: draftEditRequest.model_selector,
        model_id: draftEditRequest.modelId,
        session_id: draftEditRequest.session_id,
        task_id: draftEditRequest.task_id,
        message_count: draftEditRequest.messages?.length || 0,
        last_message: draftEditRequest.messages?.[draftEditRequest.messages?.length - 1]?.content?.substring(0, 50),
      });

      try {
        const resp = await chatProduct(draftEditRequest as any); // 临时使用 any，因为接口定义可能还没有更新

        if (resp?.success && resp.data?.content !== undefined) {
          const aiMessage = {
            id: generateMessageId(),
            sender: 'ai' as const,
            content: String(resp.data.content ?? ''),
            timestamp: new Date().toLocaleString(),
          };

          // 直接更新草稿檔內容
          updateDraftFileContent(
            fileRef.fileId,
            String(resp.data.content ?? ''),
            fileRef.filename,
            fileRef.taskId || String(taskWithUserMessage.id),
            fileRef.containerKey || null,
          );

          const editActionMessage = {
            id: generateMessageId(),
            sender: 'ai' as const,
            content: `✅ 已更新草稿檔：${fileRef.filename}`,
            timestamp: new Date().toLocaleString(),
          };

          const finalTask: Task = {
            ...taskWithUserMessage,
            messages: [
              ...(taskWithUserMessage.messages || []),
              aiMessage,
              editActionMessage,
            ],
          };

          setSelectedTask(finalTask);
          saveTask(finalTask, true).catch((error) => {
            console.error('[Home] Failed to save task after ai message:', error);
          });

          // 通知 FileTree 更新
          window.dispatchEvent(
            new CustomEvent('draftFileContentUpdated', {
              detail: {
                draftId: fileRef.fileId,
                filename: fileRef.filename,
                taskId: fileRef.taskId || String(taskWithUserMessage.id),
              },
            })
          );

          // AI 回復完成
          setCurrentStatus('completed');
          console.log('[Home] AI 狀態設置為: completed (draft edit)');
          return; // 提前返回，不執行後續的正式檔案處理
        }
      } catch (error: any) {
        console.error('[Home] chatProduct request failed for draft edit:', error);
        setCurrentStatus('error');
        console.log('[Home] AI 狀態設置為: error (stream failed)');
        console.log('[Home] AI 狀態設置為: error (draft edit failed)');
      }
    }

    const history = (taskWithUserMessage.messages || []).slice(-20);
    // 过滤掉 content 为空的消息（避免验证错误）
    const chatMessages: ChatProductMessage[] = history
      .filter((m) => m.content && m.content.trim().length > 0) // 过滤空内容
      .map((m) => ({
        role: (m.sender === 'ai' ? 'assistant' : 'user'),
        content: m.content.trim(), // 确保 content 不为空
      }));

    const attachments = fileReferences.map((ref) => ({
      file_id: String(ref.fileId ?? ''),
      file_name: String(ref.fileName ?? ''),
      file_path: ref.filePath ? String(ref.filePath) : undefined,
      task_id: ref.taskId ? String(ref.taskId) : undefined,
    })).filter((a) => a.file_id && a.file_name);

    const favoriteModels = loadFavoriteModelsLocal();
    const mode =
      modelId === 'auto'
        ? 'auto'
        : favoriteModels.includes(modelId)
          ? 'favorite'
          : 'manual';

    try {
      // 修改時間：2025-12-21 - 使用流式 API
      // 修改時間：2026-01-06 - 從消息中獲取 Assistant 的 allowedTools，而不僅僅是 web_search
      // 構建允許的工具列表（必須在使用之前聲明）
      const allowedTools: string[] = [];

      // 從消息中提取 allowedTools（如果存在）
      let messageAllowedTools: string[] = [];
      try {
        const parsedMessage = JSON.parse(raw);
        if (parsedMessage?.allowedTools && Array.isArray(parsedMessage.allowedTools)) {
          messageAllowedTools = parsedMessage.allowedTools;
        }
      } catch (e) {
        // 忽略解析錯誤
      }

      // 優先使用消息中的 allowedTools（來自 Assistant 配置）
      if (messageAllowedTools.length > 0) {
        allowedTools.push(...messageAllowedTools);
      }

      // 如果 web_search 被激活，確保包含在 allowedTools 中
      if (tools?.web_search && !allowedTools.includes('web_search')) {
        allowedTools.push('web_search');
      }

      // 修改時間：2026-01-27 - 獲取 assistantId 和 agentId（必須在使用之前聲明）
      const assistantId = taskWithUserMessage.executionConfig?.assistantId;
      const agentId = taskWithUserMessage.executionConfig?.agentId;

      // 構建 model_selector
      const model_selector: any =
        mode === 'auto'
          ? { mode: 'auto' }
          : { mode, model_id: modelId };

      console.log('[Home] Calling chatProductStream with tools:', {
        allowedTools,
        messageAllowedTools,
        isWebSearchActive: tools?.web_search,
        assistantId,
        agentId,
        toolsFromMessage: messageAllowedTools,
      });

      // 修改時間：2026-01-27 - 添加詳細的請求參數日誌
      const requestParams = {
        assistant_id: assistantId,
        agent_id: agentId,
        model_id: modelId,
        model_selector,
        web_search: tools?.web_search || false,
        messages: chatMessages,
        session_id: sessionId,
        task_id: String(taskWithUserMessage.id),
        attachments: attachments.length ? attachments : undefined,
        allowed_tools: allowedTools.length > 0 ? allowedTools : undefined,
      };

      // [send chat message] 攔截日誌
      console.log('[send chat message] 📤 發送請求:', {
        agent_id: agentId,
        assistant_id: assistantId,
        model_selector,
        model_id: modelId,
        session_id: sessionId,
        task_id: String(taskWithUserMessage.id),
        message_count: chatMessages?.length || 0,
        last_message: chatMessages?.[chatMessages?.length - 1]?.content?.substring(0, 50),
      });

      // ========================================
      // 指代消解邏輯（2026-02-04）
      // ========================================
      const lastUserMessage = chatMessages[chatMessages.length - 1]?.content || '';
      const currentEntities = taskWithUserMessage.entities || {};

      // 提取實體：檢查是否為 "X 是 Y" 模式
      const entityPatterns = [
        /^(.+?)\s*(是|為|等於)\s*(.+)$/,  // "RM01-009 是料號"
        /^(.+?)\s*=\s*(.+)$/,              // "RM01-009 = 料號"
      ];

      let newEntities = { ...currentEntities };
      let resolvedMessage = lastUserMessage;

      // 1. 提取新實體
      for (const pattern of entityPatterns) {
        const match = lastUserMessage.match(pattern);
        if (match) {
          const name = match[1].trim();
          const meaning = match[3].trim();
          // 排除常見的無意義對應
          if (name !== meaning && name.length > 1 && meaning.length > 1) {
            newEntities[name] = meaning;
            console.log('[指代消解] 📝 提取實體:', { name, meaning });
          }
          break; // 只處理第一個匹配
        }
      }

      // 2. 指代消解：將 entities 中的 key 替換為 "意義 key"
      for (const [key, meaning] of Object.entries(newEntities)) {
        // 使用正則匹配完整的 key（避免部分匹配）
        const regex = new RegExp(`\\b${key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'g');
        resolvedMessage = resolvedMessage.replace(regex, `${meaning} ${key}`);
      }

      // 3. 如果消息被修改（包含實體），更新消息
      if (resolvedMessage !== lastUserMessage) {
        console.log('[指代消解] 🔄 消解後:', resolvedMessage);
        // 更新最後一條用戶消息
        const updatedMessages = chatMessages.map((msg, idx) => {
          if (idx === chatMessages.length - 1 && msg.role === 'user') {
            return { ...msg, content: resolvedMessage };
          }
          return msg;
        });
        (requestParams as any).messages = updatedMessages;
      }

      // 4. 將 entities 保存到 task 中
      const taskWithEntities: Task = {
        ...taskWithUserMessage,
        entities: newEntities,
      };

      console.log('[指代消解] 📚 當前 entities:', newEntities);

      // console.log('[chatMessage] 📤', {
      //   agent_id: requestParams.agent_id,
      //   model_id: requestParams.model_id,
      //   last_message: requestParams.messages[requestParams.messages.length - 1]?.content?.substring(0, 50),
      // });

      // 創建初始 AI 消息（內容為空，將逐步更新）
      const aiMessageId = generateMessageId();
      const initialAiMessage = {
        id: aiMessageId,
        sender: 'ai' as const,
        content: '',
        timestamp: new Date().toLocaleString(),
      };

      // 先顯示空的 AI 消息
      const taskWithInitialAiMessage: Task = {
        ...taskWithUserMessage,
        messages: [...(taskWithUserMessage.messages || []), initialAiMessage],
      };
      setSelectedTask(taskWithInitialAiMessage);

      // 修改時間：2026-01-27 - 添加 agent_id 到請求中
      // 使用之前構建的 requestParams（已經包含所有參數）
      const requestData = requestParams;

      // console.log('[chatMessage] 📤', {
      //   agent_id: requestData.agent_id,
      //   model_id: modelId,
      //   last_message: chatMessages[chatMessages.length - 1]?.content?.substring(0, 50),
      // });

      // 验证 messages 不为空
      if (chatMessages.length === 0) {
        console.error('[Home] ❌ Error: messages array is empty!');
        const errorMessage = {
          id: generateMessageId(),
          sender: 'ai' as const,
          content: '错误：消息列表为空，无法发送请求',
          timestamp: new Date().toLocaleString(),
        };
        const errorTask: Task = {
          ...taskWithUserMessage,
          messages: [...(taskWithUserMessage.messages || []), errorMessage],
        };
        setSelectedTask(errorTask);
        setCurrentStatus('error');
        console.log('[Home] AI 狀態設置為: error (stream failed)');
        return;
      }

      // 使用流式 API 接收內容
      let fullContent = '';
      let fileCreated: any = null; // 追蹤文件創建事件
      let lastUpdateTime = Date.now();
      let pendingUpdateTimer: ReturnType<typeof setTimeout> | null = null;
      const UPDATE_THROTTLE_MS = 300; // 防抖間隔：300ms（增加間隔以減少更新頻率）

      // 使用 ref 來存儲當前內容，避免閉包問題
      const contentRef = { current: '' };

      // 使用函數式更新來避免無限循環，並使用防抖優化性能
      const updateTaskContent = (content: string, forceUpdate: boolean = false) => {
        // 更新 ref
        contentRef.current = content;

        const now = Date.now();
        const timeSinceLastUpdate = now - lastUpdateTime;

        // 如果是強制更新，立即執行
        if (forceUpdate) {
          if (pendingUpdateTimer) {
            clearTimeout(pendingUpdateTimer);
            pendingUpdateTimer = null;
          }
          lastUpdateTime = now;
          _performUpdate();
          return;
        }

        // 防抖：如果距離上次更新時間太短，延遲更新
        if (timeSinceLastUpdate < UPDATE_THROTTLE_MS) {
          // 清除之前的定時器
          if (pendingUpdateTimer) {
            clearTimeout(pendingUpdateTimer);
          }
          // 設置新的定時器，確保最後一次更新能夠執行
          pendingUpdateTimer = setTimeout(() => {
            lastUpdateTime = Date.now();
            _performUpdate();
            pendingUpdateTimer = null;
          }, UPDATE_THROTTLE_MS - timeSinceLastUpdate);
          return;
        }

        // 時間間隔足夠，立即更新
        lastUpdateTime = now;
        _performUpdate();
      };

      // 實際執行更新的函數（使用 ref 獲取最新內容）
      const _performUpdate = () => {
        const content = contentRef.current;

        setSelectedTask((currentTask) => {
          if (!currentTask || currentTask.id !== taskWithUserMessage.id) {
            return currentTask;
          }

          // 找到 AI 消息並檢查內容是否真的改變
          const messages = currentTask.messages || [];
          const aiMessageIndex = messages.findIndex(m => m.id === aiMessageId);

          // 如果找到了 AI 消息，檢查內容是否改變
          if (aiMessageIndex >= 0) {
            const currentAiMessage = messages[aiMessageIndex];
            // 如果內容相同，直接返回原對象，不創建新對象
            if (currentAiMessage.content === content) {
              return currentTask;
            }

            // 內容改變了，創建新的消息數組
            const newMessages = [...messages];
            newMessages[aiMessageIndex] = {
              ...currentAiMessage,
              content: content,
            };

            return {
              ...currentTask,
              messages: newMessages,
            };
          } else {
            // 如果找不到，添加新的 AI 消息
            return {
              ...currentTask,
              messages: [
                ...messages,
                {
                  ...initialAiMessage,
                  content: content,
                },
              ],
            };
          }
        });
      };

      // [send chat message] 攔截日誌
      console.log('[send chat message] 📤 發送請求:', {
        agent_id: requestData.agent_id,
        assistant_id: requestData.assistant_id,
        model_selector: requestData.model_selector,
        model_id: requestData.modelId,
        session_id: requestData.session_id,
        task_id: requestData.task_id,
        message_count: requestData.messages?.length || 0,
        last_message: requestData.messages?.[requestData.messages?.length - 1]?.content?.substring(0, 50),
      });

      try {
        console.log('[Home] ========== 開始接收流式響應 ==========');
        console.log('[Home] Request Data:', JSON.stringify({
          agent_id: requestData.agent_id,
          messages_count: requestData.messages?.length,
          last_message: requestData.messages?.[requestData.messages?.length - 1]?.content?.substring(0, 50)
        }));
        let eventCount = 0;
        // 修改時間: 2026-01-06 - 從消息中獲取 Assistant 的 allowedTools，而不僅僅是 web_search
        // 構建允許的工具列表（必須在使用之前聲明）
        const { requestId, stream } = await chatProductStream(requestData as any);
        if (requestId) {
          console.log('[Home] Request ID:', requestId);
          setRequestId(requestId);  // 從 store 設置 requestId
        }

        for await (const event of stream) { // 遍歷 stream 而不是 chatProductStream
          eventCount++;
          console.log('[Home] 收到事件 #' + eventCount + ':', event.type);
          if (event.type === 'content' && event.data?.chunk) {
            // 累積內容並更新消息（使用防抖）
            fullContent += event.data.chunk;
            console.log('[updateTaskContent] 📝 內容更新:', fullContent.substring(0, 100));
            updateTaskContent(fullContent);
          } else if (event.type === 'file_created' && event.data) {
            // 修改時間：2026-01-06 - 處理文件創建事件
            fileCreated = event.data;
            console.log('[Home] 📁 File created event received:', fileCreated);

            // 觸發文件上傳事件，通知 FileTree 更新
            window.dispatchEvent(
              new CustomEvent('fileUploaded', {
                detail: {
                  taskId: String(taskWithUserMessage.id),
                  fileIds: [String(fileCreated.file_id)],
                },
              })
            );
          } else if (event.type === 'error') {
            // 處理錯誤 - 必須生成新的 ID，避免與初始 AI 消息衝突
            const errorMessageId = generateMessageId();
            const errorMessage = {
              id: errorMessageId,
              sender: 'ai' as const,
              content: event.data?.error || '發生了一些錯誤，請稍後再試',
              timestamp: new Date().toLocaleString(),
            };
            setSelectedTask((currentTask) => {
              if (!currentTask || currentTask.id !== taskWithUserMessage.id) {
                return currentTask;
              }
              // 過濾掉初始的 AI 消息（空內容），然後添加錯誤消息
              const filteredMessages = (currentTask.messages || []).filter(
                (m) => m.id !== aiMessageId || m.content !== ''
              );
              return {
                ...currentTask,
                messages: [...filteredMessages, errorMessage],
              };
            });
            setCurrentStatus('error');
        console.log('[Home] AI 狀態設置為: error (stream failed)');
            return;
          } else if (event.type === 'done') {
            console.log('[Home] 收到 done 事件');
            console.log('[receive chat message] 📥 API 回覆內容:', fullContent.substring(0, 200));
            // 流結束，清除待處理的定時器並強制更新最後一次
            if (pendingUpdateTimer) {
              clearTimeout(pendingUpdateTimer);
              pendingUpdateTimer = null;
            }
            // 強制更新，確保最後的內容被應用
            if (fullContent) {
              updateTaskContent(fullContent, true);
            }
            setCurrentStatus('completed');
            console.log('[Home] AI 狀態設置為: completed (done event)');
            break;
          }
        }
      } catch (streamError: any) {
        console.error('[Home] Streaming error:', streamError);
        // 清除待處理的定時器
        if (pendingUpdateTimer) {
          clearTimeout(pendingUpdateTimer);
          pendingUpdateTimer = null;
        }
        // 生成新的 ID 避免衝突
        const errorMessageId = generateMessageId();
        const errorMessage = {
          id: errorMessageId,
          sender: 'ai' as const,
          content: streamError?.message || '發生了一些錯誤，請稍後再試',
          timestamp: new Date().toLocaleString(),
        };
        setSelectedTask((currentTask) => {
          if (!currentTask || currentTask.id !== taskWithUserMessage.id) {
            return currentTask;
          }
          // 過濾掉初始的 AI 消息（空內容），然後添加錯誤消息
          const filteredMessages = (currentTask.messages || []).filter(
            (m) => m.id !== aiMessageId || m.content !== ''
          );
          return {
            ...currentTask,
            messages: [...filteredMessages, errorMessage],
          };
        });
        setCurrentStatus('error');
        console.log('[Home] AI 狀態設置為: error (stream failed)');
        return;
      }

      // 檢查是否收到 done 事件（通過檢查 fullContent 是否已更新）
      console.log('[Home] 流式響應檢查: fullContent.length=' + fullContent.length + ', currentStatus=' + currentStatus);
      if (fullContent && currentStatus !== 'completed') {
        console.log('[Home] 流式響應正常結束，設置 completed');
        setCurrentStatus('completed');
      }

      // 如果超過 60 秒沒有完成，設置超時
      setTimeout(() => {
        if (currentStatus === 'processing') {
          console.log('[Home] 流式響應超時，設置 completed');
          setCurrentStatus('completed');
        }
      }, 60000);

      // 流式響應完成後，處理後續邏輯（標題生成等）
      const aiMessage = {
        id: aiMessageId,
        sender: 'ai' as const,
        content: fullContent,
        timestamp: new Date().toLocaleString(),
      };

      // 修改時間：2025-12-21 - 檢查是否是第一組對話，如果是則自動生成任務標題
      const userMessages = taskWithUserMessage.messages?.filter(m => m.sender === 'user') || [];
      const isFirstConversation = userMessages.length === 1; // 只有一條用戶消息，這是第一組對話

      let finalTaskTitle = taskWithUserMessage.title;
      if (isFirstConversation && userMessages.length > 0) {
        // 從第一條用戶消息中提取標題
        const firstUserMessage = userMessages[0];
        const extractedTitle = extractTaskTitle(firstUserMessage.content);
        if (extractedTitle && extractedTitle !== taskWithUserMessage.title) {
          finalTaskTitle = extractedTitle;
          console.log('[Home] Auto-generating task title from first message:', {
            originalTitle: taskWithUserMessage.title,
            newTitle: extractedTitle,
            messageContent: firstUserMessage.content.substring(0, 50)
          });
        }
      }

      const finalTask: Task = {
        ...taskWithEntities, // 使用包含 entities 的 task
        title: finalTaskTitle, // 使用提取的標題
        messages: [
          ...(taskWithUserMessage.messages || []),
          aiMessage,
        ],
      };

      console.log('[Home] ========== AI 回覆完成 ==========');
      console.log('[Home] finalTask messages count:', finalTask.messages.length);
      console.log('[Home] last message (AI):', finalTask.messages[finalTask.messages.length - 1]?.content?.substring(0, 100));
      
      setSelectedTask(finalTask);
      saveTask(finalTask, true).catch((error) => {
        console.error('[Home] Failed to save task after ai message:', error);
      });

      // AI 回復完成
      setCurrentStatus('completed');
      console.log('[Home] AI 狀態設置為: completed (stream done)');

      // 修改時間：2025-12-21 - 如果標題已更新，觸發任務列表更新事件，以便 Sidebar 顯示新標題
      if (isFirstConversation && finalTaskTitle !== taskWithUserMessage.title) {
        window.dispatchEvent(new CustomEvent('taskUpdated', {
          detail: { taskId: finalTask.id, title: finalTaskTitle }
        }));
      }

        // 修改時間：2026-01-06 - 處理文件創建事件（已在流式循環中處理，這裡僅作為備份）
      if (fileCreated?.file_id) {
        console.log('[Home] 📁 File created confirmed:', fileCreated);
        // 文件創建事件已在流式循環中處理，這裡不需要重複處理
      }
    } catch (error: any) {
      console.error('[Home] chatProduct request failed:', error);
      const errorMessage = {
        id: generateMessageId(),
        sender: 'ai' as const,
        content: error?.message || '發生了一些錯誤，請稍後再試',
        timestamp: new Date().toLocaleString(),
      };

      const finalTask: Task = {
        ...taskWithUserMessage,
        messages: [...(taskWithUserMessage.messages || []), errorMessage],
      };

      setSelectedTask(finalTask);
      saveTask(finalTask, true).catch((e) => {
        console.error('[Home] Failed to save task after network error:', e);
      });

      // AI 處理異常完成
      setCurrentStatus('error');
        console.log('[Home] AI 狀態設置為: error (stream failed)');
    }
  };

  // 修改時間：2025-12-08 09:04:21 UTC+8 - 任務保存時同步到後台
  // 修改時間：2026-01-31 - 新任務傳入 isNewTask，跳過 getUserTask 檢查避免 404
  // 處理任務創建（用於文件上傳時創建新任務）
  const handleTaskCreate = async (task: Task) => {
    setSelectedTask(task);
    // 保存任務到 localStorage 並同步到後台（新任務直接創建，避免 GET 404）
    await saveTask(task, true, { isNewTask: true });
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
      const updatedTask = {
        ...selectedTask,
        fileTree: fileTree,
      };
      setSelectedTask(updatedTask);
      // 保存到 localStorage
      saveTask(updatedTask, false).catch((error) => {
        console.error('[Home] Failed to save task:', error);
      });
    }
  };

  // 修改時間：2025-12-09 - 處理文件樹更新事件
  const handleFileTreeUpdated = (event: CustomEvent) => {
    if (!event.detail) {
      return;
    }
    const { taskId, fileTree } = event.detail;
    if (!taskId) {
      return;
    }
    setSelectedTask((currentTask) => {
      if (!currentTask || String(currentTask.id) !== String(taskId)) {
        return currentTask;
      }
      const updatedTask = {
        ...currentTask,
        fileTree: fileTree,
      };
      // 保存到 localStorage
      saveTask(updatedTask, false).catch((error) => {
        console.error('[Home] Failed to save task:', error);
      });
      return updatedTask;
    });
  };

  // 修改時間：2025-12-09 - 處理文件重新排序事件
  const handleFilesReordered = (event: CustomEvent) => {
    const { taskId, fileTree } = event.detail;
    setSelectedTask((currentTask) => {
      if (!currentTask || String(currentTask.id) !== String(taskId)) {
        return currentTask;
      }
      const updatedTask = {
        ...currentTask,
        fileTree: fileTree,
      };
      // 保存到 localStorage
      saveTask(updatedTask, false).catch((error) => {
        console.error('[Home] Failed to save task:', error);
      });
      return updatedTask;
    });
  };

  // 監聽文件上傳事件（包括模擬和真實上傳）
  useEffect(() => {
    const handleFilesUploadedEvent = (event: CustomEvent) => {
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

          // 修改時間：2025-12-08 09:04:21 UTC+8 - 任務保存時同步到後台
          // 同時更新 localStorage 中的任務數據並同步到後台（異步執行，不阻塞）
          saveTask(updatedTask, true).catch((error) => {
            console.error('[Home] Failed to save task:', error);
          });

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

          // 修改時間：2025-12-08 09:04:21 UTC+8 - 任務保存時同步到後台
          // 同時更新 localStorage 中的任務數據並同步到後台（異步執行，不阻塞）
          saveTask(updatedTask, true).catch((error) => {
            console.error('[Home] Failed to save task:', error);
          });

          return updatedTask;
        } else {
          return currentTask;
        }
      });
    };

    window.addEventListener('filesUploaded', handleFilesUploadedEvent as EventListener);
    window.addEventListener('mockFilesUploaded', handleMockFilesUploaded as EventListener);

    // 修改時間：2025-12-14 14:30:00 (UTC+8) - 監聽檔案編輯預覽就緒事件
    const handleFileEditPreviewReady = (event: CustomEvent) => {
      const detail = event?.detail || {};
      const fileId = String(detail?.file_id || '').trim();
      const filename = String(detail?.filename || '').trim();
      const requestId = String(detail?.request_id || '').trim();
      const taskId = String(detail?.task_id || '').trim();

      if (fileId && filename && requestId && taskId) {
        setEditPreviewModal({
          isOpen: true,
          fileId,
          filename,
          requestId,
          taskId,
        });
      }
    };

    window.addEventListener('fileEditPreviewReady', handleFileEditPreviewReady as EventListener);
    window.addEventListener('fileTreeUpdated', handleFileTreeUpdated as EventListener);
    window.addEventListener('filesReordered', handleFilesReordered as EventListener);

    // 監聽任務刪除事件
    const handleTaskDeleted = (event: CustomEvent) => {
      const detail = event?.detail || {};
      const deletedTaskId = String(detail?.taskId || '');

      // 使用函數式更新，確保獲取最新的 selectedTask
      setSelectedTask((currentTask) => {
        if (currentTask && String(currentTask.id) === deletedTaskId) {
          console.log('[Home] Task deleted, clearing selectedTask', { taskId: deletedTaskId });
          return undefined;
        }
        return currentTask;
      });

      // 清除瀏覽模式
      setBrowseMode(null);
    };
    window.addEventListener('taskDeleted', handleTaskDeleted as EventListener);

    return () => {
      window.removeEventListener('filesUploaded', handleFilesUploadedEvent as EventListener);
      window.removeEventListener('mockFilesUploaded', handleMockFilesUploaded as EventListener);
      window.removeEventListener('fileTreeUpdated', handleFileTreeUpdated as EventListener);
      window.removeEventListener('filesReordered', handleFilesReordered as EventListener);
      window.removeEventListener('taskDeleted', handleTaskDeleted as EventListener);
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
    // 修改時間：2026-01-31 - 新任務立即同步到後端，避免送出訊息時 GET 404
    saveTask(newTask, true, { isNewTask: true }).catch((error) => {
      console.error('[Home] Failed to save task after assistant select:', error);
    });
    // 修改時間：2026-02-22 - 觸發 taskCreated 事件通知 Sidebar 更新任務列表
    window.dispatchEvent(new CustomEvent('taskCreated', {
      detail: { taskId: newTask.id }
    }));
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
      const updatedTask: Task = {
        ...selectedTask,
        executionConfig: {
          ...selectedTask.executionConfig,
          mode: 'agent',
          agentId: agentId,
          assistantId: undefined, // 清除助理ID
        }
      };
      setSelectedTask(updatedTask);
      // 修改時間：2026-01-27 - 保存 Agent 選擇到任務，確保發送請求時能獲取到 agentId
      saveTask(updatedTask, true).catch((error) => {
        console.error('[Home] Failed to save task after agent select:', error);
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
    // 修改時間：2026-01-31 - 新任務立即同步到後端，避免送出訊息時 GET 404
    saveTask(newTask, true, { isNewTask: true }).catch((error) => {
      console.error('[Home] Failed to save task after agent select:', error);
    });
    // 修改時間：2026-02-22 - 觸發 taskCreated 事件通知 Sidebar 更新任務列表
    window.dispatchEvent(new CustomEvent('taskCreated', {
      detail: { taskId: newTask.id }
    }));
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
      fileTree: [],
    };

    setSelectedTask(newTask);
    // 修改時間：2026-01-31 - 新任務立即同步到後端，避免送出訊息時 GET 404
    saveTask(newTask, true, { isNewTask: true }).catch((error) => {
      console.error('[Home] Failed to save task after executor select:', error);
    });
    // 修改時間：2026-02-22 - 觸發 taskCreated 事件通知 Sidebar 更新任務列表
    window.dispatchEvent(new CustomEvent('taskCreated', {
      detail: { taskId: newTask.id }
    }));
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

  // 生成收藏列表（包含收藏的任務、助理和代理）- 使用 useMemo 確保語言切換時更新
  const favorites: FavoriteItem[] = useMemo(() => {
    // 從 localStorage 讀取收藏的任務
    const favoriteTasks = getFavorites().filter(fav => fav.type === 'task');

    // 添加收藏的助理 - 使用保存的名稱，如果名稱不存在則嘗試獲取
    const favoriteAssistantsList = Array.from(favoriteAssistants.entries()).map(([assistantId, assistantName]) => ({
      id: `fav-assistant-${assistantId}`,
      name: assistantName || getAssistantName(assistantId),
      type: 'assistant' as const,
      itemId: assistantId,
      icon: 'fa-robot'
    }));

    // 添加收藏的代理 - 使用保存的名稱，如果名稱不存在則嘗試獲取
    const favoriteAgentsList = Array.from(favoriteAgents.entries()).map(([agentId, agentName]) => ({
      id: `fav-agent-${agentId}`,
      name: agentName || getAgentName(agentId),
      type: 'agent' as const,
      itemId: agentId,
      icon: 'fa-user-tie'
    }));

    // 合併所有收藏：任務 + 助理 + 代理
    return [...favoriteTasks, ...favoriteAssistantsList, ...favoriteAgentsList];
  }, [favoriteAssistants, favoriteAgents, language, updateCounter, t]);

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
          onModelSelect={handleModelSelect}
          onMessageSend={handleMessageSend}
          resultPanelCollapsed={resultPanelCollapsed}
          onResultPanelToggle={() => {
            const newCollapsed = !resultPanelCollapsed;
            setResultPanelCollapsed(newCollapsed);
            if (newCollapsed) {
              setIsMarkdownView(false);
            }
          }}
          onAssistantFavorite={handleAssistantFavorite}
          favoriteAssistants={favoriteAssistants}
          onAgentFavorite={handleAgentFavorite}
          favoriteAgents={favoriteAgents}
          onTaskUpdate={(updatedTask: Task) => {
            setSelectedTask(updatedTask);
            saveTask(updatedTask, true).catch((error) => {
              console.error('[Home] Failed to save task after update:', error);
            });
          }}
          currentTaskId={selectedTask ? String(selectedTask.id) : undefined}
          onTaskCreate={handleTaskCreate}
          onTaskDelete={handleTaskDelete}
          isPreviewMode={isMarkdownView && !resultPanelCollapsed}
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
            taskId={selectedTask ? String(selectedTask.id) : undefined}
            userId={
              // 修改時間：2025-12-08 08:46:00 UTC+8 - 優先使用 user_id，確保正確從後台加載文件樹
              localStorage.getItem('user_id') || localStorage.getItem('userEmail') || undefined
            }
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

      {/* 修改時間：2025-12-14 14:30:00 (UTC+8) - 檔案編輯預覽 Modal */}
      {editPreviewModal && (
        <FileEditPreviewModal
          isOpen={editPreviewModal.isOpen}
          onClose={() => setEditPreviewModal(null)}
          fileId={editPreviewModal.fileId}
          filename={editPreviewModal.filename}
          requestId={editPreviewModal.requestId}
          taskId={editPreviewModal.taskId}
          onApplied={() => {
            // Apply 成功後，可以觸發檔案樹更新
            window.dispatchEvent(
              new CustomEvent('fileUploaded', {
                detail: {
                  taskId: editPreviewModal.taskId,
                  fileIds: [editPreviewModal.fileId],
                },
              })
            );
          }}
        />
      )}


    </div>
  );
}
