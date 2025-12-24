import { useLanguage } from '../contexts/languageContext';

interface Tab {
  id: string;
  label: string;
  translationKey?: string;
}

interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

export default function Tabs({ tabs, activeTab, onTabChange }: TabsProps) {
  const { t } = useLanguage();

  return (
    <div className="border-b border-primary theme-transition">
      <div className="flex overflow-x-auto scrollbar-hide">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`px-4 py-2 whitespace-nowrap transition-colors ${
              activeTab === tab.id
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-tertiary hover:text-primary'
            }`}
          >
            {tab.translationKey ? t(tab.translationKey) : tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}
