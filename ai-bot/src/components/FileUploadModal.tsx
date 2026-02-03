/**
 * 代碼功能說明: 文件上傳模態框組件
 * 創建日期: 2025-12-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-31 15:20 UTC+8
 *
 * 功能說明:
 * - 支持文檔文件上傳（PDF, Word, Excel, Markdown, CSV, TXT）
 * - 支持圖片文件上傳（BMP, PNG, JPEG, SVG）
 * - 拖拽上傳功能
 * - 圖片預覽功能
 * - 文件類型驗證和大小限制
 * - 可選的訪問控制設置（WBS-4.5.3）
 * - 方案 B：Agent 知識庫上架（勾選後可選 Ontology / 知識庫資料夾）
 *   - 任務 ID 來自當前任務（forceTaskId ?? defaultTaskId），不可編輯；不再檢驗 -Agent 後綴
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import type { DragEvent } from 'react';
import { X, Upload, File as FileIcon, AlertCircle, Settings, FolderOpen, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import {
  FileAccessControl,
  FileAccessLevel,
  DataClassification,
  SensitivityLabel,
  updateFileAccessControl,
  FileUploadResponse,
  fetchOntologiesByTaskId,
  getUserTask,
  importOntologies,
} from '../lib/api';

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
  forceTaskId?: string; // 強制使用指定 taskId（忽略「上傳到任務工作區」toggle）
  hideUploadToWorkspaceToggle?: boolean; // 隱藏「上傳到任務工作區」toggle（通常用於文件樹）
  userId?: string; // 用戶ID（用於訪問控制設置）
  enableAccessControl?: boolean; // 是否啟用訪問控制設置（默認 false，保持向後兼容）
  /** 方案 B：是否為 systemAdmin/授權用戶，顯示「Agent 知識庫」勾選 */
  isAgentOnboardingAllowed?: boolean;
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

const ONTOLOGY_JSON_PATTERN = /^.*(-domain|-major)\.json$/i;

function hasOntologyJson(files: File[]): boolean {
  return files.some((f) => ONTOLOGY_JSON_PATTERN.test(f.name));
}

/** 是否支援 File System Access API（可避免 Chrome webkitdirectory 的「上傳到網站」警告） */
const FS_API_SUPPORTED =
  typeof window !== 'undefined' && 'showDirectoryPicker' in window;

type DirPickResult = { files: File[]; folderName: string } | null;

/**
 * 使用 showDirectoryPicker 選資料夾，遞迴收集檔案。
 * 無「上傳到網站」警告，選完直接回 Modal 顯示路徑。
 */
async function pickFolderWithFSAPI(): Promise<DirPickResult> {
  if (!FS_API_SUPPORTED) return null;
  const w = window as Window & { showDirectoryPicker?: (opts?: { mode?: string }) => Promise<FileSystemDirectoryHandle> };
  try {
    const dir = await w.showDirectoryPicker!({ mode: 'read' });
    const folderName = dir.name;

    async function collect(dirHandle: FileSystemDirectoryHandle, basePath = ''): Promise<File[]> {
      const out: File[] = [];
      for await (const [name, handle] of dirHandle.entries()) {
        const path = basePath ? `${basePath}/${name}` : name;
        if (handle.kind === 'file') {
          const f = await (handle as FileSystemFileHandle).getFile();
          out.push(f);
        } else {
          const sub = await collect(handle as FileSystemDirectoryHandle, path);
          out.push(...sub);
        }
      }
      return out;
    }

    const files = await collect(dir);
    return { files, folderName };
  } catch (e) {
    if (e instanceof Error && e.name === 'AbortError') return null;
    throw e;
  }
}

