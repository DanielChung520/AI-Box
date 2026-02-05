/**
 * 代碼功能說明: AI 聊天輸入框組件, 包含代理, 助理, 模型選擇器
 * 創建日期: 2025-01-27
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-25 00:06 UTC+8
 */

import { useState, useRef, useEffect, useMemo, useCallback, useContext } from 'react';
import { useLanguage } from '../contexts/languageContext';
import { AuthContext } from '../contexts/authContext';
import { isSystemAdmin } from '../lib/userUtils';
import { useAIStatusStore } from '../stores/aiStatusStore';
import { createPortal } from 'react-dom';
import AIStatusWindow from './AIStatusWindow';
import FileUploadModal, { FileWithMetadata } from './FileUploadModal';
import UploadProgress from './UploadProgress';
import { uploadFiles, getFavoriteModels, setFavoriteModels, getModels, getModelsByScene, getScenes, type LLMModel, FileMetadata } from '../lib/api';
import { Task } from './Sidebar';
// 修改時間：2025-12-08 10:40:00 UTC+8 - 添加文件引用組件
import FileReference, { FileReferenceData } from './FileReference';
// 修改時間：2026-01-06 - 添加文件選擇器組件
import FileSelector from './FileSelector';
// 修改時間：2026-01-06 - 添加文件編輯狀態組件和 Context
import FileEditStatus from './FileEditStatus';
import { useFileEditing } from '../contexts/fileEditingContext';
import { applyDocEdit } from '../lib/api';
import { toast } from 'sonner';

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

// 保存選中狀態到 localStorage（目前僅保留 agentId 使用）
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

// 修改時間：2025-12-13 17:28:02 (UTC+8) - 收藏模型 localStorage key（與 api.ts 一致）
const FAVORITE_MODELS_STORAGE_KEY = 'ai-box-favorite-models';

