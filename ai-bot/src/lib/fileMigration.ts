/**
 * 代碼功能說明: 文件遷移工具 - 批量更新文件記錄為初版
 * 創建日期: 2026-01-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-06
 */

import { getFileList, updateFileMetadata, FileMetadata } from './api';

/**
 * 批量更新所有文件記錄為初版，備註"遷移原文件"
 */
export async function migrateAllFilesToInitialVersion(): Promise<{
  success: boolean;
  updated: number;
  failed: number;
  errors: string[];
}> {
  const errors: string[] = [];
  let updated = 0;
  let failed = 0;

  try {
    // 獲取所有文件
    const response = await getFileList({
      limit: 1000,
      offset: 0,
      sort_by: 'created_at',
      sort_order: 'desc',
    });

    if (!response.success || !response.data) {
      return {
        success: false,
        updated: 0,
        failed: 0,
        errors: [response.message || '獲取文件列表失敗'],
      };
    }

    const files = response.data.files;
    console.log(`[FileMigration] 找到 ${files.length} 個文件，開始批量更新...`);

    // 批量更新每個文件
    for (const file of files) {
      try {
        // 檢查文件是否已經有版本和備註
        const hasVersion = file.custom_metadata && 
          typeof file.custom_metadata === 'object' && 
          (file.custom_metadata as any).version;
        
        const hasNote = file.description === '遷移原文件' || 
          (file.custom_metadata && 
           typeof file.custom_metadata === 'object' && 
           ((file.custom_metadata as any).note === '遷移原文件' || 
            (file.custom_metadata as any).备注 === '遷移原文件'));

        // 如果已經有版本和備註，跳過
        if (hasVersion && hasNote) {
          console.log(`[FileMigration] 文件 ${file.file_id} 已更新，跳過`);
          continue;
        }

        // 準備更新數據
        const customMetadata = file.custom_metadata && typeof file.custom_metadata === 'object' 
          ? { ...(file.custom_metadata as any) }
          : {};
        
        customMetadata.version = '1.0';
        customMetadata.note = '遷移原文件';
        customMetadata.备注 = '遷移原文件';

        // 更新文件元數據
        const updateResponse = await updateFileMetadata(file.file_id, {
          description: '遷移原文件',
          custom_metadata: customMetadata,
        });

        if (updateResponse.success) {
          updated++;
          console.log(`[FileMigration] 成功更新文件 ${file.file_id}`);
        } else {
          failed++;
          const errorMsg = `文件 ${file.file_id}: ${updateResponse.message || '更新失敗'}`;
          errors.push(errorMsg);
          console.error(`[FileMigration] ${errorMsg}`);
        }
      } catch (error: any) {
        failed++;
        const errorMsg = `文件 ${file.file_id}: ${error.message || '更新失敗'}`;
        errors.push(errorMsg);
        console.error(`[FileMigration] ${errorMsg}`, error);
      }
    }

    console.log(`[FileMigration] 批量更新完成: 成功 ${updated} 個，失敗 ${failed} 個`);

    return {
      success: failed === 0,
      updated,
      failed,
      errors,
    };
  } catch (error: any) {
    console.error('[FileMigration] 批量更新失敗:', error);
    return {
      success: false,
      updated,
      failed,
      errors: [error.message || '批量更新失敗'],
    };
  }
}

