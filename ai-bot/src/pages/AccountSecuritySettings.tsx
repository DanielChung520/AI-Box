// 代碼功能說明: 賬號/安全群組設置頁面
// 創建日期: 2026-01-17 22:50 UTC+8
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-18 10:30 UTC+8

import React, { useState, useEffect } from 'react';
import { ArrowLeft, Plus, Search, Edit, Trash2, Key, UserCheck, UserX } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  getUsers,
  createUser,
  updateUser,
  deleteUser,
  resetUserPassword,
  toggleUserActive,
  UserAccount,
  UserAccountCreate,
  UserAccountUpdate,
  UserListFilters,
} from '@/lib/api';

const AccountSecuritySettings: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'accounts' | 'security_groups'>('accounts');

  // 用戶列表狀態
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<UserListFilters>({
    page: 1,
    page_size: 20,
  });
  const [searchTerm, setSearchTerm] = useState('');

  // 用戶表單狀態
  const [showUserForm, setShowUserForm] = useState(false);
  const [editingUser, setEditingUser] = useState<UserAccount | null>(null);
  const [userFormData, setUserFormData] = useState<UserAccountCreate>({
    username: '',
    email: '',
    password: '',
    roles: [],
  });

  // 密碼重置狀態
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [resetPasswordUserId, setResetPasswordUserId] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState('');

  // 載入用戶列表
  const loadUsers = async () => {
    setLoading(true);
    try {
      const result = await getUsers(filters);
      setUsers(result.users);
      setTotalUsers(result.total);
    } catch (error) {
      console.error('Failed to load users:', error);
      // 顯示錯誤提示
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'accounts') {
      loadUsers();
    }
  }, [activeTab, filters]);

  // 搜索用戶
  const handleSearch = () => {
    setFilters({ ...filters, search: searchTerm, page: 1 });
  };

  // 返回上一頁或主頁
  const handleBack = () => {
    navigate('/home');
  };

  // 打開創建用戶表單
  const handleCreateUser = () => {
    setEditingUser(null);
    setUserFormData({
      username: '',
      email: '',
      password: '',
      roles: [],
    });
    setShowUserForm(true);
  };

  // 打開編輯用戶表單
  const handleEditUser = (user: UserAccount) => {
    setEditingUser(user);
    setUserFormData({
      username: user.username,
      email: user.email,
      password: '',
      roles: user.roles,
    });
    setShowUserForm(true);
  };

  // 保存用戶
  const handleSaveUser = async () => {
    try {
      if (editingUser) {
        // 更新用戶
        const updateData: UserAccountUpdate = {
          username: userFormData.username,
          email: userFormData.email,
          roles: userFormData.roles,
        };
        await updateUser(editingUser.user_id, updateData);
      } else {
        // 創建用戶
        await createUser(userFormData);
      }
      setShowUserForm(false);
      loadUsers();
    } catch (error) {
      console.error('Failed to save user:', error);
      // 顯示錯誤提示
    }
  };

  // 刪除用戶
  const handleDeleteUser = async (userId: string) => {
    if (!confirm('確定要刪除此用戶嗎?')) return;

    try {
      await deleteUser(userId);
      loadUsers();
    } catch (error) {
      console.error('Failed to delete user:', error);
      // 顯示錯誤提示
    }
  };

  // 切換用戶啟用狀態
  const handleToggleUserActive = async (userId: string) => {
    try {
      await toggleUserActive(userId);
      loadUsers();
    } catch (error) {
      console.error('Failed to toggle user active status:', error);
      // 顯示錯誤提示
    }
  };

  // 打開密碼重置 Modal
  const handleOpenResetPassword = (userId: string) => {
    setResetPasswordUserId(userId);
    setNewPassword('');
    setShowPasswordModal(true);
  };

  // 重置密碼
  const handleResetPassword = async () => {
    if (!resetPasswordUserId || !newPassword) return;

    try {
      await resetUserPassword(resetPasswordUserId, newPassword);
      setShowPasswordModal(false);
      alert('密碼重置成功');
    } catch (error) {
      console.error('Failed to reset password:', error);
      // 顯示錯誤提示
    }
  };

  // 分頁控制
  const totalPages = Math.ceil(totalUsers / (filters.page_size || 20));

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 頂部導航欄 */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            <button
              onClick={handleBack}
              className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft size={20} />
              <span>返回</span>
            </button>
            <div className="h-6 w-px bg-gray-300"></div>
            <h1 className="text-2xl font-bold text-gray-900">賬號/安全群組設置</h1>
          </div>
        </div>

        {/* 標籤頁 */}
        <div className="flex space-x-4">
          <button
            onClick={() => setActiveTab('accounts')}
            className={`px-4 py-2 font-medium transition-colors ${
              activeTab === 'accounts'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            賬號管理
          </button>
          <button
            onClick={() => setActiveTab('security_groups')}
            className={`px-4 py-2 font-medium transition-colors ${
              activeTab === 'security_groups'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            安全群組管理
          </button>
        </div>
      </div>

      {/* 內容區域 */}
      <div className="px-6 py-6">
        {activeTab === 'accounts' ? (
          <div>
            {/* 搜索和創建按鈕 */}
            <div className="mb-6 flex items-center space-x-4">
              <div className="flex-1 flex items-center space-x-2">
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="搜索用戶名或郵箱..."
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
              <button
                onClick={handleCreateUser}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center space-x-2"
              >
                <Plus size={16} />
                <span>創建新用戶</span>
              </button>
            </div>

            {/* 用戶列表表格 */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      用戶名
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      郵箱
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      角色
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      狀態
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      最後登錄
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {loading ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                        載入中...
                      </td>
                    </tr>
                  ) : users.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                        沒有找到用戶
                      </td>
                    </tr>
                  ) : (
                    users.map((user) => (
                      <tr key={user.user_id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {user.username}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {user.email}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <div className="flex flex-wrap gap-1">
                            {user.roles.map((role) => (
                              <span
                                key={role}
                                className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
                              >
                                {role}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              user.is_active
                                ? 'bg-green-100 text-green-800'
                                : 'bg-red-100 text-red-800'
                            }`}
                          >
                            {user.is_active ? '啟用' : '禁用'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {user.last_login_at
                            ? new Date(user.last_login_at).toLocaleString('zh-TW')
                            : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <div className="flex items-center justify-end space-x-2">
                            <button
                              onClick={() => handleEditUser(user)}
                              className="text-blue-600 hover:text-blue-900"
                              title="編輯"
                            >
                              <Edit size={16} />
                            </button>
                            <button
                              onClick={() => handleOpenResetPassword(user.user_id)}
                              className="text-yellow-600 hover:text-yellow-900"
                              title="重置密碼"
                            >
                              <Key size={16} />
                            </button>
                            <button
                              onClick={() => handleToggleUserActive(user.user_id)}
                              className={user.is_active ? 'text-red-600 hover:text-red-900' : 'text-green-600 hover:text-green-900'}
                              title={user.is_active ? '禁用' : '啟用'}
                            >
                              {user.is_active ? <UserX size={16} /> : <UserCheck size={16} />}
                            </button>
                            <button
                              onClick={() => handleDeleteUser(user.user_id)}
                              className="text-red-600 hover:text-red-900"
                              title="刪除"
                            >
                              <Trash2 size={16} />
                            </button>
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
                  {Math.min((filters.page || 1) * (filters.page_size || 20), totalUsers)} 條，共{' '}
                  {totalUsers} 條
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => setFilters({ ...filters, page: (filters.page || 1) - 1 })}
                    disabled={(filters.page || 1) === 1}
                    className="px-4 py-2 bg-white border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    上一頁
                  </button>
                  <div className="flex items-center space-x-1">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => i + 1).map((page) => (
                      <button
                        key={page}
                        onClick={() => setFilters({ ...filters, page })}
                        className={`px-3 py-2 rounded-md text-sm ${
                          (filters.page || 1) === page
                            ? 'bg-blue-600 text-white'
                            : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                        }`}
                      >
                        {page}
                      </button>
                    ))}
                  </div>
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
        ) : (
          <div className="text-center py-12 text-gray-600">
            安全群組管理功能正在開發中...
          </div>
        )}
      </div>

      {/* 用戶表單 Modal */}
      {showUserForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              {editingUser ? '編輯用戶' : '創建新用戶'}
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  用戶名
                </label>
                <input
                  type="text"
                  value={userFormData.username}
                  onChange={(e) => setUserFormData({ ...userFormData, username: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  郵箱
                </label>
                <input
                  type="email"
                  value={userFormData.email}
                  onChange={(e) => setUserFormData({ ...userFormData, email: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              {!editingUser && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    密碼
                  </label>
                  <input
                    type="password"
                    value={userFormData.password}
                    onChange={(e) => setUserFormData({ ...userFormData, password: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  角色 (用逗號分隔)
                </label>
                <input
                  type="text"
                  value={userFormData.roles.join(', ')}
                  onChange={(e) =>
                    setUserFormData({
                      ...userFormData,
                      roles: e.target.value.split(',').map((r) => r.trim()).filter(Boolean),
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="例如: user, admin"
                />
              </div>
            </div>
            <div className="mt-6 flex space-x-3">
              <button
                onClick={handleSaveUser}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                保存
              </button>
              <button
                onClick={() => setShowUserForm(false)}
                className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 密碼重置 Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">重置密碼</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  新密碼
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="輸入新密碼"
                />
              </div>
            </div>
            <div className="mt-6 flex space-x-3">
              <button
                onClick={handleResetPassword}
                disabled={!newPassword}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                確認重置
              </button>
              <button
                onClick={() => setShowPasswordModal(false)}
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

export default AccountSecuritySettings;
