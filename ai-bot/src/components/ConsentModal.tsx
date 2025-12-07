/**
 * 代碼功能說明: 數據使用同意模態框組件
 * 創建日期: 2025-12-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-06
 */

import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { api } from '../lib/api';

interface ConsentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConsent: () => void;
  consentType: 'file_upload' | 'ai_processing' | 'data_sharing' | 'training';
}

const CONSENT_TEXTS: Record<string, { title: string; content: string }> = {
  file_upload: {
    title: '文件上傳同意',
    content: `
      為了使用文件上傳功能，我們需要您同意以下條款：

      1. 您上傳的文件將存儲在我們的服務器中
      2. 您的文件可能會用於AI處理和分析
      3. 我們會採取適當的安全措施保護您的數據
      4. 您可以隨時撤銷此同意

      請仔細閱讀並確認是否同意。
    `,
  },
  ai_processing: {
    title: 'AI處理同意',
    content: `
      為了提供AI處理服務，我們需要您同意以下條款：

      1. 您的文件內容將被用於AI分析和處理
      2. 處理結果可能用於改進我們的服務
      3. 我們不會將您的數據用於其他商業目的
      4. 您可以隨時撤銷此同意

      請仔細閱讀並確認是否同意。
    `,
  },
  data_sharing: {
    title: '數據共享同意',
    content: `
      為了提供更好的服務，我們需要您同意以下條款：

      1. 我們可能會在安全的環境中共享必要的數據
      2. 所有共享都將遵守隱私保護規定
      3. 我們不會將您的數據出售給第三方
      4. 您可以隨時撤銷此同意

      請仔細閱讀並確認是否同意。
    `,
  },
  training: {
    title: '訓練數據使用同意',
    content: `
      為了改進我們的AI模型，我們需要您同意以下條款：

      1. 您的數據可能會用於模型訓練
      2. 所有數據都將進行匿名化處理
      3. 我們不會使用個人識別信息
      4. 您可以隨時撤銷此同意

      請仔細閱讀並確認是否同意。
    `,
  },
};

export const ConsentModal: React.FC<ConsentModalProps> = ({
  isOpen,
  onClose,
  onConsent,
  consentType,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setError(null);
    }
  }, [isOpen]);

  const handleAccept = async () => {
    setIsLoading(true);
    setError(null);

    try {
      await api.post('/api/consent', {
        consent_type: consentType,
        purpose: `同意${CONSENT_TEXTS[consentType].title}`,
        granted: true,
      });

      onConsent();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.message || '記錄同意失敗，請稍後再試');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDecline = async () => {
    setIsLoading(true);
    setError(null);

    try {
      await api.post('/api/consent', {
        consent_type: consentType,
        purpose: `拒絕${CONSENT_TEXTS[consentType].title}`,
        granted: false,
      });

      onClose();
    } catch (err: any) {
      setError(err.response?.data?.message || '記錄選擇失敗，請稍後再試');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  const consentText = CONSENT_TEXTS[consentType];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">
            {consentText.title}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            disabled={isLoading}
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="px-6 py-4">
          <div className="prose max-w-none">
            <p className="text-gray-700 whitespace-pre-line">
              {consentText.content}
            </p>
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700">
              {error}
            </div>
          )}
        </div>

        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex items-center justify-end gap-3">
          <button
            onClick={handleDecline}
            disabled={isLoading}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            不同意
          </button>
          <button
            onClick={handleAccept}
            disabled={isLoading}
            className="px-4 py-2 text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? '處理中...' : '同意並繼續'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConsentModal;
