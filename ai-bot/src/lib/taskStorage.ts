/**
 * 代碼功能說明: 任務數據存儲管理工具，用於模擬後台數據存儲
 * 創建日期: 2025-01-27
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-01-27
 */

import { Task } from '../components/Sidebar';

const STORAGE_KEY = 'ai-box-tasks';
const STORAGE_KEY_PREFIX = 'ai-box-task-';

/**
 * 保存任務數據到 localStorage
 */
export function saveTask(task: Task): void {
  try {
    const taskKey = `${STORAGE_KEY_PREFIX}${task.id}`;
    localStorage.setItem(taskKey, JSON.stringify(task));

    // 更新任務列表
    const taskList = getTaskList();
    if (!taskList.includes(task.id)) {
      taskList.push(task.id);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(taskList));
    }
  } catch (error) {
    console.error('Failed to save task:', error);
  }
}

/**
 * 獲取任務數據
 */
export function getTask(taskId: number): Task | null {
  try {
    const taskKey = `${STORAGE_KEY_PREFIX}${taskId}`;
    const taskData = localStorage.getItem(taskKey);
    if (taskData) {
      return JSON.parse(taskData) as Task;
    }
  } catch (error) {
    console.error('Failed to get task:', error);
  }
  return null;
}

/**
 * 獲取所有任務 ID 列表
 */
export function getTaskList(): number[] {
  try {
    const taskListData = localStorage.getItem(STORAGE_KEY);
    if (taskListData) {
      return JSON.parse(taskListData) as number[];
    }
  } catch (error) {
    console.error('Failed to get task list:', error);
  }
  return [];
}

/**
 * 獲取所有任務數據
 */
export function getAllTasks(): Task[] {
  const taskList = getTaskList();
  const tasks: Task[] = [];

  for (const taskId of taskList) {
    const task = getTask(taskId);
    if (task) {
      tasks.push(task);
    }
  }

  return tasks;
}

/**
 * 刪除任務數據
 */
export function deleteTask(taskId: number): void {
  try {
    const taskKey = `${STORAGE_KEY_PREFIX}${taskId}`;
    localStorage.removeItem(taskKey);

    // 從任務列表中移除
    const taskList = getTaskList();
    const updatedList = taskList.filter(id => id !== taskId);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedList));
  } catch (error) {
    console.error('Failed to delete task:', error);
  }
}

/**
 * 更新任務數據
 */
export function updateTask(task: Task): void {
  saveTask(task);
}

/**
 * 檢查任務是否存在
 */
export function taskExists(taskId: number): boolean {
  return getTask(taskId) !== null;
}
