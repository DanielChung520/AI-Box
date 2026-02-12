/**
 * 代碼功能說明: 知識庫管理 Demo 頁面
 * 創建日期: 2026-02-12
 * 創建人: Daniel Chung
 *
 * 用於測試 KnowledgeBaseModal 組件
 */

import React, { useState } from 'react';
import { BookOpen } from 'lucide-react';
import KnowledgeBaseModal from './KnowledgeBaseModal';

export default function KnowledgeBaseDemoPage() {
  const [showModal, setShowModal] = useState(false);

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <h1 className="text-3xl font-bold mb-6">知識庫管理功能 Demo</h1>

          <div className="prose max-w-none mb-8">
            <h2>功能說明</h2>
            <ul>
              <li><strong>新增知識庫</strong>：創建根目錄，綁定 Domain 和允許的 Major</li>
              <li><strong>新增子目錄</strong>：在根目錄下創建子目錄，自動繼承 Domain</li>
              <li><strong>上傳文件</strong>：選擇目錄後上傳文件</li>
              <li><strong>文件操作</strong>：預覽、刪除</li>
            </ul>

            <h2>操作流程</h2>
            <ol>
              <li>點擊下方「打開知識庫管理」按鈕</li>
              <li>左側顯示知識庫根目錄</li>
              <li>點擊「新增知識庫」創建根目錄</li>
              <li>選擇根目錄，點擊「新增子目錄」</li>
              <li>選擇子目錄，點擊「上傳文件」</li>
            </ol>
          </div>

          <div className="flex gap-4">
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center gap-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              <BookOpen className="w-5 h-5" />
              打開知識庫管理
            </button>
          </div>
        </div>
      </div>

      {/* 知識庫管理 Modal */}
      <KnowledgeBaseModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
      />
    </div>
  );
}
