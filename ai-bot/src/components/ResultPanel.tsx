import { useState } from 'react';
import { useLanguage } from '../contexts/languageContext';
import { cn } from '../lib/utils';
import FileTree from './FileTree';
import MarkdownViewer from './MarkdownViewer';

interface ResultPanelProps {
  collapsed: boolean;
  onToggle: () => void;
  onViewChange?: (isMarkdownView: boolean) => void;
}

export default function ResultPanel({ collapsed, onToggle, onViewChange }: ResultPanelProps) {
  const [activeTab, setActiveTab] = useState<'files' | 'markdown'>('files');
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const { t } = useLanguage();

  // 模拟一个示例Markdown内容
  const exampleMarkdown = `# 数据分析报告

## 概述
这份报告分析了最近一个季度的销售数据和用户增长情况。

## 关键发现

### 销售数据
- 总销售额达到了 **1,250,000** 元，同比增长 15%
- 华东地区贡献了 45% 的销售额
- 产品 A 的销量占比最高，达到 32%

### 用户增长
- 新增用户数为 12,450 人，环比增长 8%
- 活跃用户留存率提升至 68%
- 付费转化率达到 5.2%，创历史新高

## 图表分析

\`\`\`
// 示例代码
function calculateGrowth(current, previous) {
  return ((current - previous) / previous) * 100;
}
\`\`\`

## 结论与建议
1. 继续加大对华东地区的市场投入
2. 优化产品 A 的用户体验，保持市场领先地位
3. 探索提升付费转化率的新策略

---

*报告生成时间: 2025-12-02*`;

  const handleFileSelect = (fileId: string) => {
    setSelectedFile(fileId);
    setActiveTab('markdown');
    if (onViewChange) {
      onViewChange(true);
    }
  };

  return (
    <div className={cn(
      "h-full bg-secondary border-l border-primary flex flex-col transition-all duration-300 w-full theme-transition"
    )}>
      {/* 结果面板头部 */}
      <div className="p-4 border-b border-primary flex items-center">
        <div className="flex space-x-2">
          <button
            className={`px-3 py-1 rounded-t-lg text-sm ${activeTab === 'files' ? 'bg-tertiary text-primary' : 'text-tertiary'}`}
            onClick={() => {
              setActiveTab('files');
              if (onViewChange) {
                onViewChange(false);
              }
            }}
          >
            {t('resultPanel.files')}
          </button>
          <button
            className={`px-3 py-1 rounded-t-lg text-sm ${activeTab === 'markdown' ? 'bg-tertiary text-primary' : 'text-tertiary'}`}
            onClick={() => {
              setActiveTab('markdown');
              if (onViewChange) {
                onViewChange(true);
              }
            }}
          >
            {t('resultPanel.preview')}
          </button>
        </div>
      </div>

      {/* 结果面板内容 */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'files' && (
          <FileTree onFileSelect={handleFileSelect} />
        )}
        {activeTab === 'markdown' && (
          <MarkdownViewer content={exampleMarkdown} fileName={selectedFile || '数据分析报告.md'} />
        )}
      </div>
    </div>
  );
}
