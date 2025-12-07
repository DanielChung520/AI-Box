/**
 * 代碼功能說明: 檢查任務文件的 file_id 工具
 * 創建日期: 2025-01-27
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-01-27
 */

import { getAllTasks } from './taskStorage';
import { getMockFiles } from './mockFileStorage';
import { Task } from '../components/Sidebar';

/**
 * 檢查所有任務的文件ID
 */
export function checkAllTaskFileIds(): void {
  console.log('='.repeat(60));
  console.log('檢查所有任務的文件ID');
  console.log('='.repeat(60));

  try {
    // 獲取所有任務
    const tasks = getAllTasks();
    console.log(`\n找到 ${tasks.length} 個任務\n`);

    if (tasks.length === 0) {
      console.log('⚠️  沒有找到任務');
      return;
    }

    // 檢查每個任務
    tasks.forEach((task: Task) => {
      console.log(`\n📁 任務 ID: ${task.id}`);
      console.log(`   標題: ${task.title}`);
      console.log(`   狀態: ${task.status}`);

      // 檢查任務的 fileTree
      if (task.fileTree && task.fileTree.length > 0) {
        console.log(`   fileTree 文件數量: ${task.fileTree.length}`);
        task.fileTree.forEach((file, index) => {
          console.log(`     ${index + 1}. ${file.name}`);
          console.log(`        - 文件ID (file_id): ${file.id}`);
          console.log(`        - 類型: ${file.type}`);
        });
      } else {
        console.log(`   fileTree: 無文件`);
      }

      // 檢查模擬文件存儲
      const mockFiles = getMockFiles(String(task.id));
      if (mockFiles.length > 0) {
        console.log(`   模擬文件存儲數量: ${mockFiles.length}`);
        mockFiles.forEach((file, index) => {
          console.log(`     ${index + 1}. ${file.filename}`);
          console.log(`        - 文件ID (file_id): ${file.file_id}`);
          console.log(`        - 任務ID: ${file.task_id}`);
          console.log(`        - 用戶ID: ${file.user_id || 'N/A'}`);
          console.log(`        - 文件類型: ${file.file_type}`);
          console.log(`        - 文件大小: ${file.file_size} bytes`);
          console.log(`        - 上傳時間: ${file.upload_time}`);
        });
      } else {
        console.log(`   模擬文件存儲: 無文件`);
      }

      console.log('-'.repeat(60));
    });

    // 統計
    const totalFilesInTree = tasks.reduce((sum, task) => sum + (task.fileTree?.length || 0), 0);
    const totalMockFiles = tasks.reduce((sum, task) => sum + getMockFiles(String(task.id)).length, 0);

    console.log('\n' + '='.repeat(60));
    console.log('總結：');
    console.log(`  - 總任務數: ${tasks.length}`);
    console.log(`  - fileTree 中的文件數: ${totalFilesInTree}`);
    console.log(`  - 模擬文件存儲中的文件數: ${totalMockFiles}`);
    console.log('='.repeat(60));

    // 列出所有唯一的 file_id
    const allFileIds = new Set<string>();
    tasks.forEach((task: Task) => {
      if (task.fileTree) {
        task.fileTree.forEach(file => {
          if (file.id) {
            allFileIds.add(file.id);
          }
        });
      }
      const mockFiles = getMockFiles(String(task.id));
      mockFiles.forEach(file => {
        if (file.file_id) {
          allFileIds.add(file.file_id);
        }
      });
    });

    console.log('\n所有文件ID列表：');
    console.log('-'.repeat(60));
    Array.from(allFileIds).sort().forEach((fileId, index) => {
      console.log(`  ${index + 1}. ${fileId}`);
    });
    console.log(`\n總共 ${allFileIds.size} 個唯一的文件ID`);

  } catch (error) {
    console.error('❌ 檢查失敗:', error);
  }
}

// 在瀏覽器控制台中使用：window.checkFiles()
if (typeof window !== 'undefined') {
  (window as any).checkFiles = checkAllTaskFileIds;
  console.log('[CheckFiles] 工具已加載，使用 window.checkFiles() 查看所有任務的文件ID');
}
