/**
 * Agent 註冊模態框組件
 * 功能：提供代理服務註冊界面，支持內部和外部的 Agent 註冊
 * 創建日期：2025-01-27
 * 創建人：Daniel Chung
 * 最後修改日期：2026-01-14 14:30 UTC+8
 */

import { useState, useMemo } from 'react';
import { useLanguage } from '../contexts/languageContext';
import { cn } from '../lib/utils';
import {
  registerAgent,
  verifySecret,
  getGatewayAvailableAgents,
  GatewayAvailableAgent,
  generateSecret,
} from '../lib/api';
import IconPicker from './IconPicker';
import IconRenderer from './IconRenderer';

interface AgentRegistrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  categoryName?: string; // 當前分類名稱（如「人力資源」、「物流」等）
  categoryId?: string; // 當前分類 ID（如 'human-resource'、'logistics' 等）
}

type AgentType = 'planning' | 'execution' | 'review' | '';
type ProtocolType = 'http' | 'mcp';
type AuthType = 'api_key' | 'mtls' | 'ip_whitelist' | 'none';

export default function AgentRegistrationModal({
  isOpen,
  onClose,
  onSuccess,
  categoryName,
  categoryId,
}: AgentRegistrationModalProps) {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<'basic' | 'endpoints' | 'permissions'>('basic');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 基本資訊
  const [agentName, setAgentName] = useState('');
  const [agentType, setAgentType] = useState<AgentType>('');
  const [description, setDescription] = useState('');
  const [capabilities, setCapabilities] = useState<string[]>([]);
  const [capabilityInput, setCapabilityInput] = useState('');
  const [selectedIcon, setSelectedIcon] = useState<string>('FaRobot');
  const [showIconPicker, setShowIconPicker] = useState(false);

  // Agent ID 自動生成（基於 Agent 名稱）
  const agentId = useMemo(() => {
    if (!agentName.trim()) {
      return '';
    }
    // 將 Agent 名稱轉換為 ID 格式：小寫、替換空格為連字符、移除特殊字符
    const baseId = agentName
      .toLowerCase()
      .replace(/\s+/g, '-')
      .replace(/[^a-z0-9-]/g, '')
      .substring(0, 30); // 限制長度

    // 添加隨機後綴確保唯一性
    const randomSuffix = Math.random().toString(36).substring(2, 8);
    return `${baseId}-${randomSuffix}`;
  }, [agentName]);

  // 端點配置
  const [isInternal, setIsInternal] = useState(true);
  const [protocol, setProtocol] = useState<ProtocolType>('http');
  const [httpEndpoint, setHttpEndpoint] = useState('');
  const [mcpEndpoint, setMcpEndpoint] = useState('https://mcp.k84.org'); // 默認使用系統 Gateway 端點

  // Secret 驗證（外部 Agent 需要）
  const [secretId, setSecretId] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [secretVerified, setSecretVerified] = useState(false);
  const [isVerifyingSecret, setIsVerifyingSecret] = useState(false);
  const [secretVerificationError, setSecretVerificationError] = useState<string | null>(null);
  const [isGeneratingSecret, setIsGeneratingSecret] = useState(false);

  // 權限配置（僅外部 Agent 需要）
  const [authType, setAuthType] = useState<AuthType>('none');
  const [apiKey, setApiKey] = useState('');
  const [serverCertificate, setServerCertificate] = useState('');
  const [ipWhitelist, setIpWhitelist] = useState<string[]>([]);
  const [ipInput, setIpInput] = useState('');
  const [allowedMemoryNamespaces, setAllowedMemoryNamespaces] = useState<string>('');
  const [allowedTools, setAllowedTools] = useState<string>('');
  const [allowedLlmProviders, setAllowedLlmProviders] = useState<string>('');

  // Gateway 可用 Agent 查詢
  const [availableAgents, setAvailableAgents] = useState<GatewayAvailableAgent[]>([]);
  const [selectedAvailableAgentIndex, setSelectedAvailableAgentIndex] = useState<number | null>(null);
  const [isQueryingAgents, setIsQueryingAgents] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [gatewayEndpoint, setGatewayEndpoint] = useState<string>('https://mcp.k84.org');

  const handleClose = () => {
    if (!isSubmitting) {
      // 重置表單
      setAgentName('');
      setAgentType('');
      setDescription('');
      setCapabilities([]);
      setCapabilityInput('');
      setSelectedIcon('FaRobot');
      setIsInternal(true);
      setProtocol('http');
      setAvailableAgents([]);
      setSelectedAvailableAgentIndex(null);
      setQueryError(null);
      setHttpEndpoint('');
      setMcpEndpoint('');
      setAuthType('none');
      setApiKey('');
      setServerCertificate('');
      setIpWhitelist([]);
      setIpInput('');
      setAllowedMemoryNamespaces('');
      setAllowedTools('');
      setAllowedLlmProviders('');
      setSecretId('');
      setSecretKey('');
      setSecretVerified(false);
      setSecretVerificationError(null);
      setError(null);
      setActiveTab('basic');
      setAvailableAgents([]);
      setQueryError(null);
      onClose();
    }
  };

  const addCapability = () => {
    if (capabilityInput.trim() && !capabilities.includes(capabilityInput.trim())) {
      setCapabilities([...capabilities, capabilityInput.trim()]);
      setCapabilityInput('');
    }
  };

  const removeCapability = (capability: string) => {
    setCapabilities(capabilities.filter(c => c !== capability));
  };

  const addIp = () => {
    if (ipInput.trim() && !ipWhitelist.includes(ipInput.trim())) {
      setIpWhitelist([...ipWhitelist, ipInput.trim()]);
      setIpInput('');
    }
  };

  const removeIp = (ip: string) => {
    setIpWhitelist(ipWhitelist.filter(i => i !== ip));
  };

  const handleVerifySecret = async () => {
    if (!secretId.trim() || !secretKey.trim()) {
      setSecretVerificationError(t('agentRegistration.errors.secretRequired', '請輸入 Secret ID 和 Secret Key'));
      return;
    }

    setIsVerifyingSecret(true);
    setSecretVerificationError(null);

    try {
      const response = await verifySecret({
        secret_id: secretId.trim(),
        secret_key: secretKey.trim(),
      });

      if (response.success && response.data?.valid) {
        if (response.data.is_bound) {
          setSecretVerificationError(t('agentRegistration.errors.secretAlreadyBound', '此 Secret ID 已被綁定到其他 Agent'));
        } else {
          setSecretVerified(true);
          setSecretVerificationError(null);
        }
      } else {
        setSecretVerificationError(response.error || t('agentRegistration.errors.secretInvalid', 'Secret ID 或 Secret Key 無效'));
      }
    } catch (err: any) {
      setSecretVerificationError(err.message || t('agentRegistration.errors.secretVerificationFailed', 'Secret 驗證失敗，請稍後再試'));
    } finally {
      setIsVerifyingSecret(false);
    }
  };

  const handleQueryGatewayAgents = async () => {
    setIsQueryingAgents(true);
    setQueryError(null);
    setAvailableAgents([]);

    try {
      const response = await getGatewayAvailableAgents();

      if (response.success && response.data) {
        setAvailableAgents(response.data.available_agents || []);
        if (response.data.gateway_endpoint) {
          setGatewayEndpoint(response.data.gateway_endpoint);
        }
      } else {
        setQueryError(response.error || t('agentRegistration.errors.queryFailed', '查詢 Gateway Agent 失敗'));
      }
    } catch (err: any) {
      setQueryError(err.message || t('agentRegistration.errors.queryFailed', '查詢 Gateway Agent 失敗'));
    } finally {
      setIsQueryingAgents(false);
    }
  };

  const handleSelectAvailableAgent = (index: number) => {
    // 設置選中的 Agent 索引
    setSelectedAvailableAgentIndex(index);
  };

  const handleUseSelectedAgent = () => {
    // 使用選中的 Agent 自動填充表單字段
    if (selectedAvailableAgentIndex !== null && availableAgents[selectedAvailableAgentIndex]) {
      const agent = availableAgents[selectedAvailableAgentIndex];
      setAgentName(agent.agent_name);
      setMcpEndpoint(gatewayEndpoint);
      setCapabilities(agent.suggested_capabilities || []);
      // 可以根據 pattern 推斷 Agent 類型
      if (agent.pattern.includes('warehouse')) {
        setAgentType('execution');
      }
      // 清空選擇狀態
      setSelectedAvailableAgentIndex(null);
    }
  };

  const validateForm = (): boolean => {
    if (!agentName.trim()) {
      setError(t('agentRegistration.errors.agentNameRequired', 'Agent 名稱為主填項'));
      return false;
    }
    if (!agentType) {
      setError(t('agentRegistration.errors.agentTypeRequired', 'Agent 類型為必填項'));
      return false;
    }

    // 外部 Agent 驗證
    if (!isInternal) {
      // 優先檢查 Secret 驗證
      if (!secretVerified) {
        setError(t('agentRegistration.errors.secretNotVerified', '請先驗證 Secret ID 和 Secret Key'));
        setActiveTab('endpoints'); // 切換到端點配置標籤頁
        return false;
      }

      if (protocol === 'http' && !httpEndpoint.trim()) {
        setError(t('agentRegistration.errors.httpEndpointRequired', 'HTTP 端點為必填項'));
        return false;
      }
      if (protocol === 'mcp' && !mcpEndpoint.trim()) {
        setError(t('agentRegistration.errors.mcpEndpointRequired', 'MCP 端點為必填項'));
        return false;
      }
      if (authType === 'api_key' && !apiKey.trim()) {
        setError(t('agentRegistration.errors.apiKeyRequired', 'API Key 為必填項'));
        return false;
      }
      if (authType === 'mtls' && !serverCertificate.trim()) {
        setError(t('agentRegistration.errors.certificateRequired', '服務器證書為必填項'));
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
      // 構建請求數據
      const requestData: any = {
        agent_id: agentId.trim(),
        agent_type: agentType,
        name: agentName.trim(),
        endpoints: {
          http: httpEndpoint.trim() || null,
          mcp: mcpEndpoint.trim() || null,
          protocol: protocol,
          is_internal: isInternal,
        },
        capabilities: capabilities,
        metadata: {
          version: '1.0.0',
          description: description.trim() || null,
          tags: [],
          capabilities: {},
          icon: selectedIcon || null,
        },
      };

      // 權限配置
      const permissions: any = {
        read: true,
        write: false,
        execute: true,
        admin: false,
      };

      // 外部 Agent 需要添加認證配置
      if (!isInternal) {
        if (authType === 'api_key' && apiKey.trim()) {
          permissions.api_key = apiKey.trim();
        }
        if (authType === 'mtls' && serverCertificate.trim()) {
          permissions.server_certificate = serverCertificate.trim();
        }
        if (authType === 'ip_whitelist' && ipWhitelist.length > 0) {
          permissions.ip_whitelist = ipWhitelist;
        }
        permissions.allowed_memory_namespaces = allowedMemoryNamespaces
          .split(',')
          .map(ns => ns.trim())
          .filter(ns => ns.length > 0);
        permissions.allowed_tools = allowedTools
          .split(',')
          .map(tool => tool.trim())
          .filter(tool => tool.length > 0);
        permissions.allowed_llm_providers = allowedLlmProviders
          .split(',')
          .map(provider => provider.trim())
          .filter(provider => provider.length > 0);
      }

      // 如果有 Secret ID，添加到權限配置
      if (!isInternal && secretVerified && secretId.trim()) {
        permissions.secret_id = secretId.trim();
      }

      requestData.permissions = permissions;

      // 添加 category_id（如果提供）
      if (categoryId) {
        requestData.category_id = categoryId;
      }

      // 調用 API
      console.log('[提交Agent註冊]', requestData);
      await registerAgent(requestData);

      // 成功後回調
      if (onSuccess) {
        onSuccess();
      }

      handleClose();
    } catch (err: any) {
      setError(err.message || t('agentRegistration.errors.submitFailed', '註冊失敗，請稍後再試'));
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
              {t('agentRegistration.title', '註冊新 Agent 服務')}
              {categoryName && <span className="text-tertiary font-normal"> - {categoryName}</span>}
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
            {t('agentRegistration.tabs.basic', '基本資訊')}
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
            {t('agentRegistration.tabs.endpoints', '端點配置')}
          </button>
          <button
            onClick={() => setActiveTab('permissions')}
            className={cn(
              "px-6 py-3 text-sm font-medium transition-colors",
              activeTab === 'permissions'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-tertiary hover:text-primary'
            )}
            disabled={isInternal}
          >
            {t('agentRegistration.tabs.permissions', '權限配置')}
            {isInternal && (
              <span className="ml-2 text-xs text-muted">
                ({t('agentRegistration.internalOnly', '僅內部 Agent')})
              </span>
            )}
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

          {/* 基本資訊標籤頁 */}
          {activeTab === 'basic' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  {t('agentRegistration.fields.agentName', 'Agent 名稱')} *
                </label>
                <input
                  type="text"
                  value={agentName}
                  onChange={(e) => setAgentName(e.target.value)}
                  className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder={t('agentRegistration.placeholders.agentName', '例如：My Custom Agent')}
                  disabled={isSubmitting}
                />
                <p className="text-xs text-tertiary mt-1">
                  {t('agentRegistration.hints.agentName', 'Agent ID 將自動生成')}
                </p>
              </div>

              {/* Agent ID 顯示（自動生成，只讀） */}
              {agentId && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    {t('agentRegistration.fields.agentId', 'Agent ID')}（自動生成）
                  </label>
                  <div className="w-full px-4 py-2 bg-tertiary/50 border border-primary rounded-lg text-primary flex items-center justify-between">
                    <span className="text-sm text-tertiary">{agentId}</span>
                    <button
                      type="button"
                      onClick={() => navigator.clipboard.writeText(agentId)}
                      className="text-tertiary hover:text-primary transition-colors"
                      title="複製 Agent ID"
                    >
                      <i className="fa-solid fa-copy"></i>
                    </button>
                  </div>
                </div>
              )}

              {/* Icon 選擇 */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  {t('agentRegistration.fields.icon', '圖標')}
                </label>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setShowIconPicker(true)}
                    className="px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary hover:bg-primary/20 transition-colors flex items-center gap-2"
                    disabled={isSubmitting}
                  >
                    {selectedIcon && (
                      <IconRenderer iconName={selectedIcon} size={20} />
                    )}
                    <span className="text-sm">
                      {selectedIcon ? t('agentRegistration.changeIcon', '更換圖標') : t('agentRegistration.selectIcon', '選擇圖標')}
                    </span>
                  </button>
                  {selectedIcon && (
                    <span className="text-xs text-tertiary">
                      {selectedIcon}
                    </span>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  {t('agentRegistration.fields.agentType', 'Agent 類型')} *
                </label>
                <select
                  value={agentType}
                  onChange={(e) => setAgentType(e.target.value as AgentType)}
                  className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={isSubmitting}
                >
                  <option value="">{t('agentRegistration.selectAgentType', '選擇 Agent 類型')}</option>
                  <option value="planning">{t('agentRegistration.types.planning', 'Planning (規劃)')}</option>
                  <option value="execution">{t('agentRegistration.types.execution', 'Execution (執行)')}</option>
                  <option value="review">{t('agentRegistration.types.review', 'Review (審查)')}</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  {t('agentRegistration.fields.description', '描述')}
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder={t('agentRegistration.placeholders.description', '描述此 Agent 的功能和用途')}
                  disabled={isSubmitting}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  {t('agentRegistration.fields.capabilities', '能力列表')}
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
                    placeholder={t('agentRegistration.placeholders.capability', '輸入能力並按 Enter 添加')}
                    disabled={isSubmitting}
                  />
                  <button
                    onClick={addCapability}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                    disabled={isSubmitting}
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
                          disabled={isSubmitting}
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
                    disabled={isSubmitting}
                  />
                  <span className="text-sm font-medium text-primary">
                    {t('agentRegistration.fields.isInternal', '內部 Agent（運行在同一系統中）')}
                  </span>
                </label>
                <p className="text-xs text-tertiary mt-1 ml-6">
                  {t('agentRegistration.hints.isInternal', '內部 Agent 不需要端點配置，會直接調用本地服務')}
                </p>
              </div>

              {!isInternal && (
                <>
                  {/* Secret 驗證區塊 */}
                  <div className="border-b border-primary pb-4 mb-4">
                    <label className="block text-sm font-medium text-primary mb-2">
                      {t('agentRegistration.fields.secretAuth', '外部 Agent 身份驗證')} *
                    </label>
                    <p className="text-xs text-tertiary mb-3">
                      {t('agentRegistration.hints.secretAuth', '請使用由 AI-Box 簽發的 Secret ID 和 Secret Key 進行身份驗證')}
                    </p>

                    {secretVerified ? (
                      <div className="p-3 bg-green-500/20 border border-green-500/50 rounded-lg">
                        <div className="flex items-center text-green-400">
                          <i className="fa-solid fa-check-circle mr-2"></i>
                          <span className="text-sm font-medium">
                            {t('agentRegistration.secretVerified', 'Secret 驗證成功')}
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
                            {t('agentRegistration.fields.secretId', 'Secret ID（由 AI-Box 簽發）')}
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
                            placeholder={t('agentRegistration.placeholders.secretId', '例如：aibox-example-1234567890-abc123')}
                            disabled={isSubmitting || isVerifyingSecret}
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-tertiary mb-1">
                            {t('agentRegistration.fields.secretKey', 'Secret Key（由 AI-Box 簽發）')}
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
                            placeholder={t('agentRegistration.placeholders.secretKey', '輸入 Secret Key')}
                            disabled={isSubmitting || isVerifyingSecret}
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
                          disabled={isSubmitting || isVerifyingSecret || !secretId.trim() || !secretKey.trim()}
                          className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                        >
                          {isVerifyingSecret ? (
                            <>
                              <i className="fa-solid fa-spinner fa-spin mr-2"></i>
                              {t('agentRegistration.verifyingSecret', '驗證中...')}
                            </>
                          ) : (
                            <>
                              <i className="fa-solid fa-key mr-2"></i>
                              {t('agentRegistration.verifySecret', '驗證 Secret')}
                            </>
                          )}
                        </button>
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-xs text-tertiary">
                            {t('agentRegistration.noSecret', '還沒有 Secret ID？')}
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
                                    response.error || t('agentRegistration.errors.secretGenerationFailed', '生成 Secret 失敗')
                                  );
                                }
                              } catch (err: any) {
                                setSecretVerificationError(
                                  err.message || t('agentRegistration.errors.secretGenerationFailed', '生成 Secret 失敗')
                                );
                              } finally {
                                setIsGeneratingSecret(false);
                              }
                            }}
                            disabled={isGeneratingSecret || isSubmitting}
                            className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded text-xs transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                          >
                            {isGeneratingSecret ? (
                              <>
                                <i className="fa-solid fa-spinner fa-spin"></i>
                                {t('agentRegistration.generating', '生成中...')}
                              </>
                            ) : (
                              <>
                                <i className="fa-solid fa-key"></i>
                                {t('agentRegistration.generateTestSecret', '生成測試 Secret')}
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      {t('agentRegistration.fields.protocol', '協議類型')} *
                    </label>
                    <select
                      value={protocol}
                      onChange={(e) => {
                        const newProtocol = e.target.value as ProtocolType;
                        setProtocol(newProtocol);
                        // 當選擇 MCP 協議時，自動設置默認端點
                        if (newProtocol === 'mcp' && !mcpEndpoint.trim()) {
                          setMcpEndpoint('https://mcp.k84.org');
                        }
                      }}
                      className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                      disabled={isSubmitting}
                    >
                      <option value="http">HTTP</option>
                      <option value="mcp">MCP (Model Context Protocol)</option>
                    </select>
                  </div>

                  {protocol === 'http' && (
                    <div>
                      <label className="block text-sm font-medium text-primary mb-2">
                        {t('agentRegistration.fields.httpEndpoint', 'HTTP 端點 URL')} *
                      </label>
                      <input
                        type="url"
                        value={httpEndpoint}
                        onChange={(e) => setHttpEndpoint(e.target.value)}
                        className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder={t('agentRegistration.placeholders.httpEndpoint', 'https://example.com/api/agent')}
                        disabled={isSubmitting}
                      />
                    </div>
                  )}

                  {protocol === 'mcp' && (
                    <div className="space-y-3">
                      <div>
                        <label className="block text-sm font-medium text-primary mb-2">
                          {t('agentRegistration.fields.mcpEndpoint', 'MCP 端點 URL')} *
                        </label>
                        <input
                          type="url"
                          value={mcpEndpoint}
                          onChange={(e) => setMcpEndpoint(e.target.value)}
                          className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder={t('agentRegistration.placeholders.mcpEndpoint', 'https://mcp.k84.org')}
                          disabled={isSubmitting}
                        />
                        <p className="text-xs text-tertiary mt-1">
                          {t('agentRegistration.hints.mcpEndpoint', '通常指向 Cloudflare Gateway 端點：https://mcp.k84.org')}
                        </p>
                      </div>

                      {/* Gateway 可用 Agent 查詢 */}
                      <div className="border-t border-primary pt-3">
                        <div className="flex items-center justify-between mb-2">
                          <label className="block text-sm font-medium text-primary">
                            {t('agentRegistration.fields.queryGateway', '查詢 Gateway 可用 Agent')}
                          </label>
                          <button
                            type="button"
                            onClick={handleQueryGatewayAgents}
                            disabled={isQueryingAgents || isSubmitting}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 text-sm"
                          >
                            {isQueryingAgents ? (
                              <>
                                <i className="fa-solid fa-spinner fa-spin"></i>
                                {t('agentRegistration.querying', '查詢中...')}
                              </>
                            ) : (
                              <>
                                <i className="fa-solid fa-search"></i>
                                {t('agentRegistration.queryGateway', '查詢可用 Agent')}
                              </>
                            )}
                          </button>
                        </div>

                        {queryError && (
                          <div className="mb-3 p-2 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-xs">
                            <i className="fa-solid fa-exclamation-circle mr-1"></i>
                            {queryError}
                          </div>
                        )}

                        {availableAgents.length > 0 && (
                          <div className="space-y-2">
                            <p className="text-xs text-tertiary">
                              {t('agentRegistration.foundAgents', `找到 ${availableAgents.length} 個可用 Agent（請選擇一個使用）`)}
                            </p>
                            <div className="space-y-2 max-h-48 overflow-y-auto">
                              {availableAgents.map((agent, index) => (
                                <div
                                  key={index}
                                  onClick={() => handleSelectAvailableAgent(index)}
                                  className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                                    selectedAvailableAgentIndex === index
                                      ? 'bg-blue-500/20 border-blue-500/50'
                                      : 'bg-tertiary border-primary hover:bg-primary/20'
                                  }`}
                                >
                                  <div className="flex items-start">
                                    <div className="flex items-center mr-3 mt-0.5">
                                      <input
                                        type="radio"
                                        checked={selectedAvailableAgentIndex === index}
                                        onChange={() => handleSelectAvailableAgent(index)}
                                        className="w-4 h-4 text-blue-600 focus:ring-blue-500"
                                        disabled={isSubmitting}
                                      />
                                    </div>
                                    <div className="flex-1">
                                      <div className="flex items-center gap-2 mb-1">
                                        <span className="font-medium text-primary text-sm">
                                          {agent.agent_name}
                                        </span>
                                        <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs">
                                          {agent.pattern}
                                        </span>
                                      </div>
                                      <p className="text-xs text-tertiary mb-2">
                                        {t('agentRegistration.targetEndpoint', '目標端點')}: {agent.target}
                                      </p>
                                      {agent.suggested_capabilities && agent.suggested_capabilities.length > 0 && (
                                        <div className="flex flex-wrap gap-1 mb-2">
                                          {agent.suggested_capabilities.map((cap, capIndex) => (
                                            <span
                                              key={capIndex}
                                              className="px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded text-xs"
                                            >
                                              {cap}
                                            </span>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                            <button
                              type="button"
                              onClick={handleUseSelectedAgent}
                              disabled={isSubmitting || selectedAvailableAgentIndex === null}
                              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                            >
                              <i className="fa-solid fa-check"></i>
                              {t('agentRegistration.useSelectedAgent', '使用選中的 Agent')}
                            </button>
                          </div>
                        )}

                        {availableAgents.length === 0 && !isQueryingAgents && !queryError && (
                          <p className="text-xs text-tertiary text-center py-2">
                            {t('agentRegistration.noAvailableAgents', '點擊上方按鈕查詢 Gateway 上可用的 Agent')}
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* 權限配置標籤頁（僅外部 Agent） */}
          {activeTab === 'permissions' && !isInternal && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  {t('agentRegistration.fields.authType', '認證方式')} *
                </label>
                <select
                  value={authType}
                  onChange={(e) => setAuthType(e.target.value as AuthType)}
                  className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={isSubmitting}
                >
                  <option value="none">{t('agentRegistration.auth.none', '無（使用下方配置）')}</option>
                  <option value="api_key">{t('agentRegistration.auth.apiKey', 'API Key')}</option>
                  <option value="mtls">{t('agentRegistration.auth.mtls', 'mTLS 證書')}</option>
                  <option value="ip_whitelist">{t('agentRegistration.auth.ipWhitelist', 'IP 白名單')}</option>
                </select>
              </div>

              {authType === 'api_key' && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    {t('agentRegistration.fields.apiKey', 'API Key')} *
                  </label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder={t('agentRegistration.placeholders.apiKey', '輸入 API Key')}
                    disabled={isSubmitting}
                  />
                </div>
              )}

              {authType === 'mtls' && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    {t('agentRegistration.fields.serverCertificate', '服務器證書')} *
                  </label>
                  <textarea
                    value={serverCertificate}
                    onChange={(e) => setServerCertificate(e.target.value)}
                    rows={5}
                    className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-xs"
                    placeholder={t('agentRegistration.placeholders.certificate', 'Paste certificate here...')}
                    disabled={isSubmitting}
                  />
                </div>
              )}

              {authType === 'ip_whitelist' && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    {t('agentRegistration.fields.ipWhitelist', 'IP 白名單')} *
                  </label>
                  <div className="flex gap-2 mb-2">
                    <input
                      type="text"
                      value={ipInput}
                      onChange={(e) => setIpInput(e.target.value)}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          addIp();
                        }
                      }}
                      className="flex-1 px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder={t('agentRegistration.placeholders.ip', '例如：192.168.1.0/24')}
                      disabled={isSubmitting}
                    />
                    <button
                      onClick={addIp}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                      disabled={isSubmitting}
                    >
                      <i className="fa-solid fa-plus"></i>
                    </button>
                  </div>
                  {ipWhitelist.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {ipWhitelist.map((ip) => (
                        <span
                          key={ip}
                          className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-sm flex items-center gap-2"
                        >
                          {ip}
                          <button
                            onClick={() => removeIp(ip)}
                            className="hover:text-red-400"
                            disabled={isSubmitting}
                          >
                            <i className="fa-solid fa-times text-xs"></i>
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="border-t border-primary pt-4">
                <h4 className="text-sm font-medium text-primary mb-3">
                  {t('agentRegistration.sections.resourceAccess', '資源訪問權限（可選）')}
                </h4>

                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      {t('agentRegistration.fields.allowedMemoryNamespaces', '允許訪問的 Memory 命名空間')}
                    </label>
                    <input
                      type="text"
                      value={allowedMemoryNamespaces}
                      onChange={(e) => setAllowedMemoryNamespaces(e.target.value)}
                      className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder={t('agentRegistration.placeholders.memoryNamespaces', '用逗號分隔，例如：ns1,ns2')}
                      disabled={isSubmitting}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      {t('agentRegistration.fields.allowedTools', '允許使用的工具')}
                    </label>
                    <input
                      type="text"
                      value={allowedTools}
                      onChange={(e) => setAllowedTools(e.target.value)}
                      className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder={t('agentRegistration.placeholders.tools', '用逗號分隔，例如：tool1,tool2')}
                      disabled={isSubmitting}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      {t('agentRegistration.fields.allowedLlmProviders', '允許使用的 LLM Provider')}
                    </label>
                    <input
                      type="text"
                      value={allowedLlmProviders}
                      onChange={(e) => setAllowedLlmProviders(e.target.value)}
                      className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder={t('agentRegistration.placeholders.llmProviders', '用逗號分隔，例如：openai,anthropic')}
                      disabled={isSubmitting}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 模態框底部 */}
        <div className="p-4 border-t border-primary flex justify-end gap-3 bg-tertiary/20">
          <button
            onClick={handleClose}
            className="px-4 py-2 rounded-lg bg-tertiary hover:bg-hover text-primary transition-colors"
            disabled={isSubmitting}
          >
            {t('modal.cancel', '取消')}
          </button>
          <button
            onClick={handleSubmit}
            className="px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <i className="fa-solid fa-spinner fa-spin mr-2"></i>
                {t('agentRegistration.submitting', '註冊中...')}
              </>
            ) : (
              <>
                <i className="fa-solid fa-check mr-2"></i>
                {t('agentRegistration.submit', '註冊 Agent')}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Icon 選擇器 Modal */}
      <IconPicker
        isOpen={showIconPicker}
        selectedIcon={selectedIcon}
        onSelect={setSelectedIcon}
        onClose={() => setShowIconPicker(false)}
      />
    </div>
  );
}
