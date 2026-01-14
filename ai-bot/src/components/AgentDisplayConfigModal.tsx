// 代碼功能說明: Agent Display Config 編輯模態框組件
// 創建日期: 2026-01-13
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-13

/**
 * Agent Display Config 編輯模態框
 * 用於創建或編輯代理展示配置（名稱、描述、圖標、狀態等）
 */

import { useState, useEffect, useCallback } from 'react';
import { useLanguage } from '../contexts/languageContext';
import { cn } from '../lib/utils';
import { getAgentConfig, updateAgentConfig } from '../lib/api';
import type { AgentConfig, MultilingualText } from '../types/agentDisplayConfig';
import IconPicker from './IconPicker';

interface AgentDisplayConfigModalProps {
  isOpen: boolean;
  agentId?: string; // 編輯時傳入，創建時不傳
  categoryId?: string; // 創建時需要指定分類 ID
  onClose: () => void;
  onSuccess?: () => void;
}

export default function AgentDisplayConfigModal({
  isOpen,
  agentId,
  categoryId,
  onClose,
  onSuccess,
}: AgentDisplayConfigModalProps) {
  const { t, language } = useLanguage();
  const isEditMode = !!agentId;
  const [activeTab, setActiveTab] = useState<'basic' | 'display'>('basic');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 表單字段
  const [agentIdValue, setAgentIdValue] = useState('');
  const [categoryIdValue, setCategoryIdValue] = useState(categoryId || '');
  const [displayOrder, setDisplayOrder] = useState(1);
  const [isVisible, setIsVisible] = useState(true);
  const [selectedIcon, setSelectedIcon] = useState<string>('fa-robot');
  const [showIconPicker, setShowIconPicker] = useState(false);
  const [status, setStatus] = useState<'registering' | 'online' | 'maintenance' | 'deprecated'>('online');

  // 多語言名稱
  const [nameEn, setNameEn] = useState('');
  const [nameZhCN, setNameZhCN] = useState('');
  const [nameZhTW, setNameZhTW] = useState('');

  // 多語言描述
  const [descriptionEn, setDescriptionEn] = useState('');
  const [descriptionZhCN, setDescriptionZhCN] = useState('');
  const [descriptionZhTW, setDescriptionZhTW] = useState('');

  // 加載現有配置（編輯模式）
  const loadAgentConfig = useCallback(async () => {
    if (!agentId) return;

    setIsLoading(true);
    setError(null);

    try {
      const config = await getAgentConfig(agentId);

      // 填充表單
      setAgentIdValue(config.id || agentId);
      setCategoryIdValue(config.category_id || '');
      setDisplayOrder(config.display_order || 1);
      setIsVisible(config.is_visible !== false);
      setSelectedIcon(config.icon || 'fa-robot');
      setStatus(config.status || 'online');

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
    setNameEn('');
    setNameZhCN('');
    setNameZhTW('');
    setDescriptionEn('');
    setDescriptionZhCN('');
    setDescriptionZhTW('');
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
                  {/* Agent ID（編輯時只讀，與註冊頁面一致） */}
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

                  {/* Icon 選擇（與註冊頁面一致） */}
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
          selectedIcon={undefined} // IconPicker 使用 react-icons 格式，我們使用 FontAwesome 格式，所以不傳遞
          onClose={() => setShowIconPicker(false)}
          onSelect={(icon) => {
            // IconPicker 返回的可能是 react-icons 格式（如 'FaRobot'）或 FontAwesome 格式（如 'fa-robot'）
            // 如果已經是 FontAwesome 格式（以 fa- 開頭），直接使用
            if (icon.startsWith('fa-')) {
              setSelectedIcon(icon);
            } else {
              // 轉換 react-icons 格式為 FontAwesome 格式
              // 移除前綴（Fa, Md, Hi, Si 等）
              let faIcon = icon.replace(/^(Fa|Md|Hi|Si|Lu|Tb|Ri|Bs|Bi|Ai|Io|Gr|Im|Wi|Di|Fi|Gi|Go|Hi2|Sl|Tb2|Vsc|Cg|Ri4|Bs5|Bi5|Ai5|Io5|Gr5|Im5|Wi5|Di5|Fi5|Gi5|Go5|Hi25|Sl5|Tb25|Vsc5|Cg5)/, '');

              // 將駝峰命名轉換為 kebab-case
              faIcon = faIcon.replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase();

              // 確保以 fa- 開頭
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
