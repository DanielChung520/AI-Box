/**
 * 代碼功能說明: 知識本體管理 Modal
 * 創建日期: 2026-02-12
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-02-12
 */

import React, { useState, useEffect } from 'react';
import {
  X, Plus, Edit, Trash2, Globe, Tag, Check, Search,
  ChevronRight, ChevronDown, Folder, Database, FileText, Upload, Loader2
} from 'lucide-react';

const KNOWLEDGE_TYPES = [
  { id: 'ontology', name: 'Ontology（知識本體）', description: '知識結構與關係定義' },
  { id: 'spec', name: '專業知識', description: '領域規格、標準、定義' },
  { id: 'process', name: '流程', description: '工作流程、操作步驟' },
  { id: 'skill', name: '技能', description: '技術技能、操作技能' },
  { id: 'manual', name: '手冊', description: '操作手冊、使用指南' },
  { id: 'standard', name: '規範', description: '規範、準則、政策' },
  { id: 'meeting', name: '會議', description: '會議紀錄、討論事項' },
  { id: 'creative', name: '創意發想', description: '創意構想、提案、靈感' },
  { id: 'quotation', name: '報價文件', description: '報價單、估價、合約報價' },
  { id: 'training', name: '教材', description: '培訓教材、教學資料' },
  { id: 'reference', name: '參考文件', description: '範例、模板、查閱資料' },
  { id: 'other', name: '其他', description: '不屬於以上類別' }
] as const;
type KnowledgeTypeId = typeof KNOWLEDGE_TYPES[number]['id'];

export interface Ontology {
  id: string;
  domain: string;
  domainName: string;
  description: string;
  allowedTypes: KnowledgeTypeId[];
  version?: string;
  isActive?: boolean;
  tags?: string[];
  useCases?: string[];
  entityClasses?: string[];
  objectProperties?: string[];
  inheritsFrom?: string[];
  compatibleDomains?: string[];
  createdAt?: string;
  updatedAt?: string;
}

interface OntologyManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const API_BASE = '/api/v1/knowledge/ontologies';

async function fetchOntologies(search?: string): Promise<Ontology[]> {
  const url = search ? `${API_BASE}?search=${encodeURIComponent(search)}` : API_BASE;
  const response = await fetch(url);
  if (!response.ok) throw new Error('Failed to fetch ontologies');
  const data = await response.json();
  return data.data?.items || [];
}

async function createOntology(data: { domain: string; domainName: string; description?: string; allowedTypes: KnowledgeTypeId[] }): Promise<Ontology> {
  const response = await fetch(API_BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.message || 'Failed to create ontology');
  }
  const result = await response.json();
  return result.data;
}

