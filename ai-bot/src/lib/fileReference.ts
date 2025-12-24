/**
 * 代碼功能說明: 檔案引用解析工具（解析 @filename 並查找對應檔案）
 * 創建日期: 2025-12-14 14:30:00 (UTC+8)
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-14 14:30:00 (UTC+8)
 */

export interface FileReference {
  filename: string;
  isDraft: boolean;
  fileId: string | null;
  containerKey: string | null;
  taskId: string | null;
}

export interface DraftFileContent {
  file_id: string;
  filename: string;
  content: string;
  task_id: string;
  container_key: string;
  updated_at: string;
}

const DRAFT_FILES_STORAGE_KEY = 'ai-box-draft-files-v1';
const DRAFT_CONTENT_STORAGE_KEY = 'ai-box-draft-content-v1';

export function isDraftFileId(fileId: string): boolean {
  return typeof fileId === 'string' && fileId.startsWith('draft-');
}

function loadDraftFilesFromStorage(): Record<string, any[]> {
  try {
    const raw = localStorage.getItem(DRAFT_FILES_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return {};
    return parsed as Record<string, any[]>;
  } catch {
    return {};
  }
}

/**
 * 從文本中解析檔案引用（@filename）。
 * 返回檔名（不含 @ 符號）。
 */
export function parseFileReferenceFromText(text: string): string | null {
  const t = (text || '').trim();
  // 匹配 @filename.ext 模式
  const match = t.match(/@([A-Za-z0-9_\-\u4e00-\u9fff/]+\.(?:md|txt|json))\b/);
  if (match) {
    return match[1];
  }
  return null;
}

/**
 * 根據檔名查找檔案（草稿檔和正式檔案）。
 *
 * @param filename - 檔名（不含 @ 符號）
 * @param taskId - 任務 ID（可選，用於查找正式檔案）
 * @param draftFilesByContainerKey - 草稿檔映射（可選，如果不提供則從 localStorage 讀取）
 * @returns 檔案引用信息，如果找不到則返回 null
 */
export function findFileReference(
  filename: string,
  taskId?: string | null,
  draftFilesByContainerKey?: Record<string, any[]>
): FileReference | null {
  if (!filename) return null;

  // 先查找草稿檔
  const drafts = draftFilesByContainerKey || loadDraftFilesFromStorage();
  for (const [containerKey, fileList] of Object.entries(drafts)) {
    if (!Array.isArray(fileList)) continue;
    const draft = fileList.find((f: any) => {
      const fname = String(f?.filename || '').trim();
      return fname === filename || fname.toLowerCase() === filename.toLowerCase();
    });
    if (draft) {
      const draftId = String(draft?.file_id || '').trim();
      if (draftId && isDraftFileId(draftId)) {
        return {
          filename: String(draft?.filename || filename).trim(),
          isDraft: true,
          fileId: draftId,
          containerKey: containerKey,
          taskId: String(draft?.task_id || taskId || '').trim() || null,
        };
      }
    }
  }

  // 如果提供了 taskId，可以嘗試查找正式檔案（需要調用 API）
  // 這裡只返回基本信息，實際查找由調用方處理
  if (taskId) {
    return {
      filename: filename,
      isDraft: false,
      fileId: null, // 需要通過 API 查找
      containerKey: null,
      taskId: taskId,
    };
  }

  return null;
}

/**
 * 解析檔案引用（從文本中提取並查找）。
 *
 * @param text - 包含 @filename 的文本
 * @param taskId - 任務 ID（可選）
 * @param draftFilesByContainerKey - 草稿檔映射（可選）
 * @returns 檔案引用信息，如果找不到則返回 null
 */
export function parseFileReference(
  text: string,
  taskId?: string | null,
  draftFilesByContainerKey?: Record<string, any[]>
): FileReference | null {
  const filename = parseFileReferenceFromText(text);
  if (!filename) return null;
  return findFileReference(filename, taskId, draftFilesByContainerKey);
}

/**
 * 加載草稿檔內容。
 */
function loadDraftContentFromStorage(): Record<string, DraftFileContent> {
  try {
    const raw = localStorage.getItem(DRAFT_CONTENT_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return {};
    return parsed as Record<string, DraftFileContent>;
  } catch {
    return {};
  }
}

/**
 * 保存草稿檔內容。
 */
function saveDraftContentToStorage(content: Record<string, DraftFileContent>): void {
  try {
    localStorage.setItem(DRAFT_CONTENT_STORAGE_KEY, JSON.stringify(content));
  } catch {
    // ignore
  }
}

/**
 * 更新草稿檔內容。
 *
 * @param draftId - 草稿檔 ID
 * @param newContent - 新內容
 * @param filename - 檔名（可選，如果不提供則從現有記錄中獲取）
 * @param taskId - 任務 ID（可選）
 * @param containerKey - 容器 key（可選）
 * @returns 是否更新成功
 */
export function updateDraftFileContent(
  draftId: string,
  newContent: string,
  filename?: string,
  taskId?: string | null,
  containerKey?: string | null
): boolean {
  if (!draftId || !isDraftFileId(draftId)) {
    return false;
  }

  const contentMap = loadDraftContentFromStorage();
  const existing = contentMap[draftId];

  // 如果沒有提供必要信息，嘗試從現有記錄中獲取
  const finalFilename = filename || existing?.filename || 'untitled.md';
  const finalTaskId = taskId || existing?.task_id || '';
  const finalContainerKey = containerKey || existing?.container_key || '';

  contentMap[draftId] = {
    file_id: draftId,
    filename: finalFilename,
    content: newContent,
    task_id: finalTaskId,
    container_key: finalContainerKey,
    updated_at: new Date().toISOString(),
  };

  saveDraftContentToStorage(contentMap);

  // 觸發自定義事件，通知其他組件更新
  window.dispatchEvent(
    new CustomEvent('draftFileContentUpdated', {
      detail: {
        draftId,
        filename: finalFilename,
        taskId: finalTaskId,
      },
    })
  );

  return true;
}

/**
 * 獲取草稿檔內容。
 *
 * @param draftId - 草稿檔 ID
 * @returns 草稿檔內容，如果不存在則返回 null
 */
export function getDraftFileContent(draftId: string): string | null {
  if (!draftId || !isDraftFileId(draftId)) {
    return null;
  }

  const contentMap = loadDraftContentFromStorage();
  const draft = contentMap[draftId];
  return draft?.content || null;
}
