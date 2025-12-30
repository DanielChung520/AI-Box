/**
 * Assistant 維護模態框組件
 * 功能：提供助理維護界面，包含角色說明、技能、限制等配置
 * 創建日期：2025-01-27
 * 創建人：Daniel Chung
 * 最後修改日期：2025-12-30
 */

import { useState, useEffect } from 'react';
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
  const [allowedTools, setAllowedTools] = useState<string[]>([]); // 可使用的Tools（工具ID列表）

  // 工具列表相关状态
  const [tools, setTools] = useState<ToolInfo[]>([]); // 所有工具列表
  const [filteredTools, setFilteredTools] = useState<ToolInfo[]>([]); // 过滤后的工具列表
  const [searchQuery, setSearchQuery] = useState(''); // 搜索关键词
  const [selectedCategory, setSelectedCategory] = useState<string>('all'); // 选中的分类
  const [categories, setCategories] = useState<string[]>([]); // 所有分类列表
  const [isLoadingTools, setIsLoadingTools] = useState(false); // 加载状态
  const [toolsError, setToolsError] = useState<string | null>(null); // 工具加载错误

  // 行為配置
  const [temperature, setTemperature] = useState(0.7); // Temperature (0-1)
  const [greeting, setGreeting] = useState(''); // 開場問候
  const [presetResponses, setPresetResponses] = useState<string[]>(['', '', '']); // 回應_3_個問題

  // 可見性
  const [visibility, setVisibility] = useState<'private' | 'public'>('private');

  const handleClose = () => {
    if (!isSubmitting) {
      setError(null);
      onClose();
    }
  };

  const handleSave = async () => {
    console.log('[AssistantMaintenanceModal] 🚀 handleSave called!', {
      assistantId,
      allowedTools,
      allowedToolsCount: allowedTools.length,
      hasOnSave: !!onSave,
      isSubmitting,
    });

    setError(null);
    setIsSubmitting(true);

    try {
      const data: AssistantMaintenanceData = {
        id: assistantId, // 包含助理 ID，用于保存到 localStorage
        name: name.trim(),
        icon: selectedIcon,
        role: role.trim(),
        skills: skills,
        limitations: limitations,
        outputFormat: outputFormat.trim(),
        knowledgeBases: knowledgeBases,
        allowedTools: allowedTools,
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

      console.log('[AssistantMaintenanceModal] 🔑 ID resolution:', {
        assistantIdProp: assistantId,
        assistantIdFromObject: assistant?.id,
        idToSave,
        hasAllowedTools: allowedTools.length > 0,
        allowedToolsCount: allowedTools.length,
      });

      if (idToSave && allowedTools.length > 0) {
        try {
          const storageKey = `assistant_${idToSave}_allowedTools`;
          localStorage.setItem(storageKey, JSON.stringify(allowedTools));
          console.log('[AssistantMaintenanceModal] ✅ Pre-saved to localStorage:', {
            idToSave,
            storageKey,
            allowedTools,
            hasWebSearch: allowedTools.includes('web_search'),
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

          // 触发自定义事件，通知其他组件更新
          window.dispatchEvent(new CustomEvent('assistantToolsUpdated', {
            detail: {
              assistantId: idToSave,
              allowedTools: allowedTools,
            }
          }));
          console.log('[AssistantMaintenanceModal] 📢 Dispatched assistantToolsUpdated event');
        } catch (e) {
          console.error('[AssistantMaintenanceModal] ❌ Failed to pre-save to localStorage:', e);
        }
      } else {
        console.warn('[AssistantMaintenanceModal] ⚠️ Cannot pre-save:', {
          hasAssistantIdProp: !!assistantId,
          assistantIdProp: assistantId,
          hasAssistantIdFromObject: !!assistant?.id,
          assistantIdFromObject: assistant?.id,
          hasIdToSave: !!idToSave,
          idToSave,
          hasAllowedTools: allowedTools.length > 0,
          allowedToolsCount: allowedTools.length,
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

  // 切換工具選擇（勾選/取消勾選）
  const toggleTool = (toolId: string) => {
    if (allowedTools.includes(toolId)) {
      setAllowedTools(allowedTools.filter(t => t !== toolId));
    } else {
      setAllowedTools([...allowedTools, toolId]);
    }
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
            setFilteredTools([]);
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
          setFilteredTools(toolsList);

          // 提取所有唯一分类
          const uniqueCategories = Array.from(new Set(toolsList.map((t) => t.category)));
          setCategories(uniqueCategories);

          // 默认选中所有工具
          if (toolsList.length > 0) {
            const allToolIds = toolsList.map((t) => t.id);
            setAllowedTools(allToolIds);
            console.log('[AssistantMaintenanceModal] 默认选中所有工具:', allToolIds.length);
          } else {
            console.warn('[AssistantMaintenanceModal] No tools found in response');
            setToolsError('未找到任何工具，請確認工具已註冊到 ArangoDB');
          }
        } else {
          console.error('[AssistantMaintenanceModal] Invalid response format:', response);
          setToolsError('無法獲取工具列表：響應格式錯誤');
          setTools([]);
          setFilteredTools([]);
        }
      } catch (error: any) {
        console.error('[AssistantMaintenanceModal] Failed to fetch tools:', error);
        const errorMessage = error?.message || error?.toString() || '未知錯誤';
        setToolsError(`載入工具列表失敗：${errorMessage}`);
        setTools([]);
        setFilteredTools([]);
      } finally {
        setIsLoadingTools(false);
      }
    };

    if (isOpen && activeTab === 'resources') {
      fetchTools();
    }
  }, [isOpen, activeTab]);

  // 过滤工具列表
  useEffect(() => {
    let filtered = tools;

    // 按分类过滤
    if (selectedCategory !== 'all') {
      filtered = filtered.filter((t) => t.category === selectedCategory);
    }

    // 按搜索关键词过滤
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (t) =>
          t.name.toLowerCase().includes(query) ||
          t.description.toLowerCase().includes(query) ||
          t.category.toLowerCase().includes(query)
      );
    }

    setFilteredTools(filtered);
  }, [tools, selectedCategory, searchQuery]);

  // 批量操作：全选当前
  const selectAllFiltered = () => {
    const filteredIds = filteredTools.map((t) => t.id);
    setAllowedTools([...new Set([...allowedTools, ...filteredIds])]);
  };

  // 批量操作：取消当前
  const deselectAllFiltered = () => {
    const filteredIds = filteredTools.map((t) => t.id);
    setAllowedTools(allowedTools.filter((id) => !filteredIds.includes(id)));
  };

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

              {/* 可使用的Tools */}
              <div>
                <label className="block text-sm font-medium text-primary mb-3">
                  {t('assistant.maintenance.allowedTools', '可使用的Tools')}
                  <span className="ml-2 text-xs text-tertiary font-normal">
                    ({allowedTools.length} / {tools.length} {t('common.selected', '已選')})
                  </span>
                </label>

                {/* 搜索和筛选栏 */}
                <div className="mb-4 space-y-2">
                  {/* 搜索框 */}
                  <div className="relative">
                    <i className="fa-solid fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-tertiary"></i>
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder={t('assistant.maintenance.searchTools', '搜索工具...')}
                      className="w-full pl-10 pr-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>

                  {/* 分类筛选 */}
                  {categories.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => setSelectedCategory('all')}
                        className={cn(
                          'px-3 py-1 text-sm rounded-full border transition-colors',
                          selectedCategory === 'all'
                            ? 'bg-purple-600 text-white border-purple-600'
                            : 'bg-tertiary text-primary border-primary hover:bg-hover'
                        )}
                      >
                        {t('common.all', '全部')}
                      </button>
                      {categories.map((category) => (
                        <button
                          key={category}
                          onClick={() => setSelectedCategory(category)}
                          className={cn(
                            'px-3 py-1 text-sm rounded-full border transition-colors',
                            selectedCategory === category
                              ? 'bg-purple-600 text-white border-purple-600'
                              : 'bg-tertiary text-primary border-primary hover:bg-hover'
                          )}
                        >
                          {category}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* 批量操作按钮 */}
                  {filteredTools.length > 0 && (
                    <div className="flex gap-2">
                      <button
                        onClick={selectAllFiltered}
                        className="px-3 py-1 text-sm bg-purple-600 hover:bg-purple-700 text-white rounded transition-colors"
                      >
                        {t('common.selectAll', '全選當前')}
                      </button>
                      <button
                        onClick={deselectAllFiltered}
                        className="px-3 py-1 text-sm bg-tertiary hover:bg-hover text-primary border border-primary rounded transition-colors"
                      >
                        {t('common.deselectAll', '取消當前')}
                      </button>
                    </div>
                  )}
                </div>

                {/* 工具列表容器 - 限制高度并添加滚动 */}
                <div className="border border-primary rounded-lg max-h-[400px] overflow-y-auto">
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
                  ) : filteredTools.length === 0 ? (
                    <div className="p-8 text-center text-tertiary">
                      <i className="fa-solid fa-search text-4xl mb-2 opacity-50"></i>
                      <p>{t('assistant.maintenance.noToolsFound', '未找到匹配的工具')}</p>
                    </div>
                  ) : (
                    <div className="p-2 space-y-2">
                      {filteredTools.map((tool) => {
                        const isSelected = allowedTools.includes(tool.id);
                        return (
                          <label
                            key={tool.id}
                            className={cn(
                              'flex items-start p-3 border-2 rounded-lg cursor-pointer transition-all',
                              isSelected
                                ? 'border-purple-500 bg-purple-500/10'
                                : 'border-primary hover:border-purple-500/50 hover:bg-tertiary'
                            )}
                          >
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleTool(tool.id)}
                              className="mt-1 mr-3 w-5 h-5 text-purple-600 border-primary rounded focus:ring-purple-500 focus:ring-2"
                            />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <i
                                  className={cn(
                                    'fa-solid',
                                    tool.icon || 'fa-tools',
                                    'text-purple-400 flex-shrink-0'
                                  )}
                                ></i>
                                <span className="font-medium text-primary truncate">{tool.name}</span>
                                <span className="text-xs text-tertiary bg-tertiary px-2 py-0.5 rounded flex-shrink-0">
                                  {tool.category}
                                </span>
                              </div>
                              <p className="text-sm text-tertiary line-clamp-2">{tool.description}</p>
                            </div>
                          </label>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* 已选工具快速查看 */}
                {allowedTools.length > 0 && (
                  <div className="mt-3 p-3 bg-purple-500/10 border border-purple-500/50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-primary">
                        {t('assistant.maintenance.selectedTools', '已選工具')} ({allowedTools.length})
                      </span>
                      <button
                        onClick={() => setAllowedTools([])}
                        className="text-xs text-purple-400 hover:text-purple-300"
                      >
                        {t('common.clearAll', '清除全部')}
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {allowedTools.map((toolId) => {
                        const tool = tools.find((t) => t.id === toolId);
                        if (!tool) return null;
                        return (
                          <span
                            key={toolId}
                            className="px-2 py-1 bg-purple-600 text-white rounded text-xs flex items-center gap-1"
                          >
                            {tool.name}
                            <button
                              onClick={() => toggleTool(toolId)}
                              className="hover:text-purple-200"
                            >
                              <i className="fa-solid fa-times"></i>
                            </button>
                          </span>
                        );
                      })}
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
            disabled={isSubmitting || !name.trim() || !role.trim()}
            className="px-4 py-2 text-sm rounded-lg bg-purple-600 hover:bg-purple-700 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
