/**
 * 代碼功能說明: AI 聊天輸入框組件, 包含代理, 助理, 模型選擇器
 * 創建日期: 2025-01-27
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-06
 */

import { useState, useRef, useEffect, useMemo } from 'react';
import { useLanguage } from '../contexts/languageContext';
import { createPortal } from 'react-dom';
import FileUploadModal, { FileWithMetadata } from './FileUploadModal';
import UploadProgress from './UploadProgress';
import { uploadFiles } from '../lib/api';
import { Task } from './Sidebar';

// 從 localStorage 讀取收藏數據的輔助函數
const loadFavoritesFromStorage = (key: string): Map<string, string> => {
  try {
    const saved = localStorage.getItem(key);
    if (saved) {
      const data = JSON.parse(saved);
      // 兼容舊格式（數組）
      if (Array.isArray(data)) {
        return new Map<string, string>();
      }
      // 新格式（對象）
      return new Map(Object.entries(data));
    }
  } catch (error) {
    console.error(`Error loading favorites from localStorage (${key}):`, error);
  }
  return new Map<string, string>();
};

// 從 localStorage 讀取選中狀態
const loadSelectedFromStorage = (key: string): string | undefined => {
  try {
    const saved = localStorage.getItem(key);
    return saved || undefined;
  } catch (error) {
    console.error(`Error loading selected from localStorage (${key}):`, error);
    return undefined;
  }
};

// 保存選中狀態到 localStorage
const saveSelectedToStorage = (key: string, value: string | undefined): void => {
  try {
    if (value) {
      localStorage.setItem(key, value);
    } else {
      localStorage.removeItem(key);
    }
  } catch (error) {
    console.error(`Error saving selected to localStorage (${key}):`, error);
  }
};

interface Agent {
  id: string;
  name: string;
  description: string;
  icon: string;
  status: 'registering' | 'online' | 'maintenance' | 'deprecated';
  usageCount: number;
}

interface Assistant {
  id: string;
  name: string;
  description: string;
  icon: string;
  status: 'registering' | 'online' | 'maintenance' | 'deprecated';
  usageCount: number;
}

interface ChatInputProps {
  agents?: Agent[];
  assistants?: Assistant[];
  onAgentSelect?: (agentId: string) => void;
  onAssistantSelect?: (assistantId: string) => void;
  onModelSelect?: (modelId: string) => void;
  selectedAgentId?: string;
  selectedAssistantId?: string;
  selectedModelId?: string;
  onMessageSend?: (message: string) => void;
  onTaskTitleGenerate?: (title: string) => void;
  currentTaskId?: string; // 當前任務ID，用於文件上傳
  selectedTask?: Task; // 當前選中的任務，用於判斷是否為新任務
  onTaskCreate?: (task: Task) => void; // 創建任務回調
  onTaskDelete?: (taskId: number) => void; // 刪除任務回調
}

