/**
 * Icon 選擇器組件
 * 功能：提供圖標選擇界面，支持從 react-icons 庫選擇圖標
 * 創建日期：2025-01-27
 * 創建人：Daniel Chung
 * 最後修改日期：2025-01-27
 */

import { useState, useMemo } from 'react';
import * as FaIcons from 'react-icons/fa';
import * as MdIcons from 'react-icons/md';
import * as HiIcons from 'react-icons/hi';
import * as SiIcons from 'react-icons/si';
import IconRenderer from './IconRenderer';

interface IconOption {
  name: string;
  component: any;
  category: string;
}

// Icon 庫配置 - 預定義約 50 個圖標，從 react-icons 庫中精選
const iconCategories: Record<string, IconOption[]> = {
  '常用': [
    { name: 'FaRobot', component: FaIcons.FaRobot, category: '常用' },
    { name: 'FaCode', component: FaIcons.FaCode, category: '常用' },
    { name: 'FaChartLine', component: FaIcons.FaChartLine, category: '常用' },
    { name: 'FaBolt', component: FaIcons.FaBolt, category: '常用' },
    { name: 'FaStar', component: FaIcons.FaStar, category: '常用' },
    { name: 'FaFire', component: FaIcons.FaFire, category: '常用' },
    { name: 'FaGem', component: FaIcons.FaGem, category: '常用' },
    { name: 'FaCrown', component: FaIcons.FaCrown, category: '常用' },
    { name: 'FaHeart', component: FaIcons.FaHeart, category: '常用' },
    { name: 'FaRocket', component: FaIcons.FaRocket, category: '常用' },
    { name: 'FaMagic', component: FaIcons.FaMagic, category: '常用' },
    { name: 'FaFlask', component: FaIcons.FaFlask, category: '常用' },
    { name: 'FaBrain', component: FaIcons.FaBrain, category: '常用' },
  ],
  '業務': [
    { name: 'FaFileAlt', component: FaIcons.FaFileAlt, category: '業務' },
    { name: 'FaDatabase', component: FaIcons.FaDatabase, category: '業務' },
    { name: 'FaCloud', component: FaIcons.FaCloud, category: '業務' },
    { name: 'MdWork', component: MdIcons.MdWork, category: '業務' },
    { name: 'MdSchool', component: MdIcons.MdSchool, category: '業務' },
    { name: 'MdHome', component: MdIcons.MdHome, category: '業務' },
    { name: 'FaBriefcase', component: FaIcons.FaBriefcase, category: '業務' },
    { name: 'FaBuilding', component: FaIcons.FaBuilding, category: '業務' },
    { name: 'FaChartBar', component: FaIcons.FaChartBar, category: '業務' },
    { name: 'FaUsers', component: FaIcons.FaUsers, category: '業務' },
    { name: 'FaGlobe', component: FaIcons.FaGlobe, category: '業務' },
    { name: 'MdBusiness', component: MdIcons.MdBusiness, category: '業務' },
  ],
  '技術': [
    { name: 'SiPython', component: SiIcons.SiPython, category: '技術' },
    { name: 'SiJavascript', component: SiIcons.SiJavascript, category: '技術' },
    { name: 'SiTypescript', component: SiIcons.SiTypescript, category: '技術' },
    { name: 'SiGo', component: SiIcons.SiGo, category: '技術' },
    { name: 'SiRust', component: SiIcons.SiRust, category: '技術' },
    { name: 'FaCodeBranch', component: FaIcons.FaCodeBranch, category: '技術' },
    { name: 'FaServer', component: FaIcons.FaServer, category: '技術' },
    { name: 'FaNetworkWired', component: FaIcons.FaNetworkWired, category: '技術' },
    { name: 'FaMicrochip', component: FaIcons.FaMicrochip, category: '技術' },
    { name: 'FaLaptopCode', component: FaIcons.FaLaptopCode, category: '技術' },
  ],
  '安全': [
    { name: 'FaShieldAlt', component: FaIcons.FaShieldAlt, category: '安全' },
    { name: 'FaLock', component: FaIcons.FaLock, category: '安全' },
    { name: 'FaKey', component: FaIcons.FaKey, category: '安全' },
    { name: 'FaFingerprint', component: FaIcons.FaFingerprint, category: '安全' },
    { name: 'FaEye', component: FaIcons.FaEye, category: '安全' },
    { name: 'FaUserSecret', component: FaIcons.FaUserSecret, category: '安全' },
    { name: 'FaShieldVirus', component: FaIcons.FaShieldVirus, category: '安全' },
  ],
  '工具': [
    { name: 'FaSearch', component: FaIcons.FaSearch, category: '工具' },
    { name: 'FaCog', component: FaIcons.FaCog, category: '工具' },
    { name: 'FaTools', component: FaIcons.FaTools, category: '工具' },
    { name: 'MdSettings', component: MdIcons.MdSettings, category: '工具' },
    { name: 'HiLightBulb', component: HiIcons.HiLightBulb, category: '工具' },
    { name: 'HiSparkles', component: HiIcons.HiSparkles, category: '工具' },
    { name: 'HiPuzzle', component: HiIcons.HiPuzzle, category: '工具' },
    { name: 'FaFilter', component: FaIcons.FaFilter, category: '工具' },
    { name: 'FaWrench', component: FaIcons.FaWrench, category: '工具' },
    { name: 'FaClipboard', component: FaIcons.FaClipboard, category: '工具' },
    { name: 'FaBook', component: FaIcons.FaBook, category: '工具' },
  ],
};

