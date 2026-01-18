import { useState, useMemo, useEffect, useRef, useContext } from 'react';
import { cn } from '../lib/utils';
import { useLanguage } from '../contexts/languageContext';
import { AuthContext } from '../contexts/authContext';
import { saveTask, getAllTasks, deleteTask, getFavorites, addTaskToFavorites, removeTaskFromFavorites, isTaskFavorite, clearHardcodedFavorites, removeFavorite } from '../lib/taskStorage';
import { saveMockFiles } from '../lib/mockFileStorage';
import { deleteUserTask, getUserTask, updateUserTask } from '../lib/api';
import FileRecordModal from './FileRecordModal';
import UserMenu from './UserMenu';

// 定义消息接口
export interface Message {
  id: string;
  sender: 'user' | 'ai';
  content: string;
  timestamp: string;
  containsMermaid?: boolean;
}

// 定义文件节点接口
export interface FileNode {
  id: string;
  name: string;
  type: 'folder' | 'file';
  children?: FileNode[];
}

// 定义任务接口
export interface Task {
  id: number | string;
  title: string;
  status: 'pending' | 'in-progress' | 'completed';
  task_status?: 'activate' | 'archive'; // 修改時間：2025-12-09 - 添加任務顯示狀態（activate/archive）
  label_color?: string; // 修改時間：2025-12-09 - 添加任務顏色標籤（類似 Apple Mac 的顏色標籤）
  dueDate: string;
  created_at?: string; // 修改時間：2026-01-06 - 添加創建時間（ISO 8601 格式字符串）
  updated_at?: string; // 修改時間：2026-01-06 - 添加更新時間（ISO 8601 格式字符串）
  messages?: Message[];
  executionConfig?: {
    mode: 'free' | 'assistant' | 'agent';
    assistantId?: string;
    agentId?: string;
    modelId?: string; // 修改時間：2025-12-13 17:28:02 (UTC+8) - 產品級 Chat：模型選擇（任務維度）
    sessionId?: string; // 修改時間：2025-12-13 17:28:02 (UTC+8) - 產品級 Chat：session_id（任務維度）
  };
  fileTree?: FileNode[]; // 每個任務的文件目錄結構
}

// 定义收藏项接口
export interface FavoriteItem {
  id: string;
  name: string;
  type: 'task' | 'assistant' | 'agent';
  itemId: string | number;
  icon?: string;
}

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  onTaskSelect?: (task: Task) => void;
  onAgentSelect?: (agentId: string) => void;
  onAssistantSelect?: (assistantId: string) => void;
  onBrowseAssistants?: () => void;
  onBrowseAgents?: () => void;
  selectedTask?: Task;
  browseMode?: 'assistants' | 'agents' | null;
  favorites?: FavoriteItem[];
}

