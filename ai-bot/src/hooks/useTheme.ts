import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { useLanguage } from '../contexts/languageContext';

type Theme = 'light' | 'dark';

// 检测系统主题偏好
const getSystemTheme = (): Theme => {
  if (typeof window !== 'undefined' && window.matchMedia) {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return 'dark'; // 默认值
};

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    const savedTheme = localStorage.getItem('theme') as Theme;
    if (savedTheme) {
      return savedTheme;
    }
    // 修改時間：2026-01-18 - 如果没有保存的主题，则跟随系统偏好
    return getSystemTheme();
  });
  const { t } = useLanguage();

  // 监听系统主题变化
  useEffect(() => {
    // 只在用户没有手动设置主题时，才监听系统主题变化
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
      return; // 用户已手动设置，不监听系统变化
    }

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleSystemThemeChange = (e: MediaQueryListEvent) => {
      const newTheme = e.matches ? 'dark' : 'light';
      setTheme(newTheme);
    };

    // 添加监听器
    mediaQuery.addEventListener('change', handleSystemThemeChange);

    // 清理函数
    return () => {
      mediaQuery.removeEventListener('change', handleSystemThemeChange);
    };
  }, []);

  // 初始化时设置主题类（确保与main.tsx中的初始化一致）
  useEffect(() => {
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(theme);
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, []); // 只在组件挂载时运行一次

  useEffect(() => {
    // 添加过渡效果类
    document.documentElement.classList.add('theme-transition');

    // 切换主题类
    // 移除所有主题类
    document.documentElement.classList.remove('light', 'dark');

    // 添加当前主题类
    document.documentElement.classList.add(theme);

    // Tailwind darkMode: "class" 需要 'dark' 类来启用dark模式
    // 当主题是 'dark' 时，添加 'dark' 类；当主题是 'light' 时，移除 'dark' 类
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }

    // 保存主题设置
    localStorage.setItem('theme', theme);

    // 为toast设置主题颜色
    const toastThemeClass = theme === 'dark'
      ? 'bg-gray-800 text-white border border-gray-700'
      : 'bg-white text-gray-900 border border-gray-200';

    // 更新所有当前存在的toast元素的主题
    document.querySelectorAll('.sonner-toast').forEach(toast => {
      toast.className = toast.className.replace(
        /bg-gray-800 text-white border border-gray-700|bg-white text-gray-900 border border-gray-200/g,
        toastThemeClass
      );
    });

  }, [theme]);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);

    // 显示主题切换提示 - 使用当前语言的翻译
    const themeMessage = newTheme === 'dark'
      ? t('theme.toast.dark')
      : t('theme.toast.light');

    toast(themeMessage, {
      position: 'top-center',
      duration: 2000,
      className: theme === 'dark'
        ? 'bg-gray-800 text-white border border-gray-700'
        : 'bg-white text-gray-900 border border-gray-200'
    });
  };

  return {
    theme,
    toggleTheme,
    isDark: theme === 'dark'
  };
}

// 注意：这里不需要导入translations，因为useLanguage hook已经提供了翻译功能
