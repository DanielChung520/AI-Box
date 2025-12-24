/**
 * Assistant 維護模態框組件
 * 功能：提供助理維護界面，包含角色說明、技能、限制等配置
 * 創建日期：2025-01-27
 * 創建人：Daniel Chung
 * 最後修改日期：2025-01-27
 */

import { useState } from 'react';
import { useLanguage } from '../contexts/languageContext';
import { cn } from '../lib/utils';
import IconPicker from './IconPicker';
import IconRenderer from './IconRenderer';

// 可用的工具列表（固定選項，由開發團隊持續增加）
export const AVAILABLE_TOOLS = [
  {
    id: 'clock',
    name: '時鐘',
    description: '記錄的時間上網確認',
    icon: 'fa-clock',
  },
  {
    id: 'browser',
    name: '上網',
    description: '系統的預設的瀏覽器',
    icon: 'fa-globe',
  },
  {
    id: 'code-react',
    name: '代碼工具 React/JS/TS',
    description: 'React、JavaScript/TypeScript 代碼工具',
    icon: 'fa-code',
  },
  {
    id: 'code-python',
    name: '代碼工具 Python',
    description: 'Python 代碼工具',
    icon: 'fa-python',
  },
] as const;

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
  const [allowedTools, setAllowedTools] = useState<string[]>([]); // 可使用的Tools（固定選項的ID列表）

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
    setError(null);
    setIsSubmitting(true);

    try {
      const data: AssistantMaintenanceData = {
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

      if (onSave) {
        await onSave(data);
      }

      handleClose();
    } catch (err: any) {
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
                </label>
                <div className="space-y-3">
                  {AVAILABLE_TOOLS.map((tool) => {
                    const isSelected = allowedTools.includes(tool.id);
                    return (
                      <label
                        key={tool.id}
                        className={cn(
                          "flex items-start p-4 border-2 rounded-lg cursor-pointer transition-all",
                          isSelected
                            ? "border-purple-500 bg-purple-500/10"
                            : "border-primary hover:border-purple-500/50 hover:bg-tertiary"
                        )}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleTool(tool.id)}
                          className="mt-1 mr-3 w-5 h-5 text-purple-600 border-primary rounded focus:ring-purple-500 focus:ring-2"
                        />
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <i className={`fa-solid ${tool.icon} text-purple-400`}></i>
                            <span className="font-medium text-primary">{tool.name}</span>
                          </div>
                          <p className="text-sm text-tertiary">{tool.description}</p>
                        </div>
                      </label>
                    );
                  })}
                </div>
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
