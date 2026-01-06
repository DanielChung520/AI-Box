/**
 * 代碼功能說明: 文件訪問控制設置模態框組件 (WBS-4.5.2)
 * 創建日期: 2026-01-02
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-02
 *
 * 功能說明:
 * - 設置文件訪問級別（PUBLIC, ORGANIZATION, SECURITY_GROUP, PRIVATE）
 * - 設置數據分類級別（PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED）
 * - 設置敏感性標籤（PII, PHI, FINANCIAL, IP, CUSTOMER, PROPRIETARY）
 * - 條件渲染：根據訪問級別顯示對應的授權選擇器
 * - 訪問權限過期時間設置（可選）
 */

import { useState, useEffect } from 'react';
import { X, Lock, Globe, Building2, Users, User } from 'lucide-react';
import {
  FileAccessControl,
  FileAccessLevel,
  DataClassification,
  SensitivityLabel,
  updateFileAccessControl,
  getFileAccessControl,
} from '../lib/api';

interface FileAccessControlModalProps {
  isOpen: boolean;
  onClose: () => void;
  fileId: string;
  fileName: string;
  ownerId: string;
  onSuccess?: () => void;
}

export default function FileAccessControlModal({
  isOpen,
  onClose,
  fileId,
  fileName,
  ownerId,
  onSuccess,
}: FileAccessControlModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [accessLevel, setAccessLevel] = useState<FileAccessLevel>(FileAccessLevel.PRIVATE);
  const [dataClassification, setDataClassification] = useState<DataClassification>(
    DataClassification.INTERNAL
  );
  const [sensitivityLabels, setSensitivityLabels] = useState<SensitivityLabel[]>([]);
  const [authorizedOrganizations, setAuthorizedOrganizations] = useState<string[]>([]);
  const [authorizedSecurityGroups, setAuthorizedSecurityGroups] = useState<string[]>([]);
  const [authorizedUsers, setAuthorizedUsers] = useState<string[]>([]);
  const [accessExpiresAt, setAccessExpiresAt] = useState<string>('');
  const [accessLogEnabled, setAccessLogEnabled] = useState(true);

  // 加載現有配置
  useEffect(() => {
    if (isOpen && fileId) {
      loadAccessControl();
    }
  }, [isOpen, fileId]);

  const loadAccessControl = async () => {
    try {
      const response = await getFileAccessControl(fileId);
      if (response.success && response.data) {
        const acl = response.data;
        setAccessLevel(acl.access_level as FileAccessLevel);
        setDataClassification(
          (acl.data_classification as DataClassification) || DataClassification.INTERNAL
        );
        setSensitivityLabels((acl.sensitivity_labels as SensitivityLabel[]) || []);
        setAuthorizedOrganizations(acl.authorized_organizations || []);
        setAuthorizedSecurityGroups(acl.authorized_security_groups || []);
        setAuthorizedUsers(acl.authorized_users || []);
        setAccessExpiresAt(acl.access_expires_at || '');
        setAccessLogEnabled(acl.access_log_enabled !== false);
      } else {
        // 使用默認配置
        setAccessLevel(FileAccessLevel.PRIVATE);
        setDataClassification(DataClassification.INTERNAL);
        setSensitivityLabels([]);
        setAuthorizedOrganizations([]);
        setAuthorizedSecurityGroups([]);
        setAuthorizedUsers([ownerId]);
        setAccessExpiresAt('');
        setAccessLogEnabled(true);
      }
    } catch (err: any) {
      console.error('Failed to load access control:', err);
      setError(err.message || '加載訪問控制配置失敗');
    }
  };

  const handleSensitivityLabelToggle = (label: SensitivityLabel) => {
    setSensitivityLabels((prev) => {
      if (prev.includes(label)) {
        return prev.filter((l) => l !== label);
      }
      return [...prev, label];
    });
  };

  const handleSave = async () => {
    setLoading(true);
    setError(null);

    try {
      const acl: FileAccessControl = {
        access_level: accessLevel,
        data_classification: dataClassification,
        sensitivity_labels: sensitivityLabels.length > 0 ? sensitivityLabels : undefined,
        owner_id: ownerId,
        access_log_enabled: accessLogEnabled,
        access_expires_at: accessExpiresAt || undefined,
      };

      // 根據訪問級別設置對應的授權列表
      if (accessLevel === FileAccessLevel.ORGANIZATION) {
        acl.authorized_organizations =
          authorizedOrganizations.length > 0 ? authorizedOrganizations : undefined;
      } else if (accessLevel === FileAccessLevel.SECURITY_GROUP) {
        acl.authorized_security_groups =
          authorizedSecurityGroups.length > 0 ? authorizedSecurityGroups : undefined;
      } else if (accessLevel === FileAccessLevel.PRIVATE) {
        acl.authorized_users =
          authorizedUsers.length > 0 ? authorizedUsers : [ownerId];
      }

      const response = await updateFileAccessControl(fileId, acl);
      if (response.success) {
        onSuccess?.();
        onClose();
      } else {
        setError(response.message || '更新訪問控制配置失敗');
      }
    } catch (err: any) {
      console.error('Failed to update access control:', err);
      setError(err.message || '更新訪問控制配置失敗');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-primary border border-border rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* 標題欄 */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold text-primary">設置文件權限</h2>
          <button
            onClick={onClose}
            className="text-tertiary hover:text-primary transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 文件信息 */}
        <div className="p-4 border-b border-border">
          <p className="text-sm text-secondary">
            文件：
            <span className="font-medium text-primary ml-1">{fileName}</span>
          </p>
        </div>

        {/* 表單內容 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* 錯誤提示 */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded p-3 text-sm text-red-400">
              {error}
            </div>
          )}

          {/* 訪問級別選擇 */}
          <div>
            <label className="block text-sm font-medium text-primary mb-2">
              訪問級別
            </label>
            <div className="grid grid-cols-2 gap-2">
              {[
                { value: FileAccessLevel.PUBLIC, label: '公開', icon: Globe },
                { value: FileAccessLevel.ORGANIZATION, label: '組織', icon: Building2 },
                { value: FileAccessLevel.SECURITY_GROUP, label: '安全組', icon: Users },
                { value: FileAccessLevel.PRIVATE, label: '私有', icon: Lock },
              ].map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setAccessLevel(value)}
                  className={`flex items-center gap-2 p-3 rounded border transition-colors ${
                    accessLevel === value
                      ? 'bg-blue-500/20 border-blue-500 text-blue-400'
                      : 'bg-secondary border-border text-secondary hover:border-primary'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="text-sm">{label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* 條件渲染：組織選擇器 */}
          {accessLevel === FileAccessLevel.ORGANIZATION && (
            <div>
              <label className="block text-sm font-medium text-primary mb-2">
                授權組織 ID（每行一個）
              </label>
              <textarea
                value={authorizedOrganizations.join('\n')}
                onChange={(e) =>
                  setAuthorizedOrganizations(
                    e.target.value.split('\n').filter((id) => id.trim())
                  )
                }
                className="w-full p-2 bg-secondary border border-border rounded text-primary text-sm"
                rows={3}
                placeholder="org1&#10;org2"
              />
            </div>
          )}

          {/* 條件渲染：安全組選擇器 */}
          {accessLevel === FileAccessLevel.SECURITY_GROUP && (
            <div>
              <label className="block text-sm font-medium text-primary mb-2">
                授權安全組 ID（每行一個）
              </label>
              <textarea
                value={authorizedSecurityGroups.join('\n')}
                onChange={(e) =>
                  setAuthorizedSecurityGroups(
                    e.target.value.split('\n').filter((id) => id.trim())
                  )
                }
                className="w-full p-2 bg-secondary border border-border rounded text-primary text-sm"
                rows={3}
                placeholder="group1&#10;group2"
              />
            </div>
          )}

          {/* 條件渲染：用戶選擇器 */}
          {accessLevel === FileAccessLevel.PRIVATE && (
            <div>
              <label className="block text-sm font-medium text-primary mb-2">
                授權用戶 ID（每行一個）
              </label>
              <textarea
                value={authorizedUsers.join('\n')}
                onChange={(e) =>
                  setAuthorizedUsers(e.target.value.split('\n').filter((id) => id.trim()))
                }
                className="w-full p-2 bg-secondary border border-border rounded text-primary text-sm"
                rows={3}
                placeholder="user1&#10;user2"
              />
              <p className="text-xs text-tertiary mt-1">
                注意：文件所有者（{ownerId}）自動包含在授權列表中
              </p>
            </div>
          )}

          {/* 數據分類級別 */}
          <div>
            <label className="block text-sm font-medium text-primary mb-2">
              數據分類級別
            </label>
            <select
              value={dataClassification}
              onChange={(e) => setDataClassification(e.target.value as DataClassification)}
              className="w-full p-2 bg-secondary border border-border rounded text-primary text-sm"
            >
              <option value={DataClassification.PUBLIC}>公開</option>
              <option value={DataClassification.INTERNAL}>內部</option>
              <option value={DataClassification.CONFIDENTIAL}>機密</option>
              <option value={DataClassification.RESTRICTED}>受限</option>
            </select>
          </div>

          {/* 敏感性標籤 */}
          <div>
            <label className="block text-sm font-medium text-primary mb-2">
              敏感性標籤（可多選）
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { value: SensitivityLabel.PII, label: 'PII' },
                { value: SensitivityLabel.PHI, label: 'PHI' },
                { value: SensitivityLabel.FINANCIAL, label: '財務' },
                { value: SensitivityLabel.IP, label: 'IP' },
                { value: SensitivityLabel.CUSTOMER, label: '客戶' },
                { value: SensitivityLabel.PROPRIETARY, label: '專有' },
              ].map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => handleSensitivityLabelToggle(value)}
                  className={`p-2 rounded border transition-colors text-sm ${
                    sensitivityLabels.includes(value)
                      ? 'bg-blue-500/20 border-blue-500 text-blue-400'
                      : 'bg-secondary border-border text-secondary hover:border-primary'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* 訪問權限過期時間 */}
          <div>
            <label className="block text-sm font-medium text-primary mb-2">
              訪問權限過期時間（可選）
            </label>
            <input
              type="datetime-local"
              value={accessExpiresAt}
              onChange={(e) => setAccessExpiresAt(e.target.value)}
              className="w-full p-2 bg-secondary border border-border rounded text-primary text-sm"
            />
            <p className="text-xs text-tertiary mt-1">
              留空表示永不過期
            </p>
          </div>

          {/* 訪問日誌開關 */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="accessLogEnabled"
              checked={accessLogEnabled}
              onChange={(e) => setAccessLogEnabled(e.target.checked)}
              className="w-4 h-4"
            />
            <label htmlFor="accessLogEnabled" className="text-sm text-primary">
              啟用訪問日誌記錄
            </label>
          </div>
        </div>

        {/* 操作按鈕 */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-border">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-sm text-secondary hover:text-primary transition-colors disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            className="px-4 py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}