async function updateOntology(id: string, data: Partial<Ontology>): Promise<Ontology> {
  const response = await fetch(`${API_BASE}/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.message || 'Failed to update ontology');
  }
  const result = await response.json();
  return result.data;
}

async function deleteOntology(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.message || 'Failed to delete ontology');
  }
}

export default function OntologyManagerModal({
  isOpen,
  onClose,
}: OntologyManagerModalProps) {
  const [ontologies, setOntologies] = useState<Ontology[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingOntology, setEditingOntology] = useState<Ontology | null>(null);
  const [expandedOntologies, setExpandedOntologies] = useState<Set<string>>(new Set());

  const [newOntology, setNewOntology] = useState({
    domain: '',
    domainName: '',
    description: '',
    allowedTypes: [] as KnowledgeTypeId[]
  });

  const [creating, setCreating] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadOntologies();
    }
  }, [isOpen, searchQuery]);

  const loadOntologies = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchOntologies(searchQuery);
      setOntologies(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load ontologies');
    } finally {
      setLoading(false);
    }
  };

  const filteredOntologies = ontologies;

  const toggleExpand = (id: string) => {
    const newExpanded = new Set(expandedOntologies);
    if (newExpanded.has(id)) newExpanded.delete(id);
    else newExpanded.add(id);
    setExpandedOntologies(newExpanded);
  };

  const getKnowledgeTypeName = (typeId: KnowledgeTypeId): string => KNOWLEDGE_TYPES.find(t => t.id === typeId)?.name || typeId;

  const handleCreate = async () => {
    if (!newOntology.domain || !newOntology.domainName) {
      alert('請填寫完整資訊');
      return;
    }
    setCreating(true);
    try {
      const ontologyWithId = {
        ...newOntology,
        id: `ont_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      };
      const created = await createOntology(ontologyWithId);
      setOntologies(prev => [...prev, created]);
      setShowCreateModal(false);
      setNewOntology({ domain: '', domainName: '', description: '', allowedTypes: [] });
    } catch (err) {
      alert(err instanceof Error ? err.message : '創建失敗');
    } finally {
      setCreating(false);
    }
  };

  const handleUpdate = async () => {
    if (!editingOntology) return;
    setUpdating(true);
    try {
      const updated = await updateOntology(editingOntology.id, editingOntology);
      setOntologies(prev => prev.map(o => o.id === updated.id ? updated : o));
      setEditingOntology(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : '更新失敗');
    } finally {
      setUpdating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('確定要刪除此知識本體嗎？')) return;
    setDeleting(id);
    try {
      await deleteOntology(id);
      setOntologies(prev => prev.filter(o => o.id !== id));
    } catch (err) {
      alert(err instanceof Error ? err.message : '刪除失敗');
    } finally {
      setDeleting(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="relative w-full max-w-4xl bg-white text-gray-900 rounded-xl shadow-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center gap-3">
            <Database className="w-6 h-6 text-blue-500" />
            <div>
              <h2 className="text-xl font-semibold">知識本體管理</h2>
              <p className="text-xs text-gray-500">維護領域定義，供知識庫選擇使用</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-hidden">
          <div className="flex h-full">
            <div className="w-1/3 border-r bg-gray-50 flex flex-col">
              <div className="p-4 border-b">
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="搜索領域..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="w-full mt-3 flex items-center justify-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  <Plus className="w-4 h-4" /> 新增本體
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-2">
                {loading ? (
                  <div className="text-center py-8">
                    <Loader2 className="w-8 h-8 mx-auto animate-spin text-blue-500" />
                    <p className="text-sm text-gray-500 mt-2">載入中...</p>
                  </div>
                ) : error ? (
                  <div className="text-center py-8 text-red-500">
                    <p className="text-sm">{error}</p>
                    <button onClick={loadOntologies} className="text-xs underline mt-2">重試</button>
                  </div>
                ) : filteredOntologies.length === 0 ? (
                  <div className="text-center py-8 text-gray-400">
                    <Database className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p className="text-sm">尚無知識本體</p>
                  </div>
                ) : (
                  filteredOntologies.map(ontology => (
                    <div key={ontology.id} className="mb-2">
                      <div
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer hover:bg-gray-200 ${editingOntology?.id === ontology.id ? 'bg-blue-100' : ''}`}
                        onClick={() => setEditingOntology(ontology)}
                      >
                        {expandedOntologies.has(ontology.id) ? (
                          <ChevronDown className="w-4 h-4" />
                        ) : (
                          <ChevronRight className="w-4 h-4" />
                        )}
                        <Globe className="w-4 h-4 text-blue-500" />
                        <span className="text-sm font-medium flex-1 truncate">{ontology.domainName}</span>
                        <span className="text-xs text-gray-400">({ontology.allowedTypes.length})</span>
                      </div>
                      {expandedOntologies.has(ontology.id) && (
                        <div className="ml-6 mt-1 p-2 bg-white rounded-lg border">
                          <div className="text-xs text-gray-500 mb-2">
                            <div>領域代碼: {ontology.domain}</div>
                            <div className="mt-1">{ontology.description || '無描述'}</div>
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {ontology.allowedTypes.map(typeId => (
                              <span key={typeId} className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                                {getKnowledgeTypeName(typeId)}
                              </span>
                            ))}
                          </div>
                          <div className="flex gap-1 mt-2">
                            <button
                              onClick={(e) => { e.stopPropagation(); setEditingOntology(ontology); }}
                              className="p-1 hover:bg-gray-100 rounded text-gray-500"
                              title="編輯"
                            >
                              <Edit className="w-3 h-3" />
                            </button>
                            <button
                              onClick={(e) => { e.stopPropagation(); handleDelete(ontology.id); }}
                              disabled={deleting === ontology.id}
                              className="p-1 hover:bg-red-100 rounded text-red-500 disabled:opacity-50"
                              title="刪除"
                            >
                              {deleting === ontology.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="w-2/3 flex flex-col">
              {editingOntology ? (
                <div className="flex-1 overflow-y-auto">
                  {/* 標題區域 */}
                  <div className="px-6 py-4 border-b bg-gray-50">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-lg font-semibold">{editingOntology.domainName}</h3>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">{editingOntology.domain}</span>
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded">v{editingOntology.version || '1.0'}</span>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setEditingOntology(null)}
                          className="px-3 py-1.5 border rounded-lg hover:bg-gray-100 text-sm"
                        >
                          取消
                        </button>
                        <button
                          onClick={handleUpdate}
                          disabled={updating || !editingOntology.domainName}
                          className="px-3 py-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 text-sm flex items-center gap-1"
                        >
                          {updating && <Loader2 className="w-3 h-3 animate-spin" />}
                          儲存
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* 內容區域 */}
                  <div className="p-6 space-y-6">
                    {/* 描述 */}
                    <div>
                      <h4 className="text-sm font-medium text-gray-500 mb-2">描述</h4>
                      <p className="text-sm text-gray-700">{editingOntology.description || '無描述'}</p>
                    </div>

                    {/* Tags */}
                    {editingOntology.tags && editingOntology.tags.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-500 mb-2">標籤</h4>
                        <div className="flex flex-wrap gap-1">
                          {editingOntology.tags.map((tag, idx) => (
                            <span key={idx} className="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs rounded">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Use Cases */}
                    {editingOntology.useCases && editingOntology.useCases.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-500 mb-2">使用場景</h4>
                        <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                          {editingOntology.useCases.map((useCase, idx) => (
                            <li key={idx}>{useCase}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Entity Classes */}
                    {editingOntology.entityClasses && editingOntology.entityClasses.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-500 mb-2">實體類別 ({editingOntology.entityClasses.length})</h4>
                        <div className="bg-gray-50 rounded-lg p-3">
                          <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
                            {JSON.stringify(editingOntology.entityClasses, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}

                    {/* Object Properties */}
                    {editingOntology.objectProperties && editingOntology.objectProperties.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-500 mb-2">物件屬性 ({editingOntology.objectProperties.length})</h4>
                        <div className="bg-gray-50 rounded-lg p-3">
                          <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
                            {JSON.stringify(editingOntology.objectProperties, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}

                    {/* Inherits From */}
                    {editingOntology.inheritsFrom && editingOntology.inheritsFrom.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-500 mb-2">繼承自</h4>
                        <div className="flex flex-wrap gap-1">
                          {editingOntology.inheritsFrom.map((item, idx) => (
                            <span key={idx} className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded">
                              {item}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Metadata */}
                    {editingOntology.version && (
                      <div className="pt-4 border-t">
                        <div className="flex items-center gap-4 text-xs text-gray-400">
                          <span>版本: {editingOntology.version}</span>
                          <span>|</span>
                          <span>建立: {editingOntology.createdAt ? new Date(editingOntology.createdAt).toLocaleDateString() : '-'}</span>
                          <span>|</span>
                          <span>更新: {editingOntology.updatedAt ? new Date(editingOntology.updatedAt).toLocaleDateString() : '-'}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center text-gray-400">
                  <div className="text-center">
                    <Database className="w-16 h-16 mx-auto mb-4 opacity-30" />
                    <p className="text-lg font-medium">選擇知識本體進行編輯</p>
                    <p className="text-sm mt-1">或點擊「新增本體」創建新的知識本體</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="fixed inset-0 bg-black/50" onClick={() => setShowCreateModal(false)} />
            <div className="relative w-full max-w-lg bg-white text-gray-900 rounded-xl shadow-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
              <div className="flex items-center justify-between px-6 py-4 border-b sticky top-0 bg-white">
                <h3 className="text-lg font-semibold">新增知識本體</h3>
                <button onClick={() => setShowCreateModal(false)} className="p-2 hover:bg-gray-100 rounded-lg">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">名稱 <span className="text-red-500">*</span></label>
                  <input
                    type="text"
                    value={newOntology.domainName}
                    onChange={(e) => setNewOntology({ ...newOntology, domainName: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="例如：MM-Agent 知識本體"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">類型 <span className="text-red-500">*</span></label>
                  <select
                    value={newOntology.domain}
                    onChange={(e) => setNewOntology({ ...newOntology, domain: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg"
                  >
                    <option value="">請選擇...</option>
                    <option value="domain">領域</option>
                    <option value="professional">專業</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">描述</label>
                  <textarea
                    value={newOntology.description}
                    onChange={(e) => setNewOntology({ ...newOntology, description: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg"
                    rows={3}
                    placeholder="輸入本體的描述..."
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">選擇檔案</label>
                  <div className="border-2 border-dashed rounded-lg p-4 text-center cursor-pointer hover:border-blue-500">
                    <FileText className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                    <p className="text-sm text-gray-500">點擊或拖拽上傳檔案</p>
                  </div>
                </div>
              </div>
              <div className="flex justify-end gap-2 px-6 py-4 border-t bg-gray-50 sticky bottom-0">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-100"
                >
                  取消
                </button>
                <button
                  onClick={handleCreate}
                  disabled={creating || !newOntology.domainName || !newOntology.domain}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 flex items-center gap-2"
                >
                  {creating && <Loader2 className="w-4 h-4 animate-spin" />}
                  確認創建
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
