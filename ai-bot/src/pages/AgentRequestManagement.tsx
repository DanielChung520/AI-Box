// 代碼功能說明: Agent 申請審查管理頁面
// 創建日期: 2026-01-17 23:10 UTC+8
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-18 10:30 UTC+8

import React, { useState, useEffect } from 'react';
import { ArrowLeft, Search, RefreshCw, Check, X, Eye, Copy, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  getAgentRequests,
  getAgentRequestDetail,
  approveAgentRequest,
  rejectAgentRequest,
  revokeAgentRequest,
  AgentRegistrationRequest,
  AgentRequestFilters,
  ApproveAgentRequestResult,
} from '@/lib/api';

const AgentRequestManagement: React.FC = () => {
  const navigate = useNavigate();

  const [requests, setRequests] = useState<AgentRegistrationRequest[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<AgentRequestFilters>({
    page: 1,
    page_size: 20,
  });
  const [searchTerm, setSearchTerm] = useState('');

  // Modal 狀態
  const [selectedRequest, setSelectedRequest] = useState<AgentRegistrationRequest | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [showRevokeModal, setShowRevokeModal] = useState(false);
  const [showSecretModal, setShowSecretModal] = useState(false);

  // 表單狀態
  const [rejectionReason, setRejectionReason] = useState('');
  const [revocationReason, setRevocationReason] = useState('');
  const [approvalResult, setApprovalResult] = useState<ApproveAgentRequestResult | null>(null);

  // 載入申請列表
  const loadRequests = async () => {
    setLoading(true);
    try {
      const result = await getAgentRequests(filters);
      setRequests(result.requests);
      setTotal(result.total);
    } catch (error) {
      console.error('Failed to load requests:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRequests();
  }, [filters]);

  // 搜索
  const handleSearch = () => {
    setFilters({ ...filters, search: searchTerm, page: 1 });
  };

  // 返回上一頁或主頁
  const handleBack = () => {
    navigate('/home');
  };

  // 查看詳情
  const handleViewDetail = async (request: AgentRegistrationRequest) => {
    try {
      const detail = await getAgentRequestDetail(request.request_id);
      setSelectedRequest(detail);
      setShowDetailModal(true);
    } catch (error) {
      console.error('Failed to load request detail:', error);
    }
  };

  // 批准申請
  const handleApprove = async () => {
    if (!selectedRequest) return;

    try {
      const result = await approveAgentRequest(selectedRequest.request_id);
      setApprovalResult(result);
      setShowApproveModal(false);
      setShowSecretModal(true);
      loadRequests();
    } catch (error) {
      console.error('Failed to approve request:', error);
    }
  };

  // 拒絕申請
  const handleReject = async () => {
    if (!selectedRequest || !rejectionReason) return;

    try {
      await rejectAgentRequest(selectedRequest.request_id, rejectionReason);
      setShowRejectModal(false);
      setSelectedRequest(null);
      setRejectionReason('');
      loadRequests();
    } catch (error) {
      console.error('Failed to reject request:', error);
    }
  };

  // 撤銷申請
  const handleRevoke = async () => {
    if (!selectedRequest || !revocationReason) return;

    try {
      await revokeAgentRequest(selectedRequest.request_id, revocationReason);
      setShowRevokeModal(false);
      setSelectedRequest(null);
      setRevocationReason('');
      loadRequests();
    } catch (error) {
      console.error('Failed to revoke request:', error);
    }
  };

  // 複製到剪貼板
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert('已複製到剪貼板');
  };

  // 獲取狀態標籤
  const getStatusBadge = (status: string) => {
    const statusConfig = {
      pending: { label: '待審核', color: 'bg-yellow-100 text-yellow-800' },
      approved: { label: '已批准', color: 'bg-green-100 text-green-800' },
      rejected: { label: '已拒絕', color: 'bg-red-100 text-red-800' },
      revoked: { label: '已撤銷', color: 'bg-gray-100 text-gray-800' },
    };
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
        {config.label}
      </span>
    );
  };

  // 分頁
  const totalPages = Math.ceil(total / (filters.page_size || 20));

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 頂部導航欄 */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={handleBack}
              className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft size={20} />
              <span>返回</span>
            </button>
            <div className="h-6 w-px bg-gray-300"></div>
            <h1 className="text-2xl font-bold text-gray-900">Agent 申請審查</h1>
          </div>

          <button
            onClick={loadRequests}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            <span>刷新</span>
          </button>
        </div>
      </div>

      {/* 內容區域 */}
      <div className="px-6 py-6">
        {/* 過濾和搜索 */}
        <div className="mb-6 flex items-center space-x-4">
          <div className="flex-1 flex items-center space-x-2">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="搜索 Agent 名稱、ID、申請者郵箱..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleSearch}
              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors flex items-center space-x-2"
            >
              <Search size={16} />
              <span>搜索</span>
            </button>
          </div>

          <select
            value={filters.status || ''}
            onChange={(e) => setFilters({ ...filters, status: (e.target.value || undefined) as any, page: 1 })}
            className="px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">全部狀態</option>
            <option value="pending">待審核</option>
            <option value="approved">已批准</option>
            <option value="rejected">已拒絕</option>
            <option value="revoked">已撤銷</option>
          </select>
        </div>

        {/* 申請列表表格 */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  申請 ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Agent 名稱
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Agent ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  申請者
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  請求時間
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  狀態
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                    載入中...
                  </td>
                </tr>
              ) : requests.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                    沒有找到申請記錄
                  </td>
                </tr>
              ) : (
                requests.map((request) => (
                  <tr key={request.request_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {request.request_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {request.agent_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {request.agent_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {request.applicant_info.name} ({request.applicant_info.email})
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(request.created_at).toLocaleString('zh-TW')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(request.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end space-x-2">
                        <button
                          onClick={() => handleViewDetail(request)}
                          className="text-blue-600 hover:text-blue-900"
                          title="查看詳情"
                        >
                          <Eye size={16} />
                        </button>
                        {request.status === 'pending' && (
                          <>
                            <button
                              onClick={() => {
                                setSelectedRequest(request);
                                setShowApproveModal(true);
                              }}
                              className="text-green-600 hover:text-green-900"
                              title="批准"
                            >
                              <Check size={16} />
                            </button>
                            <button
                              onClick={() => {
                                setSelectedRequest(request);
                                setShowRejectModal(true);
                              }}
                              className="text-red-600 hover:text-red-900"
                              title="拒絕"
                            >
                              <X size={16} />
                            </button>
                          </>
                        )}
                        {request.status === 'approved' && (
                          <button
                            onClick={() => {
                              setSelectedRequest(request);
                              setShowRevokeModal(true);
                            }}
                            className="text-orange-600 hover:text-orange-900"
                            title="撤銷"
                          >
                            <AlertCircle size={16} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* 分頁 */}
        {totalPages > 1 && (
          <div className="mt-6 flex items-center justify-between">
            <div className="text-sm text-gray-700">
              顯示 {((filters.page || 1) - 1) * (filters.page_size || 20) + 1} -{' '}
              {Math.min((filters.page || 1) * (filters.page_size || 20), total)} 條，共 {total} 條
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => setFilters({ ...filters, page: (filters.page || 1) - 1 })}
                disabled={(filters.page || 1) === 1}
                className="px-4 py-2 bg-white border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                上一頁
              </button>
              <button
                onClick={() => setFilters({ ...filters, page: (filters.page || 1) + 1 })}
                disabled={(filters.page || 1) === totalPages}
                className="px-4 py-2 bg-white border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                下一頁
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 詳情 Modal */}
      {showDetailModal && selectedRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900">申請詳情</h2>
              <button
                onClick={() => setShowDetailModal(false)}
                className="text-gray-600 hover:text-gray-900"
              >
                <X size={20} />
              </button>
            </div>

            <div className="space-y-6">
              {/* 基本信息 */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">基本信息</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-500">申請 ID</p>
                    <p className="text-base text-gray-900">{selectedRequest.request_id}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Agent ID</p>
                    <p className="text-base text-gray-900">{selectedRequest.agent_id}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Agent 名稱</p>
                    <p className="text-base text-gray-900">{selectedRequest.agent_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">狀態</p>
                    {getStatusBadge(selectedRequest.status)}
                  </div>
                  <div className="col-span-2">
                    <p className="text-sm text-gray-500">描述</p>
                    <p className="text-base text-gray-900">{selectedRequest.agent_description}</p>
                  </div>
                </div>
              </div>

              {/* 申請者信息 */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">申請者信息</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-500">姓名</p>
                    <p className="text-base text-gray-900">{selectedRequest.applicant_info.name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">郵箱</p>
                    <p className="text-base text-gray-900">{selectedRequest.applicant_info.email}</p>
                  </div>
                  {selectedRequest.applicant_info.company && (
                    <div>
                      <p className="text-sm text-gray-500">公司</p>
                      <p className="text-base text-gray-900">{selectedRequest.applicant_info.company}</p>
                    </div>
                  )}
                  {selectedRequest.applicant_info.contact_phone && (
                    <div>
                      <p className="text-sm text-gray-500">聯繫電話</p>
                      <p className="text-base text-gray-900">{selectedRequest.applicant_info.contact_phone}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Agent 配置 */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">Agent 配置</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-500">Agent 類型</p>
                    <p className="text-base text-gray-900">{selectedRequest.agent_config.agent_type}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">協議類型</p>
                    <p className="text-base text-gray-900">{selectedRequest.agent_config.protocol}</p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-sm text-gray-500">端點 URL</p>
                    <p className="text-base text-gray-900">{selectedRequest.agent_config.endpoint_url}</p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-sm text-gray-500">能力列表</p>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {selectedRequest.agent_config.capabilities.map((cap, idx) => (
                        <span key={idx} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {cap}
                        </span>
                      ))}
                    </div>
                  </div>
                  {selectedRequest.agent_config.input_schema && (
                    <div className="col-span-2">
                      <p className="text-sm text-gray-500 mb-2">輸入 Schema</p>
                      <pre className="bg-gray-50 rounded-md p-4 text-xs overflow-x-auto">
                        {JSON.stringify(selectedRequest.agent_config.input_schema, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>

              {/* 請求的權限 */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">請求的權限</h3>
                <div className="bg-gray-50 rounded-md p-4">
                  <pre className="text-xs overflow-x-auto">
                    {JSON.stringify(selectedRequest.requested_permissions, null, 2)}
                  </pre>
                </div>
              </div>

              {/* 審查信息 (如已審查) */}
              {selectedRequest.review_info && (selectedRequest.review_info.reviewed_by || selectedRequest.review_info.review_notes || selectedRequest.review_info.rejection_reason) && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-3">審查信息</h3>
                  <div className="grid grid-cols-2 gap-4">
                    {selectedRequest.review_info.reviewed_by && (
                      <div>
                        <p className="text-sm text-gray-500">審查人</p>
                        <p className="text-base text-gray-900">{selectedRequest.review_info.reviewed_by}</p>
                      </div>
                    )}
                    {selectedRequest.review_info.reviewed_at && (
                      <div>
                        <p className="text-sm text-gray-500">審查時間</p>
                        <p className="text-base text-gray-900">
                          {new Date(selectedRequest.review_info.reviewed_at).toLocaleString('zh-TW')}
                        </p>
                      </div>
                    )}
                    {selectedRequest.review_info.review_notes && (
                      <div className="col-span-2">
                        <p className="text-sm text-gray-500">審查意見</p>
                        <p className="text-base text-gray-900">{selectedRequest.review_info.review_notes}</p>
                      </div>
                    )}
                    {selectedRequest.review_info.rejection_reason && (
                      <div className="col-span-2">
                        <p className="text-sm text-gray-500">拒絕原因</p>
                        <p className="text-base text-red-600">{selectedRequest.review_info.rejection_reason}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Secret 信息 (如已批准) */}
              {selectedRequest.status === 'approved' && selectedRequest.secret_info?.secret_id && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-3">Secret 信息</h3>
                  <div className="bg-blue-50 rounded-md p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">Secret ID</p>
                        <p className="text-base text-gray-900 font-mono">{selectedRequest.secret_info.secret_id}</p>
                      </div>
                      <button
                        onClick={() => copyToClipboard(selectedRequest.secret_info!.secret_id!)}
                        className="text-blue-600 hover:text-blue-900"
                        title="複製"
                      >
                        <Copy size={16} />
                      </button>
                    </div>
                    <p className="text-xs text-gray-600 mt-2">
                      注意: Secret Key 僅在批准時顯示一次,已無法再次查看。
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowDetailModal(false)}
                className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
              >
                關閉
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 批准確認 Modal */}
      {showApproveModal && selectedRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">批准申請</h2>
            <p className="text-gray-700 mb-6">
              確定要批准 Agent "{selectedRequest.agent_name}" 的註冊申請嗎？
            </p>
            <p className="text-sm text-gray-600 mb-6">
              批准後將生成 Secret ID 和 Secret Key，Secret Key 僅顯示一次，請妥善保存。
            </p>
            <div className="flex space-x-3">
              <button
                onClick={handleApprove}
                className="flex-1 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
              >
                確認批准
              </button>
              <button
                onClick={() => setShowApproveModal(false)}
                className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Secret 顯示 Modal (批准後) */}
      {showSecretModal && approvalResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-2xl w-full">
            <div className="flex items-center space-x-2 mb-4">
              <AlertCircle className="text-yellow-600" size={24} />
              <h2 className="text-xl font-semibold text-gray-900">申請已批准 - Secret 信息</h2>
            </div>

            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6">
              <p className="text-sm text-yellow-800">
                <strong>重要提示:</strong> Secret Key 僅顯示此一次，請立即複製並妥善保存。關閉此視窗後將無法再次查看。
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Secret ID</label>
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    value={approvalResult.secret_id}
                    readOnly
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md bg-gray-50 font-mono text-sm"
                  />
                  <button
                    onClick={() => copyToClipboard(approvalResult.secret_id)}
                    className="px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                    title="複製"
                  >
                    <Copy size={16} />
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Secret Key</label>
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    value={approvalResult.secret_key}
                    readOnly
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md bg-gray-50 font-mono text-sm"
                  />
                  <button
                    onClick={() => copyToClipboard(approvalResult.secret_key)}
                    className="px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                    title="複製"
                  >
                    <Copy size={16} />
                  </button>
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => {
                  setShowSecretModal(false);
                  setApprovalResult(null);
                  setSelectedRequest(null);
                }}
                className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
              >
                我已保存,關閉
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 拒絕 Modal */}
      {showRejectModal && selectedRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">拒絕申請</h2>
            <p className="text-gray-700 mb-4">
              拒絕 Agent "{selectedRequest.agent_name}" 的註冊申請
            </p>
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                拒絕原因 (必填)
              </label>
              <textarea
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                rows={4}
                placeholder="請說明拒絕原因..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex space-x-3">
              <button
                onClick={handleReject}
                disabled={!rejectionReason}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                確認拒絕
              </button>
              <button
                onClick={() => {
                  setShowRejectModal(false);
                  setRejectionReason('');
                }}
                className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 撤銷 Modal */}
      {showRevokeModal && selectedRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
            <div className="flex items-center space-x-2 mb-4">
              <AlertCircle className="text-orange-600" size={24} />
              <h2 className="text-xl font-semibold text-gray-900">撤銷申請</h2>
            </div>
            <p className="text-gray-700 mb-4">
              撤銷 Agent "{selectedRequest.agent_name}" 的批准
            </p>
            <div className="bg-orange-50 border-l-4 border-orange-400 p-4 mb-6">
              <p className="text-sm text-orange-800">
                <strong>警告:</strong> 撤銷後該 Agent 將無法使用，需要重新申請。
              </p>
            </div>
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                撤銷原因 (必填)
              </label>
              <textarea
                value={revocationReason}
                onChange={(e) => setRevocationReason(e.target.value)}
                rows={4}
                placeholder="請說明撤銷原因..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex space-x-3">
              <button
                onClick={handleRevoke}
                disabled={!revocationReason}
                className="flex-1 px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                確認撤銷
              </button>
              <button
                onClick={() => {
                  setShowRevokeModal(false);
                  setRevocationReason('');
                }}
                className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentRequestManagement;
