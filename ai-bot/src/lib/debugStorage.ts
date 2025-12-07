/**
 * 代碼功能說明: 調試工具，用於查看 localStorage 中的任務和文件數據
 * 創建日期: 2025-01-27
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-01-27
 */

import { Task } from '../components/Sidebar';
import { MockFileMetadata } from './mockFileStorage';

const TASK_STORAGE_KEY = 'ai-box-tasks';
const TASK_STORAGE_KEY_PREFIX = 'ai-box-task-';
const FILE_STORAGE_KEY_PREFIX = 'ai-box-mock-files-';

/**
 * 獲取所有任務數據（用於調試）
 */
export function debugGetAllTasks(): Task[] {
  try {
    const taskListData = localStorage.getItem(TASK_STORAGE_KEY);
    if (!taskListData) {
      console.log('[Debug] No task list found');
      return [];
    }

    const taskList = JSON.parse(taskListData) as number[];
    console.log(`[Debug] Found ${taskList.length} tasks:`, taskList);

    const tasks: Task[] = [];
    for (const taskId of taskList) {
      const taskKey = `${TASK_STORAGE_KEY_PREFIX}${taskId}`;
      const taskData = localStorage.getItem(taskKey);
      if (taskData) {
        const task = JSON.parse(taskData) as Task;
        tasks.push(task);
        console.log(`[Debug] Task ${taskId}:`, {
          id: task.id,
          title: task.title,
          fileTreeLength: task.fileTree?.length || 0,
          messagesLength: task.messages?.length || 0,
          fileTree: task.fileTree,
        });
      } else {
        console.warn(`[Debug] Task ${taskId} data not found`);
      }
    }

    return tasks;
  } catch (error) {
    console.error('[Debug] Failed to get all tasks:', error);
    return [];
  }
}

/**
 * 獲取指定任務的文件列表（用於調試）
 */
export function debugGetTaskFiles(taskId: string | number): MockFileMetadata[] {
  try {
    const fileKey = `${FILE_STORAGE_KEY_PREFIX}${taskId}`;
    const fileData = localStorage.getItem(fileKey);
    if (!fileData) {
      console.log(`[Debug] No files found for task ${taskId}`);
      return [];
    }

    const files = JSON.parse(fileData) as MockFileMetadata[];
    console.log(`[Debug] Found ${files.length} files for task ${taskId}:`, files);
    return files;
  } catch (error) {
    console.error(`[Debug] Failed to get files for task ${taskId}:`, error);
    return [];
  }
}

/**
 * 打印所有任務和文件的對應關係（用於調試）
 */
export function debugPrintTaskFileMapping(): void {
  console.log('=== 任務與文件對應關係 ===');

  try {
    const taskListData = localStorage.getItem(TASK_STORAGE_KEY);
    if (!taskListData) {
      console.log('沒有找到任務列表');
      return;
    }

    const taskList = JSON.parse(taskListData) as number[];
    console.log(`找到 ${taskList.length} 個任務`);

    for (const taskId of taskList) {
      const taskKey = `${TASK_STORAGE_KEY_PREFIX}${taskId}`;
      const taskData = localStorage.getItem(taskKey);

      if (taskData) {
        const task = JSON.parse(taskData) as Task;
        console.log(`\n任務 ${taskId}: ${task.title}`);
        console.log(`  - fileTree (prop): ${task.fileTree?.length || 0} 個文件`);
        if (task.fileTree && task.fileTree.length > 0) {
          task.fileTree.forEach((file, index) => {
            console.log(`    ${index + 1}. ${file.name} (${file.type})`);
          });
        }

        // 檢查模擬文件存儲
        const files = debugGetTaskFiles(taskId);
        console.log(`  - mockFiles (storage): ${files.length} 個文件`);
        if (files.length > 0) {
          files.forEach((file, index) => {
            console.log(`    ${index + 1}. ${file.filename} (${file.file_type})`);
          });
        }
      }
    }

    console.log('\n=== 結束 ===');
  } catch (error) {
    console.error('[Debug] Failed to print task-file mapping:', error);
  }
}

/**
 * 在瀏覽器控制台中使用：window.debugStorage.printTaskFileMapping()
 */
if (typeof window !== 'undefined') {
  (window as any).debugStorage = {
    getAllTasks: debugGetAllTasks,
    getTaskFiles: debugGetTaskFiles,
    printTaskFileMapping: debugPrintTaskFileMapping,
  };

  console.log('[Debug] 調試工具已加載，使用 window.debugStorage.printTaskFileMapping() 查看任務與文件對應關係');
}
