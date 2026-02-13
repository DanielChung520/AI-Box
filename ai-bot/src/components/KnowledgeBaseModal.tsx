/**
 * 代碼功能說明: 知識庫管理 UI 組件
 * 創建日期: 2026-02-12
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-02-13
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  X, Plus, Folder, FolderPlus, Upload, FileText,
  ChevronRight, ChevronDown, Trash2, Eye,
  Search, Check, Loader2, Settings,
  Globe, Tag, Layers, Lock, Calendar, Database, Network, GitBranch
} from 'lucide-react';
import { uploadFiles, FileMetadata } from '../lib/api';
import FilePreview from './FilePreview';
import OntologyManagerModal from './OntologyManagerModal';

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

const KNOWLEDGE_TYPES = [
  { id: 'spec', name: '專業知識', description: '領域規格、標準、定義' },
  { id: 'process', name: '流程', description: '工作流程、操作步驟' },
  { id: 'skill', name: '技能', description: '技術技能、操作技能' },
  { id: 'manual', name: '手冊', description: '操作手冊、使用指南' },
  { id: 'meeting', name: '會議記錄', description: '會議紀錄、討論事項' },
  { id: 'form', name: '表單', description: '表單、模板、標準文件' },
  { id: 'plan', name: '計劃', description: '計劃、規劃、策略文件' },
  { id: 'other', name: '其他', description: '不屬於以上類別' }
] as const;
type KnowledgeTypeId = typeof KNOWLEDGE_TYPES[number]['id'];

interface OntologyOption {
  domain: string;
  domainName: string;
  allowedTypes: KnowledgeTypeId[];
}

export interface KnowledgeRoot {
  id: string;
  name: string;
  domain: string;
  domainName: string;
  allowedTypes: KnowledgeTypeId[];
  createdAt: string;
  isPrivate: boolean;
  allowInternal: boolean;
}

export interface KnowledgeFolder {
  id: string;
  rootId: string;
  parentId: string | null;
  name: string;
  domain: string;
  type: KnowledgeTypeId;
  path: string;
  domainFile?: string;
  typeFile?: string;
  otherFiles?: string[];
  isPrivate: boolean;
  allowInternal: boolean;
}

export interface KnowledgeFile {
  id: string;
  folderId: string;
  name: string;
  size: string;
  type: string;
  uploadedAt: string;
  domain: string;
  knowledgeType: KnowledgeTypeId;
  isPrivate: boolean;
  allowInternal: boolean;
  fileId?: string;
}

async function fetchOntologyOptions(): Promise<OntologyOption[]> {
  try {
    const response = await fetch('/api/v1/knowledge/ontologies');
    if (!response.ok) {
      console.warn('[KnowledgeBaseModal] API 返回錯誤');
      return [];
    }
    const data = await response.json();
    return (data.data?.items || []).map((o: any) => ({
      domain: o.domain,
      domainName: o.domainName,
      allowedTypes: o.allowedTypes || []
    }));
  } catch (error) {
    console.warn('[KnowledgeBaseModal] API 請求失敗:', error);
    return [];
  }
}

// Knowledge Base API functions
async function fetchKnowledgeBases(): Promise<KnowledgeRoot[]> {
  try {
    const response = await fetch('/api/v1/knowledge-bases');
    if (!response.ok) return [];
    const data = await response.json();
    return data.data?.items || [];
  } catch (error) {
    console.warn('[KnowledgeBaseModal] fetchKnowledgeBases 失敗:', error);
    return [];
  }
}

async function createKnowledgeBase(data: {
  name: string;
  domain: string;
  domainName: string;
  description?: string;
  allowedTypes: KnowledgeTypeId[];
  isPrivate: boolean;
  allowInternal: boolean;
}): Promise<KnowledgeRoot | null> {
  try {
    const response = await fetch('/api/v1/knowledge-bases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.message || '創建失敗');
    }
    const result = await response.json();
    return result.data;
  } catch (error) {
    console.warn('[KnowledgeBaseModal] createKnowledgeBase 失敗:', error);
    return null;
  }
}

async function deleteKnowledgeBase(id: string): Promise<boolean> {
  try {
    const response = await fetch(`/api/v1/knowledge-bases/${id}`, { method: 'DELETE' });
    return response.ok;
  } catch (error) {
    console.warn('[KnowledgeBaseModal] deleteKnowledgeBase 失敗:', error);
    return false;
  }
}

async function fetchKBFolders(kbId: string, parentId: string | null = null): Promise<KnowledgeFolder[]> {
  try {
    const url = parentId
      ? `/api/v1/knowledge-bases/${kbId}/folders?parent_id=${parentId}`
      : `/api/v1/knowledge-bases/${kbId}/folders`;
    const response = await fetch(url);
    if (!response.ok) return [];
    const data = await response.json();
    return data.data?.items || [];
  } catch (error) {
    console.warn('[KnowledgeBaseModal] fetchKBFolders 失敗:', error);
    return [];
  }
}

export interface KnowledgeFile {
  id: string;
  fileId?: string;
  folderId: string;
  name: string;
  size: string;
  type: string;
  uploadedAt: string;
  domain?: string;
  knowledgeType?: string;
  isPrivate?: boolean;
  allowInternal?: boolean;
  vectorCount?: number;
  kgStatus?: string;
  hasS3?: boolean;
}

async function fetchKBFolderFiles(folderId: string): Promise<KnowledgeFile[]> {
  try {
    const response = await fetch(`/api/v1/knowledge-bases/folders/${folderId}/files`);
    if (!response.ok) return [];
    const data = await response.json();
    return (data.data?.items || []).map((item: any) => ({
      id: item.file_id,
      fileId: item.file_id,
      folderId: folderId,
      name: item.filename,
      size: formatFileSize(item.file_size || 0),
      type: item.file_type || 'unknown',
      uploadedAt: item.upload_time ? item.upload_time.split('T')[0] : '',
      domain: item.domain,
      knowledgeType: item.knowledgeType,
      isPrivate: item.isPrivate,
      allowInternal: item.allowInternal,
      vectorCount: item.vector_count,
      kgStatus: item.kg_status,
      hasS3: !!item.storage_path,
    }));
  } catch (error) {
    console.warn('[KnowledgeBaseModal] fetchKBFolderFiles 失敗:', error);
    return [];
  }
}

async function createKBFolder(kbId: string, data: {
  name: string;
  type: KnowledgeTypeId;
  parentId?: string | null;
}): Promise<KnowledgeFolder | null> {
  try {
    const response = await fetch(`/api/v1/knowledge-bases/${kbId}/folders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.message || '創建失敗');
    }
    const result = await response.json();
    return result.data;
  } catch (error) {
    console.warn('[KnowledgeBaseModal] createKBFolder 失敗:', error);
    return null;
  }
}

async function deleteKBFolder(folderId: string): Promise<boolean> {
  try {
    const response = await fetch(`/api/v1/knowledge-bases/folders/${folderId}`, { method: 'DELETE' });
    return response.ok;
  } catch (error) {
    console.warn('[KnowledgeBaseModal] deleteKBFolder 失敗:', error);
    return false;
  }
}

function FileUploadZone({ label, required, uploadedFiles, onFilesSelected, onRemoveFile }: {
  label: string;
  required?: boolean;
  uploadedFiles: File[];
  onFilesSelected: (files: File[]) => void;
  onRemoveFile: (index: number) => void;
}) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        {required && <span className="text-red-500">*</span>}
      </div>
      <div
        className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors cursor-pointer ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}`}
        onDrop={(e) => { e.preventDefault(); setIsDragging(false); onFilesSelected(Array.from(e.dataTransfer.files)); }}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onClick={() => fileInputRef.current?.click()}
      >
        <input ref={fileInputRef} type="file" multiple className="hidden" onChange={(e) => { if (e.target.files) onFilesSelected(Array.from(e.target.files)); }} />
        <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
        <p className="text-sm text-gray-500">點擊或拖拽檔案到這裡上傳</p>
      </div>
      {uploadedFiles.length > 0 && (
        <div className="space-y-1">
          {uploadedFiles.map((file, index) => (
            <div key={index} className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg">
              <FileText className="w-4 h-4 text-blue-500" />
              <span className="flex-1 text-sm truncate">{file.name}</span>
              <span className="text-xs text-gray-400">{formatFileSize(file.size)}</span>
              <button onClick={() => onRemoveFile(index)} className="p-1 hover:bg-gray-200 rounded"><X className="w-3 h-3" /></button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

FileUploadZone.displayName = 'FileUploadZone';

interface KnowledgeBaseModalProps {
  isOpen: boolean;
  onClose: () => void;
}

function KnowledgeBaseModalComponent({ isOpen, onClose }: KnowledgeBaseModalProps) {
  if (!isOpen) return null;

  const [roots, setRoots] = useState<KnowledgeRoot[]>([]);
  const [folders, setFolders] = useState<KnowledgeFolder[]>([]);
  const [files, setFiles] = useState<KnowledgeFile[]>([]);
  const [selectedRootId, setSelectedRootId] = useState<string | null>(null);
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [expandedRoots, setExpandedRoots] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [showProperties, setShowProperties] = useState(false);

  const [showCreateRoot, setShowCreateRoot] = useState(false);
  const [showCreateFolder, setShowCreateFolder] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadFilesList, setUploadFilesList] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');

  const [showFilePreview, setShowFilePreview] = useState(false);
  const [previewFile, setPreviewFile] = useState<KnowledgeFile | null>(null);
  const [showOntologyManager, setShowOntologyManager] = useState(false);
  const [ontologies, setOntologies] = useState<Ontology[]>([
    { id: 'ont_mm_agent', domain: 'mm_agent', domainName: 'MM-Agent（物料管理）', description: '物料管理相關知識本體', allowedTypes: ['spec', 'process', 'skill', 'manual', 'standard', 'reference', 'other'], createdAt: '2026-01-01', updatedAt: '2026-01-01' },
    { id: 'ont_ka_agent', domain: 'ka_agent', domainName: 'KA-Agent（知識架構）', description: '知識架構相關本體', allowedTypes: ['ontology', 'spec', 'process', 'meeting', 'creative', 'training', 'reference'], createdAt: '2026-01-05', updatedAt: '2026-01-05' },
    { id: 'ont_sales', domain: 'sales', domainName: '業務與報價', description: '業務報價相關本體', allowedTypes: ['quotation', 'spec', 'process', 'manual', 'meeting', 'reference'], createdAt: '2026-01-10', updatedAt: '2026-01-10' }
  ]);

  const handleClose = () => {
    setSelectedRootId(null);
    setSelectedFolderId(null);
    onClose();
  };

  const [ontologyOptions, setOntologyOptions] = useState<OntologyOption[]>([]);
  const [newRoot, setNewRoot] = useState({ name: '', domain: '', allowedTypes: [] as KnowledgeTypeId[], isPrivate: true, allowInternal: false });
  const [newFolder, setNewFolder] = useState({ name: '', type: '' as KnowledgeTypeId, parentId: '' as string | null });
  const [ontologyFiles, setOntologyFiles] = useState({ domain: [] as File[], major: [] as File[], others: [] as File[] });
  const [isLoading, setIsLoading] = useState(false);

  const rootFolders = folders.filter(f => f.rootId === selectedRootId && f.parentId === null);
  const folderFiles = files.filter(f => f.folderId === selectedFolderId);
  const selectedRoot = roots.find(r => r.id === selectedRootId);
  const selectedFolder = folders.find(f => f.id === selectedFolderId);
  const selectedFile = files.find(f => f.id === selectedFileId);

  const toggleExpand = (rootId: string) => {
    setExpandedRoots(prev => {
      const newSet = new Set(prev);
      if (newSet.has(rootId)) newSet.delete(rootId);
      else newSet.add(rootId);
      return newSet;
    });
  };

  const getKnowledgeTypeName = (typeId: KnowledgeTypeId): string => {
    return KNOWLEDGE_TYPES.find(t => t.id === typeId)?.name || typeId;
  };

  useEffect(() => {
    if (isOpen) {
      fetchOntologyOptions().then(setOntologyOptions);
      loadKnowledgeBases();
    }
  }, [isOpen]);

  const loadKnowledgeBases = async () => {
    setIsLoading(true);
    try {
      const bases = await fetchKnowledgeBases();
      setRoots(bases);
      if (bases.length > 0 && !selectedRootId) {
        const firstRootId = bases[0].id;
        setSelectedRootId(firstRootId);
        setExpandedRoots(prev => new Set([...prev, firstRootId]));
      }
    } catch (error) {
      console.warn('[KnowledgeBaseModal] 載入知識庫失敗:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadKBFolders = async (kbId: string) => {
    try {
      const folderList = await fetchKBFolders(kbId);
      setFolders(folderList);
    } catch (error) {
      console.warn('[KnowledgeBaseModal] 載入目錄失敗:', error);
    }
  };

  useEffect(() => {
    if (selectedRootId) {
      loadKBFolders(selectedRootId);
    }
  }, [selectedRootId]);

  // 加載知識庫文件
  const loadKBFiles = async (folderId: string) => {
    try {
      const fileList = await fetchKBFolderFiles(folderId);
      setFiles(fileList);
    } catch (error) {
      console.warn('[KnowledgeBaseModal] 載入文件失敗:', error);
    }
  };

  useEffect(() => {
    if (selectedFolderId) {
      loadKBFiles(selectedFolderId);
    } else {
      setFiles([]);
    }
  }, [selectedFolderId]);

  const handleCreateRoot = async () => {
    if (!newRoot.name || !newRoot.domain) { alert('請填寫完整資訊'); return; }
    if (newRoot.allowedTypes.length === 0) { alert('請至少選擇一個類型'); return; }
    const domainInfo = ontologyOptions.find(o => o.domain === newRoot.domain);

    const newKB = await createKnowledgeBase({
      name: newRoot.name,
      domain: newRoot.domain,
      domainName: domainInfo?.domainName || '',
      allowedTypes: newRoot.allowedTypes,
      isPrivate: newRoot.isPrivate,
      allowInternal: newRoot.allowInternal
    });

    if (newKB) {
      setRoots([...roots, newKB]);
      setSelectedRootId(newKB.id);
    }

    setShowCreateRoot(false);
    setNewRoot({ name: '', domain: '', allowedTypes: [], isPrivate: true, allowInternal: false });
  };

  const handleCreateFolder = async () => {
    if (!newFolder.name || !newFolder.type || !selectedRoot) { alert('請填寫完整資訊'); return; }

    const newFolderData = await createKBFolder(selectedRootId, {
      name: newFolder.name,
      type: newFolder.type,
      parentId: null
    });

    if (newFolderData) {
      setFolders([...folders, newFolderData]);
      setSelectedFolderId(newFolderData.id);
    }

    setShowCreateFolder(false);
    setNewFolder({ name: '', type: '' as KnowledgeTypeId, parentId: null });
  };

  const handleDeleteFile = (fileId: string) => { if (confirm('確定要刪除此文件嗎？')) setFiles(files.filter(f => f.id !== fileId)); };

  const handleDeleteRoot = async (rootId: string) => {
    if (!confirm('確定要刪除此知識庫嗎？此操作無法復原。')) return;
    const success = await deleteKnowledgeBase(rootId);
    if (success) {
      setRoots(roots.filter(r => r.id !== rootId));
      if (selectedRootId === rootId) {
        setSelectedRootId(null);
        setSelectedFolderId(null);
        setFolders([]);
      }
    }
  };

  const handleDeleteFolder = async (folderId: string) => {
    if (!confirm('確定要刪除此目錄嗎？此操作無法復原。')) return;
    const success = await deleteKBFolder(folderId);
    if (success) {
      setFolders(folders.filter(f => f.id !== folderId));
      if (selectedFolderId === folderId) {
        setSelectedFolderId(null);
        setFiles([]);
      }
    }
  };

  const handleOpenUpload = () => { setShowUploadModal(true); setUploadFilesList([]); setUploadProgress(0); setUploadStatus('idle'); };
  const handleCloseUpload = () => { if (!isUploading) { setShowUploadModal(false); setUploadFilesList([]); } };

  const handleOpenFilePreview = (file: KnowledgeFile) => {
    setPreviewFile(file);
    setShowFilePreview(true);
  };
  const handleCloseFilePreview = () => { setShowFilePreview(false); setPreviewFile(null); };

  const handleExecuteUpload = async () => {
    if (uploadFilesList.length === 0 || !selectedFolder) return;
    setIsUploading(true); setUploadStatus('uploading'); setUploadProgress(0);
    try {
      // 修改時間：2026-02-13 - 傳遞 kb_folder_id 參數
      const response = await uploadFiles(uploadFilesList, (progress) => setUploadProgress(progress), undefined, selectedFolder.id);
      if (response.success && response.data?.uploaded) {
        setUploadStatus('success');
        // 重新加載文件列表
        const uploadedFiles = await fetchKBFolderFiles(selectedFolder.id);
        setFiles(uploadedFiles);
        setTimeout(() => { setShowUploadModal(false); setUploadFilesList([]); }, 2000);
      } else { setUploadStatus('error'); }
    } catch { setUploadStatus('error'); }
    finally { setIsUploading(false); }
  };

  const filteredFiles = folderFiles.filter(f => f.name.toLowerCase().includes(searchQuery.toLowerCase()));

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        <div className="fixed inset-0 bg-black/50" onClick={handleClose} />
        <div className="relative bg-white text-gray-900 rounded-xl shadow-2xl w-[80vw] h-[80vh] flex flex-col">
          <div className="flex flex-col h-full overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0">
              <div className="flex items-center gap-3"><Database className="w-6 h-6 text-blue-500" /><h2 className="text-xl font-semibold">知識庫管理</h2></div>
              <div className="flex items-center gap-2">
                <button onClick={() => setShowOntologyManager(true)} className="flex items-center gap-2 px-3 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600">
                  <Globe className="w-4 h-4" /> 知識本體
                </button>
                <button onClick={handleClose} className="p-2 hover:bg-gray-100 rounded-lg"><X className="w-5 h-5" /></button>
              </div>
            </div>
            <div className="flex flex-1 overflow-hidden">
              <div className="w-72 border-r bg-gray-50 flex flex-col flex-shrink-0">
                <div className="p-4 border-b">
                  <button onClick={() => setShowCreateRoot(true)} className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"><Plus className="w-4 h-4" /> 新增知識庫</button>
                </div>
                <div className="flex-1 overflow-y-auto p-2">
                  {roots.length === 0 ? (
                    <div className="text-center py-8 text-gray-400">
                      <Folder className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p className="text-sm">尚無知識庫</p>
                    </div>
                  ) : (
                    roots.map(root => (
                      <div key={root.id}>
                        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer border-l-4 transition-all duration-200 ${selectedRootId === root.id ? 'bg-blue-200 border-blue-600 shadow-sm' : 'border-gray-300 bg-white hover:bg-gray-100'}`} onClick={() => { setSelectedRootId(root.id); setSelectedFolderId(null); toggleExpand(root.id); }}>
                          {expandedRoots.has(root.id) ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                          <Folder className={`w-5 h-5 ${selectedRootId === root.id ? 'text-blue-800' : 'text-blue-600'}`} /><span className={`text-sm font-semibold truncate flex-1 ${selectedRootId === root.id ? 'text-blue-900' : 'text-gray-800'}`}>{root.name}</span>{root.isPrivate ? <Lock className="w-3 h-3 text-green-500" /> : <Lock className="w-3 h-3 text-gray-500" />}{root.allowInternal && <Globe className="w-3 h-3 text-blue-500" />}
                          {selectedRootId === root.id && <button onClick={(e) => { e.stopPropagation(); handleDeleteRoot(root.id); }} className="ml-auto p-1 hover:bg-red-100 rounded"><Trash2 className="w-3 h-3 text-red-500" /></button>}
                        </div>
                        {expandedRoots.has(root.id) && (
                          <div className="ml-6 mt-1 space-y-1">
                            {rootFolders.filter(f => f.rootId === root.id).length === 0 ? (
                              <div className="text-center py-4 text-gray-400">
                                <Folder className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                <p className="text-xs">尚無目錄</p>
                              </div>
                            ) : (
                              rootFolders.filter(f => f.rootId === root.id).map(folder => (
                                <div key={folder.id}>
                                  <div 
                                    className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer border-l-4 transition-all duration-200 ${selectedFolderId === folder.id ? 'bg-blue-200 border-blue-600 shadow-sm' : 'border-gray-300 bg-white hover:bg-gray-100'}`} 
                                    onClick={() => { 
                                      console.log('[KnowledgeBaseModal] 點擊子目錄:', folder.id, folder.name);
                                      setSelectedFolderId(folder.id); 
                                      setSelectedFileId(null); 
                                      setShowProperties(true); 
                                    }}
                                  >
                                    <Folder className={`w-4 h-4 ${selectedFolderId === folder.id ? 'text-blue-800' : 'text-gray-600'}`} />
                                    <span className={`text-sm truncate ${selectedFolderId === folder.id ? 'text-blue-900 font-semibold' : 'text-gray-700'}`}>{folder.name}</span>
                                    <span className={`text-xs ml-auto px-1.5 py-0.5 rounded ${selectedFolderId === folder.id ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'}`}>{getKnowledgeTypeName(folder.type)}</span>
                                    {selectedFolderId === folder.id && <button onClick={(e) => { e.stopPropagation(); handleDeleteFolder(folder.id); }} className="ml-1 p-0.5 hover:bg-red-100 rounded"><Trash2 className="w-3 h-3 text-red-500" /></button>}
                                  </div>
                                </div>
                              ))
                            )}
                            {selectedRootId === root.id && <button onClick={() => setShowCreateFolder(true)} className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg w-full"><FolderPlus className="w-4 h-4" /> 新增子目錄</button>}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
              <div className="flex-1 flex flex-col bg-white min-w-0">
                {selectedRootId ? (
                  <>
                    <div className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0">
                      <div className="flex items-center gap-2">
                        <Folder className="w-5 h-5 text-blue-500" />
                        <span className="font-medium">{selectedFolder ? selectedFolder.path : selectedRoot?.name}</span>
                        {selectedFolder && <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">{getKnowledgeTypeName(selectedFolder.type)}</span>}
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="relative">
                          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                          <input type="text" placeholder="搜索文件..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-9 pr-4 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                        </div>
                        {selectedFolder && <button onClick={handleOpenUpload} className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"><Upload className="w-4 h-4" /> 上傳文件</button>}
                        {(selectedFolder || selectedFileId) && <button onClick={() => setShowProperties(!showProperties)} className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${showProperties ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 hover:bg-gray-200'}`}><Settings className="w-4 h-4" /> 屬性</button>}
                      </div>
                    </div>
                    <div className="flex flex-1 overflow-hidden">
                      <div className={`flex-1 overflow-y-auto p-6 ${showProperties ? 'pr-0' : ''}`}>
                        {selectedFolder ? (
                          filteredFiles.length > 0 ? (
                            <div className="grid grid-cols-1 gap-2">
                              {filteredFiles.map(file => (
                                <div
                                  key={file.id}
                                  className={`group relative flex items-center gap-3 p-3 border rounded-lg transition-all duration-150 ${selectedFileId === file.id ? 'border-blue-500 bg-blue-100 shadow-sm' : 'hover:border-blue-400 hover:bg-blue-50'}`}
                                  onClick={() => { setSelectedFileId(file.id); setShowProperties(true); }}
                                  onDoubleClick={(e) => { e.stopPropagation(); handleOpenFilePreview(file); }}
                                >
                                  <FileText className={`w-8 h-8 flex-shrink-0 ${selectedFileId === file.id ? 'text-blue-700' : 'text-blue-500 group-hover:text-blue-700'}`} />
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                      <p className={`font-medium text-sm truncate ${selectedFileId === file.id ? 'text-blue-900' : 'text-gray-800 group-hover:text-gray-900'}`}>{file.name}</p>
                                      <span className="px-1.5 py-0.5 bg-blue-200 text-blue-800 text-xs rounded flex-shrink-0">{getKnowledgeTypeName(file.knowledgeType)}</span>
                                    </div>
                                    <div className="flex items-center gap-3 mt-1">
                                      <span className={`text-xs flex items-center gap-1 ${file.hasS3 ? 'text-green-600' : 'text-gray-400'}`}>
                                        {file.hasS3 ? <Check className="w-3 h-3" /> : <Loader2 className="w-3 h-3 animate-spin" />}
                                        S3
                                      </span>
                                      <span className={`text-xs flex items-center gap-1 ${(file.vectorCount && file.vectorCount > 0) ? 'text-green-600' : 'text-gray-400'}`}>
                                        {(file.vectorCount && file.vectorCount > 0) ? <Check className="w-3 h-3" /> : <Loader2 className="w-3 h-3 animate-spin" />}
                                        向量 {file.vectorCount ? `(${file.vectorCount})` : ''}
                                      </span>
                                      <span className={`text-xs flex items-center gap-1 ${file.kgStatus === 'completed' ? 'text-green-600' : 'text-gray-400'}`}>
                                        {file.kgStatus === 'completed' ? <Check className="w-3 h-3" /> : <Loader2 className="w-3 h-3 animate-spin" />}
                                        圖譜
                                      </span>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                                    <button onClick={(e) => { e.stopPropagation(); handleOpenFilePreview(file); }} className="p-1.5 hover:bg-blue-200 rounded text-blue-700" title="預覽"><Eye className="w-4 h-4" /></button>
                                    <button onClick={(e) => { e.stopPropagation(); handleDeleteFile(file.id); }} className="p-1.5 hover:bg-red-100 text-red-500 rounded" title="刪除"><Trash2 className="w-4 h-4" /></button>
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="text-center py-16 text-gray-400"><FileText className="w-16 h-16 mx-auto mb-4 opacity-50" /><p className="text-lg font-medium">此目錄尚無文件</p><p className="text-sm mt-1">點擊上方「上傳文件」按鈕</p></div>
                          )
                        ) : (
                          <div className="text-center py-16 text-gray-400"><Folder className="w-16 h-16 mx-auto mb-4 opacity-50" /><p className="text-lg font-medium">請選擇目錄</p><p className="text-sm mt-1">選擇左側目錄查看文件</p></div>
                        )}
                      </div>
                      {showProperties && (selectedFolder || selectedFile) && (
                        <div className="w-80 border-l bg-gray-50 flex flex-col overflow-hidden">
                          <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-100">
                            <h3 className="font-semibold">{selectedFolder ? '目錄屬性' : '文件屬性'}</h3>
                            <button onClick={() => { setShowProperties(false); }} className="p-1 hover:bg-gray-200 rounded"><X className="w-4 h-4" /></button>
                          </div>
                          <div className="flex-1 overflow-y-auto p-4 space-y-4">
                            {selectedFolder ? (
                              <>
                                <div className="space-y-3">
                                  <label className="block text-xs font-medium text-gray-500">ID</label>
                                  <div className="px-3 py-2 bg-gray-100 rounded text-sm text-gray-600 truncate">{selectedFolder.id}</div>
                                </div>
                                <div className="space-y-3">
                                  <label className="block text-xs font-medium text-gray-500">名稱</label>
                                  <input type="text" value={selectedFolder?.name || ''} onChange={(e) => setFolders(folders.map(f => f.id === selectedFolder?.id ? { ...f, name: e.target.value } : f))} className="w-full px-3 py-2 border rounded-lg text-sm" />
                                </div>
                                <div className="space-y-3">
                                  <label className="block text-xs font-medium text-gray-500">類別</label>
                                  <select value={selectedFolder?.type || ''} onChange={(e) => setFolders(folders.map(f => f.id === selectedFolder?.id ? { ...f, type: e.target.value as KnowledgeTypeId } : f))} className="w-full px-3 py-2 border rounded-lg text-sm">
                                    {selectedRoot?.allowedTypes.map(typeId => (<option key={typeId} value={typeId}>{getKnowledgeTypeName(typeId)}</option>))}
                                  </select>
                                </div>
                                <div className="bg-blue-50 rounded-lg p-3"><label className="flex items-center gap-2 text-xs font-medium text-blue-700 mb-2"><Globe className="w-3 h-3" />領域資訊（繼承自根節點）</label><div className="grid grid-cols-2 gap-2"><div className="px-3 py-2 bg-white rounded text-sm text-blue-700">{selectedRoot?.domainName || selectedRoot?.domain}</div><div className="px-3 py-2 bg-gray-100 rounded text-xs text-gray-500">{selectedRoot?.domain}</div></div></div>
                                <div className="bg-gray-50 rounded-lg p-3"><label className="flex items-center gap-2 text-xs font-medium text-gray-700 mb-2"><Lock className="w-3 h-3" />授權設定（繼承自根節點）</label><div className="space-y-2"><div className="flex items-center justify-between px-2 py-1 bg-white rounded"><span className="text-xs text-gray-600">{selectedRoot?.isPrivate ? '私有' : '公開'}</span><input type="checkbox" checked={selectedFolder.isPrivate} disabled className="w-4 h-4" /></div><div className="flex items-center justify-between px-2 py-1 bg-white rounded"><span className="text-xs text-gray-600">{selectedRoot?.allowInternal ? '允許內部分類' : '不允許內部分類'}</span><input type="checkbox" checked={selectedFolder.allowInternal} disabled className="w-4 h-4" /></div></div><p className="text-xs text-gray-500 mt-2">子目錄及檔案將繼承此授權</p></div>
                              </>
                            ) : selectedFile ? (
                              <>
                                <div className="space-y-3">
                                  <label className="block text-xs font-medium text-gray-500">名稱</label>
                                  <div className="px-3 py-2 bg-gray-100 rounded text-sm truncate">{selectedFile.name}</div>
                                </div>
                                <div className="space-y-3">
                                  <label className="flex items-center gap-2 text-xs font-medium text-gray-500"><Network className="w-3 h-3" /> 國際知識編碼</label>
                                  <input type="text" placeholder="例如：KNW-MM-AGENT-SPEC-v1.0" className="w-full px-3 py-2 border rounded-lg text-sm" />
                                </div>
                                <div className="space-y-3">
                                  <label className="block text-xs font-medium text-gray-500">版本</label>
                                  <input type="text" defaultValue="1.0.0" className="w-full px-3 py-2 border rounded-lg text-sm" />
                                </div>
                                <div className="space-y-3">
                                  <label className="flex items-center gap-2 text-xs font-medium text-gray-500"><Database className="w-3 h-3" /> S3 狀態</label>
                                  <div className="flex items-center gap-2">
                                    <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded flex items-center gap-1"><Check className="w-3 h-3" /> 已完成</span>
                                  </div>
                                </div>
                                <div className="space-y-3">
                                  <label className="flex items-center gap-2 text-xs font-medium text-gray-500"><Layers className="w-3 h-3" /> 向量狀態</label>
                                  <div className="px-3 py-2 bg-gray-100 rounded-lg">
                                    <div className="flex items-center justify-between mb-1"><span className="text-xs text-gray-600">狀態</span><span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 text-xs rounded">產生中</span></div>
                                    <div className="flex items-center justify-between"><span className="text-xs text-gray-600">塊數</span><span className="text-sm font-medium">15</span></div>
                                  </div>
                                </div>
                                <div className="space-y-3">
                                  <label className="flex items-center gap-2 text-xs font-medium text-gray-500"><GitBranch className="w-3 h-3" /> 圖譜狀態</label>
                                  <div className="px-3 py-2 bg-gray-100 rounded-lg">
                                    <div className="flex items-center justify-between mb-1"><span className="text-xs text-gray-600">狀態</span><span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 text-xs rounded">產生中</span></div>
                                    <div className="flex items-center justify-between"><span className="text-xs text-gray-600">節點/關係</span><span className="text-sm font-medium">42 / 28</span></div>
                                  </div>
                                </div>
                                <div className="space-y-3">
                                  <label className="flex items-center gap-2 text-xs font-medium text-gray-500"><Calendar className="w-3 h-3" /> 創建日期</label>
                                  <div className="px-3 py-2 bg-gray-100 rounded text-sm">{selectedFile.uploadedAt}</div>
                                </div>
                                <div className="bg-blue-50 rounded-lg p-3"><label className="flex items-center gap-2 text-xs font-medium text-blue-700 mb-2"><Globe className="w-3 h-3" />領域資訊</label><div className="grid grid-cols-2 gap-2"><div className="px-3 py-2 bg-white rounded text-sm text-blue-700">{selectedFolder?.domain || selectedRoot?.domainName}</div><div className="px-3 py-2 bg-gray-100 rounded text-xs text-gray-500">{selectedFolder?.domain || selectedRoot?.domain}</div></div></div>
                                <div className="bg-gray-50 rounded-lg p-3"><label className="flex items-center gap-2 text-xs font-medium text-gray-700 mb-2"><Lock className="w-3 h-3" />授權設定（繼承）</label><div className="space-y-2"><div className="flex items-center justify-between px-2 py-1 bg-white rounded"><span className="text-xs text-gray-600">{selectedFile.isPrivate ? '私有' : '公開'}</span><input type="checkbox" checked={selectedFile.isPrivate} disabled className="w-4 h-4" /></div><div className="flex items-center justify-between px-2 py-1 bg-white rounded"><span className="text-xs text-gray-600">{selectedFile.allowInternal ? '允許內部分類' : '不允許內部分類'}</span><input type="checkbox" checked={selectedFile.allowInternal} disabled className="w-4 h-4" /></div></div></div>
                              </>
                            ) : null}
                          </div>
                          <div className="p-4 border-t bg-gray-100"><button className="w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm">儲存變更</button></div>
                        </div>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-gray-400"><div className="text-center"><Database className="w-20 h-20 mx-auto mb-4 opacity-30" /><p className="text-xl font-medium">尚無知識庫</p><p className="text-sm mt-1">點擊上方「新增知識庫」按鈕創建</p></div></div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {showCreateRoot && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black/50" onClick={() => setShowCreateRoot(false)} />
          <div className="relative w-full max-w-md bg-white text-gray-900 rounded-xl shadow-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b sticky top-0 bg-white"><h3 className="text-lg font-semibold">新增知識庫</h3><button onClick={() => setShowCreateRoot(false)} className="p-2 hover:bg-gray-100 rounded-lg"><X className="w-5 h-5" /></button></div>
            <div className="p-6 space-y-4 max-h-[calc(90vh-80px)] overflow-y-auto">
              <div className="bg-blue-50 rounded-lg p-4"><h4 className="font-medium text-blue-700 mb-3">基本資訊</h4><div><label className="block text-sm font-medium mb-1">知識庫名稱 <span className="text-red-500">*</span></label><input type="text" value={newRoot.name} onChange={(e) => setNewRoot({ ...newRoot, name: e.target.value })} placeholder="例如：MM-Agent 知識庫" className="w-full px-3 py-2 border rounded-lg" /></div><div className="mt-4"><label className="block text-sm font-medium mb-1">選擇領域 <span className="text-red-500">*</span></label><select value={newRoot.domain} onChange={(e) => setNewRoot({ ...newRoot, domain: e.target.value })} className="w-full px-3 py-2 border rounded-lg"><option value="">請選擇...</option>{ontologyOptions.map(o => <option key={o.domain} value={o.domain}>{o.domainName}</option>)}</select></div></div>
              <div className="bg-blue-50 rounded-lg p-4"><h4 className="font-medium text-blue-700 mb-3">類型（可多選）<span className="text-red-500">*</span></h4><div className="grid grid-cols-2 gap-2">{KNOWLEDGE_TYPES.map(type => (<label key={type.id} className="flex items-start gap-2 cursor-pointer p-2 hover:bg-gray-100 rounded-lg"><input type="checkbox" checked={newRoot.allowedTypes.includes(type.id)} onChange={(e) => { if (e.target.checked) setNewRoot({ ...newRoot, allowedTypes: [...newRoot.allowedTypes, type.id] }); else setNewRoot({ ...newRoot, allowedTypes: newRoot.allowedTypes.filter(t => t !== type.id) }); }} className="w-4 h-4 mt-0.5" /><div><span className="text-sm font-medium">{type.name}</span><p className="text-xs text-gray-500">{type.description}</p></div></label>))}</div></div>
              <div className="bg-gray-50 rounded-lg p-4"><h4 className="font-medium text-gray-700 mb-3"><Lock className="w-4 h-4 inline mr-1" />授權設定</h4><div className="space-y-3"><label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={newRoot.isPrivate} onChange={(e) => setNewRoot({ ...newRoot, isPrivate: e.target.checked })} className="w-4 h-4" /><span className="text-sm">私有（僅創建者可訪問）</span></label><label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={newRoot.allowInternal} onChange={(e) => setNewRoot({ ...newRoot, allowInternal: e.target.checked })} className="w-4 h-4" /><span className="text-sm">允許內部分類</span></label></div><p className="text-xs text-gray-500 mt-2">子目錄及檔案將繼承此授權設定</p></div>
            </div>
            <div className="flex justify-end gap-2 px-6 py-4 border-t bg-gray-50 sticky bottom-0"><button onClick={() => setShowCreateRoot(false)} className="px-4 py-2 border rounded-lg hover:bg-gray-100">取消</button><button onClick={handleCreateRoot} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">確認創建</button></div>
          </div>
        </div>
      )}

      {showCreateFolder && selectedRoot && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black/50" onClick={() => setShowCreateFolder(false)} />
          <div className="relative w-full max-w-2xl bg-white text-gray-900 rounded-xl shadow-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b sticky top-0 bg-white"><h3 className="text-lg font-semibold">新增子目錄</h3><button onClick={() => setShowCreateFolder(false)} className="p-2 hover:bg-gray-100 rounded-lg"><X className="w-5 h-5" /></button></div>
            <div className="p-6 space-y-6">
              <div className="bg-blue-50 rounded-lg p-4"><h4 className="font-medium text-blue-700 mb-3">目錄資訊</h4><div className="grid grid-cols-2 gap-4"><div><label className="block text-sm font-medium mb-1">目錄名稱 <span className="text-red-500">*</span></label><input type="text" value={newFolder.name} onChange={(e) => setNewFolder({ ...newFolder, name: e.target.value })} placeholder="例如：規格文件" className="w-full px-3 py-2 border rounded-lg" /></div><div><label className="block text-sm font-medium mb-1">知識類型 <span className="text-red-500">*</span></label><select value={newFolder.type} onChange={(e) => setNewFolder({ ...newFolder, type: e.target.value as KnowledgeTypeId })} className="w-full px-3 py-2 border rounded-lg"><option value="">請選擇...</option>{selectedRoot.allowedTypes.map(typeId => (<option key={typeId} value={typeId}>{getKnowledgeTypeName(typeId)}</option>))}</select></div></div></div>
              <div className="bg-gray-50 rounded-lg p-4"><h4 className="font-medium text-gray-700 mb-3"><Globe className="w-4 h-4 inline mr-1" />領域資訊（繼承自知識庫）</h4><div className="grid grid-cols-2 gap-4"><div><label className="block text-xs text-gray-500 mb-1">領域</label><div className="px-3 py-2 bg-blue-100 rounded-lg text-sm text-blue-700">{selectedRoot.domainName || selectedRoot.domain}</div></div><div><label className="block text-xs text-gray-500 mb-1">領域代碼</label><div className="px-3 py-2 bg-gray-100 rounded-lg text-sm text-gray-600">{selectedRoot.domain}</div></div></div></div>
              <div className="bg-gray-50 rounded-lg p-4"><h4 className="font-medium text-gray-700 mb-3"><Lock className="w-4 h-4 inline mr-1" />授權設定（繼承自知識庫）</h4><div className="grid grid-cols-2 gap-4"><div className="flex items-center gap-2 px-3 py-2 bg-blue-50 rounded-lg"><input type="checkbox" checked={selectedRoot.isPrivate} disabled className="w-4 h-4" /><span className="text-sm">{selectedRoot.isPrivate ? '私有' : '公開'}</span></div><div className="flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-lg"><input type="checkbox" checked={selectedRoot.allowInternal} disabled className="w-4 h-4" /><span className="text-sm">{selectedRoot.allowInternal ? '允許內部分類' : '不允許內部分類'}</span></div></div><p className="text-xs text-gray-500 mt-2">授權設定將自動繼承至子目錄及檔案</p></div>
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-700 mb-3">Ontology 文件上傳</h4>
                <FileUploadZone label="領域（Domain）文件" required={true} uploadedFiles={ontologyFiles.domain} onFilesSelected={(files) => setOntologyFiles({ ...ontologyFiles, domain: files })} onRemoveFile={(index) => setOntologyFiles({ ...ontologyFiles, domain: ontologyFiles.domain.filter((_, i) => i !== index) })} />
                <div className="mt-4"><FileUploadZone label="專業（Major）文件" required={false} uploadedFiles={ontologyFiles.major} onFilesSelected={(files) => setOntologyFiles({ ...ontologyFiles, major: files })} onRemoveFile={(index) => setOntologyFiles({ ...ontologyFiles, major: ontologyFiles.major.filter((_, i) => i !== index) })} /></div>
                <div className="mt-4"><FileUploadZone label="其他（Others）文件" required={false} uploadedFiles={ontologyFiles.others} onFilesSelected={(files) => setOntologyFiles({ ...ontologyFiles, others: files })} onRemoveFile={(index) => setOntologyFiles({ ...ontologyFiles, others: ontologyFiles.others.filter((_, i) => i !== index) })} /></div>
              </div>
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3"><p className="text-sm text-yellow-700">💡 提示：Domain 文件為必填，類型文件和其他文件為選填。</p></div>
            </div>
            <div className="flex justify-end gap-2 px-6 py-4 border-t bg-gray-50 sticky bottom-0"><button onClick={() => { setShowCreateFolder(false); setOntologyFiles({ domain: [], major: [], others: [] }); }} className="px-4 py-2 border rounded-lg hover:bg-gray-100">取消</button><button onClick={handleCreateFolder} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">確認創建</button></div>
          </div>
        </div>
      )}

      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black/50" onClick={handleCloseUpload} />
          <div className="relative w-full max-w-2xl bg-white text-gray-900 rounded-xl shadow-2xl max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b bg-gray-50">
              <div className="flex items-center gap-3"><Upload className="w-5 h-5 text-green-500" /><div><h3 className="text-lg font-semibold">上傳文件</h3>{selectedFolder && <p className="text-xs text-gray-500">上傳到：{selectedFolder.path}</p>}</div></div>
              <button onClick={handleCloseUpload} disabled={isUploading} className="p-2 hover:bg-gray-200 rounded-lg disabled:opacity-50"><X className="w-5 h-5" /></button>
            </div>
            <div className="p-6 max-h-[60vh] overflow-y-auto">
              <div className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer ${isUploading ? 'opacity-50 cursor-not-allowed' : 'border-gray-300 hover:border-gray-400'}`} onClick={() => !isUploading && document.getElementById('kb-upload-input')?.click()}>
                <input id="kb-upload-input" type="file" multiple className="hidden" onChange={(e) => { if (e.target.files) setUploadFilesList(prev => [...prev, ...Array.from(e.target.files)]); }} disabled={isUploading} />
                <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600 mb-2">點擊或拖拽文件到這裡上傳</p>
                <p className="text-sm text-gray-400">支援 PDF, DOC, DOCX, TXT, MD, CSV, XLS, XLSX, PPT, PPTX</p>
              </div>
              {uploadFilesList.length > 0 && (
                <div className="mt-4"><h4 className="text-sm font-medium text-gray-700 mb-2">待上傳文件 ({uploadFilesList.length})</h4><div className="space-y-2 max-h-60 overflow-y-auto">{uploadFilesList.map((file, index) => (<div key={index} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"><FileText className="w-8 h-8 text-blue-500" /><div className="flex-1 min-w-0"><p className="text-sm font-medium truncate">{file.name}</p><p className="text-xs text-gray-400">{formatFileSize(file.size)}</p></div>{!isUploading && <button onClick={() => setUploadFilesList(prev => prev.filter((_, i) => i !== index))} className="p-1 hover:bg-gray-200 rounded"><X className="w-4 h-4 text-gray-500" /></button>}</div>))}</div></div>
              )}
              {uploadStatus === 'uploading' && (
                <div className="mt-4"><div className="flex items-center justify-between text-sm mb-2"><span className="text-gray-600">上傳中...</span><span className="text-gray-600">{uploadProgress}%</span></div><div className="w-full bg-gray-200 rounded-full h-2"><div className="bg-green-500 h-2 rounded-full transition-all" style={{ width: `${uploadProgress}%` }} /></div></div>
              )}
              {uploadStatus === 'success' && (
                <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg"><div className="flex items-center gap-2 text-green-700"><Check className="w-5 h-5" /><span className="font-medium">上傳成功！</span></div></div>
              )}
              {uploadStatus === 'error' && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg"><div className="flex items-center gap-2 text-red-700"><X className="w-5 h-5" /><span className="font-medium">上傳失敗，請重試</span></div></div>
              )}
            </div>
            <div className="flex justify-end gap-2 px-6 py-4 border-t bg-gray-50"><button onClick={handleCloseUpload} disabled={isUploading} className="px-4 py-2 border rounded-lg hover:bg-gray-100 disabled:opacity-50">{uploadStatus === 'success' ? '完成' : '取消'}</button><button onClick={handleExecuteUpload} disabled={uploadFilesList.length === 0 || isUploading || uploadStatus === 'success'} className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50">{isUploading ? <><Loader2 className="w-4 h-4 animate-spin" />上傳中...</> : <><Upload className="w-4 h-4" />開始上傳</>}</button></div>
          </div>
        </div>
      )}

      {showFilePreview && previewFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black/50" onClick={handleCloseFilePreview} />
          <div className="relative w-full max-w-6xl bg-white text-gray-900 rounded-xl shadow-2xl max-h-[90vh] flex flex-col overflow-hidden">
            <FilePreview
              file={{
                file_id: previewFile.fileId || previewFile.id,
                filename: previewFile.name,
                file_type: previewFile.type || 'text/markdown',
                file_size: 0,
                tags: [],
                upload_time: new Date().toISOString(),
              } as FileMetadata}
              isOpen={showFilePreview}
              onClose={handleCloseFilePreview}
              inline={true}
            />
          </div>
        </div>
      )}

      <OntologyManagerModal
        isOpen={showOntologyManager}
        onClose={() => setShowOntologyManager(false)}
      />
    </>
  );
}

KnowledgeBaseModalComponent.displayName = 'KnowledgeBaseModalComponent';

export default KnowledgeBaseModalComponent;
