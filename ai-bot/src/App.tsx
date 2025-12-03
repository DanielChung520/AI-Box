import { Routes, Route } from "react-router-dom";
import Home from "@/pages/Home";
import { useState } from "react";
import { AuthContext } from '@/contexts/authContext';
import { LanguageProvider, useLanguage } from '@/contexts/languageContext';

function AppContent() {
  const [isAuthenticated, setIsAuthenticated] = useState(true); // 默认已登录以便展示功能
  const { t } = useLanguage();

  const logout = () => {
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, setIsAuthenticated, logout }}
    >
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/other" element={<div className="text-center text-xl">{t('common.otherPage')}</div>} />
      </Routes>
    </AuthContext.Provider>
  );
}

export default function App() {
  return (
    <LanguageProvider>
      <AppContent />
    </LanguageProvider>
  );
}
