/**
 * 代碼功能說明: 任務數據存儲管理工具，用於模擬後台數據存儲
 * 創建日期: 2025-01-27
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-08 09:04:21 UTC+8
 */

// 修改時間：2025-12-08 09:04:21 UTC+8 - 添加後台同步功能
import { Task, FavoriteItem } from '../components/Sidebar';
import { syncTasks, listUserTasks, createUserTask, updateUserTask } from './api';
import { getCurrentUserId } from './jwtUtils';

const STORAGE_KEY = 'ai-box-tasks';
const STORAGE_KEY_PREFIX = 'ai-box-task-';
// 修改時間：2025-12-09 - 添加收藏夾存儲鍵
const FAVORITES_STORAGE_KEY = 'ai-box-favorites';

/**
 * 保存任務數據到 localStorage 並同步到後台
 * 修改時間：2025-12-08 09:04:21 UTC+8 - 添加後台同步功能
 */
export async function saveTask(task: Task, syncToBackend: boolean = true): Promise<void> {
  try {
    const taskKey = `${STORAGE_KEY_PREFIX}${task.id}`;
    localStorage.setItem(taskKey, JSON.stringify(task));

    // 更新任務列表
    const taskList = getTaskList();
    if (!taskList.includes(task.id)) {
      taskList.push(task.id);
      saveTaskList(taskList);
    }

    // 同步到後台（如果啟用且用戶已登錄）
    if (syncToBackend) {
      const userId = getCurrentUserId();
      if (userId) {
        try {
          // 轉換任務格式以匹配後台 API
          // 確保 executionConfig 存在且包含 mode 字段
          const executionConfig = task.executionConfig || { mode: 'free' };
          if (!executionConfig.mode) {
            executionConfig.mode = 'free';
          }

          // 修改時間：2025-01-27 - 不傳遞 user_id，後端會自動使用當前認證用戶的 user_id
          // 修改時間：2025-12-09 - 添加 task_status 字段，默認值為 activate
          const backendTask = {
            task_id: String(task.id),
            // 不傳遞 user_id，後端會自動使用當前認證用戶的 user_id（安全考慮）
            title: task.title,
            status: task.status || 'pending',
            task_status: task.task_status || 'activate', // 默認值為 activate
            label_color: task.label_color || null, // 修改時間：2025-12-09 - 包含 label_color
            dueDate: task.dueDate,
            messages: task.messages || [],
            executionConfig: executionConfig,
            fileTree: task.fileTree || [],
          };

          // 修改時間：2025-12-09 - 修復任務更新時序問題和 409 錯誤處理
          // 判斷是否為新任務：如果任務沒有 fileTree 或 fileTree 為空，且沒有 messages，可能是新任務
          // 對於新任務，直接創建；對於現有任務，先更新，失敗則創建
          const isNewTask = (!task.fileTree || task.fileTree.length === 0) &&
                           (!task.messages || task.messages.length === 0);

          let syncResult: any = null;
          let lastError: any = null;

          if (isNewTask) {
            // 新任務：直接創建
            console.log('[TaskStorage] New task detected, creating directly', { taskId: task.id });
            try {
              syncResult = await createUserTask(backendTask);
              console.log('[TaskStorage] New task created successfully', { taskId: task.id });
            } catch (createError: any) {
              lastError = createError;
              // 檢查是否為 409 錯誤（任務已存在，可能是並發創建）
              if (createError?.status === 409 || createError?.message?.includes('409') || createError?.message?.includes('unique constraint')) {
                console.log('[TaskStorage] Task already exists (409), trying to update instead', { taskId: task.id });
                // 任務已存在，嘗試更新
                try {
                  syncResult = await updateUserTask(String(task.id), {
                    title: task.title,
                    status: task.status,
                    task_status: task.task_status || 'activate', // 修改時間：2025-12-09 - 包含 task_status
                    label_color: task.label_color || null, // 修改時間：2025-12-09 - 包含 label_color
                    dueDate: task.dueDate,
                    messages: task.messages,
                    executionConfig: executionConfig,
                    fileTree: task.fileTree,
                  });
                  console.log('[TaskStorage] Task updated successfully after 409', { taskId: task.id });
                } catch (retryError: any) {
                  lastError = retryError;
                  console.warn('[TaskStorage] Failed to update task after 409', { taskId: task.id, error: retryError });
                }
              } else {
                console.warn('[TaskStorage] Failed to create new task', { taskId: task.id, error: createError });
              }
            }
          } else {
            // 現有任務：先嘗試更新
            console.log('[TaskStorage] Existing task detected, updating', { taskId: task.id });
            try {
              syncResult = await updateUserTask(String(task.id), {
                title: task.title,
                status: task.status,
                task_status: task.task_status || 'activate', // 修改時間：2025-12-09 - 包含 task_status
                label_color: task.label_color || null, // 修改時間：2025-12-09 - 包含 label_color
                dueDate: task.dueDate,
                messages: task.messages,
                executionConfig: executionConfig,
                fileTree: task.fileTree,
              });
              console.log('[TaskStorage] Task updated successfully', { taskId: task.id });
            } catch (updateError: any) {
              lastError = updateError;
              // 如果更新失敗（任務不存在），嘗試創建
              if (updateError?.status === 404 || updateError?.message?.includes('404') || updateError?.message?.includes('not found') || updateError?.isExpected) {
                // 使用 console.debug 而不是 console.log，因為這是預期行為
                console.debug('[TaskStorage] Task not found, trying to create', { taskId: task.id });
                try {
                  syncResult = await createUserTask(backendTask);
                  console.log('[TaskStorage] Task created successfully', { taskId: task.id });
                } catch (createError: any) {
                  lastError = createError;
                  // 檢查是否為 409 錯誤（任務已存在）
                  if (createError?.status === 409 || createError?.message?.includes('409') || createError?.message?.includes('unique constraint') || createError?.isExpected) {
                    // 使用 console.debug 而不是 console.log，因為這是預期行為（並發創建）
                    console.debug('[TaskStorage] Task already exists (409), retrying update', { taskId: task.id });
                    // 再次嘗試更新
                    try {
                      syncResult = await updateUserTask(String(task.id), {
                        title: task.title,
                        status: task.status,
                        dueDate: task.dueDate,
                        messages: task.messages,
                        executionConfig: executionConfig,
                        fileTree: task.fileTree,
                      });
                      console.log('[TaskStorage] Task updated successfully after 409 retry', { taskId: task.id });
                    } catch (retryError: any) {
                      lastError = retryError;
                      console.warn('[TaskStorage] Failed to update task after 409 retry', { taskId: task.id, error: retryError });
                    }
                  } else {
                    console.warn('[TaskStorage] Failed to create task', { taskId: task.id, error: createError });
                  }
                }
              } else {
                // 更新失敗但不是 404，記錄錯誤
                console.warn('[TaskStorage] Failed to update task', { taskId: task.id, error: updateError });
              }
            }
          }

          if (syncResult && syncResult.success) {
            console.log('[TaskStorage] Task synced successfully', { taskId: task.id, method: isNewTask ? 'create' : 'update' });
          } else {
            // 如果所有嘗試都失敗了，記錄警告但不拋出錯誤（允許本地保存成功）
            console.warn('[TaskStorage] Failed to sync task to backend (all attempts failed)', {
              taskId: task.id,
              isNewTask,
              lastError: lastError?.message || lastError
            });
          }
        } catch (error) {
          console.warn('[TaskStorage] Failed to sync task to backend:', error);
          // 不拋出錯誤，允許本地保存成功
        }
      }
    }
  } catch (error) {
    console.error('Failed to save task:', error);
  }
}

