// 代碼功能說明: 自動保存 Hook
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import { useEffect, useRef, useCallback } from 'react';
import { useDraftStore } from '../stores/draftStore';
import { toast } from 'sonner';

interface UseAutoSaveOptions {
  fileId: string | null;
  delay?: number; // 防抖延迟时间（毫秒），默认 2000ms
}

export function useAutoSave({ fileId, delay = 2000 }: UseAutoSaveOptions) {
  const { draftContent, stableContent, setAutoSaveStatus, setStableContent } = useDraftStore();
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isSavingRef = useRef(false);

  const performSave = useCallback(
    async (content: string) => {
      if (!fileId || isSavingRef.current) {
        return;
      }

      isSavingRef.current = true;
      setAutoSaveStatus(fileId, 'saving');

      try {
        // 获取当前稳定内容
        const currentStable = stableContent[fileId] || '';

        // 如果内容没有变化，直接标记为已保存
        if (currentStable === content) {
          setAutoSaveStatus(fileId, 'saved');
          isSavingRef.current = false;
          return;
        }

        // 使用文档编辑 API 保存文件
        // 注意：createDocEdit 使用 LLM 生成 diff，不适合自动保存
        // 暂时使用简化的保存逻辑：直接调用 saveFile API
        // TODO: 后续可以创建直接保存文件的 API 端点
        const apiModule = await import('../lib/api');
        const saveResult = await apiModule.saveFile(fileId, content);

        if (!saveResult.success) {
          throw new Error(saveResult.message || 'Failed to save file');
        }

        // 更新稳定内容
        setStableContent(fileId, content);
        setAutoSaveStatus(fileId, 'saved');
      } catch (error) {
        console.error('Auto-save failed:', error);
        setAutoSaveStatus(fileId, 'unsaved');
        toast.error('自動保存失敗，請手動保存');
      } finally {
        isSavingRef.current = false;
      }
    },
    [fileId, stableContent, setAutoSaveStatus, setStableContent]
  );

  useEffect(() => {
    if (!fileId) {
      return;
    }

    const draft = draftContent[fileId] || '';
    const stable = stableContent[fileId] || '';

    // 如果内容没有变化，不需要保存
    if (draft === stable) {
      return;
    }

    // 清除之前的定时器
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // 设置新的定时器
    timeoutRef.current = setTimeout(() => {
      performSave(draft);
    }, delay);

    // 清理函数
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [draftContent, stableContent, fileId, delay, performSave]);

  // 手动触发保存
  const manualSave = useCallback(async () => {
    if (!fileId) {
      return;
    }

    const draft = draftContent[fileId] || '';
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    await performSave(draft);
  }, [fileId, draftContent, performSave]);

  return {
    manualSave,
  };
}
