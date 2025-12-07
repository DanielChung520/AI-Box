/**
 * 代碼功能說明: 文件上傳模態框組件
 * 創建日期: 2025-12-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-06
 *
 * 功能說明:
 * - 支持文檔文件上傳（PDF, Word, Excel, Markdown, CSV, TXT）
 * - 支持圖片文件上傳（BMP, PNG, JPEG, SVG）
 * - 拖拽上傳功能
 * - 圖片預覽功能
 * - 文件類型驗證和大小限制
 */

import React, { useState, useRef, useCallback, DragEvent, useEffect } from 'react';
import { X, Upload, File as FileIcon, AlertCircle, Image as ImageIcon } from 'lucide-react';

export interface FileWithMetadata {
  file: File;
  id: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
}

interface FileUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (files: File[], taskId?: string) => Promise<void>;
  maxFileSize?: number; // bytes, default 50MB
  allowedTypes?: string[]; // MIME types or extensions
  defaultTaskId?: string; // 默認任務ID（用於組織文件到工作區）
}

const DEFAULT_MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
const DEFAULT_ALLOWED_TYPES = [
  // 文檔類型
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
  'application/msword', // .doc
  'text/plain', // .txt
  'text/markdown', // .md
  'text/csv', // .csv
  'application/vnd.ms-excel', // .xls
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
  // 圖片類型
  'image/bmp', // .bmp
  'image/png', // .png
  'image/jpeg', // .jpg, .jpeg
  'image/jpg', // .jpg
  'image/svg+xml', // .svg
];

const ALLOWED_EXTENSIONS = [
  // 文檔擴展名
  '.pdf', '.docx', '.doc', '.txt', '.md', '.csv', '.xls', '.xlsx',
  // 圖片擴展名
  '.bmp', '.png', '.jpg', '.jpeg', '.svg'
];

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

const getFileExtension = (filename: string): string => {
  return filename.slice((filename.lastIndexOf('.') - 1 >>> 0) + 2).toLowerCase();
};

const isImageFile = (file: File): boolean => {
  return file.type.startsWith('image/') ||
         ['.bmp', '.png', '.jpg', '.jpeg', '.svg'].includes('.' + getFileExtension(file.name));
};

const isValidFileType = (file: File, allowedTypes: string[]): boolean => {
  // Check MIME type
  if (allowedTypes.includes(file.type)) {
    return true;
  }

  // Check extension (case-insensitive)
  const extension = '.' + getFileExtension(file.name).toLowerCase();
  return ALLOWED_EXTENSIONS.includes(extension);
};

