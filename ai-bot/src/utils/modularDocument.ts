/**
 * 代碼功能說明: 模組化文檔工具函數
 * 創建日期: 2025-12-20
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-20
 */

/**
 * Transclusion 語法正則表達式: ![[filename]]
 */
const TRANSCLUSION_PATTERN = /!\[\[([^\]]+)\]\]/g;

/**
 * Transclusion 引用信息
 */
export interface TransclusionReference {
  syntax: string; // 完整的語法字符串（例如: ![[filename.md]]）
  filename: string; // 提取的文件名
  startIndex: number; // 在文本中的起始位置
  endIndex: number; // 在文本中的結束位置
}

/**
 * 解析文本中的 Transclusion 語法
 * @param text - 要解析的文本內容
 * @returns TransclusionReference 列表，按出現順序排列
 */
export function parseTransclusionSyntax(text: string): TransclusionReference[] {
  const references: TransclusionReference[] = [];
  let match: RegExpExecArray | null;

  // 重置正則表達式的 lastIndex
  TRANSCLUSION_PATTERN.lastIndex = 0;

  while ((match = TRANSCLUSION_PATTERN.exec(text)) !== null) {
    references.push({
      syntax: match[0],
      filename: match[1].trim(),
      startIndex: match.index,
      endIndex: match.index + match[0].length,
    });
  }

  return references;
}

/**
 * 從 Transclusion 語法中提取文件名
 * @param syntax - Transclusion 語法字符串（例如: ![[filename.md]]）
 * @returns 文件名，如果格式無效則返回 null
 */
export function extractFilenameFromReference(syntax: string): string | null {
  const match = syntax.match(/!\[\[([^\]]+)\]\]/);
  return match ? match[1].trim() : null;
}

/**
 * 替換文本中的 Transclusion 語法為實際內容
 * @param text - 原始文本
 * @param replacements - Transclusion 語法到替換內容的映射
 * @returns 替換後的文本
 */
export function replaceTransclusionSyntax(
  text: string,
  replacements: Map<string, string>
): string {
  let result = text;
  // 從後往前替換，避免位置偏移問題
  const sortedReplacements = Array.from(replacements.entries()).sort(
    (a, b) => text.lastIndexOf(b[0]) - text.lastIndexOf(a[0])
  );

  for (const [syntax, content] of sortedReplacements) {
    result = result.replace(syntax, content);
  }

  return result;
}

/**
 * 虛擬合併文檔結果
 */
export interface VirtualMergeResult {
  mergedContent: string; // 合併後的內容
  references: TransclusionReference[]; // 所有引用信息
  loadedFiles: Map<string, string>; // 已加載的文件內容映射（filename -> content）
  failedFiles: string[]; // 加載失敗的文件名列表
}

/**
 * 異步加載分文檔內容（用於虛擬合併預覽）
 * @param references - Transclusion 引用列表
 * @param loadFileContent - 加載文件內容的函數（filename -> Promise<content>）
 * @returns 虛擬合併結果
 */
export async function loadSubDocuments(
  references: TransclusionReference[],
  loadFileContent: (filename: string) => Promise<string>
): Promise<VirtualMergeResult> {
  const loadedFiles = new Map<string, string>();
  const failedFiles: string[] = [];

  // 去重文件列表
  const uniqueFilenames = Array.from(new Set(references.map((ref) => ref.filename)));

  // 並行加載所有文件
  const loadPromises = uniqueFilenames.map(async (filename) => {
    try {
      const content = await loadFileContent(filename);
      loadedFiles.set(filename, content);
    } catch (error) {
      console.error(`Failed to load sub-document: ${filename}`, error);
      failedFiles.push(filename);
    }
  });

  await Promise.all(loadPromises);

  return {
    mergedContent: '', // 將在調用方根據需要合併
    references,
    loadedFiles,
    failedFiles,
  };
}

/**
 * 將主文檔內容與分文檔內容合併
 * @param masterContent - 主文檔內容
 * @param loadedFiles - 已加載的文件內容映射
 * @param references - Transclusion 引用列表
 * @returns 合併後的內容
 */
export function mergeDocumentContent(
  masterContent: string,
  loadedFiles: Map<string, string>,
  references: TransclusionReference[]
): string {
  let mergedContent = masterContent;

  // 從後往前替換，避免位置偏移問題
  const sortedReferences = [...references].sort((a, b) => b.startIndex - a.startIndex);

  for (const ref of sortedReferences) {
    const content = loadedFiles.get(ref.filename);
    if (content !== undefined) {
      // 替換 Transclusion 語法為實際內容
      mergedContent =
        mergedContent.slice(0, ref.startIndex) +
        content +
        mergedContent.slice(ref.endIndex);
    } else {
      // 如果文件未加載，保留原始語法或顯示錯誤信息
      const errorMessage = `[無法加載文件: ${ref.filename}]`;
      mergedContent =
        mergedContent.slice(0, ref.startIndex) +
        errorMessage +
        mergedContent.slice(ref.endIndex);
    }
  }

  return mergedContent;
}
