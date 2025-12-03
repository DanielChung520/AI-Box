import { useState, useMemo } from 'react';
import { useLanguage } from '../contexts/languageContext';

interface FileTreeProps {
  onFileSelect: (fileId: string) => void;
}

interface FileNode {
  id: string;
  name: string;
  type: 'folder' | 'file';
  children?: FileNode[];
}

export default function FileTree({ onFileSelect }: FileTreeProps) {
  const { t, updateCounter, language } = useLanguage();
  const [expandedFolders, setExpandedFolders] = useState<string[]>(['reports', 'analytics']);

  // Mock文件树数据 - 使用useMemo和language確保語言變更時重新渲染
  const fileTree: FileNode[] = useMemo(() => [
    {
      id: 'reports',
      name: t('sidebar.fileTree.reports'),
      type: 'folder',
      children: [
        {
          id: 'weekly-reports',
          name: t('sidebar.fileTree.weeklyReports'),
          type: 'folder',
          children: [
            { id: 'weekly-2025-12-01', name: t('sidebar.fileTree.weeklyReport') + '2025-12-01.md', type: 'file' },
            { id: 'weekly-2025-11-24', name: t('sidebar.fileTree.weeklyReport') + '2025-11-24.md', type: 'file' }
          ]
        },
        {
          id: 'monthly-reports',
          name: t('sidebar.fileTree.monthlyReports'),
          type: 'folder',
          children: [
             { id: 'monthly-2025-11', name: t('sidebar.fileTree.weeklyReport') + '2025-11.md', type: 'file' },
             { id: 'monthly-2025-10', name: t('sidebar.fileTree.weeklyReport') + '2025-10.md', type: 'file' }
          ]
        }
      ]
    },
    {
      id: 'analytics',
      name: t('sidebar.fileTree.analytics'),
      type: 'folder',
      children: [
        { id: 'data-analysis-2025-12', name: t('fileTree.analyticsReport') + '.md', type: 'file' },
        { id: 'sales-forecast', name: t('fileTree.salesForecast') + '.xlsx', type: 'file' }
      ]
    },
    {
      id: 'documents',
      name: t('sidebar.fileTree.documents'),
      type: 'folder',
      children: [
        { id: 'meeting-notes', name: t('sidebar.fileTree.meetingNotes'), type: 'folder', children: [
          { id: 'meeting-2025-12-01', name: '2025-12-01' + t('fileTree.meetingRecord') + '.md', type: 'file' }
        ]}
      ]
    },
    { id: 'readme', name: t('sidebar.fileTree.readme'), type: 'file' }
  ], [language, updateCounter]);

  const toggleFolder = (folderId: string) => {
    setExpandedFolders(prev =>
      prev.includes(folderId)
        ? prev.filter(id => id !== folderId)
        : [...prev, folderId]
    );
  };

  const renderFileNode = (node: FileNode, level = 0) => {
    if (node.type === 'folder') {
      const isExpanded = expandedFolders.includes(node.id);
      return (
        <div key={node.id} className="mb-1">
          <div
            className="flex items-center py-1 px-3 text-sm cursor-pointer hover:bg-gray-700 rounded transition-colors"
            onClick={() => toggleFolder(node.id)}
            style={{ paddingLeft: `${level * 16 + 8}px` }}
          >
            <i className={`fa-solid mr-2 ${isExpanded ? 'fa-folder-open' : 'fa-folder'} text-yellow-500`}></i>
            <span>{node.name}</span>
          </div>
          {isExpanded && node.children && (
            <div>
              {node.children.map(childNode => renderFileNode(childNode, level + 1))}
            </div>
          )}
        </div>
      );
    } else {
      return (
        <div
          key={node.id}
          className="py-1 px-3 text-sm cursor-pointer hover:bg-gray-700 rounded transition-colors"
          onClick={() => onFileSelect(node.name)}
          style={{ paddingLeft: `${level * 16 + 8}px` }}
        >
          <i className="fa-solid mr-2 fa-file-lines text-blue-400"></i>
          <span>{node.name}</span>
        </div>
      );
    }
  };

  return (
    <div className="p-2 text-secondary theme-transition">
      {fileTree.map(node => renderFileNode(node))}
    </div>
  );
}
