/**
 * 代碼功能說明: 文件上傳進度組件
 * 創建日期: 2025-12-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-06
 */

import React from 'react';
import { X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { FileWithMetadata } from './FileUploadModal';

interface UploadProgressProps {
  files: FileWithMetadata[];
  onCancel?: (fileId: string) => void;
  onDismiss?: (fileId: string) => void;
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

export const UploadProgress: React.FC<UploadProgressProps> = ({
  files,
  onCancel,
  onDismiss,
}) => {
  if (files.length === 0) return null;

  const getStatusIcon = (status: FileWithMetadata['status']) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-600" />;
      case 'uploading':
        return <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />;
      default:
        return <Loader2 className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusText = (status: FileWithMetadata['status']) => {
    switch (status) {
      case 'success':
        return '上傳完成';
      case 'error':
        return '上傳失敗';
      case 'uploading':
        return '上傳中...';
      default:
        return '等待上傳';
    }
  };

  const getOverallProgress = () => {
    if (files.length === 0) return 0;
    const totalProgress = files.reduce((sum, f) => sum + f.progress, 0);
    return Math.round(totalProgress / files.length);
  };

  const isUploading = files.some((f) => f.status === 'uploading' || f.status === 'pending');
  const overallProgress = getOverallProgress();

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-md w-full">
      <div className="bg-white rounded-lg shadow-xl border border-gray-200 overflow-hidden">
        {/* Header */}
        <div className="bg-gray-50 px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">
            {isUploading ? `上傳中... ${overallProgress}%` : '上傳完成'}
          </h3>
          {!isUploading && (
            <button
              onClick={() => files.forEach((f) => onDismiss?.(f.id))}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              全部關閉
            </button>
          )}
        </div>

        {/* Progress Bar (Overall) */}
        {isUploading && (
          <div className="px-4 pt-3">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${overallProgress}%` }}
              />
            </div>
          </div>
        )}

        {/* File List */}
        <div className="max-h-96 overflow-y-auto">
          {files.map((fileWithMeta) => (
            <div
              key={fileWithMeta.id}
              className="px-4 py-3 border-b border-gray-100 last:border-b-0"
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  {getStatusIcon(fileWithMeta.status)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {fileWithMeta.file.name}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {formatFileSize(fileWithMeta.file.size)}
                  </p>

                  {/* Individual Progress Bar */}
                  {(fileWithMeta.status === 'uploading' || fileWithMeta.status === 'pending') && (
                    <div className="mt-2">
                      <div className="w-full bg-gray-200 rounded-full h-1.5">
                        <div
                          className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                          style={{ width: `${fileWithMeta.progress}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Status Text */}
                  <p className="text-xs mt-1 text-gray-600">
                    {getStatusText(fileWithMeta.status)}
                  </p>

                  {/* Error Message */}
                  {fileWithMeta.status === 'error' && fileWithMeta.error && (
                    <p className="text-xs mt-1 text-red-600">{fileWithMeta.error}</p>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="flex-shrink-0">
                  {fileWithMeta.status === 'uploading' || fileWithMeta.status === 'pending' ? (
                    <button
                      onClick={() => onCancel?.(fileWithMeta.id)}
                      className="text-gray-400 hover:text-red-600 transition-colors"
                      aria-label="取消上傳"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  ) : (
                    <button
                      onClick={() => onDismiss?.(fileWithMeta.id)}
                      className="text-gray-400 hover:text-gray-600 transition-colors"
                      aria-label="關閉"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default UploadProgress;
