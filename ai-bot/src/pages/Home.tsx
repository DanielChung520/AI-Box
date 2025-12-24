import { useState, useEffect, useMemo, useRef } from 'react';
import { useLanguage } from '../contexts/languageContext';
import Sidebar from '../components/Sidebar';
import ChatArea from '../components/ChatArea';
import ResultPanel from '../components/ResultPanel';
import ExecutorSelectorModal from '../components/ExecutorSelectorModal';
import FileEditPreviewModal from '../components/FileEditPreviewModal';
import { Task, FavoriteItem, FileNode } from '../components/Sidebar';
import { saveTask, deleteTask, getTask, getFavorites } from '../lib/taskStorage';
// 修改時間：2025-12-13 17:28:02 (UTC+8) - 產品級 Chat：串接 /api/v1/chat
// 修改時間：2025-12-21 - 添加流式 Chat 支持
import { chatProduct, chatProductStream, ChatProductMessage } from '../lib/api';
import { parseFileReference, updateDraftFileContent } from '../lib/fileReference';
import { getDocEditState } from '../lib/api';
import { extractTaskTitle } from '../lib/taskTitleUtils'; // 修改時間：2025-12-21 - 導入任務標題提取工具
import '../lib/debugStorage'; // 加載調試工具
import '../lib/checkFiles'; // 加載文件檢查工具

