/**
 * Assistant 維護模態框組件
 * 功能：提供助理維護界面，包含角色說明、技能、限制等配置
 * 創建日期：2025-01-27
 * 創建人：Daniel Chung
 * 最後修改日期：2026-01-06
 */

import { useState, useEffect, useMemo } from 'react';
import { useLanguage } from '../contexts/languageContext';
import { cn } from '../lib/utils';
import { apiGet } from '../lib/api';
import IconPicker from './IconPicker';
import IconRenderer from './IconRenderer';

// 工具信息接口
interface ToolInfo {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
}

// 工具图标映射函数
const getToolIcon = (toolName: string, category: string): string => {
  const iconMap: Record<string, string> = {
    // 时间相关
    'datetime': 'fa-clock',
    'date_formatter': 'fa-calendar',
    'date_calculator': 'fa-calculator',
    // 网络搜索
    'web_search': 'fa-globe',
    // 天气
    'weather': 'fa-cloud-sun',
    'forecast': 'fa-cloud-rain',
    // 地理位置
    'ip_location': 'fa-map-marker-alt',
    'geocoding': 'fa-map',
    'distance': 'fa-route',
    'timezone': 'fa-globe-americas',
    // 单位转换
    'length': 'fa-ruler',
    'weight': 'fa-weight',
    'temperature': 'fa-thermometer-half',
    'currency': 'fa-dollar-sign',
    'volume': 'fa-flask',
    'area': 'fa-square',
    // 计算
    'math': 'fa-calculator',
    'statistics': 'fa-chart-bar',
    // 文本处理
    'text_formatter': 'fa-text-width',
    'text_cleaner': 'fa-broom',
    'text_converter': 'fa-exchange-alt',
    'text_summarizer': 'fa-compress',
    // 代码相关
    'code': 'fa-code',
    'code-react': 'fa-code',
    'code-python': 'fa-python',
  };

  // 根据工具名称匹配
  if (iconMap[toolName]) {
    return iconMap[toolName];
  }

  // 根据类别匹配
  const categoryIconMap: Record<string, string> = {
    '時間與日期': 'fa-clock',
    '網絡搜索': 'fa-globe',
    '天氣': 'fa-cloud-sun',
    '地理位置': 'fa-map-marker-alt',
    '單位轉換': 'fa-exchange-alt',
    '計算': 'fa-calculator',
    '文本處理': 'fa-text-width',
  };

  if (categoryIconMap[category]) {
    return categoryIconMap[category];
  }

  // 默认图标
  return 'fa-tools';
};

interface AssistantMaintenanceModalProps {
  isOpen: boolean;
  assistantId?: string;
  assistant?: {
    id: string;
    name: string;
    description: string;
    icon: string;
  };
  onClose: () => void;
  onSave?: (data: AssistantMaintenanceData) => void;
}

export interface AssistantMaintenanceData {
  // 基本資訊
  id?: string; // 助理 ID（编辑时使用）
  name: string;
  icon: string;
  role: string; // 角色說明
  skills: string[]; // 技能
  limitations: string[]; // 限制
  outputFormat: string; // 輸出格式

  // 資源配置
  knowledgeBases: string[]; // 可接觸的知識庫
  allowedTools: string[]; // 可使用的Tools

  // 行為配置
  temperature: number; // 助理回應的Temperature (0-1)
  greeting: string; // 開場問候
  presetResponses: string[]; // 回應_3_個問題（預設回應）

  // 可見性
  visibility: 'private' | 'public'; // 助理是private或public
}

