/**
 * 代碼功能說明: 模擬文件存儲管理工具，用於創建模擬文件記錄
 * 創建日期: 2025-01-27
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-01-27
 */

import { FileNode } from '../components/Sidebar';

const STORAGE_KEY_PREFIX = 'ai-box-mock-files-';

export interface MockFileMetadata {
  file_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  task_id: string;
  user_id?: string;
  upload_time: string;
  content?: string; // 模擬文件內容（用於 Markdown 等文本文件）
}

/**
 * 遞歸遍歷 fileTree，創建所有文件的模擬記錄
 */
function createMockFilesFromTree(
  fileTree: FileNode[],
  taskId: string,
  userId?: string
): MockFileMetadata[] {
  const files: MockFileMetadata[] = [];
  const now = new Date().toISOString();

  const traverse = (nodes: FileNode[], parentPath: string = '') => {
    for (const node of nodes) {
      if (node.type === 'file') {
        const fileId = `${taskId}-${node.id}`;
        const fileType = getFileTypeFromName(node.name);

        // 生成模擬文件內容（僅用於 Markdown 文件）
        let content: string | undefined;
        if (fileType === 'text/markdown' || node.name.endsWith('.md')) {
          content = generateMockMarkdownContent(node.name, taskId);
        }

        files.push({
          file_id: fileId,
          filename: node.name,
          file_type: fileType,
          file_size: content ? content.length : 1024, // 模擬文件大小
          task_id: taskId,
          user_id: userId,
          upload_time: now,
          content: content,
        });
      } else if (node.type === 'folder' && node.children) {
        traverse(node.children, `${parentPath}/${node.name}`);
      }
    }
  };

  traverse(fileTree);
  return files;
}

/**
 * 根據文件名推斷文件類型
 */
function getFileTypeFromName(filename: string): string {
  const extension = filename.split('.').pop()?.toLowerCase();
  const typeMap: Record<string, string> = {
    'md': 'text/markdown',
    'markdown': 'text/markdown',
    'txt': 'text/plain',
    'pdf': 'application/pdf',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'doc': 'application/msword',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'xls': 'application/vnd.ms-excel',
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'gif': 'image/gif',
    'svg': 'image/svg+xml',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'ppt': 'application/vnd.ms-powerpoint',
  };
  return typeMap[extension || ''] || 'application/octet-stream';
}

/**
 * 生成模擬 Markdown 文件內容
 */
function generateMockMarkdownContent(filename: string, taskId: string): string {
  const baseName = filename.replace('.md', '').replace('.markdown', '');

  // 根據任務 ID 和文件名生成不同的內容
  const contentMap: Record<string, Record<string, string>> = {
    '1': {
      '近三個月銷售趨勢分析': `# 近三個月銷售趨勢分析

## 概述
本報告分析了近三個月（9月、10月、11月）的銷售趨勢。

## 銷售數據

### 月度銷售額
- **9月**: 1,200,000 元
- **10月**: 1,350,000 元
- **11月**: 1,580,000 元

### 增長趨勢
近三個月銷售額呈現穩步增長趨勢，11月份增長最為明顯，環比增長約 17%。

## 結論
建議繼續保持當前的市場推廣策略，並考慮在西部地區增加投入以提升市場份額。`,
      '各地區銷售占比分析': `# 各地區銷售占比分析

## 銷售占比分布

### 主要市場
- **華東地區**: 38% - 主要市場
- **華北地區**: 25% - 重要市場
- **華南地區**: 18% - 潛力市場

### 次要市場
- **西部地區**: 12% - 成長市場
- **東北地區**: 7% - 待開發市場

## 建議
華東地區是我們的主要市場，占比接近40%。建議繼續加強該地區的市場推廣，同時也可以考慮在西部地區增加投入以提升市場份額。`,
    },
    '2': {
      '項目進度報告': `# 項目進度報告

## 項目概述
本報告展示了當前項目的進度和團隊工作分配情況。

## 項目階段
1. 需求分析 ✅
2. 設計階段 ✅
3. 開發階段 🔄 進行中
4. 測試階段 ⏳ 待開始
5. 部署上線 ⏳ 待開始
6. 運維監控 ⏳ 待開始

## 當前進度
項目目前處於開發階段，各項工作正在有序推進中。`,
      '團隊工作分配': `# 團隊工作分配

## 團隊成員
- 項目經理：負責需求文檔完善
- 開發工程師1：負責數據庫設計和後端開發
- 開發工程師2：負責前端開發
- 測試工程師：負責測試計劃
- 設計師：負責 UI 設計

## 任務分配
詳細的任務分配情況請參考項目管理系統。`,
    },
    '3': {
      '當前客服流程分析': `# 當前客服流程分析

## 流程概述
當前客服響應流程包含以下步驟：
1. 用戶提交請求
2. 等待客服接收
3. 客服初步評估
4. 分配給相應專員
5. 專員處理
6. 用戶反饋
7. 流程結束

## 問題分析
當前流程的主要問題是響應時間過長，平均響應時間為 2.5 小時。`,
      '流程優化方案': `# 流程優化方案

## 優化目標
將平均響應時間縮短 60% 以上。

## 優化措施
1. 引入智能分類系統
2. 自動處理常見問題
3. 優先分配複雜問題
4. 建立快速響應機制

## 預期效果
優化後的流程預計可以將平均響應時間從 2.5 小時縮短到 1 小時以內。`,
    },
    '4': {
      '產品概述': `# 產品概述

## 產品介紹
這是一個智能化的任務管理和文件編輯平台。

## 核心功能
- 文件管理
- AI 助手
- 任務管理

## 適用場景
適用於各種需要智能協助的工作場景。`,
      '快速開始指南': `# 快速開始指南

## 第一步：創建任務
點擊側邊欄的「新增任務」按鈕，創建您的第一個任務。

## 第二步：選擇執行者
選擇 AI 助理或代理來協助您完成任務。

## 第三步：開始工作
輸入您的需求，AI 助手將協助您完成工作。`,
    },
  };

  // 嘗試從內容映射中獲取，如果沒有則生成通用內容
  const taskContent = contentMap[taskId];
  if (taskContent && taskContent[baseName]) {
    return taskContent[baseName];
  }

  // 生成通用內容
  return `# ${baseName}

## 概述
這是 ${baseName} 的詳細內容。

## 內容
本文件包含與 ${baseName} 相關的重要信息和數據。

*文件生成時間: ${new Date().toLocaleDateString('zh-TW')}*`;
}

