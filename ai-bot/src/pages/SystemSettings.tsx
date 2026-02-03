// 代碼功能說明: 系統設置頁面
// 創建日期: 2026-01-17 23:00 UTC+8
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-24 23:19 UTC+8

import React, { useState, useEffect } from "react";
import {
  ArrowLeft,
  RefreshCw,
  Edit2,
  Check,
  X,
  Eye,
  EyeOff,
  Trash2,
  ShieldCheck,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  getSystemConfigs,
  updateSystemConfig,
  SystemConfig,
  getProviderAPIKeyStatus,
  getAllProvidersStatus,
  setProviderAPIKey,
  deleteProviderAPIKey,
  updateProviderConfig,
  verifyProviderConnectivity,
  getModels,
  type LLMModel,
  type ProviderModelConfig,
  type ProviderConfigUpdateRequest,
} from "@/lib/api";
import { toast } from "sonner";

type ConfigCategory =
  | "basic"
  | "features"
  | "performance"
  | "security"
  | "business"
  | "llm_providers";

interface ConfigEditorProps {
  config: SystemConfig;
  onSave: (scope: string, data: Record<string, any>) => Promise<void>;
}

const ConfigEditor: React.FC<ConfigEditorProps> = ({ config, onSave }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedData, setEditedData] = useState(config.config_data);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(config.scope, editedData);
      setIsEditing(false);
    } catch (error) {
      console.error("Failed to save config:", error);
      // 顯示錯誤提示
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditedData(config.config_data);
    setIsEditing(false);
  };

  // 根據值的類型渲染不同的輸入控件
  const renderConfigValue = (key: string, value: any) => {
    if (typeof value === "boolean") {
      return (
        <div className="flex items-center space-x-2">
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={editedData[key]}
              onChange={(e) =>
                setEditedData({ ...editedData, [key]: e.target.checked })
              }
              disabled={!isEditing}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="ml-2 text-sm text-gray-700">
              {editedData[key] ? "啟用" : "禁用"}
            </span>
          </label>
        </div>
      );
    }

    if (typeof value === "number") {
      return (
        <input
          type="number"
          value={editedData[key]}
          onChange={(e) =>
            setEditedData({ ...editedData, [key]: Number(e.target.value) })
          }
          disabled={!isEditing}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
        />
      );
    }

    if (typeof value === "string") {
      return (
        <input
          type="text"
          value={editedData[key]}
          onChange={(e) =>
            setEditedData({ ...editedData, [key]: e.target.value })
          }
          disabled={!isEditing}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
        />
      );
    }

    if (typeof value === "object") {
      return (
        <textarea
          value={JSON.stringify(editedData[key], null, 2)}
          onChange={(e) => {
            try {
              const parsed = JSON.parse(e.target.value);
              setEditedData({ ...editedData, [key]: parsed });
            } catch (err) {
              // 忽略 JSON 解析錯誤
            }
          }}
          disabled={!isEditing}
          rows={4}
          className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
        />
      );
    }

    return <span className="text-sm text-gray-700">{String(value)}</span>;
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            {config.scope}
          </h3>
          {config.sub_scope && (
            <p className="text-sm text-gray-500">{config.sub_scope}</p>
          )}
        </div>
        <div className="flex items-center space-x-2">
          {isEditing ? (
            <>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-3 py-1.5 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-1"
              >
                <Check size={16} />
                <span>保存</span>
              </button>
              <button
                onClick={handleCancel}
                disabled={saving}
                className="px-3 py-1.5 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-1"
              >
                <X size={16} />
                <span>取消</span>
              </button>
            </>
          ) : (
            <button
              onClick={() => setIsEditing(true)}
              className="px-3 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center space-x-1"
            >
              <Edit2 size={16} />
              <span>編輯</span>
            </button>
          )}
        </div>
      </div>

      <div className="space-y-4">
        {Object.entries(config.config_data).map(([key, value]) => (
          <div key={key} className="grid grid-cols-3 gap-4 items-start">
            <div className="col-span-1">
              <label className="block text-sm font-medium text-gray-700">
                {key}
              </label>
              <p className="text-xs text-gray-500 mt-1">類型: {typeof value}</p>
            </div>
            <div className="col-span-2">{renderConfigValue(key, value)}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

const SystemSettings: React.FC = () => {
  const navigate = useNavigate();
  // 默認顯示 LLM Provider 配置（用戶最常用的功能）
  const [activeCategory, setActiveCategory] =
    useState<ConfigCategory>("llm_providers");
  const [configs, setConfigs] = useState<SystemConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  // 類別定義
  const categories = [
    { id: "basic" as ConfigCategory, label: "基礎配置" },
    { id: "features" as ConfigCategory, label: "功能開關" },
    { id: "performance" as ConfigCategory, label: "性能參數" },
    { id: "security" as ConfigCategory, label: "安全參數" },
    { id: "business" as ConfigCategory, label: "業務參數" },
    { id: "llm_providers" as ConfigCategory, label: "LLM Provider 配置" },
  ];

  // LLM Provider 列表
  const llmProviders = [
    {
      id: "chatgpt",
      name: "OpenAI (ChatGPT)",
      icon: "fa-robot",
      color: "text-green-500",
    },
    {
      id: "gemini",
      name: "Google (Gemini)",
      icon: "fa-gem",
      color: "text-blue-500",
    },
    {
      id: "grok",
      name: "xAI (Grok)",
      icon: "fa-bolt",
      color: "text-yellow-500",
    },
    {
      id: "anthropic",
      name: "Anthropic (Claude)",
      icon: "fa-brain",
      color: "text-purple-500",
    },
    {
      id: "qwen",
      name: "阿里巴巴 (Qwen)",
      icon: "fa-code",
      color: "text-orange-500",
    },
    {
      id: "chatglm",
      name: "智譜 AI (ChatGLM)",
      icon: "fa-microchip",
      color: "text-cyan-500",
    },
    {
      id: "volcano",
      name: "火山引擎 (Volcano)",
      icon: "fa-fire",
      color: "text-red-500",
    },
    {
      id: "mistral",
      name: "Mistral AI",
      icon: "fa-wind",
      color: "text-indigo-500",
    },
    {
      id: "deepseek",
      name: "DeepSeek",
      icon: "fa-search",
      color: "text-teal-500",
    },
  ];

  // 預設 Base URL 映射
  const getDefaultBaseUrl = (providerId: string): string => {
    const defaults: Record<string, string> = {
      chatgpt: "https://api.openai.com/v1",
      gemini: "https://generativelanguage.googleapis.com/v1",
      grok: "https://api.x.ai/v1",
      anthropic: "https://api.anthropic.com/v1",
      qwen: "https://dashscope.aliyuncs.com/compatible-mode/v1",
      chatglm: "https://open.bigmodel.cn/api/paas/v4",
      volcano: "https://ark.cn-beijing.volces.com/api/v3",
      mistral: "https://api.mistral.ai/v1",
      deepseek: "https://api.deepseek.com/v1",
    };
    return defaults[providerId] || "";
  };

  // LLM Provider 狀態
  const [providerStatuses, setProviderStatuses] = useState<
    Record<
      string,
      {
        has_api_key: boolean;
        base_url?: string;
        default_model?: ProviderModelConfig;
        updated_at?: string;
        health_status?: string;
      }
    >
  >({});
  const [editingProvider, setEditingProvider] = useState<string | null>(null);
  const [apiKeyValues, setApiKeyValues] = useState<Record<string, string>>({});
  const [showApiKeys, setShowApiKeys] = useState<Record<string, boolean>>({});
  const [baseUrlValues, setBaseUrlValues] = useState<Record<string, string>>(
    {},
  );
  const [modelConfigs, setModelConfigs] = useState<
    Record<string, ProviderModelConfig>
  >({});
  const [availableModels, setAvailableModels] = useState<
    Record<string, LLMModel[]>
  >({});
  const [expandedProviders, setExpandedProviders] = useState<
    Record<string, boolean>
  >({});
  const [loadingModels, setLoadingModels] = useState<Record<string, boolean>>(
    {},
  );
  const [verifying, setVerifying] = useState<Record<string, boolean>>({});

  // 載入配置
  const loadConfigs = async () => {
    setLoading(true);
    try {
      if (activeCategory === "llm_providers") {
        // 載入 LLM Provider 狀態（使用批量 API 提高速度）
        const statuses: Record<
          string,
          {
            has_api_key: boolean;
            base_url?: string;
            default_model?: ProviderModelConfig;
            updated_at?: string;
            health_status?: string;
          }
        > = {};
        const baseUrls: Record<string, string> = {};
        const modelConfigsData: Record<string, ProviderModelConfig> = {};
        const modelsData: Record<string, LLMModel[]> = {};

        // 初始化所有 Provider 為未配置狀態
        for (const provider of llmProviders) {
          statuses[provider.id] = { has_api_key: false };
          modelsData[provider.id] = [];
        }

        // 優先使用批量 API 獲取所有 Provider 狀態（單個請求，更快）
        try {
          const timeoutPromise = new Promise<never>((_, reject) => {
            setTimeout(() => reject(new Error("Request timeout")), 10000);
          });

          const allStatusResp = (await Promise.race([
            getAllProvidersStatus(),
            timeoutPromise,
          ])) as any;

          if (
            allStatusResp &&
            allStatusResp.success &&
            allStatusResp.data?.statuses
          ) {
            // 處理批量響應
            for (const status of allStatusResp.data.statuses) {
              const providerId = status.provider;
              statuses[providerId] = status;
              if (status.base_url) {
                baseUrls[providerId] = status.base_url;
              }
              if (status.default_model) {
                modelConfigsData[providerId] = status.default_model;
              }
            }
          }
        } catch (error: any) {
          // 批量 API 失敗，fallback 到單個請求（並行）
          console.warn(
            "Batch API failed, falling back to individual requests:",
            error,
          );

          // Fallback: 並行載入單個 Provider 狀態
          const providerPromises = llmProviders.map(async (provider) => {
            try {
              const timeoutPromise = new Promise<never>((_, reject) => {
                setTimeout(() => reject(new Error("Request timeout")), 5000);
              });

              const statusResp = (await Promise.race([
                getProviderAPIKeyStatus(provider.id),
                timeoutPromise,
              ])) as any;

              if (statusResp && statusResp.success && statusResp.data?.status) {
                const status = statusResp.data.status;
                statuses[provider.id] = status;
                if (status.base_url) {
                  baseUrls[provider.id] = status.base_url;
                }
                if (status.default_model) {
                  modelConfigsData[provider.id] = status.default_model;
                }
              }
            } catch (e) {
              // 靜默處理錯誤，保持未配置狀態
            }
          });

          // 等待所有請求完成，最多等待 10 秒
          await Promise.race([
            Promise.allSettled(providerPromises),
            new Promise<void>((resolve) => setTimeout(resolve, 10000)),
          ]);
        }

        // 載入所有 Provider 的模型列表（並行載入，提高速度）
        const modelPromises = llmProviders.map(async (provider) => {
          try {
            const modelsResp = await getModels({
              provider: provider.id,
              limit: 100,
              include_inactive: true,  // 管理界面：包含未激活的模型
            });
            console.log(`[SystemSettings] Models response for ${provider.id}:`, modelsResp);
            if (modelsResp.success && modelsResp.data?.models) {
              const models = modelsResp.data.models;
              console.log(`[SystemSettings] Loaded ${models.length} models for ${provider.id}:`, models.map(m => m.model_id));
              return {
                providerId: provider.id,
                models: models,
              };
            } else {
              console.warn(`[SystemSettings] Invalid response for ${provider.id}:`, {
                success: modelsResp.success,
                hasData: !!modelsResp.data,
                hasModels: !!modelsResp.data?.models,
                response: modelsResp,
              });
            }
          } catch (e) {
            console.error(`[SystemSettings] Failed to load models for ${provider.id}:`, e);
          }
          return { providerId: provider.id, models: [] };
        });

        const modelResults = await Promise.allSettled(modelPromises);
        const modelsMap: Record<string, LLMModel[]> = {};
        for (const result of modelResults) {
          if (result.status === "fulfilled" && result.value) {
            modelsMap[result.value.providerId] = result.value.models;
            console.log(`[SystemSettings] Set models for ${result.value.providerId}: ${result.value.models.length} models`);
          } else if (result.status === "rejected") {
            console.error(`[SystemSettings] Model promise rejected:`, result.reason);
          }
        }
        console.log(`[SystemSettings] Final modelsMap:`, modelsMap);

        setProviderStatuses(statuses);
        setBaseUrlValues(baseUrls);
        setModelConfigs(modelConfigsData);
        setAvailableModels(modelsMap);
      } else {
        // 根據當前選擇的分類載入配置
        const categoryMap: Record<ConfigCategory, string> = {
          basic: "basic",
          features: "feature_flag",
          performance: "performance",
          security: "security",
          business: "business",
          llm_providers: "", // 不會執行到這裡
        };
        const category = categoryMap[activeCategory];
        try {
          const result = await getSystemConfigs(undefined, category);
          setConfigs(result);
        } catch (error: any) {
          // 如果請求失敗（超時或權限問題），顯示友好提示
          console.error("Failed to load system configs:", error);
          const errorMessage =
            error.message || error.data?.detail || String(error);

          if (
            errorMessage.includes("timeout") ||
            errorMessage.includes("Timeout")
          ) {
            toast.error("載入系統配置超時，請稍後再試或聯繫管理員");
          } else if (
            error.status === 403 ||
            errorMessage.includes("permission") ||
            errorMessage.includes("權限")
          ) {
            toast.error("您沒有權限訪問系統配置");
          } else if (error.status === 401) {
            toast.error("請先登錄");
          } else {
            toast.error(`載入系統配置失敗: ${errorMessage}`);
          }
          // 設置空列表，避免 UI 卡住
          setConfigs([]);
        }
      }
    } catch (error: any) {
      console.error("Failed to load configs:", error);
      // 錯誤處理已在各個分支中處理，這裡只記錄日誌
      if (activeCategory !== "llm_providers") {
        // 對於系統配置請求，錯誤已在上面處理
        // 這裡不需要再次顯示錯誤提示
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // 只在 activeCategory 改變時載入配置
    // 如果切換到非 LLM Provider 標籤頁，才載入系統配置
    if (activeCategory !== "llm_providers") {
      loadConfigs();
    } else {
      // LLM Provider 配置直接載入（不依賴系統配置 API）
      loadConfigs();
    }
  }, [activeCategory]); // 當分類改變時重新載入

  // 保存配置
  const handleSaveConfig = async (scope: string, data: Record<string, any>) => {
    try {
      await updateSystemConfig(scope, data);
      await loadConfigs(); // 重新載入配置
      toast.success("配置保存成功");
    } catch (error) {
      console.error("Failed to update config:", error);
      toast.error("保存配置失敗");
      throw error;
    }
  };

  // 處理 Provider 完整配置更新
  const handleUpdateProviderConfig = async (provider: string) => {
    const apiKey = apiKeyValues[provider]?.trim();
    const baseUrl = baseUrlValues[provider]?.trim();
    const modelConfig = modelConfigs[provider];

    // 至少需要 API Key 或 Base URL 或 Model Config
    if (!apiKey && !baseUrl && !modelConfig) {
      toast.error("請至少配置一項內容");
      return;
    }

    try {
      setLoading(true);
      const updateRequest: ProviderConfigUpdateRequest = {};

      if (apiKey) {
        updateRequest.api_key = apiKey;
      }
      if (baseUrl) {
        updateRequest.base_url = baseUrl;
      }
      if (modelConfig) {
        updateRequest.default_model = modelConfig;
      }

      await updateProviderConfig(provider, updateRequest);
      toast.success(
        `${llmProviders.find((p) => p.id === provider)?.name || provider} 配置更新成功`,
      );
      setEditingProvider(null);
      setApiKeyValues({ ...apiKeyValues, [provider]: "" });
      await loadConfigs(); // 重新載入狀態
    } catch (error: any) {
      console.error(`Failed to update config for ${provider}:`, error);
      toast.error(`更新失敗: ${error.message || "未知錯誤"}`);
    } finally {
      setLoading(false);
    }
  };

  // 處理 Provider API Key 刪除
  const handleDeleteProviderAPIKey = async (provider: string) => {
    if (
      !confirm(
        `確定要刪除 ${llmProviders.find((p) => p.id === provider)?.name || provider} 的 API Key 嗎？`,
      )
    ) {
      return;
    }

    try {
      setLoading(true);
      await deleteProviderAPIKey(provider);
      toast.success("API Key 已刪除");
      await loadConfigs(); // 重新載入狀態
    } catch (error: any) {
      console.error(`Failed to delete API key for ${provider}:`, error);
      toast.error(`刪除失敗: ${error.message || "未知錯誤"}`);
    } finally {
      setLoading(false);
    }
  };

  // 處理 Provider 連通性驗證
  const handleVerifyProvider = async (provider: string, testApiKey?: string) => {
    try {
      setVerifying({ ...verifying, [provider]: true });
      const result = await verifyProviderConnectivity(provider, testApiKey);

      if (result.success) {
        toast.success(result.message || "連通性驗證成功");
      } else {
        toast.error(result.message || "連通性驗證失敗");
      }
    } catch (error: any) {
      console.error(`Failed to verify connectivity for ${provider}:`, error);
      toast.error(`驗證過程中出錯: ${error.message || "未知錯誤"}`);
    } finally {
      setVerifying({ ...verifying, [provider]: false });
    }
  };

  // 返回上一頁或主頁
  const handleBack = () => {
    navigate("/home");
  };

  // 過濾配置（因為已經按分類載入，這裡只需要按搜索詞過濾）
  const filteredConfigs = configs.filter((config) => {
    // 根據搜索詞過濾
    const searchMatch =
      !searchTerm ||
      config.scope.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (config.sub_scope &&
        config.sub_scope.toLowerCase().includes(searchTerm.toLowerCase()));

    return searchMatch;
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 頂部導航欄 */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            <button
              onClick={handleBack}
              className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft size={20} />
              <span>返回</span>
            </button>
            <div className="h-6 w-px bg-gray-300"></div>
            <h1 className="text-2xl font-bold text-gray-900">系統設置</h1>
          </div>

          <button
            onClick={loadConfigs}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            <span>刷新</span>
          </button>
        </div>

        {/* 類別標籤頁 */}
        <div className="flex space-x-4 overflow-x-auto">
          {categories.map((category) => (
            <button
              key={category.id}
              onClick={() => setActiveCategory(category.id)}
              className={`px-4 py-2 font-medium whitespace-nowrap transition-colors ${
                activeCategory === category.id
                  ? "text-blue-600 border-b-2 border-blue-600"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {category.label}
            </button>
          ))}
        </div>
      </div>

      {/* 內容區域 */}
      <div className="px-6 py-6">
        {/* 搜索框 */}
        <div className="mb-6">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="搜索配置項..."
            className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* 配置列表 */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="animate-spin text-gray-400" size={32} />
            <span className="ml-3 text-gray-600">載入中...</span>
          </div>
        ) : activeCategory === "llm_providers" ? (
          /* LLM Provider API Key 管理 */
          <div className="space-y-4">
            {llmProviders.map((provider) => {
              const status = providerStatuses[provider.id] || {
                has_api_key: false,
              };
              const isEditing = editingProvider === provider.id;
              const apiKeyValue = apiKeyValues[provider.id] || "";

              return (
                <div
                  key={provider.id}
                  className="bg-white rounded-lg shadow p-6"
                >
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center space-x-3">
                      <i
                        className={`fa-solid ${provider.icon} ${provider.color} text-xl`}
                      ></i>
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          {provider.name}
                        </h3>
                        <div className="flex items-center space-x-4 mt-1">
                          <span
                            className={`text-sm ${status.has_api_key ? "text-green-600" : "text-red-600"}`}
                          >
                            {status.has_api_key ? (
                              <>
                                <i className="fa-solid fa-check-circle mr-1"></i>
                                已配置
                              </>
                            ) : (
                              <>
                                <i className="fa-solid fa-times-circle mr-1"></i>
                                未配置
                              </>
                            )}
                          </span>
                          {status.updated_at && (
                            <span className="text-xs text-gray-500">
                              更新時間:{" "}
                              {new Date(status.updated_at).toLocaleString(
                                "zh-TW",
                              )}
                            </span>
                          )}
                          {status.health_status && (
                            <span
                              className={`text-xs ${status.health_status === "healthy" ? "text-green-600" : "text-yellow-600"}`}
                            >
                              狀態: {status.health_status}
                            </span>
                          )}
                        </div>
                        {status.default_model && (
                          <div className="mt-2 text-xs text-gray-600">
                            <span className="font-medium">默認模型:</span>{" "}
                            {status.default_model.model_id}
                            {status.default_model.max_tokens && (
                              <span className="ml-2">
                                Max Tokens: {status.default_model.max_tokens}
                              </span>
                            )}
                            {status.default_model.temperature !== undefined && (
                              <span className="ml-2">
                                Temperature: {status.default_model.temperature}
                              </span>
                            )}
                            {status.default_model.context_window && (
                              <span className="ml-2">
                                Context:{" "}
                                {status.default_model.context_window.toLocaleString()}
                              </span>
                            )}
                          </div>
                        )}
                        {status.base_url && (
                          <div className="mt-1 text-xs text-gray-500">
                            Base URL: {status.base_url}
                          </div>
                        )}
                      </div>
                    </div>
                    {/* 模型列表顯示 */}
                    <div className="mt-4">
                      <button
                        onClick={() => {
                          setExpandedProviders({
                            ...expandedProviders,
                            [provider.id]: !expandedProviders[provider.id],
                          });
                          // 如果展開且模型列表未載入，則載入
                          if (
                            !expandedProviders[provider.id] &&
                            (!availableModels[provider.id] ||
                              availableModels[provider.id].length === 0)
                          ) {
                            setLoadingModels({
                              ...loadingModels,
                              [provider.id]: true,
                            });
                            getModels({ provider: provider.id, limit: 100 })
                              .then((resp) => {
                                if (resp.success && resp.data?.models) {
                                  setAvailableModels({
                                    ...availableModels,
                                    [provider.id]: resp.data.models,
                                  });
                                }
                              })
                              .catch((e) => {
                                console.warn(
                                  `Failed to load models for ${provider.id}:`,
                                  e,
                                );
                              })
                              .finally(() => {
                                setLoadingModels({
                                  ...loadingModels,
                                  [provider.id]: false,
                                });
                              });
                          }
                        }}
                        className="flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-800 transition-colors"
                      >
                        <i
                          className={`fa-solid fa-chevron-${expandedProviders[provider.id] ? "down" : "right"} text-xs`}
                        ></i>
                        <span>
                          查看模型列表 (
                          {availableModels[provider.id]?.length || 0} 個)
                        </span>
                        {loadingModels[provider.id] && (
                          <RefreshCw className="animate-spin" size={14} />
                        )}
                      </button>
                      {expandedProviders[provider.id] && (
                        <div className="mt-3 bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                          {loadingModels[provider.id] ? (
                            <div className="flex items-center justify-center py-4">
                              <RefreshCw
                                className="animate-spin text-gray-400"
                                size={20}
                              />
                              <span className="ml-2 text-sm text-gray-600">
                                載入中...
                              </span>
                            </div>
                          ) : availableModels[provider.id] &&
                            availableModels[provider.id].length > 0 ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                              {availableModels[provider.id].map((model) => (
                                <div
                                  key={model.model_id}
                                  className={`bg-white rounded-md p-3 border ${
                                    model.is_active
                                      ? "border-green-200"
                                      : "border-gray-200 opacity-60"
                                  }`}
                                >
                                  <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                      <div className="flex items-center space-x-2">
                                        <span className="font-medium text-sm text-gray-900">
                                          {model.name}
                                        </span>
                                        {model.is_active && (
                                          <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
                                            Active
                                          </span>
                                        )}
                                        {!model.is_active && (
                                          <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                                            Inactive
                                          </span>
                                        )}
                                      </div>
                                      <div className="text-xs text-gray-500 mt-1">
                                        {model.model_id}
                                      </div>
                                      {model.description && (
                                        <div className="text-xs text-gray-600 mt-1 line-clamp-2">
                                          {model.description}
                                        </div>
                                      )}
                                      <div className="flex flex-wrap gap-1 mt-2">
                                        {model.capabilities?.map((cap) => (
                                          <span
                                            key={cap}
                                            className="text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded"
                                          >
                                            {cap}
                                          </span>
                                        ))}
                                      </div>
                                      <div className="flex items-center space-x-3 mt-2 text-xs text-gray-500">
                                        {model.context_window && (
                                          <span>
                                            Context:{" "}
                                            {model.context_window.toLocaleString()}
                                          </span>
                                        )}
                                        {model.parameters && (
                                          <span>
                                            Params: {model.parameters}
                                          </span>
                                        )}
                                        {model.status && (
                                          <span
                                            className={`${
                                              model.status === "active"
                                                ? "text-green-600"
                                                : model.status === "beta"
                                                  ? "text-yellow-600"
                                                  : model.status ===
                                                      "deprecated"
                                                    ? "text-red-600"
                                                    : "text-gray-600"
                                            }`}
                                          >
                                            {model.status}
                                          </span>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="text-center py-4 text-sm text-gray-500">
                              暫無可用模型
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center space-x-2">
                      {isEditing ? (
                        <>
                          <button
                            onClick={() =>
                              handleVerifyProvider(provider.id, apiKeyValue)
                            }
                            disabled={loading || verifying[provider.id]}
                            className="px-4 py-2 bg-blue-50 text-blue-600 rounded-md hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-1"
                            title="測試連通性"
                          >
                            <ShieldCheck size={16} className={verifying[provider.id] ? "animate-pulse" : ""} />
                            <span>驗證</span>
                          </button>
                          <button
                            onClick={() =>
                              handleUpdateProviderConfig(provider.id)
                            }
                            disabled={loading}
                            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-1"
                          >
                            <Check size={16} />
                            <span>保存</span>
                          </button>
                          <button
                            onClick={() => {
                              setEditingProvider(null);
                              setApiKeyValues({
                                ...apiKeyValues,
                                [provider.id]: "",
                              });
                              // 重置為原始狀態
                              const originalStatus =
                                providerStatuses[provider.id];
                              if (originalStatus) {
                                setBaseUrlValues({
                                  ...baseUrlValues,
                                  [provider.id]: originalStatus.base_url || "",
                                });
                                setModelConfigs({
                                  ...modelConfigs,
                                  [provider.id]:
                                    originalStatus.default_model || undefined,
                                });
                              }
                            }}
                            disabled={loading}
                            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-1"
                          >
                            <X size={16} />
                            <span>取消</span>
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={async () => {
                              setEditingProvider(provider.id);
                              // 初始化編輯值
                              if (
                                status.base_url &&
                                !baseUrlValues[provider.id]
                              ) {
                                setBaseUrlValues({
                                  ...baseUrlValues,
                                  [provider.id]: status.base_url,
                                });
                              }
                              if (
                                status.default_model &&
                                !modelConfigs[provider.id]
                              ) {
                                setModelConfigs({
                                  ...modelConfigs,
                                  [provider.id]: status.default_model,
                                });
                              }

                              // 延遲載入模型列表（只在編輯時載入）
                              if (
                                !availableModels[provider.id] ||
                                availableModels[provider.id].length === 0
                              ) {
                                try {
                                  const modelsResp = await getModels({
                                    provider: provider.id,
                                    limit: 100,
                                  });
                                  if (
                                    modelsResp.success &&
                                    modelsResp.data?.models
                                  ) {
                                    setAvailableModels({
                                      ...availableModels,
                                      [provider.id]: modelsResp.data.models,
                                    });
                                  }
                                } catch (e) {
                                  console.warn(
                                    `Failed to load models for ${provider.id}:`,
                                    e,
                                  );
                                  setAvailableModels({
                                    ...availableModels,
                                    [provider.id]: [],
                                  });
                                }
                              }
                            }}
                            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center space-x-1"
                          >
                            <Edit2 size={16} />
                            <span>{status.has_api_key ? "更新" : "設置"}</span>
                          </button>
                          {status.has_api_key && (
                            <>
                              <button
                                onClick={() =>
                                  handleVerifyProvider(provider.id)
                                }
                                disabled={loading || verifying[provider.id]}
                                className="px-4 py-2 bg-blue-50 text-blue-600 rounded-md hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-1"
                                title="測試連通性"
                              >
                                <ShieldCheck size={16} className={verifying[provider.id] ? "animate-pulse" : ""} />
                                <span>驗證</span>
                              </button>
                              <button
                                onClick={() =>
                                  handleDeleteProviderAPIKey(provider.id)
                                }
                                disabled={loading}
                                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-1"
                              >
                                <Trash2 size={16} />
                                <span>刪除</span>
                              </button>
                            </>
                          )}
                        </>
                      )}
                    </div>
                  </div>

                  {isEditing && (
                    <div className="mt-4 pt-4 border-t border-gray-200 space-y-4">
                      {/* API Key */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          API Key
                        </label>
                        <div className="relative">
                          <input
                            type={
                              showApiKeys[provider.id] ? "text" : "password"
                            }
                            autoComplete="new-password"
                            value={apiKeyValue}
                            onChange={(e) =>
                              setApiKeyValues({
                                ...apiKeyValues,
                                [provider.id]: e.target.value,
                              })
                            }
                            placeholder={status.has_api_key ? "已配置 API Key（輸入以覆蓋）" : "輸入 API Key（將被加密存儲）"}
                            className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setShowApiKeys({
                                ...showApiKeys,
                                [provider.id]: !showApiKeys[provider.id],
                              })
                            }
                            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                          >
                            {showApiKeys[provider.id] ? (
                              <EyeOff size={18} />
                            ) : (
                              <Eye size={18} />
                            )}
                          </button>
                        </div>
                        <p className="mt-1 text-xs text-gray-500">
                          API Key 將使用 AES-256
                          加密存儲，永遠不會以明文形式返回
                        </p>
                      </div>

                      {/* Base URL */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Base URL
                        </label>
                        <input
                          type="text"
                          value={
                            baseUrlValues[provider.id] ?? status.base_url ?? ""
                          }
                          onChange={(e) =>
                            setBaseUrlValues({
                              ...baseUrlValues,
                              [provider.id]: e.target.value,
                            })
                          }
                          placeholder={
                            status.base_url ||
                            `預設: ${getDefaultBaseUrl(provider.id)}`
                          }
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <p className="mt-1 text-xs text-gray-500">
                          {status.base_url
                            ? "留空將使用當前配置的 Base URL"
                            : `預設值: ${getDefaultBaseUrl(provider.id)}`}
                        </p>
                      </div>

                      {/* 模型選擇和參數配置 */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          默認模型配置
                        </label>
                        <div className="space-y-3">
                          {/* 模型選擇 */}
                          <div>
                            <label className="block text-xs text-gray-600 mb-1">
                              模型
                            </label>
                            <select
                              value={modelConfigs[provider.id]?.model_id || ""}
                              onChange={(e) => {
                                const selectedModel = availableModels[
                                  provider.id
                                ]?.find((m) => m.model_id === e.target.value);
                                setModelConfigs({
                                  ...modelConfigs,
                                  [provider.id]: {
                                    model_id: e.target.value,
                                    max_tokens:
                                      modelConfigs[provider.id]?.max_tokens ||
                                      selectedModel?.max_output_tokens ||
                                      4096,
                                    temperature:
                                      modelConfigs[provider.id]?.temperature ||
                                      0.7,
                                    context_window:
                                      modelConfigs[provider.id]
                                        ?.context_window ||
                                      selectedModel?.context_window ||
                                      32000,
                                  },
                                });
                              }}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                              <option value="">選擇模型...</option>
                              {availableModels[provider.id]?.map((model) => (
                                <option
                                  key={model.model_id}
                                  value={model.model_id}
                                >
                                  {model.name} ({model.model_id})
                                </option>
                              ))}
                            </select>
                          </div>

                          {/* 參數配置 */}
                          {modelConfigs[provider.id]?.model_id && (
                            <div className="grid grid-cols-2 gap-3">
                              <div>
                                <label className="block text-xs text-gray-600 mb-1">
                                  Max Tokens
                                </label>
                                <input
                                  type="number"
                                  value={
                                    modelConfigs[provider.id]?.max_tokens || ""
                                  }
                                  onChange={(e) =>
                                    setModelConfigs({
                                      ...modelConfigs,
                                      [provider.id]: {
                                        ...modelConfigs[provider.id]!,
                                        max_tokens:
                                          parseInt(e.target.value) || undefined,
                                      },
                                    })
                                  }
                                  placeholder="4096"
                                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                              </div>
                              <div>
                                <label className="block text-xs text-gray-600 mb-1">
                                  Temperature
                                </label>
                                <input
                                  type="number"
                                  step="0.1"
                                  min="0"
                                  max="2"
                                  value={
                                    modelConfigs[provider.id]?.temperature || ""
                                  }
                                  onChange={(e) =>
                                    setModelConfigs({
                                      ...modelConfigs,
                                      [provider.id]: {
                                        ...modelConfigs[provider.id]!,
                                        temperature:
                                          parseFloat(e.target.value) ||
                                          undefined,
                                      },
                                    })
                                  }
                                  placeholder="0.7"
                                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                              </div>
                              <div className="col-span-2">
                                <label className="block text-xs text-gray-600 mb-1">
                                  Context Window (tokens)
                                </label>
                                <input
                                  type="number"
                                  value={
                                    modelConfigs[provider.id]?.context_window ||
                                    ""
                                  }
                                  onChange={(e) =>
                                    setModelConfigs({
                                      ...modelConfigs,
                                      [provider.id]: {
                                        ...modelConfigs[provider.id]!,
                                        context_window:
                                          parseInt(e.target.value) || undefined,
                                      },
                                    })
                                  }
                                  placeholder="32000"
                                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : filteredConfigs.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <p className="text-gray-600">沒有找到配置項</p>
          </div>
        ) : (
          <div>
            {filteredConfigs.map((config) => (
              <ConfigEditor
                key={config.scope}
                config={config}
                onSave={handleSaveConfig}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SystemSettings;
