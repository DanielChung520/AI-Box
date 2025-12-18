// 代碼功能說明：語言上下文，用於在整個應用中共享語言狀態
// 創建日期：2025-01-27
// 創建人：Daniel Chung
// 最後修改日期：2025-01-27

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { toast } from 'sonner';

// 定义支持的语言类型
type Language = 'en' | 'zh_CN' | 'zh_TW';

// 语言显示名称映射
export const languageNames: Record<Language, string> = {
  en: 'English',
  zh_CN: '简体中文',
  zh_TW: '繁體中文'
};

// 语言图标映射
export const languageIcons: Record<Language, string> = {
  en: 'fa-globe',
  zh_CN: 'fa-language',
  zh_TW: 'fa-language'
};

// 导入翻译内容（从 useLanguage.ts 中导入）
import { translations } from '../hooks/useLanguage';

interface LanguageContextType {
  language: Language;
  setLanguage: (newLanguage: Language) => void;
  toggleLanguage: (newLanguage: Language) => void;
  languageName: string;
  supportedLanguages: Language[];
  t: (key: string, fallback?: string) => string;
  updateCounter: number;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: ReactNode }) {
  // 默认语言为繁体中文
  const [language, setLanguageState] = useState<Language>('zh_TW');
  // 添加更新计数器以确保强制重新渲染
  const [updateCounter, setUpdateCounter] = useState(0);

  // 初始化时从localStorage获取或设置默认值
  useEffect(() => {
    const savedLanguage = localStorage.getItem('language') as Language;
    if (savedLanguage && Object.keys(languageNames).includes(savedLanguage)) {
      setLanguageState(savedLanguage);
    } else {
      // 如果没有保存的语言或保存的语言无效，设置为默认的繁体中文
      localStorage.setItem('language', 'zh_TW');
      setLanguageState('zh_TW');
    }
  }, []);

  // 保存语言设置到localStorage并更新文档lang属性
  useEffect(() => {
    localStorage.setItem('language', language);
    // 將語言代碼轉換為 HTML lang 屬性格式（zh_TW -> zh-TW）
    const htmlLang = language === 'zh_TW' ? 'zh-TW' : language === 'zh_CN' ? 'zh-CN' : language;
    document.documentElement.lang = htmlLang;
    // 增加计数器以强制更新所有使用此context的组件
    setUpdateCounter(prev => prev + 1);
  }, [language]);

  // 翻译函数
  const t = (key: string, fallback?: string): string => {
    if (translations[key] && translations[key][language]) {
      return translations[key][language];
    }
    return fallback || key;
  };

  // 直接设置语言的函数
  const setLanguage = (newLanguage: Language) => {
    if (Object.keys(languageNames).includes(newLanguage)) {
      setLanguageState(newLanguage);
    }
  };

  // 切换语言函数（带toast提示）
  const toggleLanguage = (newLanguage: Language) => {
    if (Object.keys(languageNames).includes(newLanguage)) {
      setLanguageState(newLanguage);

      // 显示语言切换提示 - 使用目标语言的翻译，确保用户能理解
      setTimeout(() => {
        const toastMessage = `${translations['language.toast'][newLanguage]}${languageNames[newLanguage]}`;

        // 确定toast样式
        const toastClass = document.documentElement.classList.contains('dark')
          ? 'bg-gray-800 text-white border border-gray-700'
          : 'bg-white text-gray-900 border border-gray-200';

        toast(toastMessage, {
          position: 'top-center',
          duration: 2000,
          className: toastClass
        });
      }, 0);
    }
  };

  return (
    <LanguageContext.Provider
      value={{
        language,
        setLanguage,
        toggleLanguage,
        languageName: languageNames[language],
        supportedLanguages: Object.keys(languageNames) as Language[],
        t,
        updateCounter
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}