/**
 * 保存模擬文件記錄
 */
export function saveMockFiles(
  taskId: string,
  fileTree: FileNode[],
  userId?: string
): void {
  try {
    const files = createMockFilesFromTree(fileTree, String(taskId), userId);
    const storageKey = `${STORAGE_KEY_PREFIX}${taskId}`;
    localStorage.setItem(storageKey, JSON.stringify(files));
  } catch (error) {
    console.error('Failed to save mock files:', error);
  }
}

/**
 * 獲取任務的模擬文件列表
 */
export function getMockFiles(taskId: string): MockFileMetadata[] {
  try {
    const storageKey = `${STORAGE_KEY_PREFIX}${taskId}`;
    const filesData = localStorage.getItem(storageKey);
    if (filesData) {
      return JSON.parse(filesData) as MockFileMetadata[];
    }
  } catch (error) {
    console.error('Failed to get mock files:', error);
  }
  return [];
}

/**
 * 獲取單個模擬文件
 */
export function getMockFile(taskId: string, fileId: string): MockFileMetadata | null {
  const files = getMockFiles(taskId);
  return files.find(f => f.file_id === fileId) || null;
}

/**
 * 獲取模擬文件的內容（用於預覽）
 */
export function getMockFileContent(taskId: string, fileId: string): string | null {
  const file = getMockFile(taskId, fileId);
  return file?.content || null;
}

/**
 * 檢查任務是否有模擬文件
 */
export function hasMockFiles(taskId: string): boolean {
  const files = getMockFiles(taskId);
  return files.length > 0;
}

/**
 * 模擬文件上傳（當後端不可用時使用）
 */
export async function uploadMockFile(
  file: File,
  taskId: string,
  userId?: string
): Promise<MockFileMetadata> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = (e) => {
      try {
        const fileContent = e.target?.result as string | ArrayBuffer;
        const fileId = `${taskId}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const fileType = getFileTypeFromName(file.name);

        // 如果是文本文件，保存內容；否則只保存元數據
        let content: string | undefined;
        if (fileType.startsWith('text/') || file.name.endsWith('.md') || file.name.endsWith('.markdown')) {
          if (typeof fileContent === 'string') {
            content = fileContent;
          } else {
            // 嘗試將 ArrayBuffer 轉換為文本
            const decoder = new TextDecoder('utf-8');
            content = decoder.decode(fileContent);
          }
        }

        const mockFile: MockFileMetadata = {
          file_id: fileId,
          filename: file.name,
          file_type: fileType,
          file_size: file.size,
          task_id: taskId,
          user_id: userId,
          upload_time: new Date().toISOString(),
          content: content,
        };

        // 保存到 localStorage
        const existingFiles = getMockFiles(taskId);
        existingFiles.push(mockFile);
        const storageKey = `${STORAGE_KEY_PREFIX}${taskId}`;
        localStorage.setItem(storageKey, JSON.stringify(existingFiles));

        // 記錄上傳成功的文件 ID
        console.log(`File uploaded - file_id: ${mockFile.file_id}`);
        resolve(mockFile);
      } catch (error) {
        console.error('Failed to upload mock file:', error);
        reject(error);
      }
    };

    reader.onerror = () => {
      reject(new Error('讀取文件失敗'));
    };

    // 根據文件類型選擇讀取方式
    if (file.type.startsWith('text/') || file.name.endsWith('.md') || file.name.endsWith('.markdown')) {
      reader.readAsText(file, 'utf-8');
    } else {
      // 對於二進制文件，讀取為 ArrayBuffer（但我們不保存內容，只保存元數據）
      reader.readAsArrayBuffer(file);
    }
  });
}

/**
 * 批量模擬文件上傳
 */
export async function uploadMockFiles(
  files: File[],
  taskId: string,
  userId?: string
): Promise<{ uploaded: MockFileMetadata[]; errors: Array<{ filename: string; error: string }> }> {
  const uploaded: MockFileMetadata[] = [];
  const errors: Array<{ filename: string; error: string }> = [];

  for (const file of files) {
    try {
      const mockFile = await uploadMockFile(file, taskId, userId);
      uploaded.push(mockFile);
    } catch (error: any) {
      errors.push({
        filename: file.name,
        error: error.message || '上傳失敗',
      });
    }
  }

  return { uploaded, errors };
}