export default function Sidebar({ collapsed, onToggle, onTaskSelect, onAgentSelect, onAssistantSelect, onBrowseAssistants, onBrowseAgents, selectedTask, browseMode, favorites: externalFavorites }: SidebarProps) {
  const [activeSection, setActiveSection] = useState<'favorites' | 'tasks'>('tasks');
  const [activeItemId, setActiveItemId] = useState<string | number | null>(null); // 跟踪当前选中的具体 item ID
  const { t, updateCounter, language } = useLanguage();
  const { currentUser } = useContext(AuthContext);

  // 用戶菜單狀態
  const [showUserMenu, setShowUserMenu] = useState(false);
  const userMenuButtonRef = useRef<HTMLButtonElement>(null);

  // 可收合区域的状态管理
  const [expandedSections, setExpandedSections] = useState({
    tasks: true,
  });

  // 當 selectedTask 變化時，更新焦點
  useEffect(() => {
    if (selectedTask) {
      setActiveSection('tasks');
      setActiveItemId(selectedTask.id);
    }
  }, [selectedTask]);

  // 監聽任務創建和刪除事件，更新焦點
  useEffect(() => {
    const handleTaskCreated = (event: CustomEvent) => {
      const { taskId } = event.detail;
      setActiveSection('tasks');
      setActiveItemId(taskId);
    };

    const handleTaskDeleted = (event: CustomEvent) => {
      const { taskId } = event.detail;
      if (activeItemId === taskId) {
        setActiveItemId(null);
      }
    };

    window.addEventListener('taskCreated', handleTaskCreated as EventListener);
    window.addEventListener('taskDeleted', handleTaskDeleted as EventListener);

    return () => {
      window.removeEventListener('taskCreated', handleTaskCreated as EventListener);
      window.removeEventListener('taskDeleted', handleTaskDeleted as EventListener);
    };
  }, [activeItemId]);

  // 修改時間：2025-12-09 - 從 localStorage 讀取收藏夾，清除硬編碼數據
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);

  // 加載收藏夾
  useEffect(() => {
    // 修改時間：2025-12-09 - 首次加載時清除舊的硬編碼收藏夾數據
    const hasCleared = localStorage.getItem('favorites-hardcoded-cleared');
    if (!hasCleared) {
      clearHardcodedFavorites();
      localStorage.setItem('favorites-hardcoded-cleared', 'true');
    }

    const loadFavorites = () => {
      if (externalFavorites) {
        // 如果外部傳入了收藏列表（來自 Home.tsx），使用外部的
        // 但需要確保任務收藏是從 localStorage 讀取的（因為 externalFavorites 可能包含助理和代理）
        const savedTaskFavorites = getFavorites().filter(fav => fav.type === 'task');
        const externalNonTaskFavorites = externalFavorites.filter(fav => fav.type !== 'task');
        // 合併：從 localStorage 讀取的任務收藏 + 外部傳入的非任務收藏（助理、代理）
        setFavorites([...savedTaskFavorites, ...externalNonTaskFavorites]);
      } else {
        // 從 localStorage 讀取收藏夾
        const savedFavorites = getFavorites();
        setFavorites(savedFavorites);
      }
    };
    loadFavorites();

    // 監聽收藏夾更新事件
    const handleFavoritesUpdated = () => {
      loadFavorites();
    };

    // 修改時間：2026-01-06 - 監聽助理和代理收藏更新事件
    const handleFavoriteAssistantsUpdated = () => {
      loadFavorites();
    };

    const handleFavoriteAgentsUpdated = () => {
      loadFavorites();
    };

    window.addEventListener('favoritesUpdated', handleFavoritesUpdated);
    window.addEventListener('favoriteAssistantsUpdated', handleFavoriteAssistantsUpdated);
    window.addEventListener('favoriteAgentsUpdated', handleFavoriteAgentsUpdated);

    return () => {
      window.removeEventListener('favoritesUpdated', handleFavoritesUpdated);
      window.removeEventListener('favoriteAssistantsUpdated', handleFavoriteAssistantsUpdated);
      window.removeEventListener('favoriteAgentsUpdated', handleFavoriteAgentsUpdated);
    };
  }, [externalFavorites, updateCounter]);


  // 修改時間：2025-12-08 09:04:21 UTC+8 - 添加任務同步事件監聽
  // 從 localStorage 加載保存的任務
  const [savedTasks, setSavedTasks] = useState<Task[]>([]);

  // 修改時間：2025-12-08 14:00:00 UTC+8 - 添加歷史任務右鍵菜單狀態
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; task: Task } | null>(null);
  // 修改時間：2026-01-06 - 添加收藏夾項目右鍵菜單狀態
  const [favoriteContextMenu, setFavoriteContextMenu] = useState<{ x: number; y: number; favorite: FavoriteItem } | null>(null);
  const favoriteContextMenuRef = useRef<HTMLDivElement>(null);
  const [showTaskInfoModal, setShowTaskInfoModal] = useState(false);
  const [taskInfo, setTaskInfo] = useState<Task | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteTaskTarget, setDeleteTaskTarget] = useState<Task | null>(null);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  // 修改時間：2025-01-27 - 添加任務重命名狀態
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [renameTaskTarget, setRenameTaskTarget] = useState<Task | null>(null);
  const [renameInput, setRenameInput] = useState('');
  const renameInputRef = useRef<HTMLInputElement>(null);
  const contextMenuRef = useRef<HTMLDivElement>(null);
  // 修改時間：2025-12-09 - 添加顏色標籤相關狀態
  const [showColorMenu, setShowColorMenu] = useState(false);
  const [colorMenuPosition, setColorMenuPosition] = useState<{ x: number; y: number } | null>(null);
  const colorMenuTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // 修改時間：2026-01-06 - 添加響應式顯示限制相關狀態
  const contentAreaRef = useRef<HTMLDivElement>(null);
  const [maxFavoritesDisplay, setMaxFavoritesDisplay] = useState(10); // 默認最大10筆收藏
  const [maxTasksDisplay, setMaxTasksDisplay] = useState<number | null>(null); // 根據高度動態計算
  const [showMoreFavorites, setShowMoreFavorites] = useState(false);
  const [showMoreTasks, setShowMoreTasks] = useState(false);

  // 修改時間：2026-01-06 - 添加更多列表 Modal 狀態
  const [showMoreModal, setShowMoreModal] = useState(false);
  const [moreModalType, setMoreModalType] = useState<'favorites' | 'tasks'>('tasks');

  // 修改時間：2026-01-06 - Modal 篩選和搜尋狀態
  const [modalSearchText, setModalSearchText] = useState('');
  const [modalColorFilter, setModalColorFilter] = useState<string | null>(null);
  const [modalShowArchived, setModalShowArchived] = useState(false);

  // 修改時間：2026-01-06 - 文件記錄 Modal 狀態
  const [showFileRecordModal, setShowFileRecordModal] = useState(false);

  // 修改時間：2026-01-06 - 添加任務篩選狀態
  const [selectedColorFilter, setSelectedColorFilter] = useState<string | null>(null); // null 表示不過濾顏色
  const [showArchivedFilter, setShowArchivedFilter] = useState(false); // false 表示只顯示激活的任務，true 表示顯示歸檔的任務

  // Apple Mac 風格的顏色標籤（7 種顏色）
  const labelColors = [
    { name: '無', value: null, color: 'transparent', border: 'border-gray-400' },
    { name: '紅色', value: 'red', color: '#FF3B30', border: 'border-red-500' },
    { name: '橙色', value: 'orange', color: '#FF9500', border: 'border-orange-500' },
    { name: '黃色', value: 'yellow', color: '#FFCC00', border: 'border-yellow-500' },
    { name: '綠色', value: 'green', color: '#34C759', border: 'border-green-500' },
    { name: '藍色', value: 'blue', color: '#007AFF', border: 'border-blue-500' },
    { name: '紫色', value: 'purple', color: '#AF52DE', border: 'border-purple-500' },
    { name: '灰色', value: 'gray', color: '#8E8E93', border: 'border-gray-500' },
  ];

  // 加載保存的任務
  useEffect(() => {
    const loadSavedTasks = () => {
      try {
        const loadedTasks = getAllTasks();
        // 修改時間：2026-01-06 - 去除重複的任務（根據 task.id）
        // 注意：taskStorage.ts 已經在 getTaskList() 中去重，這裡的檢查主要是為了防禦性編程
        const uniqueTasks = loadedTasks.reduce((acc: Task[], task: Task) => {
          const existingTask = acc.find(t => String(t.id) === String(task.id));
          if (!existingTask) {
            acc.push(task);
          } else {
            // 如果找到重複的任務，保留更新時間更晚的（如果有 updated_at 字段）
            // 或者保留第一個（因為通常後面的可能是重複的）
            // 修改時間：2026-01-06 - 將警告改為 debug 級別，減少控制台噪音
            console.debug('[Sidebar] Found duplicate task:', task.id, 'Keeping first occurrence');
          }
          return acc;
        }, []);

        // 修改時間：2025-01-27 - 不再過濾任務，所有從 localStorage 加載的任務都是真實任務
        // 所有任務都應該顯示（沒有硬編碼的示範任務了）
        console.log('[Sidebar] Loaded tasks from localStorage:', {
          total: loadedTasks.length,
          unique: uniqueTasks.length,
          duplicates: loadedTasks.length - uniqueTasks.length,
          tasks: uniqueTasks.map(t => ({ id: t.id, title: t.title, task_status: t.task_status })),
        });
        setSavedTasks(uniqueTasks);
      } catch (error) {
        console.error('Failed to load saved tasks:', error);
      }
    };

    // 修改時間：2025-01-27 - 初始化時先嘗試從後端同步任務
    // 修改時間：2026-01-06 - 優化加載性能：先顯示本地任務，然後在後台同步
    const initializeTasks = async () => {
      // 先立即加載本地任務，讓用戶看到內容
      loadSavedTasks();

      // 然後在後台同步任務（不阻塞 UI）
      const userId = localStorage.getItem('user_id');
      const isAuthenticated = localStorage.getItem('isAuthenticated') === 'true';

      if (userId && isAuthenticated) {
        // 使用 setTimeout 讓同步操作在下一幀執行，不阻塞初始渲染
        setTimeout(async () => {
        console.log('[Sidebar] User authenticated, syncing tasks from backend');
        try {
          const { syncTasksBidirectional } = await import('../lib/taskStorage');
          const result = await syncTasksBidirectional();
          console.log('[Sidebar] Tasks synced:', result);
            // 同步完成後，重新加載任務列表
            loadSavedTasks();
        } catch (error) {
          console.error('[Sidebar] Failed to sync tasks on init:', error);
        }
        }, 100); // 100ms 延遲，確保初始渲染完成
      }
    };

    initializeTasks();

    // 監聽任務創建事件，重新加載任務列表
    const handleTaskCreated = () => {
      loadSavedTasks();
    };

    // 修改時間：2025-12-21 - 監聽任務更新事件（用於更新任務標題）
    const handleTaskUpdated = () => {
      console.log('[Sidebar] Task updated, reloading task list');
      loadSavedTasks();
    };

    // 修改時間：2025-12-08 09:04:21 UTC+8 - 監聽任務同步事件
    const handleTasksSynced = () => {
      console.log('[Sidebar] Tasks synced, reloading task list');
      loadSavedTasks();
    };

    // 修改時間：2025-12-08 09:04:21 UTC+8 - 監聽用戶登錄事件，觸發任務同步
    const handleUserLoggedIn = async () => {
      console.log('[Sidebar] User logged in, syncing tasks');
      try {
        const { syncTasksBidirectional } = await import('../lib/taskStorage');
        await syncTasksBidirectional();
        loadSavedTasks();
      } catch (error) {
        console.error('[Sidebar] Failed to sync tasks on login:', error);
      }
    };

    window.addEventListener('taskCreated', handleTaskCreated as EventListener);
    window.addEventListener('taskUpdated', handleTaskUpdated as EventListener); // 修改時間：2025-12-21 - 監聽任務更新事件
    window.addEventListener('storage', loadSavedTasks);
    window.addEventListener('tasksSynced', handleTasksSynced as EventListener);
    window.addEventListener('userLoggedIn', handleUserLoggedIn as EventListener);

    return () => {
      window.removeEventListener('taskCreated', handleTaskCreated as EventListener);
      window.removeEventListener('taskUpdated', handleTaskUpdated as EventListener); // 修改時間：2025-12-21 - 移除任務更新事件監聽
      window.removeEventListener('storage', loadSavedTasks);
      window.removeEventListener('tasksSynced', handleTasksSynced as EventListener);
      window.removeEventListener('userLoggedIn', handleUserLoggedIn as EventListener);
    };
  }, []);

  // 修改時間：2025-01-27 - 移除硬編碼的示範任務，只顯示真實任務
  // 修改時間：2025-12-09 - 只顯示 task_status 為 activate 的任務（或未設置 task_status 的任務，兼容舊數據）
  // 修改時間：2026-01-06 - 添加顏色和歸檔篩選功能
  // 使用 useMemo 确保语言变更时重新计算任务数据
  const tasks: Task[] = useMemo(() => {
    // 修改時間：2026-01-06 - 確保任務列表沒有重複（雙重保險）
    const uniqueSavedTasks = savedTasks.reduce((acc: Task[], task: Task) => {
      const existingTask = acc.find(t => String(t.id) === String(task.id));
      if (!existingTask) {
        acc.push(task);
      }
      return acc;
    }, []);

    const filtered = uniqueSavedTasks.filter(task => {
      // 根據歸檔篩選器過濾任務狀態
      if (showArchivedFilter) {
        // 顯示歸檔的任務
        if (task.task_status !== 'archive') {
          return false;
        }
      } else {
        // 顯示激活的任務（或未設置 task_status 的任務，兼容舊數據）
        if (task.task_status && task.task_status !== 'activate') {
          return false;
        }
      }

      // 根據顏色篩選器過濾任務
      if (selectedColorFilter !== null) {
        // 如果選擇了顏色篩選，只顯示匹配顏色的任務
        if (selectedColorFilter === 'none') {
          // 顯示沒有顏色標籤的任務
          if (task.label_color) {
            return false;
          }
        } else {
          // 顯示匹配指定顏色的任務
          if (task.label_color !== selectedColorFilter) {
            return false;
      }
        }
      }

      return true;
    });
    // 修改時間：2026-01-06 - 按最近日期排序（創建時間或更新時間，取較新的）
    const sorted = filtered.sort((a, b) => {
      // 獲取任務的最近時間（優先使用 updated_at，如果沒有則使用 created_at）
      const getLatestTime = (task: Task): number => {
        // 優先使用 updated_at
        if (task.updated_at) {
          return new Date(task.updated_at).getTime();
        }
        // 其次使用 created_at
        if (task.created_at) {
          return new Date(task.created_at).getTime();
        }
        // 如果都沒有，使用 dueDate（向後兼容）
        if (task.dueDate) {
          return new Date(task.dueDate).getTime();
        }
        // 最後回退到 0（最舊）
        return 0;
      };

      const timeA = getLatestTime(a);
      const timeB = getLatestTime(b);

      // 降序排序（最新的在前）
      return timeB - timeA;
    });

    console.log('[Sidebar] Tasks memo updated:', {
      savedTasksCount: savedTasks.length,
      filteredCount: filtered.length,
      sortedCount: sorted.length,
      colorFilter: selectedColorFilter,
      showArchived: showArchivedFilter,
      firstFiveTasks: sorted.slice(0, 5).map(t => ({
        id: t.id,
        title: t.title,
        created_at: t.created_at,
        updated_at: t.updated_at,
        latestTime: t.updated_at || t.created_at || t.dueDate
      }))
    });
    return sorted;
  }, [language, updateCounter, savedTasks, selectedColorFilter, showArchivedFilter]);

  // 使用 useMemo 缓存所有直接使用的翻译文本，确保语言变更时正确更新
  const translations = useMemo(() => {
    return {
      favorites: t('sidebar.favorites'),
      tasks: t('sidebar.tasks'),
      addTask: t('sidebar.addTask'),
      browse: t('sidebar.browse'),
      browseAssistants: t('sidebar.browseAssistants'),
      browseAgents: t('sidebar.browseAgents'),
      toggleExpand: t('sidebar.toggle.expand'),
      toggleCollapse: t('sidebar.toggle.collapse'),
      user: t('sidebar.user'),
      userEmail: t('sidebar.user.email'),
      inputPlaceholder: t('sidebar.input.placeholder'),
      buttonAdd: t('sidebar.button.add'),
      buttonCancel: t('sidebar.button.cancel'),
    };
  }, [language, updateCounter]);

  // 修改時間：2026-01-06 - 計算響應式顯示限制
  useEffect(() => {
    const calculateDisplayLimits = () => {
      if (!contentAreaRef.current || collapsed) {
        // 如果收合狀態，不限制顯示
        setMaxFavoritesDisplay(favorites.length);
        setMaxTasksDisplay(tasks.length);
        setShowMoreFavorites(false);
        setShowMoreTasks(false);
        return;
      }

      const contentArea = contentAreaRef.current;
      const availableHeight = contentArea.clientHeight;

      // 估算每個項目的高度
      // 收藏項：約 40px (p-2 rounded-lg + mb-1)
      // 任務項：約 60px (包含標題和日期兩行)
      // 標題區域：約 40px (收藏標題) + 40px (任務標題，如果任務區域展開)
      // 瀏覽區域：約 120px (如果顯示)
      // 新增任務按鈕：約 40px (如果任務區域展開)
      const favoriteItemHeight = 40;
      const taskItemHeight = 60;
      const favoritesHeaderHeight = 40;
      const tasksHeaderHeight = expandedSections.tasks ? 40 : 0;
      const addTaskButtonHeight = expandedSections.tasks ? 40 : 0;
      const browseSectionHeight = favorites.length > 0 ? 120 : 0;
      const padding = 16; // p-2 = 8px * 2

      // 計算已使用的固定高度
      const fixedHeight = favoritesHeaderHeight + tasksHeaderHeight + addTaskButtonHeight + browseSectionHeight + padding;

      // 可用於顯示項目的高度
      const availableItemHeight = availableHeight - fixedHeight;

      // 限制收藏最多10筆
      const maxFavorites = Math.min(10, favorites.length);
      const favoritesHeight = maxFavorites * favoriteItemHeight;

      // 計算剩餘可用高度用於任務（僅當任務區域展開時）
      let maxTasks: number | null = null;
      if (expandedSections.tasks) {
        const remainingHeight = availableItemHeight - favoritesHeight;
        // 計算可顯示的任務數量
        maxTasks = Math.max(0, Math.floor(remainingHeight / taskItemHeight));
      } else {
        // 如果任務區域收合，不限制任務顯示
        maxTasks = tasks.length;
      }

      // 設置顯示限制
      setMaxFavoritesDisplay(maxFavorites);
      setMaxTasksDisplay(maxTasks !== null && maxTasks > 0 ? maxTasks : null);
      setShowMoreFavorites(favorites.length > maxFavorites);
      setShowMoreTasks(expandedSections.tasks && maxTasks !== null && tasks.length > maxTasks);
    };

    // 初始計算
    calculateDisplayLimits();

    // 監聽窗口大小變化
    const handleResize = () => {
      calculateDisplayLimits();
    };

    window.addEventListener('resize', handleResize);

    // 使用 ResizeObserver 監聽內容區域大小變化
    const resizeObserver = new ResizeObserver(() => {
      calculateDisplayLimits();
    });

    if (contentAreaRef.current) {
      resizeObserver.observe(contentAreaRef.current);
    }

    return () => {
      window.removeEventListener('resize', handleResize);
      resizeObserver.disconnect();
    };
  }, [favorites.length, tasks.length, collapsed, expandedSections.tasks]);



  // 添加新任务 - 直接创建任务，不需要输入标题
  const handleAddTask = () => {
    // 修改時間：2026-01-06 - 記錄創建時間和更新時間（ISO 8601 格式）
    const now = new Date().toISOString();

    // 直接创建新任务，使用默认标题（后续聊天时会自动生成）
    // 代理和助理初始化为 undefined（显示"選擇代理"和"選擇助理"）
    // 模型初始化为"自動"
    const newTask: Task = {
      id: Date.now(), // 临时 ID，实际应该由后端生成
      title: t('sidebar.newTask', '新任務'), // 默认标题，后续会自动更新
      status: 'in-progress',
      task_status: 'activate', // 修改時間：2025-12-09 - 默認設置為 activate
      dueDate: new Date().toISOString().split('T')[0],
      created_at: now, // 修改時間：2026-01-06 - 記錄創建時間
      updated_at: now, // 修改時間：2026-01-06 - 記錄更新時間（初始與創建時間相同）
      messages: [],
      executionConfig: {
        mode: 'free', // 默认自由模式
        // agentId 和 assistantId 不设置，保持 undefined
        // 这样 ChatInput 会显示"選擇代理"和"選擇助理"
      },
      fileTree: [], // 初始化文件樹為空
    };

    // 設置焦點到新任務
    setActiveSection('tasks');
    setActiveItemId(newTask.id);

    // 通知父组件创建新任务
    if (onTaskSelect) {
      onTaskSelect(newTask);
    }

  };

  // 处理任务点击
  const handleTaskClick = (task: Task) => {
    setActiveSection('tasks');
    setActiveItemId(task.id); // 设置选中的任务 ID

    // 修改時間：2025-12-09 - 只在本地保存，不觸發後端同步（避免 409 錯誤）
    // 點擊任務時不需要立即同步到後端，只有在任務內容發生變化時才同步
    saveTask(task, false); // 不觸發後端同步

    // 如果有文件樹，創建模擬文件記錄
    if (task.fileTree && task.fileTree.length > 0) {
      const userId = localStorage.getItem('userEmail') || undefined;
      saveMockFiles(String(task.id), task.fileTree, userId);
    }


    if (onTaskSelect) {
      onTaskSelect(task);
    }
  };

  // 修改時間：2025-12-08 14:00:00 UTC+8 - 處理歷史任務右鍵菜單
  const handleTaskContextMenu = (e: React.MouseEvent, task: Task) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      task,
    });
  };

  // 關閉右鍵菜單
  const closeContextMenu = () => {
    // 清除顏色菜單的延遲計時器
    if (colorMenuTimeoutRef.current) {
      clearTimeout(colorMenuTimeoutRef.current);
      colorMenuTimeoutRef.current = null;
    }
    // 關閉顏色菜單
    setShowColorMenu(false);
    setColorMenuPosition(null);
    // 關閉右鍵菜單
    setContextMenu(null);
  };

  // 修改時間：2026-01-06 - 處理收藏夾項目右鍵菜單
  const handleFavoriteContextMenu = (e: React.MouseEvent, favorite: FavoriteItem) => {
    e.preventDefault();
    e.stopPropagation();
    setFavoriteContextMenu({
      x: e.clientX,
      y: e.clientY,
      favorite,
    });
  };

  // 修改時間：2026-01-06 - 關閉收藏夾項目右鍵菜單
  const closeFavoriteContextMenu = () => {
    setFavoriteContextMenu(null);
  };

  // 修改時間：2026-01-06 - 處理取消收藏（支持任務、助理、代理）
  const handleRemoveFavorite = () => {
    if (!favoriteContextMenu) return;

    try {
      const favorite = favoriteContextMenu.favorite;
      console.log('[Sidebar] Removing favorite:', { id: favorite.id, type: favorite.type, itemId: favorite.itemId });

      // 使用通用函數移除收藏（支持所有類型：任務、助理、代理）
      removeFavorite(favorite.id, favorite.itemId, favorite.type);

      // 重新加載收藏夾
      const updatedFavorites = getFavorites();
      console.log('[Sidebar] Favorites updated:', { count: updatedFavorites.length });
      setFavorites(updatedFavorites);

      // 觸發收藏夾更新事件
      window.dispatchEvent(new CustomEvent('favoritesUpdated'));

      // 關閉右鍵菜單
      closeFavoriteContextMenu();
    } catch (error) {
      console.error('[Sidebar] Failed to remove favorite:', error);
      alert('取消收藏失敗');
    }
  };

  // 處理右鍵菜單點擊外部關閉
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (contextMenuRef.current && !contextMenuRef.current.contains(e.target as Node)) {
        closeContextMenu();
      }
      // 修改時間：2026-01-06 - 處理收藏夾項目右鍵菜單點擊外部關閉
      if (favoriteContextMenuRef.current && !favoriteContextMenuRef.current.contains(e.target as Node)) {
        closeFavoriteContextMenu();
      }
    };

    if (contextMenu || favoriteContextMenu) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [contextMenu, favoriteContextMenu]);

  // 處理 ESC 鍵關閉菜單
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (contextMenu) {
        closeContextMenu();
        }
        // 修改時間：2026-01-06 - ESC 鍵也可以關閉收藏夾項目右鍵菜單
        if (favoriteContextMenu) {
          closeFavoriteContextMenu();
        }
        // 修改時間：2026-01-06 - ESC 鍵也可以關閉更多列表 Modal
        if (showMoreModal) {
          setShowMoreModal(false);
        }
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [contextMenu, favoriteContextMenu, showMoreModal]);

  // 查看任務資訊
  const handleViewTaskInfo = async () => {
    if (!contextMenu) return;

    try {
      // 嘗試從後台獲取任務信息
      const taskId = String(contextMenu.task.id);
      const response = await getUserTask(taskId);

      if (response.success && response.data) {
        // 轉換後台任務格式為前端任務格式
        const backendTask = response.data;
        const frontendTask: Task = {
          id: parseInt(backendTask.task_id) || contextMenu.task.id,
          title: backendTask.title || contextMenu.task.title,
          status: contextMenu.task.status,
          dueDate: backendTask.created_at?.split('T')[0] || contextMenu.task.dueDate,
          messages: contextMenu.task.messages,
          executionConfig: contextMenu.task.executionConfig,
          fileTree: contextMenu.task.fileTree,
        };
        setTaskInfo(frontendTask);
      } else {
        // 如果後台沒有，使用本地任務信息
        setTaskInfo(contextMenu.task);
      }
      setShowTaskInfoModal(true);
    } catch (error) {
      console.error('Failed to get task info:', error);
      // 如果出錯，使用本地任務信息
      setTaskInfo(contextMenu.task);
      setShowTaskInfoModal(true);
    }

    closeContextMenu();
    // 修改時間：2026-01-06 - 如果在 Modal 中打開任務資訊，關閉更多列表 Modal
    if (showMoreModal) {
      setShowMoreModal(false);
    }
  };

  // 修改時間：2025-12-09 - 任務歸檔，設置 task_status 為 archive
  const handleArchiveTask = async () => {
    if (!contextMenu) return;

    try {
      const taskId = String(contextMenu.task.id);
      // 更新任務狀態為歸檔
      const update = {
        task_status: 'archive' as const, // 設置任務顯示狀態為 archive
      };

      // 嘗試更新後台
      try {
        await updateUserTask(taskId, update);
      } catch (error) {
        console.warn('Failed to update task in backend, updating locally:', error);
      }

      // 更新本地任務
      // 修改時間：2026-01-06 - 更新時記錄 updated_at 時間
      const now = new Date().toISOString();
      const updatedTask: Task = {
        ...contextMenu.task,
        task_status: 'archive', // 設置任務顯示狀態為 archive
        created_at: contextMenu.task.created_at || now, // 保持原有創建時間，如果沒有則使用當前時間
        updated_at: now, // 更新時間設為當前時間
      };
      saveTask(updatedTask, false); // 不觸發後端同步（已經手動更新了）

      // 從列表中移除（因為只顯示 activate 的任務）
      const updatedTasks = savedTasks.filter(t => t.id !== contextMenu.task.id);
      setSavedTasks(updatedTasks);

      alert('任務已歸檔');
    } catch (error) {
      console.error('Failed to archive task:', error);
      alert('歸檔任務失敗');
    }

    closeContextMenu();
    // 修改時間：2026-01-06 - 如果在 Modal 中歸檔任務，關閉更多列表 Modal
    if (showMoreModal) {
      setShowMoreModal(false);
    }
  };

  // 修改時間：2025-12-09 - 處理收藏/取消收藏
  const handleToggleFavorite = () => {
    if (!contextMenu) return;

    try {
      const task = contextMenu.task;
      const isFavorite = isTaskFavorite(typeof task.id === 'number' ? task.id : Number(task.id));

      if (isFavorite) {
        // 取消收藏
        removeTaskFromFavorites(typeof task.id === 'number' ? task.id : Number(task.id));
      } else {
        // 收藏
        addTaskToFavorites(task);
      }

      // 重新加載收藏夾
      const updatedFavorites = getFavorites();
      setFavorites(updatedFavorites);

      // 觸發收藏夾更新事件
      window.dispatchEvent(new CustomEvent('favoritesUpdated'));

      // 關閉右鍵菜單
      closeContextMenu();
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
      alert('操作失敗');
    }
  };

  // 修改時間：2025-12-09 - 處理顏色選擇
  const handleColorSelect = async (colorValue: string | null) => {
    if (!contextMenu) return;

    try {
      const taskId = String(contextMenu.task.id);
      // 更新任務顏色標籤
      const update = {
        label_color: colorValue, // 設置任務顏色標籤
      };

      // 嘗試更新後台
      try {
        await updateUserTask(taskId, update);
      } catch (error) {
        console.warn('Failed to update task color in backend, updating locally:', error);
      }

      // 更新本地任務
      // 修改時間：2026-01-06 - 更新時記錄 updated_at 時間
      const now = new Date().toISOString();
      const updatedTask: Task = {
        ...contextMenu.task,
        label_color: colorValue || undefined, // 設置任務顏色標籤
        created_at: contextMenu.task.created_at || now, // 保持原有創建時間，如果沒有則使用當前時間
        updated_at: now, // 更新時間設為當前時間
      };
      saveTask(updatedTask, false); // 不觸發後端同步（已經手動更新了）

      // 重新加載任務列表
      const loadedTasks = getAllTasks();
      setSavedTasks(loadedTasks);

      // 清除延遲計時器
      if (colorMenuTimeoutRef.current) {
        clearTimeout(colorMenuTimeoutRef.current);
        colorMenuTimeoutRef.current = null;
      }
      // 關閉顏色選擇菜單和右鍵菜單
      setShowColorMenu(false);
      setColorMenuPosition(null);
      closeContextMenu();
    } catch (error) {
      console.error('Failed to update task color:', error);
      alert('更新任務顏色失敗');
    }
  };

  // 修改時間：2025-01-27 - 處理任務重新命名
  const handleRenameTask = () => {
    if (!contextMenu) return;
    setRenameTaskTarget(contextMenu.task);
    setRenameInput(contextMenu.task.title);
    setShowRenameModal(true);
    closeContextMenu();
    // 修改時間：2026-01-06 - 如果在 Modal 中打開重命名，關閉更多列表 Modal
    if (showMoreModal) {
      setShowMoreModal(false);
    }
  };

  // 修改時間：2025-01-27 - 確認任務重新命名
  const handleRenameConfirm = async () => {
    if (!renameTaskTarget || !renameInput.trim() || renameInput.trim() === renameTaskTarget.title) {
      return;
    }

    try {
      const taskId = String(renameTaskTarget.id);
      const newTitle = renameInput.trim();

      // 更新後端任務名稱
      try {
        await updateUserTask(taskId, {
          title: newTitle,
        });
        console.log('[Sidebar] Task renamed in backend', { taskId, newTitle });
      } catch (error: any) {
        console.error('[Sidebar] Failed to rename task in backend:', error);
        alert(`更新任務名稱失敗: ${error.message || '未知錯誤'}`);
        return;
      }

      // 更新本地任務
      // 修改時間：2026-01-06 - 更新時記錄 updated_at 時間
      const now = new Date().toISOString();
      const updatedTask: Task = {
        ...renameTaskTarget,
        title: newTitle,
        created_at: renameTaskTarget.created_at || now, // 保持原有創建時間，如果沒有則使用當前時間
        updated_at: now, // 更新時間設為當前時間
      };
      saveTask(updatedTask, false); // 不觸發後端同步（已經手動更新了）

      // 如果重命名的是當前選中的任務，更新選中狀態
      if (selectedTask && selectedTask.id === renameTaskTarget.id) {
        if (onTaskSelect) {
          onTaskSelect(updatedTask);
        }
      }

      // 重新加載任務列表
      const loadedTasks = getAllTasks();
      setSavedTasks(loadedTasks);

      // 觸發任務更新事件
      window.dispatchEvent(new CustomEvent('taskUpdated', { detail: { taskId: renameTaskTarget.id } }));

      alert('任務名稱已更新');
    } catch (error: any) {
      console.error('[Sidebar] Failed to rename task:', error);
      alert(`更新任務名稱失敗: ${error.message || '未知錯誤'}`);
    }

    setShowRenameModal(false);
    setRenameTaskTarget(null);
    setRenameInput('');
  };

  // 修改時間：2025-01-27 - 取消任務重新命名
  const handleRenameCancel = () => {
    setShowRenameModal(false);
    setRenameTaskTarget(null);
    setRenameInput('');
  };

  // 刪除任務
  const handleDeleteTask = () => {
    if (!contextMenu) return;
    setDeleteTaskTarget(contextMenu.task);
    setShowDeleteModal(true);
    closeContextMenu();
    // 修改時間：2026-01-06 - 如果在 Modal 中打開刪除確認，關閉更多列表 Modal
    if (showMoreModal) {
      setShowMoreModal(false);
    }
  };

  // 確認刪除任務
  const handleConfirmDelete = async () => {
    if (!deleteTaskTarget) return;

    // 修改時間：2025-12-08 14:15:00 UTC+8 - 驗證輸入的 DELETE 文本
    if (deleteConfirmText !== 'DELETE') {
      alert('請輸入大寫 "DELETE" 以確認刪除');
      return;
    }

    try {
      const taskId = String(deleteTaskTarget.id);

      // 修改時間：2025-12-08 14:15:00 UTC+8 - 調用後台刪除 API（會清除所有相關數據）
      // 修改時間：2026-01-06 - 改進錯誤處理：如果後端任務不存在（404），仍然允許刪除本地任務
      try {
        const result = await deleteUserTask(taskId);
        if (!result.success) {
          // 如果不是 404 錯誤（任務不存在），才拋出錯誤
          // 404 錯誤表示任務在後端不存在，可能是本地任務或已被刪除，允許繼續刪除本地任務
          if (!result.message?.includes('not found') && !result.message?.includes('404')) {
            throw new Error(result.message || '刪除任務失敗');
          } else {
            console.warn('[Sidebar] Task not found in backend, deleting locally only', { taskId });
          }
        }
      } catch (error: any) {
        // 檢查是否為 404 錯誤（任務不存在）
        const isNotFoundError =
          error?.status === 404 ||
          error?.message?.includes('404') ||
          error?.message?.includes('not found') ||
          error?.message?.includes('Task not found');

        if (isNotFoundError) {
          // 任務在後端不存在，可能是本地任務或已被刪除，允許繼續刪除本地任務
          console.warn('[Sidebar] Task not found in backend (404), deleting locally only', {
            taskId,
            error: error.message
          });
        } else {
          // 其他錯誤（如網絡錯誤、權限錯誤等），顯示錯誤但不阻止刪除本地任務
          console.error('[Sidebar] Failed to delete task from backend, deleting locally only', {
            taskId,
            error: error.message
          });
          // 不 return，繼續執行本地刪除
        }
      }

      // 從本地刪除（無論後端刪除是否成功）
      deleteTask(deleteTaskTarget.id);

      // 如果刪除的是當前選中的任務，清除選中狀態
      if (activeItemId === deleteTaskTarget.id) {
        setActiveItemId(null);
        if (onTaskSelect) {
          // 可以選擇不傳遞任務，或者傳遞 null
          // onTaskSelect(null as any);
        }
      }

      // 修改時間：2025-12-09 - 從收藏夾中移除已刪除的任務
      removeTaskFromFavorites(typeof deleteTaskTarget.id === 'number' ? deleteTaskTarget.id : Number(deleteTaskTarget.id));
      const updatedFavorites = getFavorites();
      setFavorites(updatedFavorites);
      window.dispatchEvent(new CustomEvent('favoritesUpdated'));

      // 觸發任務刪除事件
      window.dispatchEvent(new CustomEvent('taskDeleted', { detail: { taskId: deleteTaskTarget.id } }));

      // 重新加載任務列表
      const loadedTasks = getAllTasks();
      // 修改時間：2025-01-27 - 不再過濾任務
      setSavedTasks(loadedTasks);

      alert('任務已刪除');
    } catch (error: any) {
      console.error('Failed to delete task:', error);
      alert(`刪除任務失敗: ${error.message || '未知錯誤'}`);
    }

    setShowDeleteModal(false);
    setDeleteTaskTarget(null);
    setDeleteConfirmText('');
  };

  // 处理收藏项点击
  const handleFavoriteClick = (favorite: FavoriteItem) => {
    setActiveSection('favorites');
    setActiveItemId(favorite.id);

    switch (favorite.type) {
      case 'task':
        // 查找对应的任务
        const task = savedTasks.find(t => String(t.id) === favorite.itemId);
        if (task) {
          handleTaskClick(task);
        } else {
          // 如果任務不存在，從收藏夾中移除
          removeTaskFromFavorites(typeof favorite.itemId === 'number' ? favorite.itemId : Number(favorite.itemId));
          const updatedFavorites = getFavorites();
          setFavorites(updatedFavorites);
          window.dispatchEvent(new CustomEvent('favoritesUpdated'));
        }
        break;
      case 'assistant':
        // 调用助理选择回调
        if (onAssistantSelect) {
          onAssistantSelect(String(favorite.itemId));
        }
        break;
      case 'agent':
        // 调用代理选择回调
        if (onAgentSelect) {
          onAgentSelect(String(favorite.itemId));
        }
        break;
    }
  };

  // 切换区域展开/收合状态
  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // 修改時間：2026-01-06 - 處理打開更多列表 Modal
  const handleShowMore = (type: 'favorites' | 'tasks') => {
    setMoreModalType(type);
    setShowMoreModal(true);
  };

  // 修改時間：2026-01-06 - 處理關閉更多列表 Modal
  const handleCloseMoreModal = () => {
    setShowMoreModal(false);
    // 重置篩選和搜尋狀態
    setModalSearchText('');
    setModalColorFilter(null);
    setModalShowArchived(false);
  };

  return (
    <div className={cn(
      "h-full bg-secondary border-r border-primary flex flex-col transition-all duration-300 theme-transition",
      collapsed ? "w-16" : "w-64"
    )}>
      {/* 侧边栏头部 */}
      <div className="p-4 border-b border-primary flex items-center justify-between">
        {!collapsed && (
          <div className="flex items-center bg-transparent">
            <img
              src={
                browseMode === 'assistants'
                  ? "/SmartQ-LAS.svg"
                  : browseMode === 'agents'
                  ? "/SmartQ.-HCI.svg"
                  : "/SmartQ-IEE.svg" // 默认显示 SmartQ-IEE（一般情况）
              }
              alt={
                browseMode === 'assistants'
                  ? "SmartQ-LAS Logo"
                  : browseMode === 'agents'
                  ? "SmartQ-HCI Logo"
                  : "SmartQ-IEE Logo"
              }
              className="h-8 transition-opacity duration-300"
              style={{
                backgroundColor: 'transparent',
                mixBlendMode: 'normal',
                display: 'block'
              }}
            />
          </div>
        )}
        <button
          onClick={onToggle}
          className="p-2 rounded-full hover:bg-tertiary transition-colors"
          aria-label={collapsed ? translations.toggleExpand : translations.toggleCollapse}
          title={collapsed ? translations.toggleExpand : translations.toggleCollapse}
        >
          <i className={`fa-solid ${collapsed ? 'fa-chevron-right' : 'fa-chevron-left'}`}></i>
        </button>
      </div>

      {/* 侧边栏内容 - 確保可滾動 */}
      <div ref={contentAreaRef} className="flex-1 overflow-y-auto overflow-x-hidden p-2 min-h-0 custom-scrollbar">
        {/* 收藏夹 */}
        <div className="mb-4" key={`favorites-section-${language}-${updateCounter}`}>
          <div className="flex items-center mb-2">
           {!collapsed && (
             <span key={`favorites-label-${language}-${updateCounter}`} className="text-sm font-medium text-yellow-400/80">
               {translations.favorites}
             </span>
           )}
            <i className="fa-solid fa-bookmark ml-2 text-yellow-500"></i>
          </div>
           {favorites.slice(0, collapsed ? favorites.length : maxFavoritesDisplay).map(item => {
              // 根据类型确定图标和颜色
              const getIcon = () => {
                if (item.icon) {
                  return `fa-solid ${item.icon}`;
                }
                switch (item.type) {
                  case 'task':
                    return 'fa-solid fa-tasks';
                  case 'assistant':
                    return 'fa-solid fa-robot';
                  case 'agent':
                    return 'fa-solid fa-user-tie';
                  default:
                    return 'fa-solid fa-star';
                }
              };

              const getColorClass = () => {
                switch (item.type) {
                  case 'task':
                    return 'text-orange-400';
                  case 'assistant':
                    return 'text-purple-400';
                  case 'agent':
                    return 'text-green-400';
                  default:
                    return 'text-yellow-400';
                }
              };

              return (
              <button
                key={item.id}
                className={`w-full text-left p-2 rounded-lg flex items-center transition-all duration-200 mb-1
                  ${activeSection === 'favorites' && activeItemId === item.id
                    ? 'bg-yellow-500/20 text-yellow-400 border-l-2 border-yellow-500 shadow-sm'
                    : 'hover:bg-yellow-500/10 hover:text-yellow-300 hover:border-l-2 hover:border-yellow-500/50'}`}
                  onClick={() => handleFavoriteClick(item)}
                  onContextMenu={(e) => handleFavoriteContextMenu(e, item)}
              >
                {!collapsed ? (
                    <>
                      <i className={`${getIcon()} mr-2 ${getColorClass()}`}></i>
                  <span className="text-sm">{item.name}</span>
                    </>
                ) : (
                    <i className={`${getIcon()} ${getColorClass()}`}></i>
                )}
              </button>
              );
            })}

            {/* 修改時間：2026-01-06 - 顯示"更多收藏..."提示（可點擊） */}
            {!collapsed && showMoreFavorites && (
              <button
                className="w-full text-xs text-tertiary text-center py-2 px-2 hover:text-yellow-400 hover:bg-yellow-500/10 rounded-lg transition-all duration-200 cursor-pointer"
                onClick={() => handleShowMore('favorites')}
              >
                更多收藏...
              </button>
            )}

            {/* 浏览区域 */}
            {!collapsed && (
              <div className="mt-3 pt-3 border-t border-primary/30">
                <div className="text-xs text-tertiary mb-2 px-2">{t('sidebar.browse')}</div>
                <button
                  className="w-full text-left p-2 rounded-lg flex items-center transition-all duration-200 mb-1 hover:bg-yellow-500/10 hover:text-yellow-300 hover:border-l-2 hover:border-yellow-500/50 hover:shadow-lg hover:shadow-yellow-500/20"
                  onClick={() => {
                    if (onBrowseAssistants) {
                      onBrowseAssistants();
                    }
                  }}
                >
                  <i className="fa-solid fa-robot mr-2 text-purple-400"></i>
                  <span className="text-sm">{t('sidebar.browseAssistants')}</span>
                </button>
                <button
                  className="w-full text-left p-2 rounded-lg flex items-center transition-all duration-200 mb-1 hover:bg-yellow-500/10 hover:text-yellow-300 hover:border-l-2 hover:border-yellow-500/50 hover:shadow-lg hover:shadow-yellow-500/20"
                  onClick={() => {
                    if (onBrowseAgents) {
                      onBrowseAgents();
                    }
                  }}
                >
                  <i className="fa-solid fa-user-tie mr-2 text-green-400"></i>
                  <span className="text-sm">{t('sidebar.browseAgents')}</span>
                </button>
              </div>
            )}
        </div>

        {/* 任务区块 - 可收合 */}
        <div className="mb-4" key={`tasks-section-${language}-${updateCounter}`}>
          <button
            className="w-full flex items-center justify-between mb-2 p-2 rounded-lg hover:bg-orange-500/10 hover:text-orange-300 transition-all duration-200"
            onClick={() => {
              toggleSection('tasks');
              setActiveSection('tasks'); // 点击任务区域标题时，设置 activeSection 为 'tasks'
            }}
          >
             <div className="flex items-center">
               {!collapsed && <span key={`tasks-label-${language}-${updateCounter}`} className="text-sm font-medium text-orange-400/80">{translations.tasks}</span>}
               <i className="fa-solid fa-tasks ml-2 text-orange-500"></i>
             </div>
            {!collapsed && (
              <i className={`fa-solid fa-chevron-down transition-transform ${expandedSections.tasks ? 'rotate-0' : 'rotate-180'}`}></i>
            )}
          </button>

          {/* 任务区域内容 */}
          {expandedSections.tasks && (
            <>
              {/* 新增任务按钮 - 直接创建任务，不需要输入框 */}
              {!collapsed && (
                <button
                  className="w-full text-left p-2 rounded-lg flex items-center justify-between hover:bg-orange-500/10 hover:text-orange-300 transition-all duration-200 mb-2"
                  onClick={handleAddTask}
                >
                   <div className="flex items-center">
                     <i className="fa-solid fa-plus-circle mr-2 text-orange-500"></i>
                     <span className="text-sm">{translations.addTask}</span>
                   </div>
                </button>
              )}

              {/* 历史任务列表 */}
              {(collapsed ? tasks : (maxTasksDisplay !== null ? tasks.slice(0, maxTasksDisplay) : tasks)).map(task => {
                return (
                  <button
                    key={task.id}
                    className={`w-full text-left p-2 rounded-lg flex items-center transition-all duration-200 mb-1 cursor-pointer
                      ${activeSection === 'tasks' && activeItemId === task.id
                        ? 'bg-orange-500/20 text-orange-300 border-l-2 border-orange-500 shadow-sm'
                        : 'hover:bg-orange-500/10 hover:text-orange-300 hover:border-l-2 hover:border-orange-500/50'}`}
                    onClick={() => handleTaskClick(task)}
                    onContextMenu={(e) => handleTaskContextMenu(e, task)}
                  >
                    {!collapsed ? (
                      <>
                        {/* 修改時間：2025-12-09 - 使用圓形圖標，根據 label_color 顯示顏色 */}
                        <div className="relative mr-2 flex-shrink-0">
                          {task.label_color ? (
                            <div
                              className="w-3 h-3 rounded-full border-2"
                              style={{
                                backgroundColor: labelColors.find(c => c.value === task.label_color)?.color || task.label_color,
                                borderColor: labelColors.find(c => c.value === task.label_color)?.color || task.label_color,
                              }}
                            />
                          ) : (
                            <i className="fa-regular fa-circle text-tertiary text-xs"></i>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm truncate">{task.title}</div>
                          <div className="text-xs text-tertiary">{task.dueDate}</div>
                        </div>
                      </>
                    ) : (
                      <>
                        {/* 修改時間：2025-12-09 - 收合狀態下也顯示圓形圖標 */}
                        {task.label_color ? (
                          <div
                            className="w-2 h-2 rounded-full border"
                            style={{
                              backgroundColor: labelColors.find(c => c.value === task.label_color)?.color || task.label_color,
                              borderColor: labelColors.find(c => c.value === task.label_color)?.color || task.label_color,
                            }}
                          />
                        ) : (
                          <i className="fa-regular fa-circle text-tertiary text-xs"></i>
                        )}
                      </>
                    )}
                  </button>
                );
              })}

              {/* 修改時間：2026-01-06 - 顯示"更多任務..."提示（可點擊） */}
              {!collapsed && showMoreTasks && (
                <button
                  className="w-full text-xs text-tertiary text-center py-2 px-2 hover:text-orange-400 hover:bg-orange-500/10 rounded-lg transition-all duration-200 cursor-pointer"
                  onClick={() => handleShowMore('tasks')}
                >
                  更多任務...
                </button>
              )}

              {/* 修改時間：2026-01-06 - 任務篩選器（顏色和歸檔） */}
              {!collapsed && (
                <div className="mt-3 pt-3 border-t border-primary/30">
                  <div className="text-xs text-tertiary mb-2 px-2">篩選</div>

                  {/* 顏色和歸檔篩選器（同一排） */}
                  <div className="mb-3">
                    <div className="flex flex-nowrap gap-1.5 px-1 overflow-x-auto min-w-0 items-center" style={{ width: '100%' }}>
                      {/* 全部（清除顏色篩選） */}
                      <button
                        className={`w-[13.8px] h-[13.8px] rounded-full border flex-shrink-0 transition-all duration-200 flex items-center justify-center ${
                          selectedColorFilter === null
                            ? 'bg-orange-500/10 border-orange-500'
                            : 'border-gray-400 hover:border-orange-500/50'
                        }`}
                        style={{
                          backgroundColor: selectedColorFilter === null ? 'rgba(255, 149, 0, 0.1)' : 'transparent',
                          borderColor: selectedColorFilter === null ? '#FF9500' : '#9CA3AF',
                          minWidth: '13.8px',
                          maxWidth: '13.8px',
                        }}
                        onClick={() => setSelectedColorFilter(null)}
                        title="全部"
                      >
                        {selectedColorFilter === null && (
                          <i className="fa-solid fa-check text-orange-500 text-[6px]"></i>
                        )}
                      </button>

                      {/* 無顏色標籤 */}
                      <button
                        className={`w-[13.8px] h-[13.8px] rounded-full border flex-shrink-0 transition-all duration-200 flex items-center justify-center ${
                          selectedColorFilter === 'none'
                            ? 'bg-orange-500/10 border-orange-500'
                            : 'border-gray-400 hover:border-orange-500/50'
                        }`}
                        style={{
                          backgroundColor: selectedColorFilter === 'none' ? 'rgba(255, 149, 0, 0.1)' : 'transparent',
                          borderColor: selectedColorFilter === 'none' ? '#FF9500' : '#9CA3AF',
                          minWidth: '13.8px',
                          maxWidth: '13.8px',
                        }}
                        onClick={() => setSelectedColorFilter(selectedColorFilter === 'none' ? null : 'none')}
                        title="無顏色"
                      >
                        {selectedColorFilter === 'none' && (
                          <i className="fa-solid fa-check text-orange-500 text-[6px]"></i>
                        )}
                      </button>

                      {/* 各種顏色 */}
                      {labelColors.filter(c => c.value !== null).map((colorOption) => (
                        <button
                          key={colorOption.value}
                          className={`w-[13.8px] h-[13.8px] rounded-full border flex-shrink-0 transition-all duration-200 flex items-center justify-center ${
                            selectedColorFilter === colorOption.value
                              ? 'shadow-md border-orange-500'
                              : 'hover:shadow-sm'
                          }`}
                          style={{
                            backgroundColor: colorOption.color,
                            borderColor: selectedColorFilter === colorOption.value ? '#FF9500' : colorOption.color,
                            minWidth: '13.8px',
                            maxWidth: '13.8px',
                          }}
                          onClick={() => setSelectedColorFilter(selectedColorFilter === colorOption.value ? null : colorOption.value)}
                          title={colorOption.name}
                        >
                          {selectedColorFilter === colorOption.value && (
                            <i className="fa-solid fa-check text-white text-[6px] drop-shadow-md"></i>
                          )}
                        </button>
                      ))}

                      {/* 歸檔按鈕（與顏色同一排，默認不顯示激活） */}
                      <button
                        className={`ml-2 text-xs py-1 px-2 rounded-lg transition-all duration-200 flex items-center justify-center gap-1 flex-shrink-0 ${
                          showArchivedFilter
                            ? 'bg-orange-500/20 text-orange-300 border border-orange-500'
                            : 'bg-tertiary text-tertiary hover:bg-orange-500/10 hover:text-orange-300 border border-primary'
                        }`}
                        onClick={() => setShowArchivedFilter(!showArchivedFilter)}
                        title={showArchivedFilter ? '顯示激活任務' : '顯示歸檔任務'}
                      >
                        <i className="fa-solid fa-archive"></i>
                        {showArchivedFilter && <span className="ml-1">歸檔</span>}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

      </div>

      {/* 任務文件記錄入口 */}
      {!collapsed && (
        <div className="p-4 border-t border-primary">
          <button
            onClick={() => setShowFileRecordModal(true)}
            className="w-full text-left p-2 rounded-lg flex items-center gap-2 hover:bg-blue-500/10 hover:text-blue-300 transition-all duration-200"
          >
            <i className="fa-solid fa-folder-open text-blue-500"></i>
            <span className="text-sm">任務文件記錄</span>
          </button>
        </div>
      )}

      {/* 侧边栏底部 */}
      <div className="p-4 border-t border-primary relative" key={`sidebar-footer-${language}-${updateCounter}`}>
        <div className="flex items-center">
           {!collapsed && <div key={`user-info-${language}-${updateCounter}`}>
               <div className="text-sm font-medium">
                 {currentUser?.username || localStorage.getItem('userName') || translations.user}
               </div>
               <div className="text-xs text-tertiary">
                 {currentUser?.email || localStorage.getItem('userEmail') || translations.userEmail}
               </div>
            </div>}
          <button
            ref={userMenuButtonRef}
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center ml-auto cursor-pointer hover:bg-blue-700 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-secondary"
            aria-label="用戶菜單"
            title="用戶菜單"
          >
            {currentUser?.username ? (
              <span className="text-white text-xs font-medium">
                {currentUser.username.charAt(0).toUpperCase()}
              </span>
            ) : (
              <i className="fa-solid fa-user text-white text-sm"></i>
            )}
          </button>
        </div>

        {/* 用戶菜單 */}
        {showUserMenu && (
          <div className="absolute right-4" style={{ [collapsed ? 'top' : 'bottom']: '100%' }}>
            <UserMenu
              isOpen={showUserMenu}
              onClose={() => setShowUserMenu(false)}
              position={collapsed ? 'bottom' : 'top'}
            />
          </div>
        )}
      </div>

      {/* 歷史任務右鍵菜單 */}
      {contextMenu && (
        <div
          ref={contextMenuRef}
          className="fixed z-[100] bg-secondary border border-primary rounded-lg shadow-lg py-1 min-w-[180px] theme-transition"
          style={{
            left: `${contextMenu.x}px`,
            top: `${contextMenu.y}px`,
          }}
        >
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={handleViewTaskInfo}
          >
            <i className="fa-solid fa-info-circle w-4"></i>
            <span>查看任務資訊</span>
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={handleRenameTask}
          >
            <i className="fa-solid fa-pen w-4"></i>
            <span>任務重新命名</span>
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={handleArchiveTask}
          >
            <i className="fa-solid fa-archive w-4"></i>
            <span>任務歸檔</span>
          </button>
          {/* 修改時間：2025-12-09 - 添加收藏/取消收藏選項 */}
          {contextMenu && (() => {
            const taskId = typeof contextMenu.task.id === 'number' ? contextMenu.task.id : Number(contextMenu.task.id);
            const isFavorite = isTaskFavorite(taskId);
            return (
              <button
                className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
                onClick={handleToggleFavorite}
              >
                <i className={`${isFavorite ? 'fa-solid fa-heart text-red-500' : 'fa-regular fa-heart text-gray-400'} w-4`}></i>
                <span>{isFavorite ? '取消收藏' : '收藏'}</span>
              </button>
            );
          })()}
          {/* 修改時間：2025-12-09 - 添加標識顏色選項，支持懸停顯示顏色選擇子菜單 */}
          <div
            className="relative"
            onMouseEnter={() => {
              // 清除任何待處理的關閉計時器
              if (colorMenuTimeoutRef.current) {
                clearTimeout(colorMenuTimeoutRef.current);
                colorMenuTimeoutRef.current = null;
              }
              if (contextMenu) {
                // 計算子菜單位置，使其緊貼右鍵菜單右側
                setColorMenuPosition({ x: contextMenu.x + 200, y: contextMenu.y });
                setShowColorMenu(true);
              }
            }}
            onMouseLeave={(e) => {
              // 檢查滑鼠是否移動到子菜單
              const relatedTarget = e.relatedTarget as HTMLElement;
              const isMovingToSubMenu = relatedTarget && relatedTarget.closest('.fixed.bg-secondary');

              if (!isMovingToSubMenu) {
                // 延遲關閉，給用戶時間移動滑鼠到子菜單
                colorMenuTimeoutRef.current = setTimeout(() => {
                  setShowColorMenu(false);
                  colorMenuTimeoutRef.current = null;
                }, 300); // 300ms 延遲，給用戶更多時間
              }
            }}
          >
            <button
              className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            >
              <i className="fa-solid fa-tag w-4"></i>
              <span>標識顏色</span>
              <i className="fa-solid fa-chevron-right ml-auto text-xs"></i>
            </button>
            {/* 顏色選擇子菜單 */}
            {showColorMenu && colorMenuPosition && contextMenu && (
              <div
                className="fixed bg-secondary border border-primary rounded-lg shadow-lg p-2 z-[100] min-w-[180px]"
                style={{
                  left: `${colorMenuPosition.x}px`,
                  top: `${colorMenuPosition.y}px`,
                }}
                onMouseEnter={() => {
                  // 清除任何待處理的關閉計時器
                  if (colorMenuTimeoutRef.current) {
                    clearTimeout(colorMenuTimeoutRef.current);
                    colorMenuTimeoutRef.current = null;
                  }
                  setShowColorMenu(true);
                }}
                onMouseLeave={(e) => {
                  // 檢查滑鼠是否移動到父元素（標識顏色按鈕）
                  const relatedTarget = e.relatedTarget as HTMLElement;
                  const isMovingToParent = relatedTarget && relatedTarget.closest('.relative');

                  if (!isMovingToParent) {
                    // 延遲關閉，給用戶時間移動滑鼠
                    colorMenuTimeoutRef.current = setTimeout(() => {
                      setShowColorMenu(false);
                      colorMenuTimeoutRef.current = null;
                    }, 300); // 300ms 延遲，給用戶更多時間
                  } else {
                    // 如果移動到父元素，清除計時器
                    if (colorMenuTimeoutRef.current) {
                      clearTimeout(colorMenuTimeoutRef.current);
                      colorMenuTimeoutRef.current = null;
                    }
                  }
                }}
              >
                <div className="text-xs text-tertiary mb-2 px-2">選擇顏色</div>
                <div className="grid grid-cols-4 gap-2">
                  {labelColors.map((colorOption) => (
                    <button
                      key={colorOption.value || 'none'}
                      className={`w-8 h-8 rounded-full border-2 transition-all duration-200 hover:scale-110 ${
                        colorOption.value === contextMenu?.task.label_color
                          ? 'ring-2 ring-blue-500 ring-offset-1'
                          : ''
                      } ${colorOption.border}`}
                      style={{
                        backgroundColor: colorOption.color === 'transparent' ? 'transparent' : colorOption.color,
                        borderColor: colorOption.color === 'transparent' ? '#9CA3AF' : colorOption.color,
                      }}
                      onClick={() => handleColorSelect(colorOption.value)}
                      title={colorOption.name}
                    >
                      {colorOption.value === null && (
                        <i className="fa-regular fa-circle text-gray-400 text-xs"></i>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
          <div className="border-t border-primary my-1"></div>
          <button
            className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-500/20 hover:text-red-300 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={handleDeleteTask}
          >
            <i className="fa-solid fa-trash w-4"></i>
            <span>刪除任務</span>
          </button>
        </div>
      )}

      {/* 查看任務資訊 Modal */}
      {showTaskInfoModal && taskInfo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition">
          <div className="bg-secondary border border-primary rounded-lg shadow-lg w-full max-w-md p-6 theme-transition">
            <h2 className="text-lg font-semibold text-primary mb-4 theme-transition">
              任務資訊
            </h2>
            <div className="space-y-3">
              <div>
                <div className="text-xs text-tertiary mb-1">任務ID</div>
                <div className="text-sm text-primary">{taskInfo.id}</div>
              </div>
              <div>
                <div className="text-xs text-tertiary mb-1">任務標題</div>
                <div className="text-sm text-primary">{taskInfo.title}</div>
              </div>
              <div>
                <div className="text-xs text-tertiary mb-1">狀態</div>
                <div className="text-sm text-primary">
                  {taskInfo.status === 'pending' ? '待處理' :
                   taskInfo.status === 'in-progress' ? '進行中' :
                   taskInfo.status === 'completed' ? '已完成' : taskInfo.status}
                </div>
              </div>
              <div>
                <div className="text-xs text-tertiary mb-1">到期日期</div>
                <div className="text-sm text-primary">{taskInfo.dueDate}</div>
              </div>
              {taskInfo.executionConfig && (
                <div>
                  <div className="text-xs text-tertiary mb-1">執行模式</div>
                  <div className="text-sm text-primary">
                    {taskInfo.executionConfig.mode === 'free' ? '自由模式' :
                     taskInfo.executionConfig.mode === 'assistant' ? '助理模式' :
                     taskInfo.executionConfig.mode === 'agent' ? '代理模式' : taskInfo.executionConfig.mode}
                  </div>
                </div>
              )}
              {taskInfo.messages && (
                <div>
                  <div className="text-xs text-tertiary mb-1">消息數量</div>
                  <div className="text-sm text-primary">{taskInfo.messages.length}</div>
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => {
                  setShowTaskInfoModal(false);
                  setTaskInfo(null);
                }}
                className="px-4 py-2 bg-tertiary hover:bg-hover text-primary rounded-lg transition-colors"
              >
                關閉
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 任務重新命名 Modal */}
      {showRenameModal && renameTaskTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition">
          <div className="bg-secondary border border-primary rounded-lg shadow-lg w-full max-w-md p-6 theme-transition">
            <h2 className="text-lg font-semibold text-primary mb-4 theme-transition">
              任務重新命名
            </h2>
            <input
              ref={renameInputRef}
              type="text"
              value={renameInput}
              onChange={(e) => setRenameInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleRenameConfirm();
                } else if (e.key === 'Escape') {
                  handleRenameCancel();
                }
              }}
              className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary placeholder-tertiary focus:outline-none focus:ring-2 focus:ring-blue-500 theme-transition mb-4"
              placeholder="請輸入新任務名稱"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={handleRenameCancel}
                className="px-4 py-2 bg-tertiary hover:bg-hover text-primary rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleRenameConfirm}
                disabled={!renameInput.trim() || renameInput.trim() === renameTaskTarget.title}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                確定
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 刪除任務確認 Modal */}
      {showDeleteModal && deleteTaskTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition">
          <div className="bg-secondary border-2 border-red-500 rounded-lg shadow-xl w-full max-w-lg p-6 theme-transition">
            <div className="flex items-center gap-3 mb-4">
              <i className="fa-solid fa-exclamation-triangle text-red-500 text-2xl"></i>
              <h2 className="text-xl font-bold text-red-400 theme-transition">
                ⚠️ 嚴重警告：刪除任務
              </h2>
            </div>
            <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 mb-4">
              <p className="text-sm text-red-300 font-semibold mb-2">
                此操作將永久刪除以下所有數據，且無法復原：
              </p>
              <ul className="text-xs text-red-200 space-y-1 list-disc list-inside ml-2">
                <li>任務本身及其所有對話記錄</li>
                <li>任務下的所有文件</li>
                <li>所有文件的向量數據（ChromaDB）</li>
                <li>所有文件的知識圖譜數據（ArangoDB）</li>
                <li>所有文件的元數據（ArangoDB）</li>
                <li>所有文件的實體文件</li>
              </ul>
            </div>
            <p className="text-sm text-tertiary mb-4 theme-transition">
              確定要刪除任務「<span className="text-primary font-semibold">{deleteTaskTarget.title}</span>」嗎？
            </p>
            <div className="mb-4">
              <label className="block text-sm text-primary mb-2">
                請輸入大寫 <span className="font-mono font-bold text-red-400">DELETE</span> 以確認刪除：
              </label>
              <input
                type="text"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                placeholder="DELETE"
                className="w-full px-3 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-red-500/50 theme-transition font-mono"
                autoFocus
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeleteTaskTarget(null);
                  setDeleteConfirmText('');
                }}
                className="px-4 py-2 bg-tertiary hover:bg-hover text-primary rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleConfirmDelete}
                disabled={deleteConfirmText !== 'DELETE'}
                className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                確定刪除
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 修改時間：2026-01-06 - 收藏夾項目右鍵菜單 */}
      {favoriteContextMenu && (
        <div
          ref={favoriteContextMenuRef}
          className="fixed z-[100] bg-secondary border border-primary rounded-lg shadow-lg py-1 min-w-[180px] theme-transition"
          style={{
            left: `${favoriteContextMenu.x}px`,
            top: `${favoriteContextMenu.y}px`,
          }}
        >
          <button
            className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-500/20 hover:text-red-300 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={handleRemoveFavorite}
          >
            <i className="fa-regular fa-heart w-4"></i>
            <span>取消收藏</span>
          </button>
    </div>
      )}

      {/* 修改時間：2026-01-06 - 更多列表 Modal */}
      {showMoreModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition" onClick={handleCloseMoreModal}>
          <div
            className="bg-secondary border border-primary rounded-lg shadow-lg w-full max-w-2xl max-h-[80vh] flex flex-col theme-transition"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal 標題 */}
            <div className="p-4 border-b border-primary flex items-center justify-between">
              <h2 className="text-lg font-semibold text-primary theme-transition">
                {moreModalType === 'favorites' ? '我的收藏' : '所有任務'}
              </h2>
              <button
                onClick={handleCloseMoreModal}
                className="p-2 rounded-full hover:bg-tertiary transition-colors"
                aria-label="關閉"
              >
                <i className="fa-solid fa-times text-primary"></i>
              </button>
            </div>

            {/* 修改時間：2026-01-06 - Modal 篩選和搜尋欄 */}
            {moreModalType === 'tasks' && (
              <div className="p-4 border-b border-primary space-y-3">
                {/* 搜尋欄 */}
                <div className="relative">
                  <input
                    type="text"
                    value={modalSearchText}
                    onChange={(e) => setModalSearchText(e.target.value)}
                    placeholder="搜尋任務..."
                    className="w-full px-4 py-2 pl-10 bg-tertiary border border-primary rounded-lg text-primary placeholder-tertiary focus:outline-none focus:ring-2 focus:ring-orange-500/50 theme-transition"
                  />
                  <i className="fa-solid fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-tertiary"></i>
                </div>

                {/* 篩選器（顏色和歸檔） */}
                <div className="flex flex-wrap items-center gap-2">
                  {/* 顏色篩選 */}
                  <div className="flex flex-nowrap gap-1.5 items-center flex-1 min-w-0">
                    {/* 全部 */}
                    <button
                      className={`w-[13.8px] h-[13.8px] rounded-full border flex-shrink-0 transition-all duration-200 flex items-center justify-center ${
                        modalColorFilter === null
                          ? 'bg-orange-500/10 border-orange-500'
                          : 'border-gray-400 hover:border-orange-500/50'
                      }`}
                      style={{
                        backgroundColor: modalColorFilter === null ? 'rgba(255, 149, 0, 0.1)' : 'transparent',
                        borderColor: modalColorFilter === null ? '#FF9500' : '#9CA3AF',
                        minWidth: '13.8px',
                        maxWidth: '13.8px',
                      }}
                      onClick={() => setModalColorFilter(null)}
                      title="全部"
                    >
                      {modalColorFilter === null && (
                        <i className="fa-solid fa-check text-orange-500 text-[6px]"></i>
                      )}
                    </button>

                    {/* 無顏色 */}
                    <button
                      className={`w-[13.8px] h-[13.8px] rounded-full border flex-shrink-0 transition-all duration-200 flex items-center justify-center ${
                        modalColorFilter === 'none'
                          ? 'bg-orange-500/10 border-orange-500'
                          : 'border-gray-400 hover:border-orange-500/50'
                      }`}
                      style={{
                        backgroundColor: modalColorFilter === 'none' ? 'rgba(255, 149, 0, 0.1)' : 'transparent',
                        borderColor: modalColorFilter === 'none' ? '#FF9500' : '#9CA3AF',
                        minWidth: '13.8px',
                        maxWidth: '13.8px',
                      }}
                      onClick={() => setModalColorFilter(modalColorFilter === 'none' ? null : 'none')}
                      title="無顏色"
                    >
                      {modalColorFilter === 'none' && (
                        <i className="fa-solid fa-check text-orange-500 text-[6px]"></i>
                      )}
                    </button>

                    {/* 各種顏色 */}
                    {labelColors.filter(c => c.value !== null).map((colorOption) => (
                      <button
                        key={colorOption.value}
                        className={`w-[13.8px] h-[13.8px] rounded-full border flex-shrink-0 transition-all duration-200 flex items-center justify-center ${
                          modalColorFilter === colorOption.value
                            ? 'shadow-md border-orange-500'
                            : 'hover:shadow-sm'
                        }`}
                        style={{
                          backgroundColor: colorOption.color,
                          borderColor: modalColorFilter === colorOption.value ? '#FF9500' : colorOption.color,
                          minWidth: '13.8px',
                          maxWidth: '13.8px',
                        }}
                        onClick={() => setModalColorFilter(modalColorFilter === colorOption.value ? null : colorOption.value)}
                        title={colorOption.name}
                      >
                        {modalColorFilter === colorOption.value && (
                          <i className="fa-solid fa-check text-white text-[6px] drop-shadow-md"></i>
                        )}
                      </button>
                    ))}
                  </div>

                  {/* 歸檔按鈕 */}
                  <button
                    className={`text-xs py-1 px-2 rounded-lg transition-all duration-200 flex items-center justify-center gap-1 flex-shrink-0 ${
                      modalShowArchived
                        ? 'bg-orange-500/20 text-orange-300 border border-orange-500'
                        : 'bg-tertiary text-tertiary hover:bg-orange-500/10 hover:text-orange-300 border border-primary'
                    }`}
                    onClick={() => setModalShowArchived(!modalShowArchived)}
                    title={modalShowArchived ? '顯示激活任務' : '顯示歸檔任務'}
                  >
                    <i className="fa-solid fa-archive"></i>
                    {modalShowArchived && <span className="ml-1">歸檔</span>}
                  </button>
                </div>
              </div>
            )}

            {/* Modal 內容 - 可滾動列表 */}
            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
              {moreModalType === 'favorites' ? (
                /* 收藏列表 */
                <div className="space-y-1">
                  {favorites.map(item => {
                    const getIcon = () => {
                      if (item.icon) {
                        return `fa-solid ${item.icon}`;
                      }
                      switch (item.type) {
                        case 'task':
                          return 'fa-solid fa-tasks';
                        case 'assistant':
                          return 'fa-solid fa-robot';
                        case 'agent':
                          return 'fa-solid fa-user-tie';
                        default:
                          return 'fa-solid fa-star';
                      }
                    };

                    const getColorClass = () => {
                      switch (item.type) {
                        case 'task':
                          return 'text-orange-400';
                        case 'assistant':
                          return 'text-purple-400';
                        case 'agent':
                          return 'text-green-400';
                        default:
                          return 'text-yellow-400';
                      }
                    };

                    return (
                      <button
                        key={item.id}
                        className="w-full text-left p-3 rounded-lg flex items-center transition-all duration-200 hover:bg-yellow-500/10 hover:text-yellow-300 hover:border-l-2 hover:border-yellow-500/50 cursor-pointer"
                        onClick={() => {
                          handleFavoriteClick(item);
                          handleCloseMoreModal();
                        }}
                      >
                        <i className={`${getIcon()} mr-3 ${getColorClass()}`}></i>
                        <span className="text-sm flex-1">{item.name}</span>
                        <i className="fa-solid fa-chevron-right text-tertiary text-xs"></i>
                      </button>
                    );
                  })}
                </div>
              ) : (
                /* 任務列表（帶篩選和搜尋） */
                <div className="space-y-1">
                  {tasks
                    .filter(task => {
                      // 搜尋過濾
                      if (modalSearchText.trim()) {
                        const searchLower = modalSearchText.toLowerCase();
                        if (!task.title.toLowerCase().includes(searchLower)) {
                          return false;
                        }
                      }

                      // 歸檔狀態過濾
                      if (modalShowArchived) {
                        if (task.task_status !== 'archive') {
                          return false;
                        }
                      } else {
                        if (task.task_status && task.task_status !== 'activate') {
                          return false;
                        }
                      }

                      // 顏色過濾
                      if (modalColorFilter !== null) {
                        if (modalColorFilter === 'none') {
                          if (task.label_color) {
                            return false;
                          }
                        } else {
                          if (task.label_color !== modalColorFilter) {
                            return false;
                          }
                        }
                      }

                      return true;
                    })
                    .map(task => {
                    return (
                      <button
                        key={task.id}
                        className="w-full text-left p-3 rounded-lg flex items-center transition-all duration-200 hover:bg-orange-500/10 hover:text-orange-300 hover:border-l-2 hover:border-orange-500/50 cursor-pointer"
                        onClick={() => {
                          handleTaskClick(task);
                          handleCloseMoreModal();
                        }}
                        onContextMenu={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          // 修改時間：2026-01-06 - Modal 中的任務也能觸發右鍵菜單
                          handleTaskContextMenu(e, task);
                        }}
                      >
                        {/* 任務顏色標籤 */}
                        <div className="relative mr-3 flex-shrink-0">
                          {task.label_color ? (
                            <div
                              className="w-3 h-3 rounded-full border-2"
                              style={{
                                backgroundColor: labelColors.find(c => c.value === task.label_color)?.color || task.label_color,
                                borderColor: labelColors.find(c => c.value === task.label_color)?.color || task.label_color,
                              }}
                            />
                          ) : (
                            <i className="fa-regular fa-circle text-tertiary text-xs"></i>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm truncate">{task.title}</div>
                          {/* 修改時間：2026-01-06 - 顯示最近日期（優先顯示更新時間，其次創建時間，最後 dueDate） */}
                          <div className="text-xs text-tertiary">
                            {task.updated_at
                              ? new Date(task.updated_at).toLocaleString('zh-TW', {
                                  year: 'numeric',
                                  month: '2-digit',
                                  day: '2-digit',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })
                              : task.created_at
                              ? new Date(task.created_at).toLocaleString('zh-TW', {
                                  year: 'numeric',
                                  month: '2-digit',
                                  day: '2-digit',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })
                              : task.dueDate}
                          </div>
                        </div>
                        <i className="fa-solid fa-chevron-right text-tertiary text-xs ml-2"></i>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Modal 底部 */}
            <div className="p-4 border-t border-primary flex justify-end">
              <button
                onClick={handleCloseMoreModal}
                className="px-4 py-2 bg-tertiary hover:bg-hover text-primary rounded-lg transition-colors"
              >
                關閉
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 修改時間：2026-01-06 - 文件記錄 Modal */}
      <FileRecordModal
        isOpen={showFileRecordModal}
        onClose={() => setShowFileRecordModal(false)}
      />
    </div>
  );
}