const loadFavoriteModelsFromStorage = (): Set<string> => {
  try {
    const raw = localStorage.getItem(FAVORITE_MODELS_STORAGE_KEY);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.map(String));
  } catch (error) {
    console.error('Error loading favorite models from localStorage:', error);
    return new Set();
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
  allowedTools?: string[]; // 可使用的工具列表
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
  // 修改時間：2025-12-08 11:30:00 UTC+8 - 添加預覽模式狀態，用於控制按鈕顯示
  isPreviewMode?: boolean; // 是否處於預覽模式（右側文件預覽展開時為 true）
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
  isPreviewMode = false,
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [showAssistantSelector, setShowAssistantSelector] = useState(false);
  const [showAgentSelector, setShowAgentSelector] = useState(false);
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [showMentionMenu, setShowMentionMenu] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [assistantPosition, setAssistantPosition] = useState<{ top: number; left: number; width: number } | null>(null);
  const [agentPosition, setAgentPosition] = useState<{ top: number; left: number; width: number } | null>(null);
  const [modelPosition, setModelPosition] = useState<{ top: number; left: number; width: number } | null>(null);

  // 上网功能激活状态
  const [isWebSearchActive, setIsWebSearchActive] = useState(false);
  const assistantSelectorRef = useRef<HTMLDivElement>(null);
  const agentSelectorRef = useRef<HTMLDivElement>(null);
  const modelSelectorRef = useRef<HTMLDivElement>(null);
  const mentionMenuRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { t } = useLanguage();
  const { currentUser } = useContext(AuthContext);
  const { currentStatus, toggleWindow, isWindowOpen } = useAIStatusStore();

  // 從 localStorage 讀取收藏數據
  const [favoriteAgents, setFavoriteAgents] = useState<Map<string, string>>(() => loadFavoritesFromStorage('favoriteAgents'));
  const [favoriteAssistants, setFavoriteAssistants] = useState<Map<string, string>>(() => loadFavoritesFromStorage('favoriteAssistants'));
  // 修改時間：2025-12-13 17:28:02 (UTC+8) - 收藏模型（Set）
  const [favoriteModels, setFavoriteModelsState] = useState<Set<string>>(() => loadFavoriteModelsFromStorage());

  // 修改時間：2025-12-21 - 從 API 獲取模型列表
  const [llmModels, setLlmModels] = useState<Array<{ id: string; name: string; provider: string; icon?: string; color?: string }>>([]);
  
  // 修改時間：2026-01-24 - 場景感知相關狀態
  const [currentScene, setCurrentScene] = useState<string>('chat'); // 默認使用 chat 場景
  const [sceneConfig, setSceneConfig] = useState<{ frontend_editable: boolean; user_default?: string | null } | null>(null);
  const [isLoadingSceneModels, setIsLoadingSceneModels] = useState(false);

  // 使用 ref 跟踪用户是否手动选择过（防止 prop 覆盖用户选择）
  const hasUserSelectedAgent = useRef(false);
  const hasUserSelectedAssistant = useRef(false);

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
    // 修改時間：2025-12-13 17:28:02 (UTC+8) - 改為以 task.executionConfig.modelId 為準，避免跨任務污染
    return selectedModelIdProp ?? 'auto';
  });

  // 文件上傳相關狀態
  const [showFileUploadModal, setShowFileUploadModal] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState<FileWithMetadata[]>([]);

  // 修改時間：2025-12-08 10:40:00 UTC+8 - 文件引用相關狀態
  const [fileReferences, setFileReferences] = useState<FileReferenceData[]>([]);

  // 修改時間：2026-01-06 - 文件編輯相關狀態
  const [selectedFile, setSelectedFile] = useState<FileMetadata | null>(null);
  const [isSubmittingEdit, setIsSubmittingEdit] = useState(false);

  // 修改時間：2026-01-06 - 從 Context 獲取文件編輯狀態
  const {
    hasUnsavedChanges,
    currentRequestId,
    acceptChanges,
    rejectChanges,
  } = useFileEditing();

  // 修改時間：2026-01-06 - 當文件選擇變化時，觸發事件
  useEffect(() => {
    if (selectedFile) {
      window.dispatchEvent(new CustomEvent('fileSelectedForEditing', {
        detail: { fileId: selectedFile.file_id }
      }));
    } else {
      window.dispatchEvent(new CustomEvent('fileSelectedForEditing', {
        detail: { fileId: null }
      }));
    }
  }, [selectedFile]);

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

  // 确保 assistants 始终是数组（使用 useMemo 避免每次渲染都重新创建）
  // 同时尝试从 localStorage 获取助理的 allowedTools（如果 assistants 中没有）
  const [assistantToolsCache, setAssistantToolsCache] = useState<Map<string, string[]>>(new Map());

  // 首先创建基础的 safeAssistants（不包含缓存）
  const baseSafeAssistants = useMemo(() => {
    try {
      if (!assistants) {
        return [];
      }
      if (!Array.isArray(assistants)) {
        console.warn('[ChatInput] assistants is not an array:', typeof assistants, assistants);
        return [];
      }
      return assistants;
    } catch (error) {
      console.error('[ChatInput] Error creating baseSafeAssistants:', error);
      return [];
    }
  }, [assistants]);

  // 从 localStorage 加载助理的 allowedTools
  useEffect(() => {
    const loadAssistantTools = () => {
      const cache = new Map<string, string[]>();
      if (baseSafeAssistants && baseSafeAssistants.length > 0) {
        baseSafeAssistants.forEach(assistant => {
          try {
            const storageKey = `assistant_${assistant.id}_allowedTools`;
            const stored = localStorage.getItem(storageKey);
            if (stored) {
              const allowedTools = JSON.parse(stored);
              if (Array.isArray(allowedTools)) {
                cache.set(assistant.id, allowedTools);
              }
            }
          } catch (e) {
            // 忽略 localStorage 错误
          }
        });
      }
      setAssistantToolsCache(cache);
    };

    loadAssistantTools();

    // 监听助理工具更新事件
    const handleToolsUpdate = (event: CustomEvent) => {
      const { assistantId, allowedTools } = event.detail;
      if (assistantId && allowedTools) {
        setAssistantToolsCache(prev => {
          const newCache = new Map(prev);
          newCache.set(assistantId, allowedTools);
          return newCache;
        });
      }
    };

    window.addEventListener('assistantToolsUpdated', handleToolsUpdate as EventListener);
    return () => {
      window.removeEventListener('assistantToolsUpdated', handleToolsUpdate as EventListener);
    };
  }, [baseSafeAssistants]);

  // 合并基础数据和缓存中的 allowedTools
  const safeAssistants = useMemo(() => {
    return baseSafeAssistants.map(assistant => {
      // 如果已经有 allowedTools，直接返回
      if (assistant.allowedTools && Array.isArray(assistant.allowedTools) && assistant.allowedTools.length > 0) {
        return assistant;
      }

      // 尝试从缓存中获取
      const cachedTools = assistantToolsCache.get(assistant.id);
      if (cachedTools && Array.isArray(cachedTools) && cachedTools.length > 0) {
        return { ...assistant, allowedTools: cachedTools };
      }

      return assistant;
    });
  }, [baseSafeAssistants, assistantToolsCache]);

  // 当助理切换时，检查是否支持 web_search，如果不支持则取消激活
  useEffect(() => {
    try {
      // 使用函数式更新，避免依赖 isWebSearchActive
      setIsWebSearchActive((prevActive) => {
        try {
          // 如果当前未激活，不需要检查
          if (!prevActive) {
            return prevActive;
          }

          // 如果没有选中助理，取消激活
          if (!selectedAssistantId) {
            return false;
          }

          // 检查 safeAssistants 是否有效
          if (!safeAssistants || !Array.isArray(safeAssistants) || safeAssistants.length === 0) {
            return false;
          }

          // 查找选中的助理
          const selectedAssistant = safeAssistants.find(a => a && a.id === selectedAssistantId);
          if (!selectedAssistant) {
            return false;
          }

          // 检查是否支持 web_search
          // 首先从助理数据中获取
          const baseTools = selectedAssistant.allowedTools || [];

          // 然后从 localStorage 获取
          let localStorageTools: string[] = [];
          try {
            const storageKey = `assistant_${selectedAssistant.id}_allowedTools`;
            const stored = localStorage.getItem(storageKey);
            if (stored) {
              localStorageTools = JSON.parse(stored);
            }
          } catch (e) {
            // 忽略错误
          }

          // 合并所有工具
          const allAllowedTools = Array.from(new Set([
            ...(Array.isArray(baseTools) ? baseTools : []),
            ...(Array.isArray(localStorageTools) ? localStorageTools : []),
          ]));

          // 检查是否包含 web_search（支持多种格式）
          const toolNamesToCheck = ['web_search', 'webSearch', 'web-search'];
          const hasWebSearch = allAllowedTools.length > 0 &&
            toolNamesToCheck.some(toolName => allAllowedTools.includes(toolName));

          // 调试日志
          if (!hasWebSearch) {
            console.log('[ChatInput] Web search not available for assistant:', {
              assistantId: selectedAssistant.id,
              assistantName: selectedAssistant.name,
              baseTools,
              localStorageTools,
              allAllowedTools,
              searchFor: toolNamesToCheck,
            });
          }

          return hasWebSearch;
        } catch (error) {
          console.error('[ChatInput] Error in setIsWebSearchActive callback:', error);
          return false;
        }
      });
    } catch (error) {
      console.error('[ChatInput] Error in useEffect for web search:', error);
    }
  }, [selectedAssistantId, safeAssistants]);

  // 修改時間：2026-01-06 - 檢測 Assistant 是否支持文件編輯
  const canEditFiles = useMemo(() => {
    if (!selectedAssistantId) return false;
    const assistant = safeAssistants.find(a => a && a.id === selectedAssistantId);
    if (!assistant) return false;

    // 從助理數據中獲取工具列表
    const baseTools = assistant.allowedTools || [];

    // 從 localStorage 獲取工具列表
    let localStorageTools: string[] = [];
    try {
      const storageKey = `assistant_${assistant.id}_allowedTools`;
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        localStorageTools = JSON.parse(stored);
      }
    } catch (e) {
      // 忽略錯誤
    }

    // 合併所有工具
    const allAllowedTools = Array.from(new Set([
      ...(Array.isArray(baseTools) ? baseTools : []),
      ...(Array.isArray(localStorageTools) ? localStorageTools : []),
    ]));

    // 檢查是否包含文件編輯相關工具
    const toolNamesToCheck = ['document_editing', 'file_editing', 'documentEditing', 'fileEditing'];
    return allAllowedTools.length > 0 &&
      toolNamesToCheck.some(toolName => allAllowedTools.includes(toolName));
  }, [selectedAssistantId, safeAssistants]);

  // 修改時間：2025-12-13 17:28:02 (UTC+8) - modelId 直接跟隨 props（任務切換可正確恢復）
  useEffect(() => {
    setSelectedModelId(selectedModelIdProp ?? 'auto');
  }, [selectedModelIdProp]);

  // 修改時間：2025-12-13 17:28:02 (UTC+8) - 啟動時同步收藏模型（API 優先，失敗會 fallback localStorage）
  useEffect(() => {
    let cancelled = false;
    getFavoriteModels()
      .then((resp) => {
        if (cancelled) return;
        const ids = resp?.data?.model_ids || [];
        setFavoriteModelsState(new Set(ids));
      })
      .catch(() => {
        // ignore (fallback already handled)
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // 修改時間：2026-01-24 - 獲取場景列表
  useEffect(() => {
    let cancelled = false;
    getScenes()
      .then((resp) => {
        if (cancelled) return;
        if (resp?.success && resp.data?.scenes) {
          // 查找 chat 場景配置
          const chatScene = resp.data.scenes.find((s: any) => s.scene === 'chat');
          if (chatScene) {
            setSceneConfig({
              frontend_editable: chatScene.frontend_editable || false,
              user_default: chatScene.user_default || null,
            });
          }
        }
      })
      .catch((error) => {
        console.warn('[ChatInput] Failed to fetch scenes:', error);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // 修改時間：2025-12-21 - 從 API 獲取模型列表（支持場景感知）
  useEffect(() => {
    let cancelled = false;
    setIsLoadingSceneModels(true);
    
    // 優先使用場景特定的模型列表
    getModelsByScene(currentScene, true)
      .then((resp) => {
        if (cancelled) return;
        setIsLoadingSceneModels(false);
        
        if (resp?.success && resp.data?.models && Array.isArray(resp.data.models) && resp.data.models.length > 0) {
          console.log(`[ChatInput] Models from scene '${currentScene}':`, resp.data.models);
          
          // 更新場景配置
          if (resp.data.frontend_editable !== undefined) {
            setSceneConfig({
              frontend_editable: resp.data.frontend_editable,
              user_default: resp.data.user_default || null,
            });
          }
          
          // 將 API 返回的模型轉換為組件需要的格式
          const models = resp.data.models.map((model: LLMModel) => {
            const providerStr = typeof model.provider === 'string'
              ? model.provider
              : (model.provider as any)?.value || String(model.provider);

            return {
              id: model.model_id,
              name: model.name,
              provider: providerStr,
              icon: model.icon,
              color: model.color,
            };
          });
          
          // 確保 auto 模型在最前面
          const autoModel = models.find((m) => m.id === 'auto') || {
            id: 'auto',
            name: t('chatInput.model.auto', 'Auto'),
            provider: 'auto',
            icon: 'fa-magic',
            color: 'text-purple-400',
          };
          const otherModels = models.filter((m) => m.id !== 'auto');
          
          // 按 order 排序（場景模型已經按優先級排序）
          const sortedModels = [...otherModels].sort((a, b) => {
            const aModel = resp.data?.models.find((m: LLMModel) => m.model_id === a.id);
            const bModel = resp.data?.models.find((m: LLMModel) => m.model_id === b.id);
            const aOrder = (aModel as any)?.order || 999;
            const bOrder = (bModel as any)?.order || 999;
            return aOrder - bOrder;
          });
          
          setLlmModels([autoModel, ...sortedModels]);
        } else {
          // 如果場景模型列表失敗，fallback 到通用模型列表
          console.warn(`[ChatInput] Scene '${currentScene}' models not available, falling back to general models`);
          return getModels({
            include_discovered: true,
            include_favorite_status: true,
            limit: 1000,
          });
        }
      })
      .then((resp) => {
        // 處理 fallback 到通用模型列表的情況
        if (cancelled) return;
        if (!resp) return; // 如果已經處理過場景模型，跳過
        
        setIsLoadingSceneModels(false);
        if (resp?.success && resp.data?.models && Array.isArray(resp.data.models) && resp.data.models.length > 0) {
          const models = resp.data.models.map((model: LLMModel) => {
            const providerStr = typeof model.provider === 'string'
              ? model.provider
              : (model.provider as any)?.value || String(model.provider);

            return {
              id: model.model_id,
              name: model.name,
              provider: providerStr,
              icon: model.icon,
              color: model.color,
            };
          });
          
          const autoModel = models.find((m) => m.id === 'auto') || {
            id: 'auto',
            name: t('chatInput.model.auto', 'Auto'),
            provider: 'auto',
            icon: 'fa-magic',
            color: 'text-purple-400',
          };
          const otherModels = models.filter((m) => m.id !== 'auto');
          const sortedModels = [...otherModels].sort((a, b) => {
            const aOrder = resp.data?.models.find((m: LLMModel) => m.model_id === a.id)?.order || 999;
            const bOrder = resp.data?.models.find((m: LLMModel) => m.model_id === b.id)?.order || 999;
            return aOrder - bOrder;
          });
          setLlmModels([autoModel, ...sortedModels]);
        } else {
          // 最終 fallback
          const fallbackModels = [
            { id: 'auto', name: t('chatInput.model.auto', 'Auto'), provider: 'auto', icon: 'fa-magic', color: 'text-purple-400' },
          ];
          setLlmModels(fallbackModels);
        }
      })
      .catch((error) => {
        if (cancelled) return;
        setIsLoadingSceneModels(false);
        console.error('[ChatInput] Failed to fetch models:', error);
        // 失敗時使用默認模型列表（fallback）
        const fallbackModels = [
          { id: 'auto', name: t('chatInput.model.auto', 'Auto'), provider: 'auto', icon: 'fa-magic', color: 'text-purple-400' },
          { id: 'smartq-hci', name: t('chatInput.model.smartqHCI', 'SmartQ HCI'), provider: 'smartq', icon: 'fa-microchip', color: 'text-orange-400' },
        ];
        setLlmModels(fallbackModels);
      });
    return () => {
      cancelled = true;
    };
  }, [currentScene, t]);

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

  // LLM 模型列表現在從 API 獲取（見上面的 useEffect）

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
    if (!safeAssistants || safeAssistants.length === 0 || favoriteAssistants.size === 0) {
      return [];
    }
    const filtered = safeAssistants.filter(assistant => assistant && favoriteAssistants.has(assistant.id));
    return filtered;
  }, [safeAssistants, favoriteAssistants]);

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
    const favoriteAssistant = favoriteAssistantsList.find(a => a && a.id === selectedAssistantId);
    if (favoriteAssistant) {
      return favoriteAssistant.name;
    }

    // 再檢查所有助理列表
    if (safeAssistants && safeAssistants.length > 0) {
      const assistant = safeAssistants.find(a => a && a.id === selectedAssistantId);
      if (assistant) {
        return assistant.name;
      }
    }

    return t('chatInput.selectAssistant', '選擇助理');
  }, [selectedAssistantId, favoriteAssistantsList, safeAssistants, t]);

  // 獲取選中的模型名稱
  const selectedModel = llmModels.find(m => m.id === selectedModelId);
  const selectedModelName = selectedModel ? selectedModel.name : t('chatInput.model.auto', 'Auto');
  console.log('[ChatInput] Selected model:', { selectedModelId, selectedModel, selectedModelName, llmModelsLength: llmModels.length }); // 調試

  // 跟踪选中状态变化（已移除調試日誌）

  // 處理代理選擇
  const handleAgentSelect = (agentId: string) => {

    hasUserSelectedAgent.current = true; // 标记用户已选择
    setSelectedAgentId(agentId);
    saveSelectedToStorage('selectedAgentId', agentId);


    onAgentSelect?.(agentId);
    setShowAgentSelector(false);
    setAgentPosition(null);
  };

  // 處理助理選擇
  const handleAssistantSelect = (assistantId: string) => {

    hasUserSelectedAssistant.current = true; // 标记用户已选择
    setSelectedAssistantId(assistantId);
    // 不再保存到 localStorage，只通过 props 传递


    onAssistantSelect?.(assistantId);
    setShowAssistantSelector(false);
    setAssistantPosition(null);
  };

  // 處理模型選擇
  const handleModelSelect = (modelId: string) => {
    setSelectedModelId(modelId);
    onModelSelect?.(modelId);
    setShowModelSelector(false);
    setModelPosition(null);
  };

  // 修改時間：2025-12-13 17:28:02 (UTC+8) - 收藏/取消收藏模型（localStorage 優先，可同步後端）
  const toggleFavoriteModel = async (modelId: string) => {
    const next = new Set(favoriteModels);
    if (next.has(modelId)) {
      next.delete(modelId);
    } else {
      next.add(modelId);
    }
    setFavoriteModelsState(next);

    const modelIds = Array.from(next.values());
    try {
      await setFavoriteModels(modelIds);
    } catch (error) {
      // setFavoriteModels 已經會 fallback localStorage；這裡只記錄
      console.warn('[ChatInput] Failed to sync favorite models:', error);
    }
  };

  // 修改時間：2025-12-08 10:40:00 UTC+8 - 發送消息時包含文件引用信息
  // 修改時間：2026-01-06 - 處理文件編輯操作

  /**
   * 處理接受修改
   */
  const handleAcceptEdit = useCallback(() => {
    acceptChanges();
    toast.success('修改已接受');
  }, [acceptChanges]);

  /**
   * 處理拒絕修改
   */
  const handleRejectEdit = useCallback(() => {
    rejectChanges();
    toast.info('修改已拒絕，已恢復原始內容');
  }, [rejectChanges]);

  /**
   * 處理提交修改
   */
  const handleSubmitEdit = useCallback(async () => {
    if (!currentRequestId) {
      toast.error('沒有可提交的編輯請求');
      return;
    }

    setIsSubmittingEdit(true);
    try {
      const response = await applyDocEdit(currentRequestId);
      if (response.success) {
        toast.success('修改已成功提交到後端');
        // 清除編輯狀態（Context 會處理）
        rejectChanges(); // 使用 rejectChanges 來清除狀態
      } else {
        toast.error(response.message || '提交失敗');
      }
    } catch (error: any) {
      console.error('[ChatInput] Failed to submit edit:', error);
      toast.error(error.message || '提交失敗，請稍後再試');
    } finally {
      setIsSubmittingEdit(false);
    }
  }, [currentRequestId, rejectChanges]);

  const handleSend = async () => {
    if (message.trim() || fileReferences.length > 0) {
      setIsLoading(true);
      const messageText = message.trim();

      // 修改時間：2025-01-27 - 重構任務創建邏輯
      // 如果沒有選中任務，必須創建新任務
      if (!selectedTask && onTaskCreate) {
        // 生成任務標題：取消息的前30個字符，如果超過則添加省略號
        const taskTitle = messageText.length > 30
          ? messageText.substring(0, 30) + '...'
          : (messageText || '新任務');

        const newTaskId = Date.now();
        const newTask: Task = {
          id: newTaskId,
          title: taskTitle,
          status: 'pending',
          dueDate: new Date().toISOString().split('T')[0],
          messages: [],
          executionConfig: {
            mode: 'free',
          },
          fileTree: [],
        };

        try {
          await onTaskCreate(newTask);
          // 等待任務保存完成
          await new Promise(resolve => setTimeout(resolve, 100));
        } catch (error) {
          console.error('[ChatInput] Failed to create task:', error);
          // 如果任務創建失敗，不發送消息
          setIsLoading(false);
          return;
        }
      } else if (selectedTask && onTaskTitleGenerate) {
        // 如果是第一條消息，自動生成任務標題（從消息內容中提取前30個字符）
        // 檢查是否為新任務（標題為"新任務"且沒有消息）
        const isNewTask = (
          (selectedTask.title === '新任務' || selectedTask.title === '新任务' || selectedTask.title === 'New Task') &&
          (!selectedTask.messages || selectedTask.messages.length === 0)
        );

        if (isNewTask) {
          // 生成任務標題：取消息的前30個字符，如果超過則添加省略號
          const title = messageText.length > 30
            ? messageText.substring(0, 30) + '...'
            : (messageText || '新任務');
          onTaskTitleGenerate(title);
        }
      }

      // 修改時間：2026-01-06 - 獲取 Assistant 的 allowedTools 並添加到消息中
      // 從 Assistant 配置中獲取 allowedTools（包括 document_editing）
      let assistantAllowedTools: string[] = [];
      if (selectedAssistantId) {
        const assistant = safeAssistants.find(a => a && a.id === selectedAssistantId);
        if (assistant) {
          // 從助理數據中獲取工具列表
          const baseTools = assistant.allowedTools || [];

          // 從 localStorage 獲取工具列表
          let localStorageTools: string[] = [];
          try {
            const storageKey = `assistant_${assistant.id}_allowedTools`;
            const stored = localStorage.getItem(storageKey);
            if (stored) {
              localStorageTools = JSON.parse(stored);
            }
          } catch (e) {
            // 忽略錯誤
          }

          // 合併所有工具
          assistantAllowedTools = Array.from(new Set([
            ...(Array.isArray(baseTools) ? baseTools : []),
            ...(Array.isArray(localStorageTools) ? localStorageTools : []),
          ]));
        }
      }

      // 構建包含文件引用的消息對象
      const messageWithFiles = {
        text: messageText,
        fileReferences: fileReferences.map(ref => ({
          fileId: ref.fileId,
          fileName: ref.fileName,
          filePath: ref.filePath,
          taskId: ref.taskId,
        })),
        // 添加工具使用信息
        tools: {
          web_search: isWebSearchActive, // 是否启用网络搜索
        },
        // 添加选中的助理信息（用于后端确定可用的工具）
        assistantId: selectedAssistantId,
        // 修改時間：2026-01-06 - 添加 Assistant 的 allowedTools 到消息中
        allowedTools: assistantAllowedTools.length > 0 ? assistantAllowedTools : undefined,
      };

      console.log('[ChatInput] 📤 Sending message with tools:', {
        text: messageText.substring(0, 100),
        textLength: messageText.length,
        isWebSearchActive,
        webSearchInTools: messageWithFiles.tools?.web_search,
        assistantId: selectedAssistantId,
        tools: messageWithFiles.tools,
        fullPayload: messageWithFiles,
      });

      // 如果消息包含"上網"但 web_search 未激活，发出警告
      if (messageText.includes('上網') && !isWebSearchActive) {
        console.warn('[ChatInput] ⚠️ Message contains "上網" but web_search is NOT active!', {
          messageText: messageText.substring(0, 100),
          isWebSearchActive,
          tools: messageWithFiles.tools,
        });
      }

      // 修改時間：2026-01-06 - 如果有選中的文件，觸發文件編輯消息事件
      if (selectedFile && canEditFiles) {
        window.dispatchEvent(new CustomEvent('messageSentForFileEditing', {
          detail: {
            message: messageText,
            fileId: selectedFile.file_id,
          }
        }));
      }

      // 发送消息（傳遞包含文件引用和工具信息的對象）
      console.log('[ChatInput] 發送消息, hasHandler:', !!onMessageSend);
      onMessageSend?.(JSON.stringify(messageWithFiles));

      setMessage('');
      setFileReferences([]); // 清空文件引用
      setIsLoading(false); // 發送完成後立即重置按鈕狀態
    }
  };

  // 修改時間：2025-12-08 10:40:00 UTC+8 - 監聽文件附加到聊天事件
  useEffect(() => {
    const handleFileAttach = (event: CustomEvent) => {
      const { fileId, fileName, filePath, taskId } = event.detail;

      // 檢查是否已經附加過這個文件
      if (fileReferences.some(ref => ref.fileId === fileId)) {
        return; // 已經附加過，不重複添加
      }

      // 創建文件引用
      const newFileRef: FileReferenceData = {
        fileId,
        fileName,
        filePath,
        taskId,
      };

      // 添加到文件引用列表
      setFileReferences(prev => [...prev, newFileRef]);

      // 插入文件引用到輸入框的光標位置
      const textarea = textareaRef.current;
      if (textarea) {
        const cursorPos = textarea.selectionStart;
        const textBeforeCursor = textarea.value.substring(0, cursorPos);
        const textAfterCursor = textarea.value.substring(cursorPos);

        // 在光標位置插入文件引用標記（類似 @文件名）
        const fileMark = `@${fileName} `;
        const newText = textBeforeCursor + fileMark + textAfterCursor;
        setMessage(newText);

        // 設置光標位置到插入文本之後
        setTimeout(() => {
          const newCursorPos = cursorPos + fileMark.length;
          textarea.setSelectionRange(newCursorPos, newCursorPos);
          textarea.focus();
        }, 0);
      }
    };

    window.addEventListener('fileAttachToChat', handleFileAttach as EventListener);
    return () => {
      window.removeEventListener('fileAttachToChat', handleFileAttach as EventListener);
    };
  }, [fileReferences]);

  // 修改時間：2025-12-08 10:40:00 UTC+8 - 移除文件引用
  const handleRemoveFileReference = useCallback((fileId: string) => {
    setFileReferences(prev => {
      // 找到要移除的文件引用
      const fileRef = prev.find(ref => ref.fileId === fileId);

      // 從輸入框中移除對應的文件標記
      if (fileRef) {
        const textarea = textareaRef.current;
        if (textarea) {
          // 移除 @文件名 標記
          const fileMark = `@${fileRef.fileName} `;
          setMessage(currentMessage =>
            currentMessage.replace(new RegExp(fileMark.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), '')
          );
        }
      }

      // 從列表中移除
      return prev.filter(ref => ref.fileId !== fileId);
    });
  }, []);

  // 文件上傳處理函數
  const handlePaperclipClick = () => {
    setShowFileUploadModal(true);
  };

  const handleFileUpload = async (files: File[], taskId?: string) => {
    if (files.length === 0) return;

    // 修改時間：2025-01-27 - 重構文件上傳邏輯，移除 temp-workspace
    // 檢查是否為新任務（第一次上傳文件）：
    // 1. 必須有 selectedTask
    // 2. 任務標題必須是"新任務"（表示是剛創建的空白任務）
    // 3. 沒有消息和文件
    const isNewTask = selectedTask &&
      (selectedTask.title === '新任務' || selectedTask.title === '新任务' || selectedTask.title === 'New Task') &&
      (!selectedTask.messages || selectedTask.messages.length === 0) &&
      (!selectedTask.fileTree || selectedTask.fileTree.length === 0);

    let finalTaskId: string | undefined = undefined;

    // 如果是新任務，創建任務並使用第一個文件名作為任務名稱
    if (isNewTask && onTaskCreate && selectedTask) {
      const firstFileName = files[0]?.name || '新任務';
      // 移除文件擴展名作為任務名稱
      const taskTitle = firstFileName.replace(/\.[^/.]+$/, '') || '新任務';

      // 生成新的任務ID（使用時間戳確保唯一性）
      const newTaskId = Date.now();

      const createdTask: Task = {
        ...selectedTask,
        id: newTaskId,
        title: taskTitle,
        fileTree: [], // 初始化文件樹
        // 確保 executionConfig 存在
        executionConfig: selectedTask.executionConfig || {
          mode: 'free',
        },
      };

      // 先創建任務，確保任務ID已生成並保存到後端
      try {
        await onTaskCreate(createdTask);
        // saveTask 現在會等待後端同步完成，不需要額外等待
        finalTaskId = String(newTaskId);
      } catch (error) {
        const msg = error instanceof Error ? error.message : String(error);
        console.error('[ChatInput] Failed to create task:', error);
        toast.error(`創建任務失敗: ${msg}`);
        setUploadingFiles([]);
        return;
      }
    } else if (selectedTask && !isNewTask) {
      // 已有任務，使用現有任務ID
      finalTaskId = String(selectedTask.id);
    } else if (taskId) {
      // 使用傳遞的 taskId
      finalTaskId = taskId;
    } else {
      // 沒有任務且未提供 taskId，必須創建新任務
      const firstFileName = files[0]?.name || '新任務';
      const taskTitle = firstFileName.replace(/\.[^/.]+$/, '') || '新任務';
      const newTaskId = Date.now();

      const newTask: Task = {
        id: newTaskId,
        title: taskTitle,
        status: 'pending',
        dueDate: new Date().toISOString().split('T')[0],
        messages: [],
        executionConfig: {
          mode: 'free',
        },
        fileTree: [],
      };

      if (onTaskCreate) {
        try {
          await onTaskCreate(newTask);
          // saveTask 現在會等待後端同步完成，不需要額外等待
          finalTaskId = String(newTaskId);
        } catch (error) {
          console.error('[ChatInput] Failed to create task:', error);
          setUploadingFiles([]);
          return;
        }
        } else {
          console.error('[ChatInput] onTaskCreate callback not available');
          toast.error('無法創建任務，請先選擇或建立任務');
          setUploadingFiles([]);
          return;
        }
    }

    // 創建文件元數據
    const filesWithMetadata: FileWithMetadata[] = files.map((file) => ({
      file,
      id: `${Date.now()}-${Math.random()}`,
      status: 'pending',
      progress: 0,
    }));

    setUploadingFiles(filesWithMetadata);

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
        const errMsg = response.message || response.error || '上傳失敗';
        toast.error(`文件上傳失敗: ${errMsg}`);
        setUploadingFiles((prev) =>
          prev.map((f) => ({
            ...f,
            status: 'error',
            error: errMsg,
          }))
        );
      }
    } catch (error: any) {
      const msg = error?.message || String(error);
      console.error('File upload error:', error);
      toast.error(`文件上傳失敗: ${msg}`);

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
          if (isNewTask && finalTaskId && onTaskDelete) {
            const taskIdNum = parseInt(String(finalTaskId));
            if (!isNaN(taskIdNum)) {
              onTaskDelete(taskIdNum);
            }
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
      if (isNewTask && finalTaskId && onTaskDelete) {
        try {
          const taskIdNum = parseInt(finalTaskId);
          if (!isNaN(taskIdNum)) {
            onTaskDelete(taskIdNum);
          }
        } catch (e) {
          console.error('[ChatInput] Failed to delete task after upload error:', e);
        }
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
    <>
      <style>{`
        @keyframes breathe {
          0%, 100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.6;
            transform: scale(0.95);
          }
        }
      `}</style>
      <div className="bg-secondary rounded-xl overflow-hidden theme-transition">
      {/* 工具欄 */}
      <div className="flex items-center p-1.5 border-b border-primary">
        {/* 上网功能按钮 */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            try {
              // 检查当前选中的助理是否可以使用 web_search 工具
              if (!selectedAssistantId) {
                // 使用 alert 显示警示（可以后续改为 toast）
                alert(t('chatInput.webSearch.noAssistant', '請先選擇助理'));
                return;
              }

              if (!safeAssistants || safeAssistants.length === 0) {
                alert(t('chatInput.webSearch.assistantNotFound', '找不到選中的助理'));
                return;
              }

              const selectedAssistant = safeAssistants.find(a => a && a.id === selectedAssistantId);
              if (!selectedAssistant) {
                alert(t('chatInput.webSearch.assistantNotFound', '找不到選中的助理'));
                return;
              }

              // 调试：输出助理信息
              console.log('[ChatInput] Selected Assistant:', {
                id: selectedAssistant.id,
                name: selectedAssistant.name,
                allowedTools: selectedAssistant.allowedTools,
                allowedToolsType: typeof selectedAssistant.allowedTools,
                isArray: Array.isArray(selectedAssistant.allowedTools),
                fullAssistant: selectedAssistant,
              });

              // 检查 localStorage 中是否有该助理的工具数据
              let localStorageTools: string[] = [];
              try {
                const storageKey = `assistant_${selectedAssistant.id}_allowedTools`;
                const stored = localStorage.getItem(storageKey);
                if (stored) {
                  localStorageTools = JSON.parse(stored);
                  console.log('[ChatInput] ✅ Found tools in localStorage:', {
                    storageKey,
                    storedTools: localStorageTools,
                    isArray: Array.isArray(localStorageTools),
                    hasWebSearch: localStorageTools.includes('web_search'),
                  });
                } else {
                  console.log('[ChatInput] ❌ No tools found in localStorage for:', storageKey);

                  // 尝试查找所有相关的 localStorage 键
                  const allKeys: string[] = [];
                  for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    if (key && key.includes('assistant') && key.includes('allowedTools')) {
                      allKeys.push(key);
                    }
                  }
                  console.log('[ChatInput] All assistant tool keys in localStorage:', allKeys);

                  // 尝试读取所有相关的键
                  allKeys.forEach(key => {
                    try {
                      const value = localStorage.getItem(key);
                      if (value) {
                        const parsed = JSON.parse(value);
                        console.log(`[ChatInput] Key "${key}":`, parsed);
                      }
                    } catch (e) {
                      console.error(`[ChatInput] Error parsing key "${key}":`, e);
                    }
                  });

                  // 临时调试：尝试手动设置 web_search 工具
                  console.warn('[ChatInput] ⚠️ 临时调试：尝试手动设置 web_search 工具到 localStorage');
                  try {
                    const testTools = ['web_search'];
                    localStorage.setItem(storageKey, JSON.stringify(testTools));
                    console.log('[ChatInput] ✅ 临时设置成功，请重新点击地球图标测试');
                    localStorageTools = testTools;
                  } catch (e) {
                    console.error('[ChatInput] ❌ 临时设置失败:', e);
                  }
                }
              } catch (e) {
                console.error('[ChatInput] Error reading localStorage:', e);
              }

              // 合并 allowedTools 和 localStorage 中的工具
              const baseTools = selectedAssistant.allowedTools || [];
              const allAllowedTools = Array.from(new Set([
                ...(Array.isArray(baseTools) ? baseTools : []),
                ...(Array.isArray(localStorageTools) ? localStorageTools : []),
              ]));

              // 检查助理是否可以使用 web_search 工具
              // 支持多种可能的工具名称格式
              const toolNamesToCheck = ['web_search', 'webSearch', 'web-search'];
              const hasWebSearch = allAllowedTools.length > 0 &&
                toolNamesToCheck.some(toolName => allAllowedTools.includes(toolName));

              console.log('[ChatInput] Web Search Check:', {
                assistantId: selectedAssistant.id,
                assistantName: selectedAssistant.name,
                baseTools,
                localStorageTools,
                allAllowedTools,
                hasWebSearch,
                isWebSearchActive,
                searchFor: toolNamesToCheck,
                foundTools: allAllowedTools.filter(t => toolNamesToCheck.includes(t)),
                cacheTools: assistantToolsCache.get(selectedAssistant.id),
              });

              if (!hasWebSearch && !isWebSearchActive) {
                // 显示无法上网的警示，包含调试信息
                console.warn('[ChatInput] Web search not available:', {
                  assistantId: selectedAssistant.id,
                  assistantName: selectedAssistant.name,
                  baseTools,
                  localStorageTools,
                  allAllowedTools,
                  hasWebSearch,
                });
                alert(t('chatInput.webSearch.notAvailable', '當前助理無法使用上網功能，請在助理維護中啟用 web_search 工具'));
                return;
              }

              // 切换激活状态
              setIsWebSearchActive((prev) => !prev);
            } catch (error) {
              console.error('[ChatInput] Error in web search toggle:', error);
              alert(t('chatInput.webSearch.error', '發生錯誤，請稍後再試'));
            }
          }}
          className={`p-1.5 rounded transition-colors ${
            isWebSearchActive
              ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
              : 'hover:bg-tertiary text-tertiary hover:text-primary'
          }`}
          aria-label={t('chatInput.webSearch.toggle', '切換上網功能')}
          title={isWebSearchActive ? t('chatInput.webSearch.active', '上網功能已啟用') : t('chatInput.webSearch.inactive', '點擊啟用上網功能')}
        >
          <i className="fa-solid fa-globe"></i>
        </button>
        <button
          onClick={toggleWindow}
          className={`p-1.5 rounded transition-colors ${
            currentStatus === 'processing'
              ? 'text-green-500'
              : 'hover:bg-tertiary text-tertiary hover:text-primary'
          }`}
          style={currentStatus === 'processing' ? {
            animation: 'breathe 2s ease-in-out infinite'
          } : {}}
          aria-label={currentStatus === 'processing' ? t('chatInput.aiProcessing', 'AI 正在處理') : '深度思考'}
        >
          <i className="fa-solid fa-brain"></i>
        </button>
        {/* 編輯文件按鈕 */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            // 觸發文件編輯模式切換事件
            if (canEditFiles) {
              // 如果支持文件編輯，觸發編輯事件（允許 fileId 為 null，用於創建新文件）
              window.dispatchEvent(new CustomEvent('toggleFileEditing', {
                detail: { fileId: selectedFile?.file_id || null }
              }));
            } else {
              // 如果不支持編輯，提示選擇支持文件編輯的助理
              alert(t('chatInput.fileEdit.noAssistant', '請選擇支持文件編輯的助理'));
            }
          }}
          className={`p-1.5 rounded transition-colors ${
            canEditFiles
              ? 'bg-blue-500/20 text-blue-400 hover:bg-blue-500/30'
              : 'hover:bg-tertiary text-tertiary hover:text-primary'
          }`}
          aria-label={t('chatInput.fileEdit.toggle', '切換文件編輯模式')}
          title={canEditFiles
            ? t('chatInput.fileEdit.active', '文件編輯模式已啟用')
            : t('chatInput.fileEdit.inactive', '點擊啟用文件編輯模式')}
        >
          <i className="fa-solid fa-file-edit"></i>
        </button>

        {/* 助理選擇器 */}
        <div className="relative ml-2" ref={assistantSelectorRef}>
          <button
            className="px-2.5 py-0.5 rounded bg-tertiary hover:bg-hover transition-colors text-[12.6px] flex items-center text-secondary"
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
                favoriteAssistantsList.map((assistant) => {
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
            className="px-2.5 py-0.5 rounded bg-tertiary hover:bg-hover transition-colors text-[12.6px] flex items-center text-secondary"
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
              {fixedAgents.map((agent) => {
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
                favoriteAgentsList.map((agent) => {
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

        {/* 文件選擇器（僅在支持文件編輯時顯示） */}
        {canEditFiles && (
          <div className="ml-2 flex items-center gap-2">
            <FileSelector
              file={selectedFile}
              onFileChange={setSelectedFile}
              taskId={currentTaskId}
              userId={undefined}
              fileTree={undefined}
            />
            {/* 文件編輯狀態按鈕（僅在有未保存修改時顯示） */}
            {hasUnsavedChanges && (
              <FileEditStatus
                onAccept={handleAcceptEdit}
                onReject={handleRejectEdit}
                onSubmit={handleSubmitEdit}
                isSubmitting={isSubmittingEdit}
              />
            )}
          </div>
        )}

        {/* 模型選擇器 */}
        <div className="relative ml-2" ref={modelSelectorRef}>
          <button
            className="px-2.5 py-0.5 rounded bg-tertiary hover:bg-hover transition-colors text-[12.6px] flex items-center text-secondary"
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
              {/* 場景提示 UI - 當使用 SmartQ-HCI 時顯示 */}
              {selectedModelId === 'smartq-hci' && (
                <div className="px-3 py-2 bg-blue-50 dark:bg-blue-900/20 border-b border-primary">
                  <div className="flex items-start gap-2 text-xs text-blue-700 dark:text-blue-300">
                    <i className="fa-solid fa-info-circle mt-0.5"></i>
                    <div>
                      <div className="font-medium mb-1">SmartQ-HCI 智能融合模型</div>
                      <div className="text-blue-600 dark:text-blue-400">
                        系統會自動為您選擇最佳後端模型，無需手動配置。根據場景智能路由到最優模型。
                      </div>
                    </div>
                  </div>
                </div>
              )}
              {/* 場景配置提示 - 當場景不可編輯時顯示 */}
              {sceneConfig && !sceneConfig.frontend_editable && currentScene === 'chat' && (
                <div className="px-3 py-1.5 bg-yellow-50 dark:bg-yellow-900/20 border-b border-primary">
                  <div className="flex items-center gap-2 text-xs text-yellow-700 dark:text-yellow-300">
                    <i className="fa-solid fa-lightbulb"></i>
                    <span>當前場景已為您優化模型選擇</span>
                  </div>
                </div>
              )}
              {(() => {
                console.log('[ChatInput] Rendering model selector, llmModels:', llmModels); // 調試：查看渲染時的模型列表
                console.log('[ChatInput] favoriteModels:', favoriteModels); // 調試：查看收藏的模型
                const autoModel = llmModels.find(m => m.id === 'auto');
                const favoriteModelItems = llmModels.filter(m => m.id !== 'auto' && favoriteModels.has(m.id));
                const allModelItems = llmModels.filter(m => m.id !== 'auto');
                console.log('[ChatInput] autoModel:', autoModel); // 調試
                console.log('[ChatInput] favoriteModelItems:', favoriteModelItems); // 調試
                console.log('[ChatInput] allModelItems:', allModelItems); // 調試

                const renderModelRow = (model: any, showStar: boolean = true) => {
                  const isSelected = selectedModelId === model.id;
                  const isFavorite = favoriteModels.has(model.id);
                  const isInactive = model.status === 'inactive' || model.metadata?.status === 'inactive';
                  const inactiveReason = model.inactive_reason || model.metadata?.inactive_reason || '暫時不可用';

                  return (
                    <button
                      key={model.id}
                      className={`w-full text-left px-4 py-2 text-sm transition-colors flex items-center gap-2 ${
                        isSelected ? 'bg-tertiary font-medium' : ''
                      } ${isInactive ? 'opacity-50 cursor-not-allowed' : 'hover:bg-tertiary'}`}
                      disabled={isInactive}
                      onMouseDown={(e) => {
                        e.stopPropagation();
                        e.preventDefault();
                        if (!isInactive) {
                          handleModelSelect(model.id);
                        }
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        e.preventDefault();
                      }}
                      title={isInactive ? inactiveReason : ''}
                    >
                      <i className={`fa-solid ${
                        // 如果 API 返回的 icon 已經包含 fa- 前綴，直接使用；否則添加 fa- 前綴
                        (model.icon && (model.icon.startsWith('fa-') ? model.icon : `fa-${model.icon}`)) || (
                          model.id === 'auto' ? 'fa-magic' :
                          model.id === 'smartq-iee' ? 'fa-microchip' :
                          model.id === 'smartq-hci' ? 'fa-microchip' :
                          model.provider === 'chatgpt' ? 'fa-robot' :
                          model.provider === 'gemini' ? 'fa-gem' :
                          model.provider === 'qwen' ? 'fa-code' :
                          model.provider === 'grok' ? 'fa-bolt' :
                          model.provider === 'ollama' ? 'fa-server' :
                          model.provider === 'anthropic' ? 'fa-brain' :
                          model.provider === 'mistral' ? 'fa-wind' :
                          model.provider === 'deepseek' ? 'fa-search' :
                          'fa-server'
                        )
                      } ${
                        model.color || (
                          model.id === 'auto' ? 'text-purple-400' :
                          model.id === 'smartq-iee' ? 'text-blue-400' :
                          model.id === 'smartq-hci' ? 'text-orange-400' :
                          model.provider === 'chatgpt' ? 'text-green-400' :
                          model.provider === 'gemini' ? 'text-blue-400' :
                          model.provider === 'qwen' ? 'text-orange-400' :
                          model.provider === 'grok' ? 'text-yellow-400' :
                          model.provider === 'ollama' ? 'text-gray-400' :
                          model.provider === 'anthropic' ? 'text-orange-400' :
                          model.provider === 'mistral' ? 'text-purple-400' :
                          model.provider === 'deepseek' ? 'text-blue-400' :
                          'text-gray-400'
                        )
                      } ${isInactive ? 'grayscale' : ''}`}></i>

                      <span className={`flex-1 truncate ${isInactive ? 'text-tertiary' : 'text-secondary'}`}>{model.name}</span>

                      {isInactive && (
                        <i className="fa-solid fa-lock text-tertiary ml-1" title={inactiveReason}></i>
                      )}

                      {isSelected && !isInactive && (
                        <i className="fa-solid fa-check text-blue-400 ml-1" title="已選中"></i>
                      )}
                    </button>
                  );
                };

                return (
                  <>
                    {/* Auto */}
                    {autoModel && renderModelRow(autoModel, false)}

                    {/* All models */}
                    <div className="border-t border-primary my-1"></div>
                    <div className="px-4 py-2 text-xs text-tertiary font-medium">
                      {t('chatInput.model.all', '所有模型')}
                    </div>
                    {allModelItems.map((m) => renderModelRow(m, false))}
                  </>
                );
              })()}
            </div>,
            document.body
          )}
        </div>

        <div className="ml-auto flex items-center space-x-1 relative">
          {/* @ 提及按鈕 - 放在回纹针左侧 */}
          <button
            onClick={handleMentionClick}
            className="p-1.5 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
            title={t('chatInput.mention.title', '提及 (@)')}
            aria-label={t('chatInput.mention.title', '提及 (@)')}
          >
            <span className="text-base font-semibold">@</span>
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
            className="p-1.5 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
            aria-label="上傳文件"
          >
            <i className="fa-solid fa-paperclip"></i>
          </button>
          <button
            className="p-1.5 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
            aria-label="表情"
          >
            <i className="fa-solid fa-smile"></i>
          </button>
          <button
            className="p-1.5 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
            aria-label="語音輸入"
          >
            <i className="fa-solid fa-microphone"></i>
          </button>
        </div>
      </div>

      {/* 修改時間：2025-12-08 10:40:00 UTC+8 - 文件引用顯示區域 */}
      {fileReferences.length > 0 && (
        <div className="px-3 pt-3 pb-2 border-b border-primary/50">
          <div className="flex flex-wrap gap-2">
            {fileReferences.map((fileRef) => (
              <FileReference
                key={fileRef.fileId}
                file={fileRef}
                onRemove={handleRemoveFileReference}
              />
            ))}
          </div>
        </div>
      )}

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

        {/* 修改時間：2025-12-08 11:20:00 UTC+8 - 右側按鈕區域（清除和發送按鈕） */}
        <div className="ml-2 flex flex-col gap-2">
          {/* 清除按鈕 */}
          <button
            className={`px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg transition-colors flex items-center justify-center ${isPreviewMode ? 'px-2' : ''}`}
            onClick={() => {
              setMessage('');
              setFileReferences([]); // 同時清除文件引用
              if (textareaRef.current) {
                textareaRef.current.focus();
              }
            }}
            title="清除輸入內容"
            aria-label="清除輸入內容"
          >
            {!isPreviewMode && <span>{t('chatInput.clear', '清除')}</span>}
            <i className={`fa-solid fa-xmark ${!isPreviewMode ? 'ml-2' : ''}`}></i>
          </button>

           {/* 發送按鈕 */}
           <button
             className={`px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center justify-center ${isPreviewMode ? 'px-2' : ''} ${isLoading ? 'opacity-75 cursor-not-allowed' : ''}`}
             onClick={handleSend}
             disabled={isLoading}
           >
             {isLoading ? (
               <>
                 {!isPreviewMode && <span>{t('chatInput.sending', '發送中')}</span>}
                 <i className={`fa-solid fa-spinner fa-spin ${!isPreviewMode ? 'ml-2' : ''}`}></i>
               </>
             ) : (
               <>
                 {!isPreviewMode && <span>{t('chatInput.send', '發送')}</span>}
                 <i className={`fa-solid fa-paper-plane ${!isPreviewMode ? 'ml-2' : ''}`}></i>
               </>
             )}
           </button>
        </div>
      </div>

      {/* 文件上傳模態框 */}
      <FileUploadModal
        isOpen={showFileUploadModal}
        onClose={() => setShowFileUploadModal(false)}
        onUpload={handleFileUpload}
        defaultTaskId={currentTaskId || 'temp-workspace'}
        isAgentOnboardingAllowed={isSystemAdmin(currentUser)}
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

      {/* AI Status Window Portal - 2/3 AI message 區域 */}
      {isWindowOpen && createPortal(
        <div className="fixed inset-0 flex items-center justify-center pointer-events-none z-50 p-4">
          <div className="relative w-2/3 h-2/3 pointer-events-auto">
            <AIStatusWindow />
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