interface IconPickerProps {
  isOpen: boolean;
  selectedIcon?: string;
  onSelect: (iconName: string) => void;
  onClose: () => void;
}

export default function IconPicker({ isOpen, selectedIcon, onSelect, onClose }: IconPickerProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('常用');
  const [customIconName, setCustomIconName] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);

  // 所有圖標列表
  const allIcons = useMemo(() => {
    return Object.values(iconCategories).flat();
  }, []);

  // 過濾圖標
  const filteredIcons = useMemo(() => {
    if (!searchTerm) {
      return iconCategories[selectedCategory] || [];
    }
    return allIcons.filter(icon =>
      icon.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [searchTerm, selectedCategory, allIcons]);

  // 條件返回必須在所有 hooks 之後
  if (!isOpen) return null;

  const handleIconSelect = (iconName: string) => {
    onSelect(iconName);
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition"
      onClick={onClose}
    >
      <div
        className="bg-secondary border border-primary rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col theme-transition"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 頭部 */}
        <div className="p-4 border-b border-primary flex items-center justify-between bg-blue-500/10">
          <h3 className="text-lg font-semibold text-primary">選擇圖標</h3>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
          >
            <i className="fa-solid fa-times"></i>
          </button>
        </div>

        {/* 搜索和分類 */}
        <div className="p-4 border-b border-primary bg-tertiary/20">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="搜索圖標..."
            className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500 mb-3"
          />

          {/* 分類標籤 */}
          <div className="flex flex-wrap gap-2 mb-3">
            {Object.keys(iconCategories).map((category) => (
              <button
                key={category}
                onClick={() => {
                  setSelectedCategory(category);
                  setSearchTerm('');
                  setShowCustomInput(false);
                }}
                className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                  selectedCategory === category
                    ? 'bg-blue-600 text-white'
                    : 'bg-tertiary text-primary hover:bg-primary/20'
                }`}
              >
                {category}
              </button>
            ))}
            <button
              onClick={() => {
                setSelectedCategory('自定義');
                setSearchTerm('');
                setShowCustomInput(true);
              }}
              className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                selectedCategory === '自定義'
                  ? 'bg-blue-600 text-white'
                  : 'bg-tertiary text-primary hover:bg-primary/20'
              }`}
            >
              自定義圖標
            </button>
          </div>

          {/* 自定義圖標輸入 */}
          {showCustomInput && (
            <div className="border-t border-primary pt-3">
              <label className="block text-xs text-tertiary mb-2">
                輸入圖標名稱：
                <br />
                • <a href="https://react-icons.github.io/react-icons/" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-500 underline">react-icons</a> 格式（例如：FaBeer, MdFavorite）
                <br />
                • <a href="https://fontawesome.com/icons" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-500 underline">FontAwesome</a> 類名格式（例如：fa-beer, fa-user-tie）
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={customIconName}
                  onChange={(e) => setCustomIconName(e.target.value)}
                  placeholder="例如：FaBeer 或 fa-beer"
                  className="flex-1 px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {customIconName.trim() && (
                  <div className="flex items-center gap-2 px-3 bg-tertiary border border-primary rounded-lg">
                    {customIconName.trim().startsWith('fa-') ? (
                      <i className={`fa-solid ${customIconName.trim()} text-blue-400`} style={{ fontSize: '24px' }}></i>
                    ) : (
                      <IconRenderer iconName={customIconName.trim()} size={24} />
                    )}
                  </div>
                )}
                <button
                  onClick={() => {
                    if (customIconName.trim()) {
                      handleIconSelect(customIconName.trim());
                    }
                  }}
                  disabled={!customIconName.trim()}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  使用
                </button>
              </div>
              <p className="text-xs text-tertiary mt-2">
                💡 提示：支持 react-icons 格式（如 Fa、Md、Hi 等）或 FontAwesome 類名格式（如 fa-beer、fa-user-tie）
              </p>
            </div>
          )}
        </div>

        {/* 圖標網格 */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="grid grid-cols-6 gap-3">
            {filteredIcons.map((iconOption) => {
              const IconComponent = iconOption.component;
              const isSelected = selectedIcon === iconOption.name;

              return (
                <button
                  key={iconOption.name}
                  onClick={() => handleIconSelect(iconOption.name)}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    isSelected
                      ? 'border-blue-500 bg-blue-500/20 text-blue-400'
                      : 'border-primary hover:border-blue-500/50 hover:bg-tertiary text-primary'
                  }`}
                  title={iconOption.name}
                >
                  <IconComponent size={24} className="mx-auto" />
                </button>
              );
            })}
          </div>
        </div>

        {/* 底部：react-icons 官網鏈接 */}
        <div className="p-4 border-t border-primary bg-tertiary/20">
          <div className="flex items-center justify-center gap-2 text-sm">
            <span className="text-tertiary">需要更多圖標？</span>
            <a
              href="https://react-icons.github.io/react-icons/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:text-blue-500 underline flex items-center gap-1 transition-colors"
              onClick={(e) => e.stopPropagation()}
            >
              <i className="fa-solid fa-external-link-alt"></i>
              <span>瀏覽 react-icons 官網</span>
            </a>
          </div>
          <p className="text-xs text-tertiary text-center mt-2">
            在官網找到圖標後，使用「自定義圖標」功能輸入圖標名稱即可使用
          </p>
        </div>
      </div>
    </div>
  );
}