export const FileUploadModal: React.FC<FileUploadModalProps> = ({
  isOpen,
  onClose,
  onUpload,
  maxFileSize = DEFAULT_MAX_FILE_SIZE,
  allowedTypes = DEFAULT_ALLOWED_TYPES,
  defaultTaskId = 'temp-workspace', // 默認使用任務工作區
}) => {
  const [files, setFiles] = useState<FileWithMetadata[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [dragError, setDragError] = useState<string | null>(null);
  const [imageUrls, setImageUrls] = useState<Map<string, string>>(new Map());
  const [uploadToWorkspace, setUploadToWorkspace] = useState(true); // 默認上傳到任務工作區
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFiles = (fileList: File[]): { valid: File[]; errors: string[] } => {
    const valid: File[] = [];
    const errors: string[] = [];

    fileList.forEach((file) => {
      // Check file size
      if (file.size > maxFileSize) {
        errors.push(`${file.name}: 文件大小超過限制 (${formatFileSize(maxFileSize)})`);
        return;
      }

      // Check file type
      if (!isValidFileType(file, allowedTypes)) {
        errors.push(`${file.name}: 不支持的文件類型`);
        return;
      }

      valid.push(file);
    });

    return { valid, errors };
  };

  const handleFileSelect = useCallback((selectedFiles: FileList | null) => {
    if (!selectedFiles || selectedFiles.length === 0) return;

    const fileArray = Array.from(selectedFiles);
    const { valid, errors } = validateFiles(fileArray);

    if (errors.length > 0) {
      setDragError(errors.join('; '));
      setTimeout(() => setDragError(null), 5000);
    }

    if (valid.length > 0) {
      const newFiles: FileWithMetadata[] = valid.map((file) => ({
        file,
        id: `${Date.now()}-${Math.random()}`,
        status: 'pending',
        progress: 0,
      }));

      // 为图片文件创建预览 URL
      const newImageUrls = new Map(imageUrls);
      newFiles.forEach((fileWithMeta) => {
        if (isImageFile(fileWithMeta.file)) {
          const url = URL.createObjectURL(fileWithMeta.file);
          newImageUrls.set(fileWithMeta.id, url);
        }
      });
      setImageUrls(newImageUrls);

      setFiles((prev) => [...prev, ...newFiles]);
    }
  }, [maxFileSize, allowedTypes]);

  const handleDragEnter = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const droppedFiles = e.dataTransfer.files;
      handleFileSelect(droppedFiles);
    },
    [handleFileSelect]
  );

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      handleFileSelect(e.target.files);
      // Reset input value to allow selecting the same file again
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    },
    [handleFileSelect]
  );

  const handleRemoveFile = useCallback((id: string) => {
    // 清理图片 URL
    const imageUrl = imageUrls.get(id);
    if (imageUrl) {
      URL.revokeObjectURL(imageUrl);
      setImageUrls((prev) => {
        const newMap = new Map(prev);
        newMap.delete(id);
        return newMap;
      });
    }
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }, [imageUrls]);

  const handleUpload = useCallback(async () => {
    if (files.length === 0) return;

    const filesToUpload = files.map((f) => f.file);
    // 如果選擇上傳到任務工作區，使用 defaultTaskId
    const taskId = uploadToWorkspace ? defaultTaskId : undefined;
    try {
      await onUpload(filesToUpload, taskId);
      // 清理图片 URL
      imageUrls.forEach((url) => {
        URL.revokeObjectURL(url);
      });
      setImageUrls(new Map());
      setFiles([]);
      onClose();
    } catch (error) {
      console.error('Upload failed:', error);
    }
  }, [files, onUpload, onClose, imageUrls, uploadToWorkspace, defaultTaskId]);

  // 清理图片 URL（组件卸载时）
  useEffect(() => {
    return () => {
      // 组件卸载时清理所有图片 URL
      imageUrls.forEach((url) => {
        URL.revokeObjectURL(url);
      });
    };
  }, [imageUrls]);

  const handleClose = useCallback(() => {
    // 清理所有图片 URL
    imageUrls.forEach((url) => {
      URL.revokeObjectURL(url);
    });
    setImageUrls(new Map());
    setFiles([]);
    setDragError(null);
    onClose();
  }, [onClose, imageUrls]);

  if (!isOpen) return null;

  const totalSize = files.reduce((sum, f) => sum + f.file.size, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">上傳文件</h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4">
          {/* Drag and Drop Area */}
          <div
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragging
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <p className="text-gray-700 mb-2">
              拖拽文件到此處或{' '}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="text-blue-600 hover:text-blue-700 underline"
              >
                選擇文件
              </button>
            </p>
            <p className="text-sm text-gray-500">
              支持文檔: PDF, DOCX, DOC, TXT, MD, CSV, XLS, XLSX<br />
              支持圖片: BMP, PNG, JPG, JPEG, SVG<br />
              (最大 {formatFileSize(maxFileSize)})
            </p>

            {/* 工作區選擇 */}
            <div className="mt-4 flex items-center gap-2 p-3 bg-blue-50 rounded-lg border border-blue-200">
              <input
                type="checkbox"
                id="upload-to-workspace"
                checked={uploadToWorkspace}
                onChange={(e) => setUploadToWorkspace(e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <label
                htmlFor="upload-to-workspace"
                className="text-sm text-gray-700 cursor-pointer flex-1"
              >
                上傳到任務工作區
              </label>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={handleFileInputChange}
              accept={ALLOWED_EXTENSIONS.join(',')}
            />
          </div>

          {/* Error Message */}
          {dragError && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{dragError}</p>
            </div>
          )}

          {/* File List */}
          {files.length > 0 && (
            <div className="mt-6">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-medium text-gray-900">
                  已選擇文件 ({files.length})
                </h3>
                <span className="text-sm text-gray-500">
                  總大小: {formatFileSize(totalSize)}
                </span>
              </div>
              <div className="space-y-2">
                {files.map((fileWithMeta) => {
                  const isImage = isImageFile(fileWithMeta.file);
                  const imageUrl = isImage ? imageUrls.get(fileWithMeta.id) : null;

                  return (
                    <div
                      key={fileWithMeta.id}
                      className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200"
                    >
                      {isImage && imageUrl ? (
                        <div className="w-12 h-12 flex-shrink-0 rounded border border-gray-200 overflow-hidden bg-gray-100">
                          <img
                            src={imageUrl}
                            alt={fileWithMeta.file.name}
                            className="w-full h-full object-cover"
                          />
                        </div>
                      ) : (
                        <FileIcon className="w-5 h-5 text-gray-400 flex-shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {fileWithMeta.file.name}
                        </p>
                        <p className="text-xs text-gray-500">
                          {formatFileSize(fileWithMeta.file.size)}
                          {isImage && ' • 圖片'}
                        </p>
                      </div>
                      <button
                        onClick={() => handleRemoveFile(fileWithMeta.id)}
                        className="text-gray-400 hover:text-red-600 transition-colors flex-shrink-0"
                        aria-label="移除文件"
                      >
                        <X className="w-5 h-5" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex items-center justify-end gap-3">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleUpload}
            disabled={files.length === 0}
            className="px-4 py-2 text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            上傳 ({files.length})
          </button>
        </div>
      </div>
    </div>
  );
};

export default FileUploadModal;
