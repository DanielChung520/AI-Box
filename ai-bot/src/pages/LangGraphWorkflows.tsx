// 代碼功能說明: LangGraph 工作流管理頁面
// 創建日期: 2026-01-24
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-24

import React, { useState, useEffect } from 'react';
import { PlayCircle, Eye, CheckCircle, XCircle, Loader, ArrowLeft, Image as ImageIcon, FileText } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface WorkflowExecution {
  workflow_id: string;
  status: 'running' | 'completed' | 'failed';
  start_time?: string;
  end_time?: string;
  execution_time?: number;
  node_count?: number;
  error_count?: number;
  layers_executed?: string[];
  final_layer?: string;
}

interface AgentInfo {
  name: string;
  description: string;
  layer: string;
}

const LangGraphWorkflows: React.FC = () => {
  const navigate = useNavigate();
  const [executing, setExecuting] = useState(false);
  const [workflows, setWorkflows] = useState<WorkflowExecution[]>([]);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowExecution | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [visionResults, setVisionResults] = useState<any[]>([]); // 新增：視覺結果
  const [formData, setFormData] = useState({
    task: '',
    user_id: '',
    context: ''
  });

  // 獲取工作流列表
  const fetchWorkflows = async () => {
    try {
      // 這裡應該調用後端API來獲取工作流列表
      // 現在先使用模擬數據
      setWorkflows([
        {
          workflow_id: 'wf_001',
          status: 'completed',
          start_time: '2026-01-24T10:00:00Z',
          end_time: '2026-01-24T10:05:30Z',
          execution_time: 5.3,
          node_count: 12,
          error_count: 0,
          layers_executed: ['semantic_analysis', 'intent_classification', 'capability_matching'],
          final_layer: 'response_generation'
        }
      ]);
    } catch (error) {
      console.error('獲取工作流列表失敗');
    }
  };

  // 獲取Agent列表
  const fetchAgents = async () => {
    try {
      const response = await fetch('/api/langgraph/agents');
      if (response.ok) {
        const data = await response.json();
        setAgents(data.data.agents);
      }
    } catch (error) {
      console.error('獲取Agent列表失敗');
    }
  };

  // 執行工作流
  const executeWorkflow = async () => {
    if (!formData.task || !formData.user_id) {
      alert('請填寫任務描述和用戶ID');
      return;
    }

    setExecuting(true);
    try {
      const response = await fetch('/api/langgraph/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task: formData.task,
          user_id: formData.user_id,
          session_id: `session_${formData.user_id}`,
          context: formData.context ? JSON.parse(formData.context) : {},
          workflow_config: {}
        })
      });

      if (response.ok) {
        alert('工作流已啟動');
        fetchWorkflows(); // 重新獲取工作流列表
        setFormData({ task: '', user_id: '', context: '' });
      } else {
        alert('工作流執行失敗');
      }
    } catch (error) {
      alert('工作流執行失敗');
    } finally {
      setExecuting(false);
    }
  };

  // 獲取工作流結果
  const getWorkflowResults = async (workflowId: string) => {
    try {
      const response = await fetch(`/api/langgraph/results/${workflowId}`);
      if (response.ok) {
        const data = await response.json();
        setSelectedWorkflow(data.data);
        setVisionResults(data.data.final_state?.vision_analysis || []); // 提取視覺結果
        setModalVisible(true);
      } else {
        alert('獲取工作流結果失敗');
      }
    } catch (error) {
      alert('獲取工作流結果失敗');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Loader className="w-4 h-4 animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Loader className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-blue-600 bg-blue-100';
      case 'completed':
        return 'text-green-600 bg-green-100';
      case 'failed':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  useEffect(() => {
    fetchWorkflows();
    fetchAgents();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => navigate('/home')}
            className="flex items-center space-x-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            <ArrowLeft size={20} />
            <span>返回</span>
          </button>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">LangGraph 工作流管理</h1>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* 工作流執行區域 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold mb-6 text-gray-900 dark:text-white">執行新工作流</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                任務描述 *
              </label>
              <textarea
                rows={4}
                value={formData.task}
                onChange={(e) => setFormData({ ...formData, task: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                placeholder="請描述您要執行的工作流任務..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                用戶ID *
              </label>
              <input
                type="text"
                value={formData.user_id}
                onChange={(e) => setFormData({ ...formData, user_id: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                placeholder="輸入用戶ID"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                上下文信息 (JSON格式，可選)
              </label>
              <textarea
                rows={3}
                value={formData.context}
                onChange={(e) => setFormData({ ...formData, context: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                placeholder='{"key": "value"}'
              />
            </div>

            <button
              onClick={executeWorkflow}
              disabled={executing}
              className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-6 py-2 rounded-md transition-colors"
            >
              {executing ? (
                <Loader className="w-4 h-4 animate-spin" />
              ) : (
                <PlayCircle className="w-4 h-4" />
              )}
              <span>{executing ? '執行中...' : '執行工作流'}</span>
            </button>
          </div>
        </div>

        {/* Agent 列表 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold mb-6 text-gray-900 dark:text-white">可用 Agent</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((agent) => (
              <div key={agent.name} className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
                <h3 className="font-medium text-gray-900 dark:text-white">{agent.name}</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{agent.description}</p>
                <span className="inline-block mt-2 px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded">
                  {agent.layer}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* 工作流歷史 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold mb-6 text-gray-900 dark:text-white">工作流執行歷史</h2>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-600">
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">工作流ID</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">狀態</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">執行時間</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">節點數</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">錯誤數</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">操作</th>
                </tr>
              </thead>
              <tbody>
                {workflows.map((workflow) => (
                  <tr key={workflow.workflow_id} className="border-b border-gray-100 dark:border-gray-700">
                    <td className="py-3 px-4 text-gray-900 dark:text-white font-mono text-xs">
                      {workflow.workflow_id}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs ${getStatusColor(workflow.status)}`}>
                        {getStatusIcon(workflow.status)}
                        <span>{workflow.status === 'running' ? '執行中' : workflow.status === 'completed' ? '完成' : '失敗'}</span>
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                      {workflow.execution_time ? `${workflow.execution_time.toFixed(2)}s` : '-'}
                    </td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                      {workflow.node_count || '-'}
                    </td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                      {workflow.error_count || '-'}
                    </td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => getWorkflowResults(workflow.workflow_id)}
                        className="flex items-center space-x-1 text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200"
                      >
                        <Eye className="w-4 h-4" />
                        <span>查看</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 工作流結果模態框 */}
      {modalVisible && selectedWorkflow && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">工作流執行結果</h3>
                <button
                  onClick={() => setModalVisible(false)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                >
                  <XCircle className="w-6 h-6" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <span className="font-medium text-gray-900 dark:text-white">工作流ID:</span>
                  <span className="ml-2 font-mono text-sm text-gray-600 dark:text-gray-400">
                    {selectedWorkflow.workflow_id}
                  </span>
                </div>

                <div>
                  <span className="font-medium text-gray-900 dark:text-white">狀態:</span>
                  <span className={`ml-2 inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs ${getStatusColor(selectedWorkflow.status)}`}>
                    {getStatusIcon(selectedWorkflow.status)}
                    <span>{selectedWorkflow.status === 'running' ? '執行中' : selectedWorkflow.status === 'completed' ? '成功' : '失敗'}</span>
                  </span>
                </div>

                {selectedWorkflow.execution_time && (
                  <div>
                    <span className="font-medium text-gray-900 dark:text-white">執行時間:</span>
                    <span className="ml-2 text-gray-600 dark:text-gray-400">
                      {selectedWorkflow.execution_time.toFixed(2)}s
                    </span>
                  </div>
                )}

                {selectedWorkflow.node_count && (
                  <div>
                    <span className="font-medium text-gray-900 dark:text-white">節點數:</span>
                    <span className="ml-2 text-gray-600 dark:text-gray-400">
                      {selectedWorkflow.node_count}
                    </span>
                  </div>
                )}

                {selectedWorkflow.error_count !== undefined && (
                  <div>
                    <span className="font-medium text-gray-900 dark:text-white">錯誤數:</span>
                    <span className="ml-2 text-gray-600 dark:text-gray-400">
                      {selectedWorkflow.error_count}
                    </span>
                  </div>
                )}

                {selectedWorkflow.final_layer && (
                  <div>
                    <span className="font-medium text-gray-900 dark:text-white">最終層級:</span>
                    <span className="ml-2 text-gray-600 dark:text-gray-400">
                      {selectedWorkflow.final_layer}
                    </span>
                  </div>
                )}

                {selectedWorkflow.layers_executed && (
                  <div>
                    <span className="font-medium text-gray-900 dark:text-white">執行的層級:</span>
                    <span className="ml-2 text-gray-600 dark:text-gray-400">
                      {selectedWorkflow.layers_executed.join(', ')}
                    </span>
                  </div>
                )}

                {/* 視覺分析結果區域 */}
                {visionResults.length > 0 && (
                  <div className="mt-4 border-t border-gray-100 dark:border-gray-700 pt-4">
                    <h4 className="text-md font-semibold mb-3 flex items-center gap-2">
                      <ImageIcon className="w-4 h-4 text-blue-500" />
                      視覺分析結果
                    </h4>
                    <div className="space-y-4">
                      {visionResults.map((result, idx) => (
                        <div key={idx} className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                          <p className="text-xs text-gray-400 font-mono mb-2">文件ID: {result.file_id}</p>
                          <div className="prose prose-sm dark:prose-invert max-w-none">
                            {/* 這裡渲染描述文本，支持簡單的換行 */}
                            {result.description.split('\n').map((line: string, i: number) => (
                              <p key={i} className="mb-1">{line}</p>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div>
                  <span className="font-medium text-gray-900 dark:text-white">推理過程:</span>
                  <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-700 rounded-md">
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {/* 這裡可以顯示更詳細的推理信息 */}
                      工作流已完成執行，詳細的推理過程和中間結果可以在服務器日誌中查看。
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setModalVisible(false)}
                  className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-md transition-colors"
                >
                  關閉
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LangGraphWorkflows;