export default function Home() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [resultPanelCollapsed, setResultPanelCollapsed] = useState(false);
  const [isMarkdownView, setIsMarkdownView] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | undefined>(undefined);
  const [isLoadingAI, setIsLoadingAI] = useState(false); // 修改時間：2025-12-21 - AI 回復加載狀態
  const prevResultPanelCollapsedRef = useRef<boolean>(false);
  const { t, updateCounter, language } = useLanguage();

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

    // 修改時間：2025-12-21 - 設置 AI 回復加載狀態
    setIsLoadingAI(true);

    let text = '';
    let fileReferences: Array<any> = [];

    try {
      const parsed = JSON.parse(raw);
      text = String(parsed?.text ?? '').trim();
      fileReferences = Array.isArray(parsed?.fileReferences) ? parsed.fileReferences : [];
    } catch {
      text = String(raw ?? '').trim();
    }

    const now = new Date();
    const timestamp = now.toLocaleString();

    const sessionId =
      selectedTask.executionConfig?.sessionId || generateSessionId();
    const modelId = selectedTask.executionConfig?.modelId || 'auto';

    const userMessage = {
      id: `msg-${Date.now()}-user`,
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
    saveTask(taskWithUserMessage, true).catch((error) => {
      console.error('[Home] Failed to save task after user message:', error);
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

      try {
        const resp = await chatProduct({
          messages: chatMessages,
          session_id: sessionId,
          task_id: String(taskWithUserMessage.id),
          model_selector,
          attachments: attachments.length ? attachments : undefined,
        });

        if (resp?.success && resp.data?.content !== undefined) {
          const aiMessage = {
            id: `msg-${Date.now()}-ai`,
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
            id: `msg-${Date.now()}-ai-edit-action`,
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

          // 修改時間：2025-12-21 - AI 回復完成，清除加載狀態
          setIsLoadingAI(false);
          return; // 提前返回，不執行後續的正式檔案處理
        }
      } catch (error: any) {
        console.error('[Home] chatProduct request failed for draft edit:', error);
        // 如果失敗，清除加載狀態並繼續執行正常的流程
        setIsLoadingAI(false);
      }
    }

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

    try {
      // 修改時間：2025-12-21 - 使用流式 API
      // 創建初始 AI 消息（內容為空，將逐步更新）
      const aiMessageId = `msg-${Date.now()}-ai`;
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

      // 使用流式 API 接收內容
      let fullContent = '';
      try {
        for await (const event of chatProductStream({
          messages: chatMessages,
          session_id: sessionId,
          task_id: String(taskWithUserMessage.id),
          model_selector,
          attachments: attachments.length ? attachments : undefined,
        })) {
          if (event.type === 'content' && event.data?.chunk) {
            // 累積內容並更新消息
            fullContent += event.data.chunk;
            const updatedAiMessage = {
              ...initialAiMessage,
              content: fullContent,
            };
            const updatedTask: Task = {
              ...taskWithUserMessage,
              messages: [...(taskWithUserMessage.messages || []), updatedAiMessage],
            };
            setSelectedTask(updatedTask);
          } else if (event.type === 'error') {
            // 處理錯誤
            const errorMessage = {
              id: aiMessageId,
              sender: 'ai' as const,
              content: `Chat failed: ${event.data?.error || 'unknown error'}`,
              timestamp: new Date().toLocaleString(),
            };
            const errorTask: Task = {
              ...taskWithUserMessage,
              messages: [...(taskWithUserMessage.messages || []), errorMessage],
            };
            setSelectedTask(errorTask);
            setIsLoadingAI(false);
            return;
          } else if (event.type === 'done') {
            // 流結束
            break;
          }
        }
      } catch (streamError: any) {
        console.error('[Home] Streaming error:', streamError);
        const errorMessage = {
          id: aiMessageId,
          sender: 'ai' as const,
          content: `Chat failed: ${streamError?.message || 'streaming error'}`,
          timestamp: new Date().toLocaleString(),
        };
        const errorTask: Task = {
          ...taskWithUserMessage,
          messages: [...(taskWithUserMessage.messages || []), errorMessage],
        };
        setSelectedTask(errorTask);
        setIsLoadingAI(false);
        return;
      }

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
        ...taskWithUserMessage,
        title: finalTaskTitle, // 使用提取的標題
        messages: [
          ...(taskWithUserMessage.messages || []),
          aiMessage,
        ],
      };

      setSelectedTask(finalTask);
      saveTask(finalTask, true).catch((error) => {
        console.error('[Home] Failed to save task after ai message:', error);
      });

      // 修改時間：2025-12-21 - AI 回復完成，清除加載狀態
      setIsLoadingAI(false);

      // 修改時間：2025-12-21 - 如果標題已更新，觸發任務列表更新事件，以便 Sidebar 顯示新標題
      if (isFirstConversation && finalTaskTitle !== taskWithUserMessage.title) {
        window.dispatchEvent(new CustomEvent('taskUpdated', {
          detail: { taskId: finalTask.id, title: finalTaskTitle }
        }));
      }

        // 修改時間：2025-12-21 - 流式 API 暫時不返回 actions，暫時註釋
        /*
        // 若有新建檔案，通知 FileTree 重新載入
        if (fileCreated?.file_id) {
          window.dispatchEvent(
            new CustomEvent('fileUploaded', {
              detail: {
                taskId: String(taskWithUserMessage.id),
                fileIds: [String(fileCreated.file_id)],
              },
            })
          );
        }

        // 若有編輯檔案（草稿檔），通知 FileTree 更新
        if (fileEdited?.is_draft && fileEdited?.file_id) {
          window.dispatchEvent(
            new CustomEvent('draftFileContentUpdated', {
              detail: {
                draftId: fileEdited.file_id,
                filename: fileEdited.filename,
                taskId: fileEdited.task_id || String(taskWithUserMessage.id),
              },
            })
          );
        }
        */
    } catch (error: any) {
      console.error('[Home] chatProduct request failed:', error);
      const errorMessage = {
        id: `msg-${Date.now()}-ai-error`,
        sender: 'ai' as const,
        content: `Chat failed: ${error?.message || 'network error'}`,
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

      // 修改時間：2025-12-21 - AI 回復完成（異常情況），清除加載狀態
      setIsLoadingAI(false);
    }
  };

  // 修改時間：2025-12-08 09:04:21 UTC+8 - 任務保存時同步到後台
  // 處理任務創建（用於文件上傳時創建新任務）
  const handleTaskCreate = (task: Task) => {
    setSelectedTask(task);
    // 保存任務到 localStorage 並同步到後台（異步執行，不阻塞）
    saveTask(task, true).catch((error) => {
      console.error('[Home] Failed to save task:', error);
    });
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

    return () => {
      window.removeEventListener('filesUploaded', handleFilesUploadedEvent as EventListener);
      window.removeEventListener('mockFilesUploaded', handleMockFilesUploaded as EventListener);
      window.removeEventListener('fileTreeUpdated', handleFileTreeUpdated as EventListener);
      window.removeEventListener('filesReordered', handleFilesReordered as EventListener);
      window.removeEventListener('fileEditPreviewReady', handleFileEditPreviewReady as EventListener);
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
          isLoadingAI={isLoadingAI} // 修改時間：2025-12-21 - 傳遞 AI 回復加載狀態
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
            // 同步保存，確保 executionConfig/modelId/sessionId 等欄位不丟失
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
            taskId={(() => {
              // 邏輯說明：
              // 1. 如果任務已經有 fileTree（從 prop 傳入），不傳遞 taskId，FileTree 會使用 fileTree prop
              // 2. 如果任務沒有 fileTree 但需要從後端獲取，傳遞 taskId
              // 3. 新任務（剛創建，沒有文件、沒有消息、標題為"新任務"）不傳遞 taskId，避免不必要的 API 調用
              if (!selectedTask) {
                return undefined;
              }

              // 如果已經有 fileTree，不調用 API，使用 prop
              if (selectedTask.fileTree?.length) {
                return undefined;
              }

              // 檢查是否為新任務：標題為"新任務"且沒有消息和文件
              const isNewTask = (
                (selectedTask.title === '新任務' || selectedTask.title === '新任务' || selectedTask.title === 'New Task') &&
                (!selectedTask.messages || selectedTask.messages.length === 0) &&
                (!selectedTask.fileTree || selectedTask.fileTree.length === 0)
              );

              if (isNewTask) {
                return undefined;
              }

              // 其他情況都傳遞 taskId，讓 FileTree 從後端獲取文件
              return String(selectedTask.id);
            })()}
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
