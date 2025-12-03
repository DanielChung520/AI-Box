import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { useLanguage } from '../contexts/languageContext';

type Theme = 'light' | 'dark';

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    const savedTheme = localStorage.getItem('theme') as Theme;
    if (savedTheme) {
      return savedTheme;
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });
  const { t } = useLanguage();

  useEffect(() => {
    // 添加过渡效果类
    document.documentElement.classList.add('theme-transition');

    // 切换主题类
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(theme);

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