export default function AssistantMaintenanceModal({
  isOpen,
  assistantId,
  assistant,
  onClose,
  onSave,
}: AssistantMaintenanceModalProps) {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<'basic' | 'resources' | 'behavior' | 'visibility'>('basic');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 基本資訊
  const [name, setName] = useState(assistant?.name || '');
  const [selectedIcon, setSelectedIcon] = useState<string>(assistant?.icon || 'FaRobot');
  const [showIconPicker, setShowIconPicker] = useState(false);
  const [role, setRole] = useState(''); // 角色說明
  const [skills, setSkills] = useState<string[]>([]); // 技能
  const [skillInput, setSkillInput] = useState('');
  const [limitations, setLimitations] = useState<string[]>([]); // 限制
  const [limitationInput, setLimitationInput] = useState('');
  const [outputFormat, setOutputFormat] = useState(''); // 輸出格式

  // 資源配置
  const [knowledgeBases, setKnowledgeBases] = useState<string[]>([]); // 可接觸的知識庫
  const [knowledgeBaseInput, setKnowledgeBaseInput] = useState('');
  const [allowedCategories, setAllowedCategories] = useState<string[]>([]); // 可使用的工具類別（類別列表）
  const [enableFileEditing, setEnableFileEditing] = useState(false); // 是否啟用文件編輯功能

  // 工具列表相关状态
  const [tools, setTools] = useState<ToolInfo[]>([]); // 所有工具列表（用於計算類別下的工具數量）
  const [categories, setCategories] = useState<string[]>([]); // 所有分类列表
  const [isLoadingTools, setIsLoadingTools] = useState(false); // 加载状态
  const [toolsError, setToolsError] = useState<string | null>(null); // 工具加载错误

  // 行為配置
  const [temperature, setTemperature] = useState(0.7); // Temperature (0-1)
  const [greeting, setGreeting] = useState(''); // 開場問候
  const [presetResponses, setPresetResponses] = useState<string[]>(['', '', '']); // 回應_3_個問題

  // 可見性
  const [visibility, setVisibility] = useState<'private' | 'public'>('private');

  // 保存初始數據，用於檢測是否有修改
  const [initialData, setInitialData] = useState<{
    name: string;
    icon: string;
    role: string;
    skills: string[];
    limitations: string[];
    outputFormat: string;
    knowledgeBases: string[];
    allowedCategories: string[];
    enableFileEditing: boolean;
    temperature: number;
    greeting: string;
    presetResponses: string[];
    visibility: 'private' | 'public';
  } | null>(null);

  // 當 modal 打開時，保存初始數據
  useEffect(() => {
    if (isOpen) {
      // 使用 setTimeout 確保所有狀態都已初始化（特別是從 assistant prop 加載的數據）
      const timer = setTimeout(() => {
      const currentData = {
        name: name.trim(),
        icon: selectedIcon,
        role: role.trim(),
        skills: [...skills],
        limitations: [...limitations],
        outputFormat: outputFormat.trim(),
        knowledgeBases: [...knowledgeBases],
        allowedCategories: [...allowedCategories],
        enableFileEditing,
        temperature,
        greeting: greeting.trim(),
        presetResponses: presetResponses.filter(r => r.trim() !== ''),
        visibility,
      };
      setInitialData(currentData);
      }, 100); // 延遲 100ms 確保狀態已更新

      return () => clearTimeout(timer);
    } else {
      // modal 關閉時重置
      setInitialData(null);
    }
  }, [isOpen]); // 只在 modal 打開時執行一次，使用 setTimeout 確保狀態已初始化

  // 檢測是否有修改
  const hasChanges = useMemo(() => {
    if (!initialData) return false; // 新建模式，沒有初始數據

    const currentData = {
      name: name.trim(),
      icon: selectedIcon,
      role: role.trim(),
      skills: [...skills].sort(),
      limitations: [...limitations].sort(),
      outputFormat: outputFormat.trim(),
      knowledgeBases: [...knowledgeBases].sort(),
      allowedCategories: [...allowedCategories].sort(),
      enableFileEditing,
      temperature,
      greeting: greeting.trim(),
      presetResponses: presetResponses.filter(r => r.trim() !== '').sort(),
      visibility,
    };

    const initialDataSorted = {
      ...initialData,
      skills: [...initialData.skills].sort(),
      limitations: [...initialData.limitations].sort(),
      knowledgeBases: [...initialData.knowledgeBases].sort(),
      allowedCategories: [...initialData.allowedCategories].sort(),
      enableFileEditing: initialData.enableFileEditing || false,
      presetResponses: initialData.presetResponses.filter(r => r.trim() !== '').sort(),
    };

    // 比較所有字段
    return (
      currentData.name !== initialDataSorted.name ||
      currentData.icon !== initialDataSorted.icon ||
      currentData.role !== initialDataSorted.role ||
      JSON.stringify(currentData.skills) !== JSON.stringify(initialDataSorted.skills) ||
      JSON.stringify(currentData.limitations) !== JSON.stringify(initialDataSorted.limitations) ||
      currentData.outputFormat !== initialDataSorted.outputFormat ||
      JSON.stringify(currentData.knowledgeBases) !== JSON.stringify(initialDataSorted.knowledgeBases) ||
      JSON.stringify(currentData.allowedCategories) !== JSON.stringify(initialDataSorted.allowedCategories) ||
      currentData.enableFileEditing !== initialDataSorted.enableFileEditing ||
      currentData.temperature !== initialDataSorted.temperature ||
      currentData.greeting !== initialDataSorted.greeting ||
      JSON.stringify(currentData.presetResponses) !== JSON.stringify(initialDataSorted.presetResponses) ||
      currentData.visibility !== initialDataSorted.visibility
    );
  }, [
    initialData,
    name,
    selectedIcon,
    role,
    skills,
    limitations,
    outputFormat,
    knowledgeBases,
    allowedCategories,
    enableFileEditing,
    temperature,
    greeting,
    presetResponses,
    visibility,
  ]);

  const handleClose = () => {
    if (!isSubmitting) {
      setError(null);
      onClose();
    }
  };

  const handleSave = async () => {
    console.log('[AssistantMaintenanceModal] 🚀 handleSave called!', {
      assistantId,
      allowedCategories,
      allowedCategoriesCount: allowedCategories.length,
      hasOnSave: !!onSave,
      isSubmitting,
    });

    setError(null);
    setIsSubmitting(true);

    try {
      // 檢查：如果用戶選擇了類別但工具尚未加載，提示用戶
      if (allowedCategories.length > 0 && tools.length === 0 && !isLoadingTools) {
        setError('工具列表尚未加載完成，請稍候再試');
        setIsSubmitting(false);
        return;
      }

      // 如果正在加載工具，也提示用戶等待
      if (allowedCategories.length > 0 && isLoadingTools) {
        setError('工具列表正在加載中，請稍候再試');
        setIsSubmitting(false);
        return;
      }

      // 獲取完整的工具ID列表（包括類別工具和文件編輯工具）
      const allowedTools = getAllowedTools();

      // 如果選擇了類別但轉換後工具列表為空，且工具已加載，提示用戶
      const categoryTools = getToolsByCategories(allowedCategories);
      if (allowedCategories.length > 0 && categoryTools.length === 0 && tools.length > 0) {
        console.warn('[AssistantMaintenanceModal] ⚠️ Selected categories but no tools found:', {
          allowedCategories,
          availableCategories: categories,
          toolsCount: tools.length,
        });
        // 不阻止保存，但記錄警告（可能是類別名稱不匹配）
      }

      const data: AssistantMaintenanceData = {
        id: assistantId, // 包含助理 ID，用于保存到 localStorage
        name: name.trim(),
        icon: selectedIcon,
        role: role.trim(),
        skills: skills,
        limitations: limitations,
        outputFormat: outputFormat.trim(),
        knowledgeBases: knowledgeBases,
        allowedTools: allowedTools, // 從類別轉換為工具ID列表
        temperature: temperature,
        greeting: greeting.trim(),
        presetResponses: presetResponses.filter(r => r.trim() !== ''),
        visibility: visibility,
      };

      console.log('[AssistantMaintenanceModal] 📦 Saving data:', {
        assistantId,
        dataId: data.id,
        allowedTools: data.allowedTools,
        allowedToolsCount: data.allowedTools.length,
        hasWebSearch: data.allowedTools.includes('web_search'),
        webSearchIndex: data.allowedTools.indexOf('web_search'),
        allToolIds: data.allowedTools,
        fullData: data,
      });

      // 在保存前，先尝试保存到 localStorage（作为备份）
      // 优先使用 assistantId prop，如果没有则尝试从 assistant 对象获取
      const idToSave = assistantId || assistant?.id;

      // 獲取完整的工具ID列表（包括類別工具和文件編輯工具）
      const toolsToSave = getAllowedTools();

      console.log('[AssistantMaintenanceModal] 🔑 ID resolution:', {
        assistantIdProp: assistantId,
        assistantIdFromObject: assistant?.id,
        idToSave,
        allowedCategories,
        allowedCategoriesCount: allowedCategories.length,
        toolsToSave,
        toolsToSaveCount: toolsToSave.length,
      });

      // 保存到 localStorage（即使 toolsToSave 為空也允許保存）
      if (idToSave) {
        try {
          const storageKey = `assistant_${idToSave}_allowedTools`;
          localStorage.setItem(storageKey, JSON.stringify(toolsToSave));
          console.log('[AssistantMaintenanceModal] ✅ Pre-saved to localStorage:', {
            idToSave,
            storageKey,
            allowedCategories,
            allowedCategoriesCount: allowedCategories.length,
            toolsToSave,
            toolsToSaveCount: toolsToSave.length,
            hasWebSearch: toolsToSave.includes('web_search'),
          });

          // 验证保存
          const verify = localStorage.getItem(storageKey);
          const verifyParsed = verify ? JSON.parse(verify) : null;
          console.log('[AssistantMaintenanceModal] 🔍 Verification:', {
            storageKey,
            stored: verify,
            parsed: verifyParsed,
            isArray: Array.isArray(verifyParsed),
            hasWebSearch: Array.isArray(verifyParsed) && verifyParsed.includes('web_search'),
          });

          // 触发自定义事件，通知其他组件更新（即使工具列表為空也觸發）
          window.dispatchEvent(new CustomEvent('assistantToolsUpdated', {
            detail: {
              assistantId: idToSave,
              allowedTools: toolsToSave,
            }
          }));
          console.log('[AssistantMaintenanceModal] 📢 Dispatched assistantToolsUpdated event');
        } catch (e) {
          console.error('[AssistantMaintenanceModal] ❌ Failed to pre-save to localStorage:', e);
          // 不阻止保存流程，只記錄錯誤
        }
      } else {
        console.warn('[AssistantMaintenanceModal] ⚠️ Cannot pre-save: No assistant ID', {
          hasAssistantIdProp: !!assistantId,
          assistantIdProp: assistantId,
          hasAssistantIdFromObject: !!assistant?.id,
          assistantIdFromObject: assistant?.id,
        });
      }

      if (onSave) {
        console.log('[AssistantMaintenanceModal] 📤 Calling onSave callback...');
        await onSave(data);
        console.log('[AssistantMaintenanceModal] ✅ onSave callback completed');
      } else {
        console.warn('[AssistantMaintenanceModal] ⚠️ No onSave callback provided!');
      }

      handleClose();
    } catch (err: any) {
      console.error('[AssistantMaintenanceModal] ❌ Error in handleSave:', err);
      setError(err.message || '保存失敗，請稍後再試');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 添加技能
  const addSkill = () => {
    if (skillInput.trim() && !skills.includes(skillInput.trim())) {
      setSkills([...skills, skillInput.trim()]);
      setSkillInput('');
    }
  };

  // 移除技能
  const removeSkill = (skill: string) => {
    setSkills(skills.filter(s => s !== skill));
  };

  // 添加限制
  const addLimitation = () => {
    if (limitationInput.trim() && !limitations.includes(limitationInput.trim())) {
      setLimitations([...limitations, limitationInput.trim()]);
      setLimitationInput('');
    }
  };

  // 移除限制
  const removeLimitation = (limitation: string) => {
    setLimitations(limitations.filter(l => l !== limitation));
  };

  // 添加知識庫
  const addKnowledgeBase = () => {
    if (knowledgeBaseInput.trim() && !knowledgeBases.includes(knowledgeBaseInput.trim())) {
      setKnowledgeBases([...knowledgeBases, knowledgeBaseInput.trim()]);
      setKnowledgeBaseInput('');
    }
  };

  // 移除知識庫
  const removeKnowledgeBase = (kb: string) => {
    setKnowledgeBases(knowledgeBases.filter(k => k !== kb));
  };

  // 切換類別選擇（勾選/取消勾選）
  const toggleCategory = (category: string) => {
    if (allowedCategories.includes(category)) {
      setAllowedCategories(allowedCategories.filter(c => c !== category));
    } else {
      setAllowedCategories([...allowedCategories, category]);
    }
  };

  // 從類別獲取該類別下的所有工具ID
  const getToolsByCategories = (categories: string[]): string[] => {
    if (categories.length === 0) return [];
    if (tools.length === 0) {
      console.warn('[AssistantMaintenanceModal] ⚠️ Tools not loaded yet, returning empty array');
      return [];
    }
    return tools
      .filter(tool => categories.includes(tool.category))
      .map(tool => tool.id);
  };

  // 獲取完整的工具ID列表（包括類別工具和文件編輯工具）
  const getAllowedTools = (): string[] => {
    const categoryTools = getToolsByCategories(allowedCategories);
    const allTools = [...categoryTools];

    // 如果啟用文件編輯，添加 document_editing 工具
    if (enableFileEditing && !allTools.includes('document_editing')) {
      allTools.push('document_editing');
    }

    return allTools;
  };

  // 从 API 获取工具列表
  useEffect(() => {
    const fetchTools = async () => {
      setIsLoadingTools(true);
      setToolsError(null);
      try {
        console.log('[AssistantMaintenanceModal] Fetching tools from API...');
        const response = await apiGet<{
          success: boolean;
          data: {
            tools: Array<{
              name: string;
              category: string;
              description: string;
              purpose?: string;
            }>;
            total: number;
          };
        }>('/tools/registry?is_active=true');

        console.log('[AssistantMaintenanceModal] API Response:', response);
        console.log('[AssistantMaintenanceModal] Response data:', response?.data);
        console.log('[AssistantMaintenanceModal] Response data.tools:', response?.data?.tools);
        console.log('[AssistantMaintenanceModal] Response data.tools length:', response?.data?.tools?.length);

        if (response && response.success && response.data) {
          // 检查 tools 是否存在且是数组
          if (!response.data.tools || !Array.isArray(response.data.tools)) {
            console.error('[AssistantMaintenanceModal] Invalid tools array:', response.data.tools);
            setToolsError('工具列表格式錯誤：tools 不是數組');
            setTools([]);
            return;
          }

          const toolsList: ToolInfo[] = response.data.tools.map((tool) => ({
            id: tool.name,
            name: tool.name,
            description: tool.description || tool.purpose || '',
            category: tool.category,
            icon: getToolIcon(tool.name, tool.category),
          }));

          console.log('[AssistantMaintenanceModal] Processed tools:', toolsList.length, toolsList);

          setTools(toolsList);

          // 提取所有唯一分类
          const uniqueCategories = Array.from(new Set(toolsList.map((t) => t.category)));
          setCategories(uniqueCategories);

          // 如果已有選中的工具（從舊數據或編輯模式加載），從工具推斷類別
          // 否則默認選中所有類別
          if (toolsList.length > 0) {
            // 嘗試從 localStorage 讀取舊的工具ID數據並轉換為類別
            const idToLoad = assistantId || assistant?.id;
            if (idToLoad) {
              try {
                const storageKey = `assistant_${idToLoad}_allowedTools`;
                const stored = localStorage.getItem(storageKey);
                if (stored) {
                    const toolIds = JSON.parse(stored);
                    if (Array.isArray(toolIds) && toolIds.length > 0) {
                      // 檢查是否包含文件編輯工具
                      const hasFileEditing = toolIds.includes('document_editing') ||
                                            toolIds.includes('file_editing') ||
                                            toolIds.includes('documentEditing') ||
                                            toolIds.includes('fileEditing');
                      if (hasFileEditing) {
                        setEnableFileEditing(true);
                      }

                      // 從工具ID推斷類別（此時 toolsList 已設置）
                      // 過濾掉文件編輯相關的工具ID，只處理類別工具
                      const categoryToolIds = toolIds.filter(id =>
                        !['document_editing', 'file_editing', 'documentEditing', 'fileEditing'].includes(id)
                      );

                      if (categoryToolIds.length > 0) {
                        const inferredCategories = Array.from(new Set(
                          toolsList
                            .filter(tool => categoryToolIds.includes(tool.id))
                            .map(tool => tool.category)
                        ));
                        if (inferredCategories.length > 0) {
                          setAllowedCategories(inferredCategories);
                          console.log('[AssistantMaintenanceModal] 從舊數據推斷類別:', inferredCategories);
                        }
                      }

                      // 如果有工具數據，設置完成後返回
                      setIsLoadingTools(false);
                      return;
                    }
                }
              } catch (e) {
                console.warn('[AssistantMaintenanceModal] 讀取舊數據失敗:', e);
              }
            }

            // 如果沒有舊數據，默認選中所有類別
            if (allowedCategories.length === 0) {
              setAllowedCategories(uniqueCategories);
              console.log('[AssistantMaintenanceModal] 默认选中所有類別:', uniqueCategories.length);
            }
          } else {
            console.warn('[AssistantMaintenanceModal] No tools found in response');
            setToolsError('未找到任何工具，請確認工具已註冊到 ArangoDB');
          }
        } else {
          console.error('[AssistantMaintenanceModal] Invalid response format:', response);
          setToolsError('無法獲取工具列表：響應格式錯誤');
          setTools([]);
        }
      } catch (error: any) {
        console.error('[AssistantMaintenanceModal] Failed to fetch tools:', error);
        const errorMessage = error?.message || error?.toString() || '未知錯誤';
        setToolsError(`載入工具列表失敗：${errorMessage}`);
        setTools([]);
      } finally {
        setIsLoadingTools(false);
      }
    };

    if (isOpen && activeTab === 'resources') {
      fetchTools();
    }
  }, [isOpen, activeTab]);

  // 當工具列表加載完成後，如果有舊的工具ID數據，轉換為類別
  useEffect(() => {
    // 這個 effect 用於處理從 localStorage 加載的舊數據（工具ID格式）
    // 如果 tools 已加載且 allowedCategories 為空，嘗試從其他地方獲取
    // 注意：這裡假設舊數據可能通過其他方式傳入，需要根據實際情況調整
  }, [tools]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition"
      onClick={handleClose}
    >
      <div
        className={cn(
          "bg-secondary border border-primary rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col theme-transition"
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 模態框頭部 */}
        <div className="p-4 border-b border-primary flex items-center justify-between bg-purple-500/10">
          <div className="flex items-center">
            <i className="fa-solid fa-robot mr-3 text-purple-400"></i>
            <h3 className="text-lg font-semibold text-primary">
              {assistantId ? t('assistant.maintenance.title', '助理維護') : t('assistant.maintenance.new', '新建助理')}
            </h3>
          </div>
          <button
            onClick={handleClose}
            className="p-2 rounded-full hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
            disabled={isSubmitting}
            aria-label={t('modal.close', '關閉')}
          >
            <i className="fa-solid fa-times"></i>
          </button>
        </div>

        {/* 標籤頁導航 */}
        <div className="flex border-b border-primary bg-tertiary/20 overflow-x-auto">
          <button
            onClick={() => setActiveTab('basic')}
            className={cn(
              "px-6 py-3 text-sm font-medium transition-colors whitespace-nowrap",
              activeTab === 'basic'
                ? 'text-purple-400 border-b-2 border-purple-400'
                : 'text-tertiary hover:text-primary'
            )}
          >
            {t('assistant.maintenance.tabs.basic', '基本資訊')}
          </button>
          <button
            onClick={() => setActiveTab('resources')}
            className={cn(
              "px-6 py-3 text-sm font-medium transition-colors whitespace-nowrap",
              activeTab === 'resources'
                ? 'text-purple-400 border-b-2 border-purple-400'
                : 'text-tertiary hover:text-primary'
            )}
          >
            {t('assistant.maintenance.tabs.resources', '資源配置')}
          </button>
          <button
            onClick={() => setActiveTab('behavior')}
            className={cn(
              "px-6 py-3 text-sm font-medium transition-colors whitespace-nowrap",
              activeTab === 'behavior'
                ? 'text-purple-400 border-b-2 border-purple-400'
                : 'text-tertiary hover:text-primary'
            )}
          >
            {t('assistant.maintenance.tabs.behavior', '行為配置')}
          </button>
          <button
            onClick={() => setActiveTab('visibility')}
            className={cn(
              "px-6 py-3 text-sm font-medium transition-colors whitespace-nowrap",
              activeTab === 'visibility'
                ? 'text-purple-400 border-b-2 border-purple-400'
                : 'text-tertiary hover:text-primary'
            )}
          >
            {t('assistant.maintenance.tabs.visibility', '可見性')}
          </button>
        </div>

        {/* 內容區域 */}
        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* 基本資訊標籤頁 */}
          {activeTab === 'basic' && (
            <div className="space-y-4">
              {/* 助理名稱 */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  {t('assistant.maintenance.name', '助理名稱')} *
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder={t('assistant.maintenance.namePlaceholder', '輸入助理名稱')}
                />
              </div>

              {/* 圖標選擇 */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  {t('assistant.maintenance.icon', '圖標')}
                </label>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setShowIconPicker(true)}
                    className="p-3 bg-tertiary border border-primary rounded-lg hover:bg-hover transition-colors"
                  >
                    <IconRenderer iconName={selectedIcon} size={24} />
                  </button>
                  <span className="text-sm text-tertiary">{selectedIcon}</span>
                </div>
              </div>

              {/* 角色說明 */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  {t('assistant.maintenance.role', '角色說明')} *
                </label>
                <textarea
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  rows={4}
                  className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder={t('assistant.maintenance.rolePlaceholder', '描述助理的角色和職責')}
                />
              </div>

              {/* 技能 */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  {t('assistant.maintenance.skills', '技能')}
                </label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={skillInput}
                    onChange={(e) => setSkillInput(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addSkill();
                      }
                    }}
                    className="flex-1 px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder={t('assistant.maintenance.skillPlaceholder', '輸入技能後按 Enter')}
                  />
                  <button
                    onClick={addSkill}
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                  >
                    {t('common.add', '添加')}
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {skills.map((skill, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-purple-500/20 text-purple-400 rounded-full text-sm flex items-center gap-2"
                    >
                      {skill}
                      <button
                        onClick={() => removeSkill(skill)}
                        className="text-purple-400 hover:text-purple-300"
                      >
                        <i className="fa-solid fa-times"></i>
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              {/* 限制 */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  {t('assistant.maintenance.limitations', '限制')}
                </label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={limitationInput}
                    onChange={(e) => setLimitationInput(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addLimitation();
                      }
                    }}
                    className="flex-1 px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder={t('assistant.maintenance.limitationPlaceholder', '輸入限制後按 Enter')}
                  />
                  <button
                    onClick={addLimitation}
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                  >
                    {t('common.add', '添加')}
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {limitations.map((limitation, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-yellow-500/20 text-yellow-400 rounded-full text-sm flex items-center gap-2"
                    >
                      {limitation}
                      <button
                        onClick={() => removeLimitation(limitation)}
                        className="text-yellow-400 hover:text-yellow-300"
                      >
                        <i className="fa-solid fa-times"></i>
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              {/* 輸出格式 */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  {t('assistant.maintenance.outputFormat', '輸出格式')}
                </label>
                <textarea
                  value={outputFormat}
                  onChange={(e) => setOutputFormat(e.target.value)}
                  rows={3}
                  className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder={t('assistant.maintenance.outputFormatPlaceholder', '描述輸出格式要求')}
                />
              </div>
            </div>
          )}

          {/* 資源配置標籤頁 */}
          {activeTab === 'resources' && (
            <div className="space-y-4">
              {/* 可接觸的知識庫 */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  {t('assistant.maintenance.knowledgeBases', '可接觸的知識庫')}
                </label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={knowledgeBaseInput}
                    onChange={(e) => setKnowledgeBaseInput(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addKnowledgeBase();
                      }
                    }}
                    className="flex-1 px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder={t('assistant.maintenance.knowledgeBasePlaceholder', '輸入知識庫名稱後按 Enter')}
                  />
                  <button
                    onClick={addKnowledgeBase}
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                  >
                    {t('common.add', '添加')}
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {knowledgeBases.map((kb, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-sm flex items-center gap-2"
                    >
                      {kb}
                      <button
                        onClick={() => removeKnowledgeBase(kb)}
                        className="text-blue-400 hover:text-blue-300"
                      >
                        <i className="fa-solid fa-times"></i>
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              {/* 文件編輯功能 */}
              <div>
                <label className="block text-sm font-medium text-primary mb-3">
                  {t('assistant.maintenance.fileEditing', '文件編輯功能')}
                </label>
                <div className="border border-primary rounded-lg p-4">
                  <label className="flex items-start cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enableFileEditing}
                      onChange={(e) => setEnableFileEditing(e.target.checked)}
                      className="mt-1 mr-3 w-5 h-5 text-purple-600 border-primary rounded focus:ring-purple-500 focus:ring-2"
                    />
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <i className="fa-solid fa-file-edit text-purple-400"></i>
                        <span className="font-medium text-primary">
                          {t('assistant.maintenance.enableFileEditing', '啟用文件編輯功能')}
                        </span>
                      </div>
                      <p className="text-sm text-tertiary mb-2">
                        {t('assistant.maintenance.fileEditingDesc', '啟用後，該助理將具備文件編輯能力，可以在聊天時編輯 Markdown 文件')}
                      </p>
                      <div className="text-xs text-tertiary bg-tertiary/50 p-2 rounded">
                        <p className="mb-1">
                          <strong>{t('assistant.maintenance.fileEditingFeatures', '功能說明')}:</strong>
                        </p>
                        <ul className="list-disc list-inside space-y-1 ml-2">
                          <li>{t('assistant.maintenance.fileEditingFeature1', '聊天輸入框會顯示文件選擇器圖標')}</li>
                          <li>{t('assistant.maintenance.fileEditingFeature2', '可以選擇 Markdown 文件進行編輯')}</li>
                          <li>{t('assistant.maintenance.fileEditingFeature3', '聊天時會自動調用文件編輯 Agent')}</li>
                          <li>{t('assistant.maintenance.fileEditingFeature4', '支持流式編輯預覽和編輯確認')}</li>
                        </ul>
                      </div>
                    </div>
                  </label>
                </div>
              </div>

              {/* 可使用的工具類別 */}
              <div>
                <label className="block text-sm font-medium text-primary mb-3">
                  {t('assistant.maintenance.allowedTools', '可使用的工具類別')}
                  <span className="ml-2 text-xs text-tertiary font-normal">
                    ({allowedCategories.length} / {categories.length} {t('common.selected', '已選')})
                  </span>
                </label>

                {/* 類別選擇容器 */}
                <div className="border border-primary rounded-lg p-4">
                  {isLoadingTools ? (
                    <div className="p-8 text-center text-tertiary">
                      <i className="fa-solid fa-spinner fa-spin text-4xl mb-2 opacity-50"></i>
                      <p>{t('common.loading', '載入中...')}</p>
                    </div>
                  ) : toolsError ? (
                    <div className="p-8 text-center">
                      <i className="fa-solid fa-exclamation-triangle text-yellow-400 text-4xl mb-2"></i>
                      <p className="text-yellow-400 mb-2">{toolsError}</p>
                      <p className="text-xs text-tertiary">
                        {t('assistant.maintenance.toolsNote', '提示：工具選項由開發團隊持續增加')}
                      </p>
                    </div>
                  ) : categories.length === 0 ? (
                    <div className="p-8 text-center text-tertiary">
                      <i className="fa-solid fa-folder-open text-4xl mb-2 opacity-50"></i>
                      <p>{t('assistant.maintenance.noCategoriesFound', '未找到工具類別')}</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {categories.map((category) => {
                        const isSelected = allowedCategories.includes(category);
                        const categoryTools = tools.filter(t => t.category === category);
                        const toolCount = categoryTools.length;

                        return (
                          <label
                            key={category}
                            className={cn(
                              'flex items-center p-4 border-2 rounded-lg cursor-pointer transition-all',
                              isSelected
                                ? 'border-purple-500 bg-purple-500/10'
                                : 'border-primary hover:border-purple-500/50 hover:bg-tertiary'
                            )}
                          >
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleCategory(category)}
                              className="mr-3 w-5 h-5 text-purple-600 border-primary rounded focus:ring-purple-500 focus:ring-2"
                            />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-medium text-primary">{category}</span>
                                <span className="text-xs text-tertiary bg-tertiary px-2 py-0.5 rounded">
                                  {toolCount} {t('assistant.maintenance.tools', '個工具')}
                                </span>
                              </div>
                              {categoryTools.length > 0 && (
                                <p className="text-xs text-tertiary line-clamp-1">
                                  {categoryTools.slice(0, 3).map(t => t.name).join('、')}
                                  {categoryTools.length > 3 && '...'}
                                </p>
                              )}
                            </div>
                          </label>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* 已選類別快速查看 */}
                {allowedCategories.length > 0 && (
                  <div className="mt-3 p-3 bg-purple-500/10 border border-purple-500/50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-primary">
                        {t('assistant.maintenance.selectedCategories', '已選類別')} ({allowedCategories.length})
                      </span>
                      <button
                        onClick={() => setAllowedCategories([])}
                        className="text-xs text-purple-400 hover:text-purple-300"
                      >
                        {t('common.clearAll', '清除全部')}
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {allowedCategories.map((category) => {
                        const categoryTools = tools.filter(t => t.category === category);
                        return (
                          <span
                            key={category}
                            className="px-3 py-1 bg-purple-600 text-white rounded-full text-xs flex items-center gap-2"
                          >
                            {category}
                            <span className="text-purple-200">({categoryTools.length})</span>
                            <button
                              onClick={() => toggleCategory(category)}
                              className="hover:text-purple-100"
                            >
                              <i className="fa-solid fa-times"></i>
                            </button>
                          </span>
                        );
                      })}
                    </div>
                    <div className="mt-2 text-xs text-tertiary">
                      {t('assistant.maintenance.categoryNote', '提示：選擇類別後，該類別下的所有工具都會被啟用')}
                    </div>
                  </div>
                )}

                <p className="text-xs text-tertiary mt-3">
                  {t('assistant.maintenance.toolsNote', '提示：工具選項由開發團隊持續增加')}
                </p>
              </div>
            </div>
          )}

          {/* 行為配置標籤頁 */}
          {activeTab === 'behavior' && (
            <div className="space-y-4">
              {/* Temperature */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  {t('assistant.maintenance.temperature', '回應溫度')} ({temperature.toFixed(2)})
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-tertiary mt-1">
                  <span>{t('assistant.maintenance.temperatureLow', '更確定')}</span>
                  <span>{t('assistant.maintenance.temperatureHigh', '更創造')}</span>
                </div>
              </div>

              {/* 開場問候 */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  {t('assistant.maintenance.greeting', '開場問候')}
                </label>
                <textarea
                  value={greeting}
                  onChange={(e) => setGreeting(e.target.value)}
                  rows={3}
                  className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder={t('assistant.maintenance.greetingPlaceholder', '輸入開場問候語')}
                />
              </div>

              {/* 預設回應（3個問題） */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  {t('assistant.maintenance.presetResponses', '預設回應（3個問題）')}
                </label>
                {[0, 1, 2].map((index) => (
                  <div key={index} className="mb-3">
                    <label className="block text-xs text-tertiary mb-1">
                      {t('assistant.maintenance.question', '問題')} {index + 1}
                    </label>
                    <textarea
                      value={presetResponses[index] || ''}
                      onChange={(e) => {
                        const newResponses = [...presetResponses];
                        newResponses[index] = e.target.value;
                        setPresetResponses(newResponses);
                      }}
                      rows={2}
                      className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder={t('assistant.maintenance.responsePlaceholder', '輸入預設回應')}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 可見性標籤頁 */}
          {activeTab === 'visibility' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-primary mb-4">
                  {t('assistant.maintenance.visibility', '助理可見性')}
                </label>
                <div className="space-y-3">
                  <label className="flex items-center p-4 border border-primary rounded-lg cursor-pointer hover:bg-tertiary transition-colors">
                    <input
                      type="radio"
                      name="visibility"
                      value="private"
                      checked={visibility === 'private'}
                      onChange={(e) => setVisibility(e.target.value as 'private' | 'public')}
                      className="mr-3"
                    />
                    <div>
                      <div className="font-medium text-primary">
                        {t('assistant.maintenance.private', '私有 (Private)')}
                      </div>
                      <div className="text-sm text-tertiary">
                        {t('assistant.maintenance.privateDesc', '只有您可以看到和使用此助理')}
                      </div>
                    </div>
                  </label>
                  <label className="flex items-center p-4 border border-primary rounded-lg cursor-pointer hover:bg-tertiary transition-colors">
                    <input
                      type="radio"
                      name="visibility"
                      value="public"
                      checked={visibility === 'public'}
                      onChange={(e) => setVisibility(e.target.value as 'private' | 'public')}
                      className="mr-3"
                    />
                    <div>
                      <div className="font-medium text-primary">
                        {t('assistant.maintenance.public', '公開 (Public)')}
                      </div>
                      <div className="text-sm text-tertiary">
                        {t('assistant.maintenance.publicDesc', '所有用戶都可以看到和使用此助理')}
                      </div>
                    </div>
                  </label>
                </div>
              </div>

              <div className="p-4 bg-yellow-500/10 border border-yellow-500/50 rounded-lg">
                <div className="flex items-start">
                  <i className="fa-solid fa-info-circle text-yellow-400 mr-2 mt-1"></i>
                  <div className="text-sm text-yellow-400">
                    {t('assistant.maintenance.noReviewNote', '注意：助理不需要 AI-Box 管理審查，創建後立即可用。')}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 底部操作按鈕 */}
        <div className="p-4 border-t border-primary flex justify-end gap-3 bg-tertiary/20">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-sm rounded-lg border border-primary hover:bg-tertiary transition-colors text-primary"
            disabled={isSubmitting}
          >
            {t('common.cancel', '取消')}
          </button>
          <button
            onClick={handleSave}
            disabled={Boolean(
              isSubmitting ||
              // 新建模式：名稱和角色必填
              (!assistantId && (!name.trim() || !role.trim())) ||
              // 編輯模式：如果有修改，允許保存（即使名稱或角色為空）；如果沒有修改，名稱和角色必填
              (assistantId && !hasChanges && (!name.trim() || !role.trim()))
            )}
            className="px-4 py-2 text-sm rounded-lg bg-purple-600 hover:bg-purple-700 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title={
              assistantId && hasChanges && (!name.trim() || !role.trim())
                ? t('assistant.maintenance.saveWithChanges', '檢測到修改，可以保存（但建議填寫名稱和角色）')
                : ''
            }
          >
            {isSubmitting ? t('common.saving', '保存中...') : t('common.save', '保存')}
          </button>
        </div>
      </div>

      {/* 圖標選擇器 */}
      <IconPicker
        isOpen={showIconPicker}
        selectedIcon={selectedIcon}
        onSelect={(icon) => {
          setSelectedIcon(icon);
          setShowIconPicker(false);
        }}
        onClose={() => setShowIconPicker(false)}
      />
    </div>
  );
}