export const FileUploadModal: React.FC<FileUploadModalProps> = ({
  isOpen,
  onClose,
  onUpload,
  maxFileSize = DEFAULT_MAX_FILE_SIZE,
  allowedTypes = DEFAULT_ALLOWED_TYPES,
  defaultTaskId, // 默認使用任務工作區（可選；若不提供則由後端自行創建 task）
  forceTaskId,
  hideUploadToWorkspaceToggle = false,
  userId,
  enableAccessControl = false, // 默認關閉，保持向後兼容
  isAgentOnboardingAllowed = false,
}) => {
  const [files, setFiles] = useState<FileWithMetadata[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [dragError, setDragError] = useState<string | null>(null);
  const [imageUrls, setImageUrls] = useState<Map<string, string>>(new Map());
  const [uploadToWorkspace, setUploadToWorkspace] = useState(true); // 默認上傳到任務工作區
  const [showAccessControl, setShowAccessControl] = useState(false); // 是否顯示訪問控制設置
  const [accessLevel, setAccessLevel] = useState<FileAccessLevel>(FileAccessLevel.PRIVATE);
  const [dataClassification, setDataClassification] = useState<DataClassification>(
    DataClassification.INTERNAL
  );
  const [sensitivityLabels, setSensitivityLabels] = useState<SensitivityLabel[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 方案 B：Agent 知識庫上架（任務 ID 來自 forceTaskId ?? defaultTaskId，不可編輯）
  const [agentKnowledgeMode, setAgentKnowledgeMode] = useState(false);
  const [isAgentTask, setIsAgentTask] = useState<boolean | null>(null); // 當前任務是否為 Agent 任務
  const [checkingAgentTask, setCheckingAgentTask] = useState(false); // 正在檢查 is_agent_task
  const [agentCheck, setAgentCheck] = useState<{
    loading: boolean;
    /** 任務是否存在；null 表示尚未查完 */
    taskExists: boolean | null;
    hasAny: boolean;
    error: string | null;
  }>({ loading: false, taskExists: null, hasAny: false, error: null });
  const [ontologyFolderFiles, setOntologyFolderFiles] = useState<File[]>([]);
  const [ontologyFolderLabel, setOntologyFolderLabel] = useState<string | null>(null);
  const [knowledgeFolderFiles, setKnowledgeFolderFiles] = useState<File[]>([]);
  const [knowledgeFolderLabel, setKnowledgeFolderLabel] = useState<string | null>(null);
  const [agentUploading, setAgentUploading] = useState(false);
  const [pickingFolder, setPickingFolder] = useState<'ontology' | 'knowledge' | null>(null);
  const ontologyInputRef = useRef<HTMLInputElement>(null);
  const knowledgeInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setDragError(null);
      setPickingFolder(null);
      setAgentKnowledgeMode(false);
      setIsAgentTask(null);
      setCheckingAgentTask(false);
      setOntologyFolderFiles([]);
      setOntologyFolderLabel(null);
      setKnowledgeFolderFiles([]);
      setKnowledgeFolderLabel(null);
    }
  }, [isOpen]);

  const resolvedTaskId = forceTaskId ?? defaultTaskId ?? '';

  // 檢查當前任務是否為 Agent 任務（當有任務 ID 時）
  useEffect(() => {
    if (!isOpen || !resolvedTaskId.trim()) {
      setIsAgentTask(null);
      setCheckingAgentTask(false);
      return;
    }
    const tid = resolvedTaskId.trim();
    let cancelled = false;
    setCheckingAgentTask(true);
    getUserTask(tid)
      .then((r) => {
        if (!cancelled) {
          if (r.success && r.data) {
            setIsAgentTask(r.data.is_agent_task || false);
          } else {
            // 任務不存在，視為非 Agent 任務
            setIsAgentTask(false);
          }
          setCheckingAgentTask(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setIsAgentTask(false);
          setCheckingAgentTask(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [isOpen, resolvedTaskId]);

  // 方案 B：並行查詢 ① 任務是否存在 ② Ontology，以區分新 Agent / 既有 Agent（僅在勾選後執行）
  useEffect(() => {
    if (!isOpen || !agentKnowledgeMode || !resolvedTaskId.trim()) {
      setAgentCheck({ loading: false, taskExists: null, hasAny: false, error: null });
      return;
    }
    const tid = resolvedTaskId.trim();
    let cancelled = false;
    setAgentCheck((prev) => ({ ...prev, loading: true, error: null }));
    Promise.all([
      getUserTask(tid).then((r) => ({ exists: r.success && !!r.data })),
      fetchOntologiesByTaskId(tid).then((d) => d.has_any),
    ])
      .then(([taskResult, hasAny]) => {
        if (!cancelled) {
          setAgentCheck({
            loading: false,
            taskExists: taskResult.exists,
            hasAny,
            error: null,
          });
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setAgentCheck({
            loading: false,
            taskExists: null,
            hasAny: false,
            error: e instanceof Error ? e.message : String(e),
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [isOpen, agentKnowledgeMode, resolvedTaskId]);

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

  const handleOntologyFolderSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      // 重要：阻止任何可能的默認行為或事件冒泡
      e.preventDefault();
      e.stopPropagation();
      
      // 確保在 Agent 知識庫模式下才處理（防禦性檢查）
      if (!agentKnowledgeMode) {
        console.warn('[FileUploadModal] handleOntologyFolderSelect called but agentKnowledgeMode is false');
        if (ontologyInputRef.current) ontologyInputRef.current.value = '';
        return;
      }
      
      const list = e.target.files;
      if (!list?.length) {
        // 重置 input 值，允許重複選擇
        if (ontologyInputRef.current) ontologyInputRef.current.value = '';
        return;
      }
      const arr = Array.from(list);
      if (!hasOntologyJson(arr)) {
        setDragError('Ontology 資料夾須至少包含一個 *-domain.json 或 *-major.json');
        setTimeout(() => setDragError(null), 5000);
        // 重置 input 值
        if (ontologyInputRef.current) ontologyInputRef.current.value = '';
        return;
      }
      
      // ⚠️ 重要：僅設置 state，絕對不觸發上傳（上傳需點擊「知識庫上架」按鈕）
      // 此處只做文件選擇和路徑顯示，不會調用 onUpload 或任何上傳相關函數
      setOntologyFolderFiles(arr);
      
      // 提取資料夾名稱：從 webkitRelativePath 的第一層目錄
      let folderName = '';
      const first = arr[0] as File & { webkitRelativePath?: string };
      if (first?.webkitRelativePath) {
        const parts = first.webkitRelativePath.split('/').filter(Boolean);
        if (parts.length > 0) {
          folderName = parts[0].trim();
        }
      }
      
      // 如果沒有 webkitRelativePath（如 Safari），嘗試從文件名推斷
      if (!folderName) {
        const jsonFiles = arr.filter((f) => /\.json$/i.test(f.name));
        if (jsonFiles.length > 0) {
          const jsonFile = jsonFiles[0];
          const nameMatch = jsonFile.name.match(/^(.+?)(-domain|-major)\.json$/i);
          if (nameMatch && nameMatch[1]) {
            folderName = nameMatch[1];
          }
        }
      }
      
      // 最終顯示：資料夾名稱或檔案數量（確保總是顯示）
      const displayPath = folderName || `已選 ${arr.length} 個檔案`;
      console.log('[FileUploadModal] Ontology folder selected (NO UPLOAD):', { folderName, displayPath, fileCount: arr.length, agentKnowledgeMode });
      setOntologyFolderLabel(displayPath);
      
      // 重置 input 值，允許重複選擇同一資料夾
      if (ontologyInputRef.current) ontologyInputRef.current.value = '';
    },
    [agentKnowledgeMode]
  );

  const handleKnowledgeFolderSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      // 重要：阻止任何可能的默認行為或事件冒泡
      e.preventDefault();
      e.stopPropagation();
      
      // 確保在 Agent 知識庫模式下才處理（防禦性檢查）
      if (!agentKnowledgeMode) {
        console.warn('[FileUploadModal] handleKnowledgeFolderSelect called but agentKnowledgeMode is false');
        if (knowledgeInputRef.current) knowledgeInputRef.current.value = '';
        return;
      }
      
      const list = e.target.files;
      if (!list?.length) {
        // 重置 input 值，允許重複選擇
        if (knowledgeInputRef.current) knowledgeInputRef.current.value = '';
        return;
      }
      const arr = Array.from(list);
      
      // ⚠️ 重要：僅設置 state，絕對不觸發上傳（上傳需點擊「知識庫上架」按鈕）
      // 此處只做文件選擇和路徑顯示，不會調用 onUpload 或任何上傳相關函數
      setKnowledgeFolderFiles(arr);
      
      // 提取資料夾名稱：從 webkitRelativePath 的第一層目錄
      let folderName = '';
      const first = arr[0] as File & { webkitRelativePath?: string };
      if (first?.webkitRelativePath) {
        const parts = first.webkitRelativePath.split('/').filter(Boolean);
        if (parts.length > 0) {
          folderName = parts[0].trim();
        }
      }
      
      // 如果沒有 webkitRelativePath（如 Safari），嘗試從文件路徑推斷
      if (!folderName && arr.length > 0) {
        // 嘗試從多個文件的共同路徑推斷
        const paths = arr
          .map((f) => (f as File & { webkitRelativePath?: string }).webkitRelativePath)
          .filter(Boolean) as string[];
        if (paths.length > 0) {
          const commonPrefix = paths.reduce((prefix, path) => {
            const parts = path.split('/').filter(Boolean);
            const prefixParts = prefix.split('/').filter(Boolean);
            let i = 0;
            while (i < prefixParts.length && i < parts.length && prefixParts[i] === parts[i]) {
              i++;
            }
            return prefixParts.slice(0, i).join('/');
          }, paths[0]);
          if (commonPrefix) {
            const commonParts = commonPrefix.split('/').filter(Boolean);
            if (commonParts.length > 0) {
              folderName = commonParts[0];
            }
          }
        }
      }
      
      // 最終顯示：資料夾名稱或檔案數量（確保總是顯示）
      const displayPath = folderName || `已選 ${arr.length} 個檔案`;
      console.log('[FileUploadModal] Knowledge folder selected (NO UPLOAD):', { folderName, displayPath, fileCount: arr.length, agentKnowledgeMode });
      setKnowledgeFolderLabel(displayPath);
      
      // 重置 input 值，允許重複選擇同一資料夾
      if (knowledgeInputRef.current) knowledgeInputRef.current.value = '';
    },
    [agentKnowledgeMode]
  );

  /** 使用 File System Access API 選 Ontology 資料夾，避免「上傳到網站」警告，選完回 Modal 顯示路徑 */
  const handlePickOntologyFolder = useCallback(async () => {
    if (!agentKnowledgeMode) return;
    if (FS_API_SUPPORTED) {
      setPickingFolder('ontology');
      setDragError(null);
      try {
        const result = await pickFolderWithFSAPI();
        if (!result) {
          setPickingFolder(null);
          return;
        }
        const { files, folderName } = result;
        if (!hasOntologyJson(files)) {
          setDragError('Ontology 資料夾須至少包含一個 *-domain.json 或 *-major.json');
          setTimeout(() => setDragError(null), 5000);
        } else {
          setOntologyFolderFiles(files);
          setOntologyFolderLabel(folderName || `已選 ${files.length} 個檔案`);
        }
      } catch (e) {
        setDragError(e instanceof Error ? e.message : '選擇資料夾失敗');
        setTimeout(() => setDragError(null), 5000);
      } finally {
        setPickingFolder(null);
      }
      return;
    }
    ontologyInputRef.current?.click();
  }, [agentKnowledgeMode]);

  /** 使用 File System Access API 選知識庫資料夾，避免「上傳到網站」警告，選完回 Modal 顯示路徑 */
  const handlePickKnowledgeFolder = useCallback(async () => {
    if (!agentKnowledgeMode) return;
    if (FS_API_SUPPORTED) {
      setPickingFolder('knowledge');
      setDragError(null);
      try {
        const result = await pickFolderWithFSAPI();
        if (!result) {
          setPickingFolder(null);
          return;
        }
        const { files, folderName } = result;
        setKnowledgeFolderFiles(files);
        setKnowledgeFolderLabel(folderName || `已選 ${files.length} 個檔案`);
      } catch (e) {
        setDragError(e instanceof Error ? e.message : '選擇資料夾失敗');
        setTimeout(() => setDragError(null), 5000);
      } finally {
        setPickingFolder(null);
      }
      return;
    }
    knowledgeInputRef.current?.click();
  }, [agentKnowledgeMode]);

  const handleAgentUpload = useCallback(() => {
    const taskId = forceTaskId ?? defaultTaskId;
    if (!taskId?.trim()) {
      setDragError('請在任務工作區中打開上傳（需有當前任務）');
      setTimeout(() => setDragError(null), 5000);
      return;
    }
    const taskExists = agentCheck.taskExists === true;
    const needBothFolders = !taskExists || !agentCheck.hasAny;
    if (needBothFolders && ontologyFolderFiles.length === 0) {
      setDragError('請選擇 Ontology 資料夾');
      setTimeout(() => setDragError(null), 5000);
      return;
    }
    if (knowledgeFolderFiles.length === 0) {
      setDragError('請選擇知識庫資料夾');
      setTimeout(() => setDragError(null), 5000);
      return;
    }
    const jsonFiles = needBothFolders
      ? ontologyFolderFiles.filter((f) => /\.json$/i.test(f.name))
      : [];
    const knowledgeFiles = [...knowledgeFolderFiles];

    onClose();

    const run = async () => {
      toast.info('知識庫上架中...');
      try {
        // 先執行 onUpload：立即顯示右下角進度條、上傳文件、建立 RQ job
        // 若先執行 importOntologies 且失敗（如 SeaweedFS 500），會導致無進度、無 RQ job
        await onUpload(knowledgeFiles, taskId);

        // Ontology 匯入（與上傳並行或之後執行，失敗不阻擋文件上傳）
        if (needBothFolders && jsonFiles.length > 0) {
          try {
            await importOntologies(jsonFiles);
          } catch (ontErr) {
            const ontMsg = ontErr instanceof Error ? ontErr.message : String(ontErr);
            console.error('[FileUploadModal] Ontology 匯入失敗:', ontErr);
            toast.error(`Ontology 匯入失敗: ${ontMsg}（文件已上傳）`);
            return;
          }
        }

        toast.success('知識庫上架完成');
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error('[FileUploadModal] 知識庫上架失敗:', msg);
        toast.error(`知識庫上架失敗: ${msg}`);
        window.dispatchEvent(
          new CustomEvent('uploadError', { detail: { message: msg } })
        );
      }
    };
    void run();
  }, [
    forceTaskId,
    defaultTaskId,
    agentCheck.taskExists,
    agentCheck.hasAny,
    ontologyFolderFiles,
    knowledgeFolderFiles,
    onUpload,
    onClose,
  ]);

  const resolveTaskIdToUse = useCallback((): string | undefined => {
    return forceTaskId ?? (uploadToWorkspace ? defaultTaskId : undefined);
  }, [forceTaskId, uploadToWorkspace, defaultTaskId]);

  const handleSensitivityLabelToggle = useCallback((label: SensitivityLabel) => {
    setSensitivityLabels((prev) => {
      if (prev.includes(label)) {
        return prev.filter((l) => l !== label);
      }
      return [...prev, label];
    });
  }, []);

  const handleUpload = useCallback(async () => {
    if (files.length === 0) return;

    const filesToUpload = files.map((f) => f.file);
    // 如果選擇上傳到任務工作區，使用 defaultTaskId
    const taskId = resolveTaskIdToUse();
    toast.info('文件上傳中...');
    try {
      // 先執行上傳
      await onUpload(filesToUpload, taskId);

      // 如果啟用了訪問控制設置，且用戶設置了自定義配置，則更新訪問控制
      if (enableAccessControl && showAccessControl && userId) {
        try {
          // 獲取上傳響應（需要從 onUpload 回調中獲取 fileIds）
          // 由於 onUpload 是回調函數，我們無法直接獲取響應
          // 這裡我們需要在上傳成功後，通過事件或其他方式獲取 fileIds
          // 暫時跳過，因為需要修改 onUpload 接口才能獲取 fileIds
          // 或者可以在上傳後通過文件列表 API 獲取最新上傳的文件
          console.log('[FileUploadModal] Access control settings will be applied after upload');
        } catch (error) {
          console.error('[FileUploadModal] Failed to update access control:', error);
          // 不阻止上傳流程，只記錄錯誤
        }
      }

      // 清理图片 URL
      imageUrls.forEach((url) => {
        URL.revokeObjectURL(url);
      });
      setImageUrls(new Map());
      setFiles([]);
      // 重置訪問控制設置
      setShowAccessControl(false);
      setAccessLevel(FileAccessLevel.PRIVATE);
      setDataClassification(DataClassification.INTERNAL);
      setSensitivityLabels([]);
      onClose();
      toast.success('文件上傳完成');
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      console.error('Upload failed:', error);
      toast.error(`文件上傳失敗: ${msg}`);
    }
  }, [
    files,
    onUpload,
    onClose,
    imageUrls,
    resolveTaskIdToUse,
    enableAccessControl,
    showAccessControl,
    userId,
  ]);

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
    imageUrls.forEach((url) => URL.revokeObjectURL(url));
    setImageUrls(new Map());
    setFiles([]);
    setDragError(null);
    setPickingFolder(null);
    setAgentKnowledgeMode(false);
    setIsAgentTask(null);
    setCheckingAgentTask(false);
    setAgentCheck({ loading: false, taskExists: null, hasAny: false, error: null });
    setOntologyFolderFiles([]);
    setOntologyFolderLabel(null);
    setKnowledgeFolderFiles([]);
    setKnowledgeFolderLabel(null);
    onClose();
  }, [onClose, imageUrls]);

  if (!isOpen) return null;

  const totalSize = files.reduce((sum, f) => sum + f.file.size, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex-shrink-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">上傳文件</h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content：可滾動區，Footer 固定於底部始終可見 */}
        <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="px-6 py-4">
          {/* 方案 B：Agent 知識庫 checkbox（僅授權用戶） */}
          {isAgentOnboardingAllowed && (
            <div className="mb-4 flex items-center gap-2 p-3 bg-amber-50 rounded-lg border border-amber-200">
              <input
                type="checkbox"
                id="agent-knowledge-mode"
                checked={agentKnowledgeMode}
                disabled={
                  checkingAgentTask ||
                  !resolvedTaskId.trim() ||
                  (resolvedTaskId.trim() && isAgentTask === false) ||
                  (resolvedTaskId.trim() && isAgentTask === null)
                }
                onChange={async (e) => {
                  const wantToCheck = e.target.checked;
                  if (!wantToCheck) {
                    // 取消勾選：直接關閉 Agent 模式
                    setAgentKnowledgeMode(false);
                    setOntologyFolderFiles([]);
                    setOntologyFolderLabel(null);
                    setKnowledgeFolderFiles([]);
                    setKnowledgeFolderLabel(null);
                    return;
                  }
                  // 勾選：必須先通過 is_agent_task 檢查
                  if (!resolvedTaskId.trim()) {
                    setDragError('請在任務工作區中打開上傳（需有當前任務）');
                    setTimeout(() => setDragError(null), 5000);
                    setAgentKnowledgeMode(false); // 確保不勾選
                    return;
                  }
                  if (checkingAgentTask) {
                    setAgentKnowledgeMode(false); // 確保不勾選
                    return; // 正在檢查中，不處理
                  }
                  if (isAgentTask === false) {
                    setDragError('當前任務不是 Agent 任務，無法使用知識庫上架功能。請先在任務右鍵選單中「標記為 Agent 任務」。');
                    setTimeout(() => setDragError(null), 8000);
                    setAgentKnowledgeMode(false); // 確保不勾選
                    return;
                  }
                  if (isAgentTask === true) {
                    // 是 Agent 任務，允許勾選
                    setAgentKnowledgeMode(true);
                  } else {
                    // isAgentTask 為 null（尚未查完），先檢查（理論上不應該到這裡，因為已禁用）
                    setCheckingAgentTask(true);
                    setAgentKnowledgeMode(false); // 先確保不勾選
                    try {
                      const taskRes = await getUserTask(resolvedTaskId.trim());
                      if (taskRes.success && taskRes.data) {
                        const isAgent = taskRes.data.is_agent_task || false;
                        setIsAgentTask(isAgent);
                        if (isAgent) {
                          setAgentKnowledgeMode(true);
                        } else {
                          setDragError('當前任務不是 Agent 任務，無法使用知識庫上架功能。請先在任務右鍵選單中「標記為 Agent 任務」。');
                          setTimeout(() => setDragError(null), 8000);
                        }
                      } else {
                        // 任務不存在，視為非 Agent 任務
                        setIsAgentTask(false);
                        setDragError('任務不存在，無法使用知識庫上架功能。');
                        setTimeout(() => setDragError(null), 5000);
                      }
                    } catch (error) {
                      setDragError('檢查任務狀態失敗，請稍後再試。');
                      setTimeout(() => setDragError(null), 5000);
                    } finally {
                      setCheckingAgentTask(false);
                    }
                  }
                }}
                className="w-4 h-4 text-amber-600 border-gray-300 rounded focus:ring-amber-500 disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <label
                htmlFor="agent-knowledge-mode"
                className={`text-sm flex-1 ${
                  checkingAgentTask ||
                  !resolvedTaskId.trim() ||
                  (resolvedTaskId.trim() && isAgentTask === false) ||
                  (resolvedTaskId.trim() && isAgentTask === null)
                    ? 'text-gray-400 cursor-not-allowed'
                    : 'text-gray-700 cursor-pointer'
                }`}
              >
                {checkingAgentTask ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    檢查中...
                  </span>
                ) : !resolvedTaskId.trim() ? (
                  '上架知識庫（需有當前任務）'
                ) : isAgentTask === null ? (
                  '上架知識庫（檢查中...）'
                ) : isAgentTask === false ? (
                  '上架知識庫（需先標記為 Agent 任務）'
                ) : (
                  '上架知識庫'
                )}
              </label>
              {resolvedTaskId.trim() && isAgentTask === false && (
                <p className="text-xs text-amber-700 ml-2">
                  （需先標記為 Agent 任務）
                </p>
              )}
            </div>
          )}

          {agentKnowledgeMode ? (
            /* 方案 B：Agent 知識庫上架區（任務 ID 來自當前任務，不可編輯） */
            <div className="border-2 border-dashed border-amber-200 rounded-lg p-6 bg-amber-50/50 space-y-4">
              {resolvedTaskId.trim() && (
                <p className="text-sm text-gray-600">
                  上架至任務：<span className="font-medium text-gray-900">{resolvedTaskId}</span>
                </p>
              )}
              {!resolvedTaskId.trim() && (
                <p className="text-sm text-amber-700">請在任務工作區中打開上傳（需有當前任務）</p>
              )}
              {agentCheck.loading && (
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  檢查任務與 Ontology…
                </div>
              )}
              {!agentCheck.loading && agentCheck.error && (
                <p className="text-sm text-red-600">{agentCheck.error}</p>
              )}
              {!agentCheck.loading && !agentCheck.error && resolvedTaskId.trim() && agentCheck.taskExists !== null && (
                <p className="text-sm text-gray-600">
                  {agentCheck.taskExists === false
                    ? '此為新 Agent，請選擇 Ontology 與知識庫資料夾。'
                    : agentCheck.hasAny
                      ? '已有 Ontology，只需選擇知識庫資料夾。'
                      : '尚無 Ontology，請選擇 Ontology 與知識庫資料夾。'}
                </p>
              )}
              {!agentCheck.loading &&
                resolvedTaskId.trim() &&
                (agentCheck.taskExists === false || !agentCheck.hasAny) && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Ontology 資料夾（*-domain.json / *-major.json）
                  </label>
                  <input
                    ref={ontologyInputRef}
                    type="file"
                    // @ts-expect-error webkitdirectory is supported in modern browsers
                    webkitdirectory=""
                    className="hidden"
                    onChange={handleOntologyFolderSelect}
                  />
                  <button
                    type="button"
                    onClick={handlePickOntologyFolder}
                    disabled={!!pickingFolder}
                    className="flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {pickingFolder === 'ontology' ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <FolderOpen className="w-4 h-4" />
                    )}
                    {pickingFolder === 'ontology' ? '選擇中…' : '選擇 Ontology 資料夾'}
                  </button>
                  {ontologyFolderLabel && (
                    <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded">
                      <p className="text-sm text-green-800 font-medium">
                        ✅ 已選擇 Ontology 資料夾：{ontologyFolderLabel}
                      </p>
                    </div>
                  )}
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  知識庫資料夾
                </label>
                <input
                  ref={knowledgeInputRef}
                  type="file"
                  // @ts-expect-error webkitdirectory is supported in modern browsers
                  webkitdirectory=""
                  className="hidden"
                  onChange={handleKnowledgeFolderSelect}
                />
                <button
                  type="button"
                  onClick={handlePickKnowledgeFolder}
                  disabled={!!pickingFolder}
                  className="flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {pickingFolder === 'knowledge' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <FolderOpen className="w-4 h-4" />
                  )}
                  {pickingFolder === 'knowledge' ? '選擇中…' : '選擇知識庫資料夾'}
                </button>
                {knowledgeFolderLabel && (
                  <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded">
                    <p className="text-sm text-green-800 font-medium">
                      ✅ 已選擇知識庫資料夾：{knowledgeFolderLabel}
                    </p>
                  </div>
                )}
              </div>
              <div className="space-y-2">
                <p className="text-sm text-amber-800 bg-amber-100/80 border border-amber-200 rounded px-3 py-2">
                  <strong>⚠️ 重要提示：</strong>
                </p>
                <ul className="text-sm text-amber-800 bg-amber-100/80 border border-amber-200 rounded px-3 py-2 list-disc list-inside space-y-1">
                  {FS_API_SUPPORTED ? (
                    <>
                      <li>點擊「選擇 Ontology 資料夾」或「選擇知識庫資料夾」會打開<strong>資料夾選擇器</strong></li>
                      <li><strong>選完後直接回到本視窗顯示路徑</strong>，不會出現「上傳到網站」警告，也不會自動上傳</li>
                    </>
                  ) : (
                    <>
                      <li>點擊按鈕會打開瀏覽器文件選擇對話框；若出現「上傳到網站」提示，請選擇「允許」後即回到本視窗顯示路徑</li>
                      <li>選擇資料夾後<strong>只會顯示路徑，不會自動上傳</strong></li>
                    </>
                  )}
                  <li>確認路徑無誤後，點擊右下角「<strong>知識庫上架</strong>」才開始上傳</li>
                </ul>
              </div>
            </div>
          ) : (
            <>
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
                    type="button"
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
                {!hideUploadToWorkspaceToggle && (
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
                )}
                {enableAccessControl && (
                  <div className="mt-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
                        <Settings className="w-4 h-4" />
                        訪問控制設置（可選）
                      </label>
                      <button
                        type="button"
                        onClick={() => setShowAccessControl(!showAccessControl)}
                        className="text-xs text-blue-600 hover:text-blue-700"
                      >
                        {showAccessControl ? '隱藏' : '顯示'}
                      </button>
                    </div>
                    {showAccessControl && (
                      <div className="mt-3 space-y-3">
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            訪問級別
                          </label>
                          <select
                            value={accessLevel}
                            onChange={(e) => setAccessLevel(e.target.value as FileAccessLevel)}
                            className="w-full p-2 text-sm border border-gray-300 rounded bg-white"
                          >
                            <option value={FileAccessLevel.PRIVATE}>私有（默認）</option>
                            <option value={FileAccessLevel.PUBLIC}>公開</option>
                            <option value={FileAccessLevel.ORGANIZATION}>組織</option>
                            <option value={FileAccessLevel.SECURITY_GROUP}>安全組</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            數據分類級別
                          </label>
                          <select
                            value={dataClassification}
                            onChange={(e) =>
                              setDataClassification(e.target.value as DataClassification)
                            }
                            className="w-full p-2 text-sm border border-gray-300 rounded bg-white"
                          >
                            <option value={DataClassification.INTERNAL}>內部（默認）</option>
                            <option value={DataClassification.PUBLIC}>公開</option>
                            <option value={DataClassification.CONFIDENTIAL}>機密</option>
                            <option value={DataClassification.RESTRICTED}>受限</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            敏感性標籤（可多選）
                          </label>
                          <div className="flex flex-wrap gap-2">
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
                                className={`px-2 py-1 text-xs rounded border transition-colors ${
                                  sensitivityLabels.includes(value)
                                    ? 'bg-blue-500 text-white border-blue-500'
                                    : 'bg-white text-gray-700 border-gray-300 hover:border-gray-400'
                                }`}
                              >
                                {label}
                              </button>
                            ))}
                          </div>
                        </div>
                        <p className="text-xs text-gray-500 mt-2">
                          注意：如果未設置，將使用默認配置（私有訪問，內部數據分類）
                        </p>
                      </div>
                    )}
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  className="hidden"
                  onChange={handleFileInputChange}
                  accept={ALLOWED_EXTENSIONS.join(',')}
                />
              </div>

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
            </>
          )}
        </div>

        {/* Error Message */}
        {dragError && (
          <div className="px-6 pb-4">
            <div className="p-3 bg-red-50 border border-red-200 rounded flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{dragError}</p>
            </div>
          </div>
        )}
        </div>

        {/* Footer：固定於 Modal 底部，上架/上傳按鈕始終可見 */}
        <div className="flex-shrink-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={handleClose}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors"
          >
            取消
          </button>
          {/* Agent 知識庫模式：一律顯示「知識庫上架」按鈕，絕不顯示「上傳」 */}
          {/* 重要：當 agentKnowledgeMode 為 true 時，絕對不顯示「上傳」按鈕 */}
          {agentKnowledgeMode === true ? (
            (() => {
              const needBoth =
                agentCheck.taskExists !== true || !agentCheck.hasAny;
              const pathsReady = needBoth
                ? ontologyFolderFiles.length > 0 && knowledgeFolderFiles.length > 0
                : knowledgeFolderFiles.length > 0;
              const disabled =
                agentUploading ||
                !resolvedTaskId.trim() ||
                agentCheck.loading ||
                !!agentCheck.error ||
                !pathsReady;
              
              // 調試日誌（開發環境）
              console.log('[FileUploadModal] Footer: Agent mode active', {
                agentKnowledgeMode,
                pathsReady,
                disabled,
                ontologyCount: ontologyFolderFiles.length,
                knowledgeCount: knowledgeFolderFiles.length,
                needBoth,
                resolvedTaskId: resolvedTaskId.trim(),
              });
              
              return (
                <button
                  type="button"
                  onClick={disabled ? undefined : handleAgentUpload}
                  disabled={disabled}
                  title={
                    disabled && !pathsReady
                      ? `請先選擇知識庫路徑${needBoth ? '及 Ontology 路徑' : ''}`
                      : undefined
                  }
                  className="px-4 py-2 text-white bg-amber-600 rounded hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                >
                  {agentUploading && <Loader2 className="w-4 h-4 animate-spin" />}
                  知識庫上架
                </button>
              );
            })()
          ) : (
            // 一般上傳模式：顯示「上傳」按鈕（僅在 agentKnowledgeMode 為 false 時顯示）
            (() => {
              // 調試日誌（開發環境）
              console.log('[FileUploadModal] Footer: Normal mode (NOT Agent)', {
                agentKnowledgeMode,
                filesCount: files.length,
              });
              
              return (
                <button
                  type="button"
                  onClick={handleUpload}
                  disabled={files.length === 0}
                  className="px-4 py-2 text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  上傳 ({files.length})
                </button>
              );
            })()
          )}
        </div>
      </div>
    </div>
  );
};

export default FileUploadModal;