/**
 * 獲取任務數據
 */
export function getTask(taskId: string | number): Task | null {
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
export function getTaskList(): (string | number)[] {
  try {
    const taskListData = localStorage.getItem(STORAGE_KEY);
    if (taskListData) {
      return JSON.parse(taskListData) as (string | number)[];
    }
  } catch (error) {
    console.error('Failed to get task list:', error);
  }
  return [];
}

/**
 * 保存任務 ID 列表
 */
export function saveTaskList(taskList: (string | number)[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(taskList));
  } catch (error) {
    console.error('Failed to save task list:', error);
  }
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
export function deleteTask(taskId: string | number): void {
  try {
    const taskKey = `${STORAGE_KEY_PREFIX}${taskId}`;
    localStorage.removeItem(taskKey);

    // 從任務列表中移除
    const taskList = getTaskList();
    const updatedList = taskList.filter(id => String(id) !== String(taskId));
    saveTaskList(updatedList);
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
export function taskExists(taskId: string | number): boolean {
  return getTask(taskId) !== null;
}

/**
 * 從後台同步任務數據到 localStorage
 * 修改時間：2025-12-08 09:04:21 UTC+8 - 添加後台同步功能
 */
export async function syncTasksFromBackend(): Promise<{ synced: number; errors: number }> {
  const userId = getCurrentUserId();
  if (!userId) {
    console.warn('[TaskStorage] Cannot sync tasks: user not logged in');
    return { synced: 0, errors: 0 };
  }

  try {
    // 修改時間：2026-01-27 - 分頁獲取所有任務（包括歸檔的），確保同步所有任務
    let allTasks: any[] = [];
    let offset = 0;
    // 修改時間：2026-01-06 - 減少 limit 以提升性能，避免超時
    const limit = 500; // 每次獲取最多 500 個任務（減少以提升性能）
    let hasMore = true;

    // 循環獲取所有任務，直到沒有更多任務
    while (hasMore) {
      const response = await listUserTasks(true, limit, offset); // include_archived=true, limit, offset
      if (!response.success || !response.data) {
        console.error('[TaskStorage] Failed to fetch tasks from backend:', response.message);
        break;
      }

      const tasks = response.data.tasks || [];
      allTasks = allTasks.concat(tasks);

      // 如果返回的任務數量小於 limit，說明已經獲取完所有任務
      if (tasks.length < limit) {
        hasMore = false;
      } else {
        offset += limit;
      }
    }

    console.log(`[TaskStorage] Fetched ${allTasks.length} tasks from backend (in ${Math.ceil(allTasks.length / limit)} pages)`);
    if (allTasks.length > 0) {
      console.log('[TaskStorage] First 5 tasks:', allTasks.slice(0, 5).map(t => ({ id: t.task_id, title: t.title, status: t.task_status })));
    }

    let synced = 0;
    let errors = 0;
    const currentTaskList = getTaskList();
    const updatedTaskList = [...currentTaskList];

    // 將後台任務轉換為前端格式並保存到 localStorage
    for (const backendTask of allTasks) {
      try {
        const taskId = backendTask.task_id;
        
        // 修改時間：2025-12-09 - 從 localStorage 讀取現有任務，保留本地的 label_color
        const existingTask = getTask(taskId);

        // 修改時間：2025-01-27 - 優先使用後端的 task_status，確保同步最新狀態
        // 強制使用後端的 task_status（如果後端有設置），否則使用本地的，最後默認為 activate
        const finalTaskStatus = backendTask.task_status !== undefined && backendTask.task_status !== null
          ? backendTask.task_status
          : (existingTask?.task_status || 'activate');

        const frontendTask: Task = {
          id: taskId, // 修改時間：2026-01-06 - 支持字符串 ID，不再強制轉換為數字
          title: backendTask.title,
          status: backendTask.status as 'pending' | 'in-progress' | 'completed',
          task_status: finalTaskStatus,
          // 修改時間：2025-12-09 - 優先使用後端的 label_color，如果後端沒有則使用本地的
          label_color: backendTask.label_color !== undefined && backendTask.label_color !== null
            ? backendTask.label_color
            : existingTask?.label_color,
          dueDate: backendTask.dueDate || '',
          messages: backendTask.messages,
          executionConfig: backendTask.executionConfig,
          fileTree: backendTask.fileTree,
        };

        // 保存到 localStorage（不觸發後台同步，避免循環）
        const taskKey = `${STORAGE_KEY_PREFIX}${frontendTask.id}`;
        localStorage.setItem(taskKey, JSON.stringify(frontendTask));

        // 更新任務列表
        if (!updatedTaskList.includes(frontendTask.id)) {
          updatedTaskList.push(frontendTask.id);
        }

        synced++;
      } catch (error) {
        console.error('[TaskStorage] Failed to sync task:', backendTask.task_id, error);
        errors++;
      }
    }

    // 批量更新任務列表，提高效能
    if (synced > 0) {
      saveTaskList(updatedTaskList);
    }

    console.log(`[TaskStorage] Synced ${synced} tasks from backend, ${errors} errors`);
    return { synced, errors };
  } catch (error) {
    console.error('[TaskStorage] Failed to sync tasks from backend:', error);
    return { synced: 0, errors: 1 };
  }
}

/**
 * 將本地任務同步到後台
 * 修改時間：2025-12-08 09:04:21 UTC+8 - 添加後台同步功能
 */
export async function syncTasksToBackend(): Promise<{ synced: number; errors: number }> {
  const userId = getCurrentUserId();
  if (!userId) {
    console.warn('[TaskStorage] Cannot sync tasks: user not logged in');
    return { synced: 0, errors: 0 };
  }

  try {
    const localTasks = getAllTasks();
    if (localTasks.length === 0) {
      return { synced: 0, errors: 0 };
    }

    // 轉換為後台格式
    const tasksToSync = localTasks.map(task => ({
      id: task.id,
      task_id: String(task.id),
      title: task.title,
      status: task.status,
      dueDate: task.dueDate,
      messages: task.messages,
      executionConfig: task.executionConfig,
      fileTree: task.fileTree,
    }));

    const response = await syncTasks(tasksToSync);
    if (!response.success || !response.data) {
      console.error('[TaskStorage] Failed to sync tasks to backend:', response.message);
      return { synced: 0, errors: 1 };
    }

    console.log(`[TaskStorage] Synced ${response.data.total} tasks to backend (created: ${response.data.created}, updated: ${response.data.updated}, errors: ${response.data.errors})`);
    return { synced: response.data.total - response.data.errors, errors: response.data.errors };
  } catch (error) {
    console.error('[TaskStorage] Failed to sync tasks to backend:', error);
    return { synced: 0, errors: 1 };
  }
}

/**
 * 雙向同步任務數據（從後台獲取並合併本地數據）
 * 修改時間：2025-12-08 09:04:21 UTC+8 - 添加後台同步功能
 */
export async function syncTasksBidirectional(): Promise<{ synced: number; errors: number }> {
  const userId = getCurrentUserId();
  if (!userId) {
    console.warn('[TaskStorage] Cannot sync tasks: user not logged in');
    return { synced: 0, errors: 0 };
  }

  try {
    // 1. 先將本地任務同步到後台
    await syncTasksToBackend();

    // 2. 然後從後台獲取最新數據（包含其他設備的任務）
    const result = await syncTasksFromBackend();

    // 3. 觸發任務更新事件，通知 UI 刷新
    window.dispatchEvent(new CustomEvent('tasksSynced', {
      detail: { synced: result.synced, errors: result.errors }
    }));

    return result;
  } catch (error) {
    console.error('[TaskStorage] Failed to sync tasks bidirectionally:', error);
    return { synced: 0, errors: 1 };
  }
}

/**
 * 獲取所有收藏的任務
 * 修改時間：2025-12-09 - 添加收藏夾管理功能
 */
export function getFavorites(): FavoriteItem[] {
  try {
    const favoritesJson = localStorage.getItem(FAVORITES_STORAGE_KEY);
    if (!favoritesJson) {
      return [];
    }
    return JSON.parse(favoritesJson);
  } catch (error) {
    console.error('[TaskStorage] Failed to get favorites:', error);
    return [];
  }
}

/**
 * 保存收藏列表
 * 修改時間：2025-12-09 - 添加收藏夾管理功能
 */
export function saveFavorites(favorites: FavoriteItem[]): void {
  try {
    localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(favorites));
  } catch (error) {
    console.error('[TaskStorage] Failed to save favorites:', error);
  }
}

/**
 * 添加任務到收藏夾
 * 修改時間：2025-12-09 - 添加收藏夾管理功能
 */
export function addTaskToFavorites(task: Task): void {
  try {
    const favorites = getFavorites();
    // 檢查是否已經收藏
    const existingIndex = favorites.findIndex(
      fav => fav.type === 'task' && fav.itemId === String(task.id)
    );

    if (existingIndex === -1) {
      // 添加到收藏夾
      const favoriteItem: FavoriteItem = {
        id: `fav-task-${task.id}`,
        name: task.title,
        type: 'task',
        itemId: String(task.id),
        icon: 'fa-tasks',
      };
      favorites.push(favoriteItem);
      saveFavorites(favorites);
    }
  } catch (error) {
    console.error('[TaskStorage] Failed to add task to favorites:', error);
  }
}

/**
 * 從收藏夾移除任務
 * 修改時間：2025-12-09 - 添加收藏夾管理功能
 */
export function removeTaskFromFavorites(taskId: number): void {
  try {
    const favorites = getFavorites();
    const filtered = favorites.filter(
      fav => !(fav.type === 'task' && fav.itemId === String(taskId))
    );
    saveFavorites(filtered);
  } catch (error) {
    console.error('[TaskStorage] Failed to remove task from favorites:', error);
  }
}

/**
 * 從收藏夾移除收藏項（通用函數，支持任務、助理、代理）
 * 修改時間：2026-01-06 - 添加通用移除收藏功能
 */
export function removeFavorite(favoriteId: string, itemId: string | number, type: 'task' | 'assistant' | 'agent'): void {
  try {
    console.log('[TaskStorage] Removing favorite:', { favoriteId, itemId, type });
    
    if (type === 'task') {
      // 任務收藏存儲在 'ai-box-favorites' 中
      const favorites = getFavorites();
      const filtered = favorites.filter(
        fav => {
          const matchById = fav.id === favoriteId;
          const matchByTypeAndItemId = fav.type === type && String(fav.itemId) === String(itemId);
          const shouldKeep = !(matchById || matchByTypeAndItemId);
          
          if (!shouldKeep) {
            console.log('[TaskStorage] Removing task favorite:', { id: fav.id, type: fav.type, itemId: fav.itemId });
          }
          
          return shouldKeep;
        }
      );
      
      console.log('[TaskStorage] Task favorites after removal:', { before: favorites.length, after: filtered.length });
      saveFavorites(filtered);
    } else if (type === 'assistant') {
      // 助理收藏存儲在 'favoriteAssistants' 中
      const saved = localStorage.getItem('favoriteAssistants');
      if (saved) {
        try {
          const data = JSON.parse(saved);
          const favoriteMap = new Map(Object.entries(data));
          favoriteMap.delete(String(itemId));
          
          const updatedData = Object.fromEntries(favoriteMap);
          localStorage.setItem('favoriteAssistants', JSON.stringify(updatedData));
          console.log('[TaskStorage] Removed assistant favorite:', { itemId, before: data, after: updatedData });
          
          // 觸發事件通知 Home.tsx 更新
          window.dispatchEvent(new CustomEvent('favoriteAssistantsUpdated', {
            detail: { type: 'favoriteAssistants' }
          }));
        } catch (error) {
          console.error('[TaskStorage] Failed to remove assistant favorite:', error);
        }
      }
    } else if (type === 'agent') {
      // 代理收藏存儲在 'favoriteAgents' 中
      const saved = localStorage.getItem('favoriteAgents');
      if (saved) {
        try {
          const data = JSON.parse(saved);
          const favoriteMap = new Map(Object.entries(data));
          favoriteMap.delete(String(itemId));
          
          const updatedData = Object.fromEntries(favoriteMap);
          localStorage.setItem('favoriteAgents', JSON.stringify(updatedData));
          console.log('[TaskStorage] Removed agent favorite:', { itemId, before: data, after: updatedData });
          
          // 觸發事件通知 Home.tsx 更新
          window.dispatchEvent(new CustomEvent('favoriteAgentsUpdated', {
            detail: { type: 'favoriteAgents' }
          }));
        } catch (error) {
          console.error('[TaskStorage] Failed to remove agent favorite:', error);
        }
      }
    }
  } catch (error) {
    console.error('[TaskStorage] Failed to remove favorite:', error);
    throw error;
  }
}

/**
 * 檢查任務是否已收藏
 * 修改時間：2025-12-09 - 添加收藏夾管理功能
 */
export function isTaskFavorite(taskId: number): boolean {
  try {
    const favorites = getFavorites();
    return favorites.some(
      fav => fav.type === 'task' && fav.itemId === String(taskId)
    );
  } catch (error) {
    console.error('[TaskStorage] Failed to check if task is favorite:', error);
    return false;
  }
}

/**
 * 清除舊的硬編碼收藏夾數據（fav-1, fav-2, fav-3）
 * 修改時間：2025-12-09 - 清除硬編碼的收藏夾數據
 */
export function clearHardcodedFavorites(): void {
  try {
    const favorites = getFavorites();
    // 過濾掉舊的硬編碼收藏（id 為 fav-1, fav-2, fav-3 的任務收藏）
    const filtered = favorites.filter(
      fav => !(fav.type === 'task' && (fav.id === 'fav-1' || fav.id === 'fav-2' || fav.id === 'fav-3'))
    );
    saveFavorites(filtered);
    console.log('[TaskStorage] Cleared hardcoded favorites');
  } catch (error) {
    console.error('[TaskStorage] Failed to clear hardcoded favorites:', error);
  }
}
