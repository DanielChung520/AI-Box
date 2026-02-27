import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { useLanguage } from '../contexts/languageContext';

type Theme = 'light' | 'dark' | 'blue-light';

// 检测系统主题偏好
const getSystemTheme = (): Theme => {
  if (typeof window !== 'undefined' && window.matchMedia) {
    const savedTheme = localStorage.getItem('theme') as Theme;
    if (savedTheme) return savedTheme;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return 'dark';
};

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => {
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
    document.documentElement.classList.remove('light', 'dark', 'blue-light');
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
    document.documentElement.classList.remove('light', 'dark', 'blue-light');

    // 添加当前主题类
    document.documentElement.classList.add(theme);

    // 直接设置 body 背景色，确保立即生效
    const bgColors: Record<Theme, string> = {
      'light': '#f8fafc',
      'dark': '#111827',
      'blue-light': '#eff6ff'
    };
    document.body.style.setProperty('background-color', bgColors[theme], 'important');

    // Tailwind darkMode: "class" 需要 'dark' 类来启用dark模式
    // 当主题是 'dark' 时，添加 'dark' 类；当主题是 'light' 或 'blue-light' 时，移除 'dark' 类
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }

    // 保存主题设置
    localStorage.setItem('theme', theme);

    // 为toast设置主题颜色
    const isDarkTheme = theme === 'dark';
    const toastThemeClass = isDarkTheme
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

  const changeTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
    const themeMessage = newTheme === 'dark' 
      ? t('theme.toast.dark')
      : newTheme === 'blue-light'
        ? t('theme.toast.blue-light') || '藍色淺色主題'
        : t('theme.toast.light');

    toast(themeMessage, {
      position: 'top-center',
      duration: 2000,
      className: newTheme === 'dark'
        ? 'bg-gray-800 text-white border border-gray-700'
        : 'bg-white text-gray-900 border border-gray-200'
    });
  };

  const toggleTheme = () => {
    const themeOrder: Theme[] = ['light', 'blue-light', 'dark'];
    const currentIndex = themeOrder.indexOf(theme);
    const newTheme = themeOrder[(currentIndex + 1) % themeOrder.length];
    changeTheme(newTheme);
  };

  return {
    theme,
    setTheme: changeTheme,
    toggleTheme,
    isDark: theme === 'dark'
  };
}

// 注意：这里不需要导入translations，因为useLanguage hook已经提供了翻译功能
