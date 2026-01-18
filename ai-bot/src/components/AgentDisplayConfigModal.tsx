// 代碼功能說明: Agent Display Config 編輯模態框組件
// 創建日期: 2026-01-13
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-15 09:16 UTC+8

/**
 * Agent Display Config 編輯模態框
 * 用於創建或編輯代理展示配置（名稱、描述、圖標、狀態、端點等）
 * 界面與 AgentRegistrationModal 保持一致
 */

import { useState, useEffect, useCallback } from 'react';
import { useLanguage } from '../contexts/languageContext';
import { cn } from '../lib/utils';
import { getAgentConfig, updateAgentConfig, verifySecret, generateSecret } from '../lib/api';
import type { AgentConfig, MultilingualText } from '../types/agentDisplayConfig';
import IconPicker from './IconPicker';

interface AgentDisplayConfigModalProps {
  isOpen: boolean;
  agentId?: string; // 編輯時傳入，創建時不傳
  categoryId?: string; // 創建時需要指定分類 ID
  onClose: () => void;
  onSuccess?: () => void;
}

type AgentType = 'planning' | 'execution' | 'review' | '';
type ProtocolType = 'http' | 'mcp';

export default function AgentDisplayConfigModal({
  isOpen,
  agentId,
  categoryId,
  onClose,
  onSuccess,
}: AgentDisplayConfigModalProps) {
  const { t, language } = useLanguage();
  const isEditMode = !!agentId;
  const [activeTab, setActiveTab] = useState<'basic' | 'endpoints' | 'display'>('basic');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 表單字段 - 基本資訊
  const [agentIdValue, setAgentIdValue] = useState('');
  const [categoryIdValue, setCategoryIdValue] = useState(categoryId || '');
  const [displayOrder, setDisplayOrder] = useState(1);
  const [isVisible, setIsVisible] = useState(true);
  const [selectedIcon, setSelectedIcon] = useState<string>('fa-robot');
  const [showIconPicker, setShowIconPicker] = useState(false);
  const [status, setStatus] = useState<'registering' | 'online' | 'maintenance' | 'deprecated'>('online');
  const [agentType, setAgentType] = useState<AgentType>('execution');
  const [capabilities, setCapabilities] = useState<string[]>([]);
  const [capabilityInput, setCapabilityInput] = useState('');

  // 多語言名稱
  const [nameEn, setNameEn] = useState('');
  const [nameZhCN, setNameZhCN] = useState('');
  const [nameZhTW, setNameZhTW] = useState('');

  // 多語言描述
  const [descriptionEn, setDescriptionEn] = useState('');
  const [descriptionZhCN, setDescriptionZhCN] = useState('');
  const [descriptionZhTW, setDescriptionZhTW] = useState('');

  // 端點配置
  const [isInternal, setIsInternal] = useState(false);
  const [protocol, setProtocol] = useState<ProtocolType>('mcp');
  const [httpEndpoint, setHttpEndpoint] = useState('');
  const [mcpEndpoint, setMcpEndpoint] = useState('https://mcp-gateway.896445070.workers.dev');

  // Secret 驗證（外部 Agent 需要）
  const [secretId, setSecretId] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [secretVerified, setSecretVerified] = useState(false);
  const [isVerifyingSecret, setIsVerifyingSecret] = useState(false);
  const [secretVerificationError, setSecretVerificationError] = useState<string | null>(null);
  const [isGeneratingSecret, setIsGeneratingSecret] = useState(false);

  // 能力列表輔助函數
  const addCapability = () => {
    const trimmed = capabilityInput.trim();
    if (trimmed && !capabilities.includes(trimmed)) {
      setCapabilities([...capabilities, trimmed]);
      setCapabilityInput('');
    }
  };

  const removeCapability = (cap: string) => {
    setCapabilities(capabilities.filter((c) => c !== cap));
  };

  // Secret 驗證處理
  const handleVerifySecret = async () => {
    if (!secretId.trim() || !secretKey.trim()) {
      setSecretVerificationError(t('agentConfig.errors.secretRequired', 'Secret ID 和 Secret Key 為必填項'));
      return;
    }

    setIsVerifyingSecret(true);
    setSecretVerificationError(null);

    try {
      const result = await verifySecret(secretId, secretKey);
      if (result.success && result.data?.valid) {
        setSecretVerified(true);
        setSecretVerificationError(null);
      } else {
        setSecretVerified(false);
        setSecretVerificationError(result.error || t('agentConfig.errors.secretInvalid', 'Secret 驗證失敗'));
      }
    } catch (err: any) {
      setSecretVerified(false);
      setSecretVerificationError(err.message || t('agentConfig.errors.secretVerificationFailed', 'Secret 驗證失敗'));
    } finally {
      setIsVerifyingSecret(false);
    }
  };

  // 加載現有配置（編輯模式）
  const loadAgentConfig = useCallback(async () => {
    if (!agentId) return;

    setIsLoading(true);
    setError(null);

    try {
      const config = await getAgentConfig(agentId);

      // 填充表單 - 基本資訊
      setAgentIdValue(config.id || agentId);
      setCategoryIdValue(config.category_id || '');
      setDisplayOrder(config.display_order || 1);
      setIsVisible(config.is_visible !== false);
      setSelectedIcon(config.icon || 'fa-robot');
      setStatus(config.status || 'online');
      setAgentType((config.agent_type as AgentType) || 'execution');
      setCapabilities(config.capabilities || []);

      // 填充多語言名稱
      if (config.name) {
        setNameEn(config.name.en || '');
        setNameZhCN(config.name.zh_CN || '');
        setNameZhTW(config.name.zh_TW || '');
      }

      // 填充多語言描述
      if (config.description) {
        setDescriptionEn(config.description.en || '');
        setDescriptionZhCN(config.description.zh_CN || '');
        setDescriptionZhTW(config.description.zh_TW || '');
      }

      // 填充端點配置
      setProtocol((config.protocol as ProtocolType) || 'mcp');
      const endpointUrl = config.endpoint_url || '';
      if (config.protocol === 'http' || (!config.protocol && endpointUrl.includes('http'))) {
        setHttpEndpoint(endpointUrl);
        setProtocol('http');
      } else {
        setMcpEndpoint(endpointUrl || 'https://mcp-gateway.896445070.workers.dev');
        setProtocol('mcp');
      }

      // 填充 Secret 資訊
      if (config.secret_id) {
        setSecretId(config.secret_id);
        setSecretVerified(true); // 已有 Secret 視為已驗證
        setIsInternal(false);
      } else {
        setIsInternal(true);
      }
      // Note: secret_key 通常不會從 API 返回，只在創建時使用

    } catch (err: any) {
      setError(err.message || t('agentConfig.errors.loadFailed', '載入配置失敗'));
    } finally {
      setIsLoading(false);
    }
  }, [agentId, t]);

  const resetForm = useCallback(() => {
    if (!isEditMode) {
      setAgentIdValue('');
    }
    setCategoryIdValue(categoryId || '');
    setDisplayOrder(1);
    setIsVisible(true);
    setSelectedIcon('fa-robot');
    setStatus('online');
    setAgentType('execution');
    setCapabilities([]);
    setCapabilityInput('');
    setNameEn('');
    setNameZhCN('');
    setNameZhTW('');
    setDescriptionEn('');
    setDescriptionZhCN('');
    setDescriptionZhTW('');
    setIsInternal(false);
    setProtocol('mcp');
    setHttpEndpoint('');
    setMcpEndpoint('https://mcp-gateway.896445070.workers.dev');
    setSecretId('');
    setSecretKey('');
    setSecretVerified(false);
    setSecretVerificationError(null);
    setError(null);
    setActiveTab('basic');
  }, [isEditMode, categoryId]);

  useEffect(() => {
    if (isOpen && isEditMode && agentId) {
      loadAgentConfig();
    } else if (isOpen && !isEditMode) {
      // 創建模式：重置表單
      resetForm();
    }
  }, [isOpen, agentId, isEditMode, loadAgentConfig, resetForm]);


  const handleClose = () => {
    if (!isSubmitting && !isLoading) {
      resetForm();
      onClose();
    }
  };

  const validateForm = (): boolean => {
    if (!isEditMode && !agentIdValue.trim()) {
      setError(t('agentConfig.errors.agentIdRequired', '代理 ID 為必填項'));
      return false;
    }
    if (!categoryIdValue.trim()) {
      setError(t('agentConfig.errors.categoryIdRequired', '分類 ID 為必填項'));
      return false;
    }
    if (!nameEn.trim() && !nameZhCN.trim() && !nameZhTW.trim()) {
      setError(t('agentConfig.errors.nameRequired', '至少需要填寫一個語言的名稱'));
      return false;
    }
    if (!descriptionEn.trim() && !descriptionZhCN.trim() && !descriptionZhTW.trim()) {
      setError(t('agentConfig.errors.descriptionRequired', '至少需要填寫一個語言的描述'));
      return false;
    }
    if (!selectedIcon) {
      setError(t('agentConfig.errors.iconRequired', '請選擇圖標'));
      return false;
    }
    if (!agentType) {
      setError(t('agentConfig.errors.agentTypeRequired', '請選擇 Agent 類型'));
      return false;
    }

    // 端點配置驗證
    if (!isInternal) {
      if (!secretVerified) {
        setError(t('agentConfig.errors.secretNotVerified', '請先驗證 Secret'));
        setActiveTab('endpoints');
        return false;
      }
      if (protocol === 'http' && !httpEndpoint.trim()) {
        setError(t('agentConfig.errors.httpEndpointRequired', 'HTTP 端點 URL 為必填項'));
        setActiveTab('endpoints');
        return false;
      }
      if (protocol === 'mcp' && !mcpEndpoint.trim()) {
        setError(t('agentConfig.errors.mcpEndpointRequired', 'MCP 端點 URL 為必填項'));
        setActiveTab('endpoints');
        return false;
      }
    }

    return true;
  };

  const handleSubmit = async () => {
    setError(null);

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      // 構建多語言文本
      const name: MultilingualText = {
        en: nameEn.trim() || nameZhTW.trim() || nameZhCN.trim() || '',
        zh_CN: nameZhCN.trim() || nameZhTW.trim() || nameEn.trim() || '',
        zh_TW: nameZhTW.trim() || nameZhCN.trim() || nameEn.trim() || '',
      };

      const description: MultilingualText = {
        en: descriptionEn.trim() || descriptionZhTW.trim() || descriptionZhCN.trim() || '',
        zh_CN: descriptionZhCN.trim() || descriptionZhTW.trim() || descriptionEn.trim() || '',
        zh_TW: descriptionZhTW.trim() || descriptionZhCN.trim() || descriptionEn.trim() || '',
      };

      // 構建 AgentConfig
      const agentConfig: AgentConfig = {
        id: agentIdValue.trim(),
        category_id: categoryIdValue.trim(),
        display_order: displayOrder,
        is_visible: isVisible,
        name,
        description,
        icon: selectedIcon,
        status,
        agent_type: agentType,
        protocol: isInternal ? undefined : protocol,
        endpoint_url: isInternal
          ? undefined
          : protocol === 'http'
          ? httpEndpoint.trim()
          : mcpEndpoint.trim(),
        secret_id: isInternal ? undefined : secretId.trim(),
        secret_key: isInternal ? undefined : secretKey.trim(),
        capabilities,
      };

      // 調用 API 更新
      if (isEditMode && agentId) {
        await updateAgentConfig(agentId, agentConfig);
      } else {
        // TODO: 創建模式需要調用 createAgentConfig API
        setError(t('agentConfig.errors.createNotImplemented', '創建功能尚未實現'));
        return;
      }

      // 成功後回調
      if (onSuccess) {
        onSuccess();
      }

      handleClose();
    } catch (err: any) {
      setError(err.message || t('agentConfig.errors.submitFailed', '保存失敗，請稍後再試'));
    } finally {
      setIsSubmitting(false);
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
        <div className="p-4 border-b border-primary flex items-center justify-between bg-blue-500/10">
          <div className="flex items-center">
            <i className="fa-solid fa-robot mr-3 text-blue-400"></i>
            <h3 className="text-lg font-semibold text-primary">
              {isEditMode
                ? t('agentConfig.title.edit', '編輯代理配置')
                : t('agentConfig.title.create', '創建代理配置')}
            </h3>
          </div>
          <button
            onClick={handleClose}
            className="p-2 rounded-full hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
            disabled={isSubmitting || isLoading}
            aria-label={t('modal.close', '關閉')}
          >
            <i className="fa-solid fa-times"></i>
          </button>
        </div>

        {/* 標籤頁導航 */}
        <div className="flex border-b border-primary bg-tertiary/20">
          <button
            onClick={() => setActiveTab('basic')}
            className={cn(
              "px-6 py-3 text-sm font-medium transition-colors",
              activeTab === 'basic'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-tertiary hover:text-primary'
            )}
          >
            {t('agentConfig.tabs.basic', '基本資訊')}
          </button>
          <button
            onClick={() => setActiveTab('endpoints')}
            className={cn(
              "px-6 py-3 text-sm font-medium transition-colors",
              activeTab === 'endpoints'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-tertiary hover:text-primary'
            )}
          >
            {t('agentConfig.tabs.endpoints', '端點配置')}
          </button>
          <button
            onClick={() => setActiveTab('display')}
            className={cn(
              "px-6 py-3 text-sm font-medium transition-colors",
              activeTab === 'display'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-tertiary hover:text-primary'
            )}
          >
            {t('agentConfig.tabs.display', '顯示配置')}
          </button>
        </div>

        {/* 模態框內容 */}
        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
              <i className="fa-solid fa-exclamation-circle mr-2"></i>
              {error}
            </div>
          )}

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <i className="fa-solid fa-spinner fa-spin text-[28.8px] text-tertiary"></i>
            </div>
          ) : (
            <>
              {/* 基本資訊標籤頁 */}
              {activeTab === 'basic' && (
                <div className="space-y-4">
                  {/* Agent ID（編輯時只讀） */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      {t('agentConfig.fields.agentId', '代理 ID')} *
                      {isEditMode && (
                        <span className="ml-2 text-xs text-tertiary">({t('agentConfig.readonly', '不可修改')})</span>
                      )}
                    </label>
                    {isEditMode ? (
                      <div className="w-full px-4 py-2 bg-tertiary/50 border border-primary rounded-lg text-primary flex items-center justify-between">
                        <span className="text-sm text-tertiary">{agentIdValue}</span>
                        <button
                          type="button"
                          onClick={() => navigator.clipboard.writeText(agentIdValue)}
                          className="text-tertiary hover:text-primary transition-colors"
                          title="複製 Agent ID"
                        >
                          <i className="fa-solid fa-copy"></i>
                        </button>
                      </div>
                    ) : (
                      <>
                        <input
                          type="text"
                          value={agentIdValue}
                          onChange={(e) => setAgentIdValue(e.target.value)}
                          className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder={t('agentConfig.placeholders.agentId', '例如：hr-1')}
                          disabled={isSubmitting || isLoading}
                        />
                        <p className="text-xs text-tertiary mt-1">
                          {t('agentConfig.hints.agentId', '代理 ID 用於唯一標識此代理')}
                        </p>
                      </>
                    )}
                  </div>

                  {/* 分類 ID */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      {t('agentConfig.fields.categoryId', '分類 ID')} *
                    </label>
                    <input
                      type="text"
                      value={categoryIdValue}
                      onChange={(e) => setCategoryIdValue(e.target.value)}
                      className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder={t('agentConfig.placeholders.categoryId', '例如：human-resource')}
                      disabled={isSubmitting || isLoading}
                    />
                  </div>

                  {/* 多語言名稱 */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      {t('agentConfig.fields.name', '名稱')} *
                    </label>
                    <div className="space-y-2">
                      <div>
                        <label className="block text-xs text-tertiary mb-1">English</label>
                        <input
                          type="text"
                          value={nameEn}
                          onChange={(e) => setNameEn(e.target.value)}
                          className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder={t('agentConfig.placeholders.nameEn', '英文名稱')}
                          disabled={isSubmitting || isLoading}
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-tertiary mb-1">简体中文</label>
                        <input
                          type="text"
                          value={nameZhCN}
                          onChange={(e) => setNameZhCN(e.target.value)}
                          className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder={t('agentConfig.placeholders.nameZhCN', '簡體中文名稱')}
                          disabled={isSubmitting || isLoading}
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-tertiary mb-1">繁體中文</label>
                        <input
                          type="text"
                          value={nameZhTW}
                          onChange={(e) => setNameZhTW(e.target.value)}
                          className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder={t('agentConfig.placeholders.nameZhTW', '繁體中文名稱')}
                          disabled={isSubmitting || isLoading}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Icon 選擇 */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      {t('agentConfig.fields.icon', '圖標')}
                    </label>
                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        onClick={() => setShowIconPicker(true)}
                        className="px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary hover:bg-primary/20 transition-colors flex items-center gap-2"
                        disabled={isSubmitting || isLoading}
                      >
                        <i className={`fa-solid ${selectedIcon} text-blue-400`}></i>
                        <span className="text-sm">
                          {selectedIcon ? t('agentConfig.changeIcon', '更換圖標') : t('agentConfig.selectIcon', '選擇圖標')}
                        </span>
                      </button>
                      {selectedIcon && (
                        <span className="text-xs text-tertiary">
                          {selectedIcon}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Agent 類型 */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      {t('agentConfig.fields.agentType', 'Agent 類型')} *
                    </label>
                    <select
                      value={agentType}
                      onChange={(e) => setAgentType(e.target.value as AgentType)}
                      className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                      disabled={isSubmitting || isLoading}
                    >
                      <option value="">{t('agentConfig.selectAgentType', '選擇 Agent 類型')}</option>
                      <option value="planning">{t('agentConfig.types.planning', 'Planning (規劃)')}</option>
                      <option value="execution">{t('agentConfig.types.execution', 'Execution (執行)')}</option>
                      <option value="review">{t('agentConfig.types.review', 'Review (審查)')}</option>
                    </select>
                  </div>

                  {/* 多語言描述 */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      {t('agentConfig.fields.description', '描述')} *
                    </label>
                    <div className="space-y-2">
                      <div>
                        <label className="block text-xs text-tertiary mb-1">English</label>
                        <textarea
                          value={descriptionEn}
                          onChange={(e) => setDescriptionEn(e.target.value)}
                          rows={3}
                          className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder={t('agentConfig.placeholders.descriptionEn', '英文描述')}
                          disabled={isSubmitting || isLoading}
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-tertiary mb-1">简体中文</label>
                        <textarea
                          value={descriptionZhCN}
                          onChange={(e) => setDescriptionZhCN(e.target.value)}
                          rows={3}
                          className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder={t('agentConfig.placeholders.descriptionZhCN', '簡體中文描述')}
                          disabled={isSubmitting || isLoading}
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-tertiary mb-1">繁體中文</label>
                        <textarea
                          value={descriptionZhTW}
                          onChange={(e) => setDescriptionZhTW(e.target.value)}
                          rows={3}
                          className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder={t('agentConfig.placeholders.descriptionZhTW', '繁體中文描述')}
                          disabled={isSubmitting || isLoading}
                        />
                      </div>
                    </div>
                  </div>

                  {/* 能力列表 */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      {t('agentConfig.fields.capabilities', '能力列表')}
                    </label>
                    <div className="flex gap-2 mb-2">
                      <input
                        type="text"
                        value={capabilityInput}
                        onChange={(e) => setCapabilityInput(e.target.value)}
                        onKeyPress={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            addCapability();
                          }
                        }}
                        className="flex-1 px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder={t('agentConfig.placeholders.capability', '輸入能力並按 Enter 添加')}
                        disabled={isSubmitting || isLoading}
                      />
                      <button
                        onClick={addCapability}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                        disabled={isSubmitting || isLoading}
                      >
                        <i className="fa-solid fa-plus"></i>
                      </button>
                    </div>
                    {capabilities.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {capabilities.map((cap) => (
                          <span
                            key={cap}
                            className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-sm flex items-center gap-2"
                          >
                            {cap}
                            <button
                              onClick={() => removeCapability(cap)}
                              className="hover:text-red-400"
                              disabled={isSubmitting || isLoading}
                            >
                              <i className="fa-solid fa-times text-xs"></i>
                            </button>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 端點配置標籤頁 */}
              {activeTab === 'endpoints' && (
                <div className="space-y-4">
                  <div>
                    <label className="flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={isInternal}
                        onChange={(e) => setIsInternal(e.target.checked)}
                        className="mr-2"
                        disabled={isSubmitting || isLoading}
                      />
                      <span className="text-sm font-medium text-primary">
                        {t('agentConfig.fields.isInternal', '內部 Agent（運行在同一系統中）')}
                      </span>
                    </label>
                    <p className="text-xs text-tertiary mt-1 ml-6">
                      {t('agentConfig.hints.isInternal', '內部 Agent 不需要端點配置，會直接調用本地服務')}
                    </p>
                  </div>

                  {!isInternal && (
                    <>
                      {/* Secret 驗證區塊 */}
                      <div className="border-b border-primary pb-4 mb-4">
                        <label className="block text-sm font-medium text-primary mb-2">
                          {t('agentConfig.fields.secretAuth', '外部 Agent 身份驗證')} *
                        </label>
                        <p className="text-xs text-tertiary mb-3">
                          {t('agentConfig.hints.secretAuth', '請使用由 AI-Box 簽發的 Secret ID 和 Secret Key 進行身份驗證')}
                        </p>

                        {secretVerified ? (
                          <div className="p-3 bg-green-500/20 border border-green-500/50 rounded-lg">
                            <div className="flex items-center text-green-400">
                              <i className="fa-solid fa-check-circle mr-2"></i>
                              <span className="text-sm font-medium">
                                {t('agentConfig.secretVerified', 'Secret 驗證成功')}
                              </span>
                            </div>
                            <p className="text-xs text-tertiary mt-1">
                              Secret ID: {secretId}
                            </p>
                          </div>
                        ) : (
                          <div className="space-y-3">
                            <div>
                              <label className="block text-xs text-tertiary mb-1">
                                {t('agentConfig.fields.secretId', 'Secret ID（由 AI-Box 簽發）')}
                              </label>
                              <input
                                type="text"
                                value={secretId}
                                onChange={(e) => {
                                  setSecretId(e.target.value);
                                  setSecretVerified(false);
                                  setSecretVerificationError(null);
                                }}
                                className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder={t('agentConfig.placeholders.secretId', '例如：aibox-example-1234567890-abc123')}
                                disabled={isSubmitting || isVerifyingSecret || isLoading}
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-tertiary mb-1">
                                {t('agentConfig.fields.secretKey', 'Secret Key（由 AI-Box 簽發）')}
                              </label>
                              <input
                                type="password"
                                value={secretKey}
                                onChange={(e) => {
                                  setSecretKey(e.target.value);
                                  setSecretVerified(false);
                                  setSecretVerificationError(null);
                                }}
                                className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder={t('agentConfig.placeholders.secretKey', '輸入 Secret Key')}
                                disabled={isSubmitting || isVerifyingSecret || isLoading}
                              />
                            </div>
                            {secretVerificationError && (
                              <div className="p-2 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-xs">
                                <i className="fa-solid fa-exclamation-circle mr-1"></i>
                                {secretVerificationError}
                              </div>
                            )}
                            <button
                              onClick={handleVerifySecret}
                              disabled={isSubmitting || isVerifyingSecret || !secretId.trim() || !secretKey.trim() || isLoading}
                              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                            >
                              {isVerifyingSecret ? (
                                <>
                                  <i className="fa-solid fa-spinner fa-spin mr-2"></i>
                                  {t('agentConfig.verifyingSecret', '驗證中...')}
                                </>
                              ) : (
                                <>
                                  <i className="fa-solid fa-key mr-2"></i>
                                  {t('agentConfig.verifySecret', '驗證 Secret')}
                                </>
                              )}
                            </button>
                            <div className="flex items-center justify-between gap-2">
                              <p className="text-xs text-tertiary">
                                {t('agentConfig.noSecret', '還沒有 Secret ID？')}
                              </p>
                              <button
                                type="button"
                                onClick={async () => {
                                  setIsGeneratingSecret(true);
                                  setSecretVerificationError(null);
                                  try {
                                    const response = await generateSecret();
                                    if (response.success && response.data) {
                                      setSecretId(response.data.secret_id);
                                      setSecretKey(response.data.secret_key);
                                      // 自動驗證生成的 Secret
                                      setTimeout(() => {
                                        handleVerifySecret();
                                      }, 100);
                                    } else {
                                      setSecretVerificationError(
                                        response.error || t('agentConfig.errors.secretGenerationFailed', '生成 Secret 失敗')
                                      );
                                    }
                                  } catch (err: any) {
                                    setSecretVerificationError(
                                      err.message || t('agentConfig.errors.secretGenerationFailed', '生成 Secret 失敗')
                                    );
                                  } finally {
                                    setIsGeneratingSecret(false);
                                  }
                                }}
                                disabled={isGeneratingSecret || isSubmitting || isLoading}
                                className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded text-xs transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                              >
                                {isGeneratingSecret ? (
                                  <>
                                    <i className="fa-solid fa-spinner fa-spin"></i>
                                    {t('agentConfig.generating', '生成中...')}
                                  </>
                                ) : (
                                  <>
                                    <i className="fa-solid fa-key"></i>
                                    {t('agentConfig.generateTestSecret', '生成測試 Secret')}
                                  </>
                                )}
                              </button>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* 協議類型 */}
                      <div>
                        <label className="block text-sm font-medium text-primary mb-2">
                          {t('agentConfig.fields.protocol', '協議類型')} *
                        </label>
                        <select
                          value={protocol}
                          onChange={(e) => {
                            const newProtocol = e.target.value as ProtocolType;
                            setProtocol(newProtocol);
                            // 當選擇 MCP 協議時，自動設置默認端點
                            if (newProtocol === 'mcp' && !mcpEndpoint.trim()) {
                              setMcpEndpoint('https://mcp-gateway.896445070.workers.dev');
                            }
                          }}
                          className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                          disabled={isSubmitting || isLoading}
                        >
                          <option value="http">HTTP</option>
                          <option value="mcp">MCP (Model Context Protocol)</option>
                        </select>
                      </div>

                      {/* HTTP 端點 */}
                      {protocol === 'http' && (
                        <div>
                          <label className="block text-sm font-medium text-primary mb-2">
                            {t('agentConfig.fields.httpEndpoint', 'HTTP 端點 URL')} *
                          </label>
                          <input
                            type="url"
                            value={httpEndpoint}
                            onChange={(e) => setHttpEndpoint(e.target.value)}
                            className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder={t('agentConfig.placeholders.httpEndpoint', 'https://example.com/api/agent')}
                            disabled={isSubmitting || isLoading}
                          />
                        </div>
                      )}

                      {/* MCP 端點 */}
                      {protocol === 'mcp' && (
                        <div>
                          <label className="block text-sm font-medium text-primary mb-2">
                            {t('agentConfig.fields.mcpEndpoint', 'MCP 端點 URL')} *
                          </label>
                          <input
                            type="url"
                            value={mcpEndpoint}
                            onChange={(e) => setMcpEndpoint(e.target.value)}
                            className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder={t('agentConfig.placeholders.mcpEndpoint', 'https://mcp-gateway.896445070.workers.dev')}
                            disabled={isSubmitting || isLoading}
                          />
                          <p className="text-xs text-tertiary mt-1">
                            {t('agentConfig.hints.mcpEndpoint', '推薦使用：https://mcp-gateway.896445070.workers.dev')}
                          </p>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* 顯示配置標籤頁 */}
              {activeTab === 'display' && (
                <div className="space-y-4">
                  {/* 狀態 */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      {t('agentConfig.fields.status', '狀態')}
                    </label>
                    <select
                      value={status}
                      onChange={(e) => setStatus(e.target.value as typeof status)}
                      className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                      disabled={isSubmitting || isLoading}
                    >
                      <option value="registering">{t('agent.status.registering', '註冊中')}</option>
                      <option value="online">{t('agent.status.online', '在線')}</option>
                      <option value="maintenance">{t('agent.status.maintenance', '維修中')}</option>
                      <option value="deprecated">{t('agent.status.deprecated', '已作廢')}</option>
                    </select>
                  </div>

                  {/* 顯示順序 */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      {t('agentConfig.fields.displayOrder', '顯示順序')}
                    </label>
                    <input
                      type="number"
                      value={displayOrder}
                      onChange={(e) => setDisplayOrder(parseInt(e.target.value) || 1)}
                      min={0}
                      className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                      disabled={isSubmitting || isLoading}
                    />
                    <p className="text-xs text-tertiary mt-1">
                      {t('agentConfig.hints.displayOrder', '數字越小越靠前')}
                    </p>
                  </div>

                  {/* 是否可見 */}
                  <div>
                    <label className="flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={isVisible}
                        onChange={(e) => setIsVisible(e.target.checked)}
                        className="mr-2"
                        disabled={isSubmitting || isLoading}
                      />
                      <span className="text-sm font-medium text-primary">
                        {t('agentConfig.fields.isVisible', '是否顯示')}
                      </span>
                    </label>
                    <p className="text-xs text-tertiary mt-1 ml-6">
                      {t('agentConfig.hints.isVisible', '取消勾選後，此代理將不會在前端顯示')}
                    </p>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* 模態框底部 */}
        <div className="p-4 border-t border-primary flex justify-end gap-3 bg-tertiary/20">
          <button
            onClick={handleClose}
            className="px-4 py-2 rounded-lg bg-tertiary hover:bg-hover text-primary transition-colors"
            disabled={isSubmitting || isLoading}
          >
            {t('modal.cancel', '取消')}
          </button>
          <button
            onClick={handleSubmit}
            className="px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isSubmitting || isLoading}
          >
            {isSubmitting ? (
              <>
                <i className="fa-solid fa-spinner fa-spin mr-2"></i>
                {t('agentConfig.submitting', '保存中...')}
              </>
            ) : (
              <>
                <i className="fa-solid fa-check mr-2"></i>
                {t('agentConfig.submit', '保存配置')}
              </>
            )}
          </button>
        </div>
      </div>

      {/* 圖標選擇器 */}
      {showIconPicker && (
        <IconPicker
          isOpen={showIconPicker}
          selectedIcon={undefined}
          onClose={() => setShowIconPicker(false)}
          onSelect={(icon) => {
            // 轉換圖標格式
            if (icon.startsWith('fa-')) {
              setSelectedIcon(icon);
            } else {
              let faIcon = icon.replace(/^(Fa|Md|Hi|Si|Lu|Tb|Ri|Bs|Bi|Ai|Io|Gr|Im|Wi|Di|Fi|Gi|Go|Hi2|Sl|Tb2|Vsc|Cg|Ri4|Bs5|Bi5|Ai5|Io5|Gr5|Im5|Wi5|Di5|Fi5|Gi5|Go5|Hi25|Sl5|Tb25|Vsc5|Cg5)/, '');
              faIcon = faIcon.replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase();
              if (!faIcon.startsWith('fa-')) {
                faIcon = 'fa-' + faIcon;
              }
              setSelectedIcon(faIcon);
            }
            setShowIconPicker(false);
          }}
        />
      )}
    </div>
  );
}