export default function ChatInput({
  agents = [],
  assistants = [],
  onAgentSelect,
  onAssistantSelect,
  onModelSelect,
  selectedAgentId: selectedAgentIdProp,
  selectedAssistantId: selectedAssistantIdProp,
  selectedModelId: selectedModelIdProp = 'auto',
  onMessageSend,
  onTaskTitleGenerate,
  currentTaskId,
  selectedTask,
  onTaskCreate,
  onTaskDelete,
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [showAssistantSelector, setShowAssistantSelector] = useState(false);
  const [showAgentSelector, setShowAgentSelector] = useState(false);
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [showMentionMenu, setShowMentionMenu] = useState(false);
  const [assistantPosition, setAssistantPosition] = useState<{ top: number; left: number; width: number } | null>(null);
  const [agentPosition, setAgentPosition] = useState<{ top: number; left: number; width: number } | null>(null);
  const [modelPosition, setModelPosition] = useState<{ top: number; left: number; width: number } | null>(null);
  const assistantSelectorRef = useRef<HTMLDivElement>(null);
  const agentSelectorRef = useRef<HTMLDivElement>(null);
  const modelSelectorRef = useRef<HTMLDivElement>(null);
  const mentionMenuRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { t } = useLanguage();

  // 從 localStorage 讀取收藏數據
  const [favoriteAgents, setFavoriteAgents] = useState<Map<string, string>>(() => loadFavoritesFromStorage('favoriteAgents'));
  const [favoriteAssistants, setFavoriteAssistants] = useState<Map<string, string>>(() => loadFavoritesFromStorage('favoriteAssistants'));

  // 使用 ref 跟踪用户是否手动选择过（防止 prop 覆盖用户选择）
  const hasUserSelectedAgent = useRef(false);
  const hasUserSelectedAssistant = useRef(false);
  const hasUserSelectedModel = useRef(false);

  // 選中狀態：優先使用 prop，如果沒有則不從 localStorage 讀取，不設置默認值
  // 未選取時顯示"選擇代理"和"選擇助理"
  const [selectedAgentId, setSelectedAgentId] = useState<string | undefined>(() => {
    // 只使用 prop，不使用 localStorage（避免显示之前的选择）
    return selectedAgentIdProp;
  });
  const [selectedAssistantId, setSelectedAssistantId] = useState<string | undefined>(() => {
    // 只使用 prop，不使用 localStorage（避免显示之前的选择）
    return selectedAssistantIdProp;
  });
  const [selectedModelId, setSelectedModelId] = useState<string>(() => {
    const saved = loadSelectedFromStorage('selectedModelId');
    return selectedModelIdProp ?? saved ?? 'auto';
  });

  // 文件上傳相關狀態
  const [showFileUploadModal, setShowFileUploadModal] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState<FileWithMetadata[]>([]);

  // 不再需要初始化默认值

  // 當 prop 變化時更新狀態（但不要覆蓋用戶的選擇）
  // 只在用戶還沒有選擇過，且 prop 有值時，才更新內部狀態
  // 重要：如果 prop 变为 undefined（新任务），重置用户选择标志
  useEffect(() => {
    // 如果 prop 变为 undefined（新任务），重置用户选择标志
    if (selectedAgentIdProp === undefined) {
      if (hasUserSelectedAgent.current) {
        hasUserSelectedAgent.current = false;
      }
      if (selectedAgentId !== undefined) {
        setSelectedAgentId(undefined);
      }
      return;
    }

    // 如果用户已经选择过，完全忽略 prop 更新
    if (hasUserSelectedAgent.current) {
      return;
    }

    // 只在 prop 有值且与当前状态不同时才更新
    if (selectedAgentIdProp !== selectedAgentId) {
      setSelectedAgentId(selectedAgentIdProp);
    }
  }, [selectedAgentIdProp, selectedAgentId]);

  useEffect(() => {
    // 如果 prop 变为 undefined（新任务），重置用户选择标志
    if (selectedAssistantIdProp === undefined) {
      if (hasUserSelectedAssistant.current) {
        hasUserSelectedAssistant.current = false;
      }
      if (selectedAssistantId !== undefined) {
        setSelectedAssistantId(undefined);
      }
      return;
    }

    if (hasUserSelectedAssistant.current) {
      return;
    }

    if (selectedAssistantIdProp !== selectedAssistantId) {
      setSelectedAssistantId(selectedAssistantIdProp);
    }
  }, [selectedAssistantIdProp, selectedAssistantId]);

  useEffect(() => {
    if (hasUserSelectedModel.current) {
      return;
    }
    if (selectedModelIdProp !== undefined && selectedModelIdProp !== selectedModelId) {
      setSelectedModelId(selectedModelIdProp);
      saveSelectedToStorage('selectedModelId', selectedModelIdProp);
    }
  }, [selectedModelIdProp, selectedModelId]);

  // 監聽 localStorage 變化（跨窗口和同窗口）
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'favoriteAgents' && e.newValue) {
        try {
          const data = JSON.parse(e.newValue);
          if (!Array.isArray(data)) {
            setFavoriteAgents(new Map(Object.entries(data)));
          }
        } catch (error) {
          console.error('Error parsing favoriteAgents from storage event:', error);
        }
      } else if (e.key === 'favoriteAssistants' && e.newValue) {
        try {
          const data = JSON.parse(e.newValue);
          if (!Array.isArray(data)) {
            setFavoriteAssistants(new Map(Object.entries(data)));
          }
        } catch (error) {
          console.error('Error parsing favoriteAssistants from storage event:', error);
        }
      }
      // 不再监听 selectedAgentId、selectedAssistantId、selectedModelId 的 storage 事件
      // 这些值应该只从 props 获取，不依赖 localStorage
    };

    const handleFavoriteUpdate = (e: CustomEvent) => {
      if (e.detail?.type === 'favoriteAgents') {
        setFavoriteAgents(loadFavoritesFromStorage('favoriteAgents'));
      } else if (e.detail?.type === 'favoriteAssistants') {
        setFavoriteAssistants(loadFavoritesFromStorage('favoriteAssistants'));
      }
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('favoritesUpdated' as any, handleFavoriteUpdate as EventListener);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('favoritesUpdated' as any, handleFavoriteUpdate as EventListener);
    };
  }, [selectedAgentId, selectedAssistantId, selectedModelId]);

  // 計算下拉菜單位置
  const calculatePosition = (ref: React.RefObject<HTMLDivElement>, width: number) => {
    if (!ref.current) return null;
    const rect = ref.current.getBoundingClientRect();
    return {
      top: rect.top - 4,
      left: rect.left,
      width: width,
    };
  };

  // LLM 模型列表
  const llmModels = useMemo(() => [
    { id: 'auto', name: t('chatInput.model.auto', 'Auto'), provider: 'auto' },
    { id: 'smartq-iee', name: t('chatInput.model.smartqIEE', 'SmartQ IEE'), provider: 'smartq' },
    { id: 'smartq-hci', name: t('chatInput.model.smartqHCI', 'SmartQ HCI'), provider: 'smartq' },
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

  // 更新下拉菜單位置
  useEffect(() => {
    if (showAssistantSelector && assistantSelectorRef.current) {
      setAssistantPosition(calculatePosition(assistantSelectorRef, 192));
    }
    if (showAgentSelector && agentSelectorRef.current) {
      setAgentPosition(calculatePosition(agentSelectorRef, 256));
    }
    if (showModelSelector && modelSelectorRef.current) {
      setModelPosition(calculatePosition(modelSelectorRef, 224));
    }
  }, [showAssistantSelector, showAgentSelector, showModelSelector]);

  // 點擊外部關閉下拉菜單
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;

      // 检查是否点击在下拉菜单内部（通过查找包含 data-dropdown 属性的元素）
      const clickedDropdown = (target as Element)?.closest?.('[data-dropdown]');

      // 检查是否点击在按钮或按钮容器内
      const clickedButton =
        (assistantSelectorRef.current && assistantSelectorRef.current.contains(target)) ||
        (agentSelectorRef.current && agentSelectorRef.current.contains(target)) ||
        (modelSelectorRef.current && modelSelectorRef.current.contains(target));

      // 如果点击在下拉菜单内或按钮上，不关闭
      if (clickedDropdown || clickedButton) {
        return;
      }

      // 否则关闭所有下拉菜单
      if (showAssistantSelector) {
        setShowAssistantSelector(false);
        setAssistantPosition(null);
      }
      if (showAgentSelector) {
        setShowAgentSelector(false);
        setAgentPosition(null);
      }
      if (showModelSelector) {
        setShowModelSelector(false);
        setModelPosition(null);
      }
      if (mentionMenuRef.current && !mentionMenuRef.current.contains(target)) {
        setShowMentionMenu(false);
      }
    };

    const handleScroll = () => {
      if (showAssistantSelector && assistantSelectorRef.current) {
        setAssistantPosition(calculatePosition(assistantSelectorRef, 192));
      }
      if (showAgentSelector && agentSelectorRef.current) {
        setAgentPosition(calculatePosition(agentSelectorRef, 256));
      }
      if (showModelSelector && modelSelectorRef.current) {
        setModelPosition(calculatePosition(modelSelectorRef, 224));
      }
    };

    const handleResize = () => {
      if (showAssistantSelector && assistantSelectorRef.current) {
        setAssistantPosition(calculatePosition(assistantSelectorRef, 192));
      }
      if (showAgentSelector && agentSelectorRef.current) {
        setAgentPosition(calculatePosition(agentSelectorRef, 256));
      }
      if (showModelSelector && modelSelectorRef.current) {
        setModelPosition(calculatePosition(modelSelectorRef, 224));
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('scroll', handleScroll, true);
    window.addEventListener('resize', handleResize);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('scroll', handleScroll, true);
      window.removeEventListener('resize', handleResize);
    };
  }, [showAssistantSelector, showAgentSelector, showModelSelector]);

  // 監聽輸入框中的 @ 符號
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const handleInput = (e: Event) => {
      const target = e.target as HTMLTextAreaElement;
      const cursorPos = target.selectionStart;
      const textBeforeCursor = target.value.substring(0, cursorPos);
      const lastAt = textBeforeCursor.lastIndexOf('@');

      if (lastAt !== -1 && lastAt === cursorPos - 1) {
        setShowMentionMenu(true);
      } else if (lastAt !== -1) {
        const textAfterAt = textBeforeCursor.substring(lastAt + 1);
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

  // 提及選項
  const mentionOptions = useMemo(() => [
    { id: 'file', label: t('chatInput.mention.file', '文件'), icon: 'fa-file', description: t('chatInput.mention.fileDesc', '提及文件') },
    { id: 'code', label: t('chatInput.mention.code', '代碼'), icon: 'fa-code', description: t('chatInput.mention.codeDesc', '提及代碼片段') },
    { id: 'context', label: t('chatInput.mention.context', '上下文'), icon: 'fa-layer-group', description: t('chatInput.mention.contextDesc', '提及上下文') },
    { id: 'variable', label: t('chatInput.mention.variable', '變量'), icon: 'fa-tag', description: t('chatInput.mention.variableDesc', '提及變量') },
    { id: 'function', label: t('chatInput.mention.function', '函數'), icon: 'fa-function', description: t('chatInput.mention.functionDesc', '提及函數') },
  ], [t]);

  // 插入提及到輸入框
  const insertMention = (option: { id: string; label: string; icon: string; description: string }) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const cursorPos = textarea.selectionStart;
    const textBeforeCursor = textarea.value.substring(0, cursorPos);
    const textAfterCursor = textarea.value.substring(cursorPos);
    const lastAt = textBeforeCursor.lastIndexOf('@');

    if (lastAt !== -1) {
      const newText = textarea.value.substring(0, lastAt) + `@${option.label} ` + textAfterCursor;
      setMessage(newText);

      setTimeout(() => {
        const newCursorPos = lastAt + option.label.length + 2;
        textarea.setSelectionRange(newCursorPos, newCursorPos);
        textarea.focus();
      }, 0);
    } else {
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

  // 處理 @ 按鈕點擊
  const handleMentionClick = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      const cursorPos = textarea.selectionStart;
      const textBeforeCursor = textarea.value.substring(0, cursorPos);
      const textAfterCursor = textarea.value.substring(cursorPos);

      setMessage(textBeforeCursor + '@' + textAfterCursor);

      setTimeout(() => {
        textarea.setSelectionRange(cursorPos + 1, cursorPos + 1);
        textarea.focus();
        setShowMentionMenu(true);
      }, 0);
    }
  };

  // 固定的代理選項列表（僅 Auto）
  const fixedAgents = useMemo(() => [
    { id: 'auto', name: t('chatInput.agent.auto', 'Auto'), icon: 'fa-magic', description: t('chatInput.agent.autoDesc', '自動選擇代理') },
  ], [t]);

  // 從 localStorage 讀取的收藏代理列表
  const favoriteAgentsList = useMemo(() => {
    if (!agents || agents.length === 0 || favoriteAgents.size === 0) {
      return [];
    }
    const filtered = agents.filter(agent => favoriteAgents.has(agent.id));
    return filtered;
  }, [agents, favoriteAgents]);

  // 從 localStorage 讀取的收藏助理列表
  const favoriteAssistantsList = useMemo(() => {
    if (!assistants || assistants.length === 0 || favoriteAssistants.size === 0) {
      return [];
    }
    const filtered = assistants.filter(assistant => favoriteAssistants.has(assistant.id));
    return filtered;
  }, [assistants, favoriteAssistants]);

  // 獲取選中的代理名稱
  const selectedAgentName = useMemo(() => {
    if (!selectedAgentId) {
      return t('chatInput.selectAgent', '選擇代理');
    }

    // 先檢查固定代理
    const fixedAgent = fixedAgents.find(a => a.id === selectedAgentId);
    if (fixedAgent) {
      return fixedAgent.name;
    }

    // 再檢查收藏的代理列表
    const favoriteAgent = favoriteAgentsList.find(a => a.id === selectedAgentId);
    if (favoriteAgent) {
      return favoriteAgent.name;
    }

    // 最後檢查所有代理列表
    const agent = agents.find(a => a.id === selectedAgentId);
    if (agent) {
      return agent.name;
    }

    return t('chatInput.selectAgent', '選擇代理');
  }, [selectedAgentId, fixedAgents, favoriteAgentsList, agents, t]);

  // 獲取選中的助理名稱
  const selectedAssistantName = useMemo(() => {
    if (!selectedAssistantId) {
      return t('chatInput.selectAssistant', '選擇助理');
    }

    // 先檢查收藏的助理列表
    const favoriteAssistant = favoriteAssistantsList.find(a => a.id === selectedAssistantId);
    if (favoriteAssistant) {
      return favoriteAssistant.name;
    }

    // 再檢查所有助理列表
    const assistant = assistants.find(a => a.id === selectedAssistantId);
    if (assistant) {
      return assistant.name;
    }

    return t('chatInput.selectAssistant', '選擇助理');
  }, [selectedAssistantId, favoriteAssistantsList, assistants, t]);

  // 獲取選中的模型名稱
  const selectedModel = llmModels.find(m => m.id === selectedModelId);
  const selectedModelName = selectedModel ? selectedModel.name : t('chatInput.model.auto', 'Auto');

  // 跟踪选中状态变化（已移除調試日誌）

  // 處理代理選擇
  const handleAgentSelect = (agentId: string) => {

    hasUserSelectedAgent.current = true; // 标记用户已选择
    setSelectedAgentId(agentId);
    saveSelectedToStorage('selectedAgentId', agentId);


    onAgentSelect?.(agentId);
    setShowAgentSelector(false);
    setAgentPosition(null);

    // 验证状态更新（使用闭包捕获最新的 agentId）
    const capturedAgentId = agentId;
    setTimeout(() => {
    }, 100);
  };

  // 處理助理選擇
  const handleAssistantSelect = (assistantId: string) => {

    hasUserSelectedAssistant.current = true; // 标记用户已选择
    setSelectedAssistantId(assistantId);
    // 不再保存到 localStorage，只通过 props 传递


    onAssistantSelect?.(assistantId);
    setShowAssistantSelector(false);
    setAssistantPosition(null);

    // 验证状态更新（使用闭包捕获最新的 assistantId）
    const capturedAssistantId = assistantId;
    setTimeout(() => {
    }, 100);
  };

  // 處理模型選擇
  const handleModelSelect = (modelId: string) => {

    hasUserSelectedModel.current = true; // 标记用户已选择
    setSelectedModelId(modelId);
    saveSelectedToStorage('selectedModelId', modelId);


    onModelSelect?.(modelId);
    setShowModelSelector(false);
    setModelPosition(null);

    // 验证状态更新（使用闭包捕获最新的 modelId）
    const capturedModelId = modelId;
    setTimeout(() => {
    }, 100);
  };

  const handleSend = () => {
    if (message.trim()) {
      const messageText = message.trim();

      // 发送消息
      onMessageSend?.(messageText);

      // 如果是第一条消息，自动生成任务标题（从消息内容中提取前30个字符）
      if (onTaskTitleGenerate) {
        // 生成任务标题：取消息的前30个字符，如果超过则添加省略号
        const title = messageText.length > 30
          ? messageText.substring(0, 30) + '...'
          : messageText;
        onTaskTitleGenerate(title);
      }

      setMessage('');
    }
  };

  // 文件上傳處理函數
  const handlePaperclipClick = () => {
    setShowFileUploadModal(true);
  };

  const handleFileUpload = async (files: File[], taskId?: string) => {
    if (files.length === 0) return;

    // 檢查是否為新任務：
    // 1. 必須有 selectedTask
    // 2. 任務標題必須是"新任務"（表示是剛創建的空白任務）
    // 3. 沒有消息和文件
    const isNewTask = selectedTask &&
      (selectedTask.title === '新任務' || selectedTask.title === '新任务' || selectedTask.title === 'New Task') &&
      (!selectedTask.messages || selectedTask.messages.length === 0) &&
      (!selectedTask.fileTree || selectedTask.fileTree.length === 0);

    let createdTaskId: number | null = null;
    let createdTask: Task | null = null;

    // 如果是新任務，創建任務並使用第一個文件名作為任務名稱
    if (isNewTask && onTaskCreate && selectedTask) {
      const firstFileName = files[0]?.name || '新任務';
      // 移除文件擴展名作為任務名稱
      const taskTitle = firstFileName.replace(/\.[^/.]+$/, '') || '新任務';

      createdTask = {
        ...selectedTask,
        id: Date.now(), // 生成新的任務ID
        title: taskTitle,
        fileTree: [], // 初始化文件樹
      };

      createdTaskId = createdTask.id;
      onTaskCreate(createdTask);
    }

    // 創建文件元數據
    const filesWithMetadata: FileWithMetadata[] = files.map((file) => ({
      file,
      id: `${Date.now()}-${Math.random()}`,
      status: 'pending',
      progress: 0,
    }));

    setUploadingFiles(filesWithMetadata);

    // 確定要使用的任務ID：
    // 1. 如果是新任務且已創建，使用新創建的任務ID
    // 2. 如果已有選中的任務（不是新任務），使用現有任務ID
    // 3. 否則使用傳遞的 taskId 或默認的 "temp-workspace"
    const finalTaskId = createdTaskId
      ? String(createdTaskId)
      : (selectedTask && !isNewTask
          ? String(selectedTask.id)
          : (taskId || 'temp-workspace'));

    try {
      // 更新所有文件狀態為上傳中
      setUploadingFiles((prev) =>
        prev.map((f) => ({ ...f, status: 'uploading' }))
      );

      const response = await uploadFiles(files, (progress) => {
        // 更新總體進度到所有文件
        setUploadingFiles((prev) =>
          prev.map((f) => ({ ...f, progress }))
        );
      }, finalTaskId);

      // 處理上傳結果
      if (response.success && response.data) {
        const uploadedMap = new Map(
          response.data.uploaded?.map((u) => [u.filename, u]) || []
        );
        const errorsMap = new Map(
          response.data.errors?.map((e) => [e.filename, e.error]) || []
        );

        // 更新每個文件的狀態
        setUploadingFiles((prev) =>
          prev.map((f) => {
            if (uploadedMap.has(f.file.name)) {
              return { ...f, status: 'success', progress: 100 };
            } else if (errorsMap.has(f.file.name)) {
              return {
                ...f,
                status: 'error',
                error: errorsMap.get(f.file.name) || '上傳失敗',
              };
            } else {
              return {
                ...f,
                status: 'error',
                error: '未知錯誤',
              };
            }
          })
        );

        // 觸發文件上傳完成事件，通知文件管理頁面刷新
        window.dispatchEvent(new CustomEvent('fileUploaded', {
          detail: { fileIds: response.data.uploaded?.map((u: any) => u.file_id) || [] }
        }));

        // 觸發文件樹更新事件，通知父組件更新文件樹（真實上傳成功）
        if (response.data.uploaded && response.data.uploaded.length > 0) {
          // 記錄上傳成功的文件 ID
          response.data.uploaded.forEach((u: any) => {
            console.log(`File uploaded - file_id: ${u.file_id}`);
          });

          window.dispatchEvent(new CustomEvent('filesUploaded', {
            detail: {
              taskId: finalTaskId,
              files: response.data.uploaded.map((u: any) => ({
                file_id: u.file_id,
                filename: u.filename,
                file_type: u.file_type,
                file_size: u.file_size,
              }))
            }
          }));
        }

        // 所有文件處理完成後，等待3秒後清除（給用戶時間查看結果）
        setTimeout(() => {
          setUploadingFiles([]);
        }, 3000);
      } else {
        // 整體失敗
        setUploadingFiles((prev) =>
          prev.map((f) => ({
            ...f,
            status: 'error',
            error: response.message || response.error || '上傳失敗',
          }))
        );
      }
    } catch (error: any) {
      console.error('File upload error:', error);

      // 如果後端不可用，嘗試使用模擬文件上傳
      if (error.message?.includes('網絡錯誤') || error.message?.includes('ERR_CONNECTION_TIMED_OUT') || error.message?.includes('Failed to fetch')) {

        try {
          const { uploadMockFiles } = await import('../lib/mockFileStorage');
          const userId = localStorage.getItem('userEmail') || undefined;
          const result = await uploadMockFiles(files, String(finalTaskId), userId);

          // 更新文件狀態
          setUploadingFiles((prev) =>
            prev.map((f) => {
              const uploaded = result.uploaded.find((u) => u.filename === f.file.name);
              const error = result.errors.find((e) => e.filename === f.file.name);

              if (uploaded) {
                return { ...f, status: 'success', progress: 100 };
              } else if (error) {
                return { ...f, status: 'error', error: error.error };
              } else {
                return { ...f, status: 'error', error: '上傳失敗' };
              }
            })
          );

          // 觸發文件上傳完成事件
          window.dispatchEvent(new CustomEvent('fileUploaded', {
            detail: { fileIds: result.uploaded.map((u) => u.file_id) }
          }));

          // 記錄上傳成功的文件 ID
          result.uploaded.forEach((u) => {
            console.log(`File uploaded - file_id: ${u.file_id}`);
          });

          // 觸發文件樹更新事件，通知父組件更新文件樹
          window.dispatchEvent(new CustomEvent('mockFilesUploaded', {
            detail: { taskId: finalTaskId, files: result.uploaded }
          }));

          // 所有文件處理完成後，等待3秒後清除
          setTimeout(() => {
            setUploadingFiles([]);
          }, 3000);

          // 模擬上傳成功，不需要繼續處理錯誤
          return;
        } catch (mockError: any) {
          console.error('Mock file upload error:', mockError);
          // 如果模擬上傳也失敗，繼續執行下面的錯誤處理
          // 如果是新任務且模擬上傳失敗，清除任務
          if (isNewTask && createdTaskId && onTaskDelete) {
            onTaskDelete(createdTaskId);
          }
        }
      }

      // 處理錯誤（只有在不是網絡錯誤或模擬上傳失敗時才執行）
      setUploadingFiles((prev) =>
        prev.map((f) => ({
          ...f,
          status: 'error',
          error: error.message || '上傳失敗',
        }))
      );

      // 如果是新任務且上傳失敗，清除任務
      if (isNewTask && createdTaskId && onTaskDelete) {
        onTaskDelete(createdTaskId);
      }
    }
  };

  const handleCancelUpload = (fileId: string) => {
    // TODO: 實現取消上傳功能
    setUploadingFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  const handleDismissUpload = (fileId: string) => {
    setUploadingFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="bg-secondary rounded-xl overflow-hidden theme-transition">
      {/* 工具欄 */}
      <div className="flex items-center p-2 border-b border-primary">
        <button
          className="p-2 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
          aria-label="使用互聯網"
        >
          <i className="fa-solid fa-globe"></i>
        </button>
        <button
          className="p-2 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
          aria-label="深度思考"
        >
          <i className="fa-solid fa-brain"></i>
        </button>

        {/* 助理選擇器 */}
        <div className="relative ml-2" ref={assistantSelectorRef}>
          <button
            className="px-3 py-1 rounded bg-tertiary hover:bg-hover transition-colors text-sm flex items-center text-secondary"
            onClick={(e) => {
              e.stopPropagation();
              const newState = !showAssistantSelector;
              setShowAssistantSelector(newState);
              setShowAgentSelector(false);
              setShowModelSelector(false);
              if (newState) {
                setAssistantPosition(calculatePosition(assistantSelectorRef, 192));
              } else {
                setAssistantPosition(null);
              }
            }}
          >
            <i className="fa-solid fa-robot mr-2"></i>
            <span className="max-w-[100px] truncate">{selectedAssistantName}</span>
            <i className={`fa-solid fa-chevron-down ml-2 transition-transform ${showAssistantSelector ? 'rotate-180' : ''}`}></i>
          </button>

          {showAssistantSelector && assistantPosition && createPortal(
            <div
              data-dropdown="assistant"
              className="fixed bg-secondary border border-primary rounded-lg shadow-lg z-[9999] theme-transition max-h-[400px] overflow-y-auto"
              style={{
                top: `${assistantPosition.top}px`,
                left: `${assistantPosition.left}px`,
                width: `${assistantPosition.width}px`,
                transform: 'translateY(-100%)',
                marginBottom: '4px',
              }}
            >
              <div className="p-2 border-b border-primary text-sm font-medium text-primary sticky top-0 bg-secondary">
                {t('chatInput.selectAssistant', '選擇助理')}
              </div>
              {favoriteAssistantsList.length > 0 ? (
                favoriteAssistantsList.map((assistant, index) => {
                  const isSelected = selectedAssistantId === assistant.id;
                  return (
                    <button
                      key={assistant.id}
                      className={`w-full text-left px-4 py-2 text-sm hover:bg-tertiary transition-colors flex items-center ${
                        isSelected ? 'bg-tertiary font-medium' : ''
                      }`}
                      onMouseDown={(e) => {
                        // 使用 onMouseDown 而不是 onClick，确保在 handleClickOutside 之前触发
                        e.stopPropagation();
                        e.preventDefault();
                        handleAssistantSelect(assistant.id);
                      }}
                      onClick={(e) => {
                        // 保留 onClick 作为备用
                        e.stopPropagation();
                        e.preventDefault();
                      }}
                    >
                    <i className={`fa-solid ${assistant.icon} mr-2 ${
                      assistant.status === 'online' ? 'text-green-400' :
                      assistant.status === 'maintenance' ? 'text-yellow-400' :
                      assistant.status === 'deprecated' ? 'text-red-400' :
                      'text-gray-400'
                    }`}></i>
                    <div className="flex-1 min-w-0">
                      <div className="text-secondary truncate">{assistant.name}</div>
                      <div className="text-xs text-tertiary truncate">{assistant.description}</div>
                    </div>
                    {isSelected && (
                      <i className="fa-solid fa-check text-blue-400 ml-2" title="已選中"></i>
                    )}
                  </button>
                  );
                })
              ) : (
                <div className="px-4 py-8 text-center text-tertiary text-sm">
                  {t('chatInput.noFavoriteAssistants', '暫無收藏的助理')}
                </div>
              )}
            </div>,
            document.body
          )}
        </div>

        {/* 代理選擇器 */}
        <div className="relative ml-2" ref={agentSelectorRef}>
          <button
            className="px-3 py-1 rounded bg-tertiary hover:bg-hover transition-colors text-sm flex items-center text-secondary"
            onClick={(e) => {
              e.stopPropagation();
              const newState = !showAgentSelector;
              setShowAgentSelector(newState);
              setShowAssistantSelector(false);
              setShowModelSelector(false);
              if (newState) {
                setAgentPosition(calculatePosition(agentSelectorRef, 256));
              } else {
                setAgentPosition(null);
              }
            }}
          >
            <i className="fa-solid fa-user-tie mr-2"></i>
            <span className="max-w-[100px] truncate">{selectedAgentName}</span>
            <i className={`fa-solid fa-chevron-down ml-2 transition-transform ${showAgentSelector ? 'rotate-180' : ''}`}></i>
          </button>

          {showAgentSelector && agentPosition && createPortal(
            <div
              data-dropdown="agent"
              className="fixed bg-secondary border border-primary rounded-lg shadow-lg z-[9999] theme-transition max-h-[400px] overflow-y-auto"
              style={{
                top: `${agentPosition.top}px`,
                left: `${agentPosition.left}px`,
                width: `${agentPosition.width}px`,
                transform: 'translateY(-100%)',
                marginBottom: '4px',
              }}
            >
              <div className="p-2 border-b border-primary text-sm font-medium text-primary sticky top-0 bg-secondary">
                {t('chatInput.selectAgent', '選擇代理')}
              </div>

              {/* 固定代理選項 */}
              {fixedAgents.map((agent, index) => {
                const isSelected = selectedAgentId === agent.id;
                return (
                  <button
                    key={agent.id}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-tertiary transition-colors flex items-center ${
                      isSelected ? 'bg-tertiary font-medium' : ''
                    }`}
                    onMouseDown={(e) => {
                      // 使用 onMouseDown 而不是 onClick，确保在 handleClickOutside 之前触发
                      e.stopPropagation();
                      e.preventDefault();
                      handleAgentSelect(agent.id);
                    }}
                    onClick={(e) => {
                      // 保留 onClick 作为备用
                      e.stopPropagation();
                      e.preventDefault();
                    }}
                  >
                  <i className={`fa-solid ${agent.icon} mr-2 ${
                    agent.id === 'auto' ? 'text-purple-400' : 'text-gray-400'
                  }`}></i>
                    <div className="flex-1 min-w-0">
                      <div className="text-secondary truncate">{agent.name}</div>
                      <div className="text-xs text-tertiary truncate">{agent.description}</div>
                    </div>
                    {isSelected && (
                      <i className="fa-solid fa-check text-blue-400 ml-2" title="已選中"></i>
                    )}
                  </button>
                );
              })}

              {/* 分隔線（如果有收藏的代理） */}
              {favoriteAgentsList.length > 0 && (
                <>
                  <div className="border-t border-primary my-1"></div>
                  <div className="px-4 py-2 text-xs text-tertiary font-medium">
                    {t('chatInput.agent.favoriteAgents', '收藏的代理')}
                  </div>
                </>
              )}

              {/* 收藏的代理列表 */}
              {favoriteAgentsList.length > 0 ? (
                favoriteAgentsList.map((agent, index) => {
                  const isSelected = selectedAgentId === agent.id;
                  return (
                    <button
                      key={agent.id}
                      className={`w-full text-left px-4 py-2 text-sm hover:bg-tertiary transition-colors flex items-center ${
                        isSelected ? 'bg-tertiary font-medium' : ''
                      }`}
                      onClick={(e) => {
                        e.stopPropagation();
                        e.preventDefault();
                        handleAgentSelect(agent.id);
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
                    {isSelected && (
                      <i className="fa-solid fa-check text-blue-400 ml-2" title="已選中"></i>
                    )}
                  </button>
                  );
                })
              ) : (
                <div className="px-4 py-2 text-xs text-tertiary">
                  {t('chatInput.agent.noFavoriteAgents', '暫無收藏的代理')}
                </div>
              )}
            </div>,
            document.body
          )}
        </div>

        {/* 模型選擇器 */}
        <div className="relative ml-2" ref={modelSelectorRef}>
          <button
            className="px-3 py-1 rounded bg-tertiary hover:bg-hover transition-colors text-sm flex items-center text-secondary"
            onClick={(e) => {
              e.stopPropagation();
              const newState = !showModelSelector;
              setShowModelSelector(newState);
              setShowAssistantSelector(false);
              setShowAgentSelector(false);
              if (newState) {
                setModelPosition(calculatePosition(modelSelectorRef, 224));
              } else {
                setModelPosition(null);
              }
            }}
          >
            <i className="fa-solid fa-brain mr-2"></i>
            <span className="max-w-[120px] truncate">{selectedModelName}</span>
            <i className={`fa-solid fa-chevron-down ml-2 transition-transform ${showModelSelector ? 'rotate-180' : ''}`}></i>
          </button>

          {showModelSelector && modelPosition && createPortal(
            <div
              data-dropdown="model"
              className="fixed bg-secondary border border-primary rounded-lg shadow-lg z-[9999] theme-transition max-h-[400px] overflow-y-auto"
              style={{
                top: `${modelPosition.top}px`,
                left: `${modelPosition.left}px`,
                width: `${modelPosition.width}px`,
                transform: 'translateY(-100%)',
                marginBottom: '4px',
              }}
            >
              <div className="p-2 border-b border-primary text-sm font-medium text-primary sticky top-0 bg-secondary">
                {t('chatInput.selectModel', '選擇模型')}
              </div>
              {llmModels.map((model, index) => {
                const isSelected = selectedModelId === model.id;
                return (
                  <button
                    key={model.id}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-tertiary transition-colors flex items-center ${
                      isSelected ? 'bg-tertiary font-medium' : ''
                    }`}
                    onMouseDown={(e) => {
                      // 使用 onMouseDown 而不是 onClick，确保在 handleClickOutside 之前触发
                      e.stopPropagation();
                      e.preventDefault();
                      handleModelSelect(model.id);
                    }}
                    onClick={(e) => {
                      // 保留 onClick 作为备用
                      e.stopPropagation();
                      e.preventDefault();
                    }}
                  >
                  <i className={`fa-solid ${
                    model.id === 'auto' ? 'fa-magic' :
                    model.id === 'smartq-iee' ? 'fa-microchip' :
                    model.id === 'smartq-hci' ? 'fa-robot' :
                    model.provider === 'chatgpt' ? 'fa-robot' :
                    model.provider === 'gemini' ? 'fa-gem' :
                    model.provider === 'qwen' ? 'fa-code' :
                    model.provider === 'grok' ? 'fa-bolt' :
                    'fa-server'
                  } mr-2 ${
                    model.id === 'auto' ? 'text-purple-400' :
                    model.id === 'smartq-iee' ? 'text-blue-400' :
                    model.id === 'smartq-hci' ? 'text-green-400' :
                    model.provider === 'chatgpt' ? 'text-green-400' :
                    model.provider === 'gemini' ? 'text-blue-400' :
                    model.provider === 'qwen' ? 'text-orange-400' :
                    model.provider === 'grok' ? 'text-yellow-400' :
                    'text-gray-400'
                  }`}></i>
                  <span className="text-secondary flex-1">{model.name}</span>
                  {isSelected && (
                    <i className="fa-solid fa-check text-blue-400 ml-2" title="已選中"></i>
                  )}
                </button>
                );
              })}
            </div>,
            document.body
          )}
        </div>

        <div className="ml-auto flex items-center space-x-1 relative">
          {/* @ 提及按鈕 - 放在回纹针左侧 */}
          <button
            onClick={handleMentionClick}
            className="p-2 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
            title={t('chatInput.mention.title', '提及 (@)')}
            aria-label={t('chatInput.mention.title', '提及 (@)')}
          >
            <span className="text-lg font-semibold">@</span>
          </button>

          {/* 提及菜單 */}
          {showMentionMenu && (
            <div
              ref={mentionMenuRef}
              className="absolute bottom-full right-0 mb-2 w-64 bg-secondary border border-primary rounded-lg shadow-lg z-[9999] theme-transition max-h-80 overflow-y-auto"
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
            onClick={handlePaperclipClick}
            className="p-2 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
            aria-label="上傳文件"
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
            aria-label="語音輸入"
          >
            <i className="fa-solid fa-microphone"></i>
          </button>
        </div>
      </div>

      {/* 輸入框 */}
      <div className="flex items-end p-3 relative">
        <textarea
          ref={textareaRef}
          className="flex-1 bg-transparent border border-primary rounded-lg p-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-primary"
          placeholder={t('chatInput.placeholder', '輸入消息...')}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          rows={3}
        />

        <button
          className="ml-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center"
          onClick={handleSend}
        >
          <span>{t('chatInput.send', '發送')}</span>
          <i className="fa-solid fa-paper-plane ml-2"></i>
        </button>
      </div>

      {/* 文件上傳模態框 */}
      <FileUploadModal
        isOpen={showFileUploadModal}
        onClose={() => setShowFileUploadModal(false)}
        onUpload={handleFileUpload}
        defaultTaskId={currentTaskId || 'temp-workspace'}
      />

      {/* 上傳進度顯示 */}
      {uploadingFiles.length > 0 && (
        <UploadProgress
          files={uploadingFiles}
          onCancel={handleCancelUpload}
          onDismiss={handleDismissUpload}
        />
      )}
    </div>
  );
}
