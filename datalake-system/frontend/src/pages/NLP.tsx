import { Card, Input, Button, Typography, Row, Col, Tag, Table, Badge, Tooltip } from 'antd';
import { useState, useEffect, useRef, useCallback } from 'react';
import { SendOutlined, ClearOutlined, ClockCircleOutlined, DatabaseOutlined, CheckCircleOutlined, FileSearchOutlined, BarChartOutlined, SyncOutlined } from '@ant-design/icons';
import { useDashboardStore } from '../stores/dashboardStore';
import { useAIStatusStore, AIStatusEvent } from '../stores/aiStatusStore';
import BrainIcon from '../components/BrainIcon';
import AIStatusWindow from '../components/AIStatusWindow';
import { mmAgentBusinessProcess, mmAgentAutoExecute, executeSqlQuery, dataAgentApi } from '../lib/api';
import { v4 as uuidv4 } from 'uuid';
import Markdown from 'react-markdown';

const FRONTEND_API = 'http://localhost:8005';
const MM_AGENT_API = 'http://localhost:8003';
import './pages.css';

// 產生唯一 ID 的輔助函數
const generateUniqueId = (): string => uuidv4();

const { Title, Text } = Typography;
const { TextArea } = Input;

interface IntentInfo {
  intent_type?: string;
  description?: string;
  table?: string;
  warehouse?: string;
}

interface IntentClassification {
  success: boolean;
  intent: 'GREETING' | 'KNOWLEDGE_QUERY' | 'SIMPLE_QUERY' | 'COMPLEX_TASK' | 'CLARIFICATION';
  confidence: number;
  is_simple_query: boolean;
  needs_clarification: boolean;
  missing_fields: string[];
  clarification_prompts: Record<string, string>;
  thought_process: string;
  session_id: string;
  knowledge_source_type?: 'internal' | 'external' | 'unknown';
}

const EXAMPLE_QUERIES = [
  '查詢 W01 倉庫的庫存總量',
  '列出所有負庫存的物料',
  '統計 2024 年的採購進貨筆數',
  '查詢料號 10-0001 的庫存信息',
  'RM05-008 上月買進多少',
];

export default function NLPPage() {
  const { chatMessages, addChatMessage, updateChatMessage, clearChatMessages } = useDashboardStore();
  const { currentStatus, isConnected, isWindowOpen, toggleWindow, setCurrentStatus, openWindow, addEvent, clearEvents, setIsConnected } = useAIStatusStore();
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [queryStep, setQueryStep] = useState(0);
  const [queryResult, setQueryResult] = useState<any>(null);
  const [sqlQuery, setSqlQuery] = useState('');
  const [intentInfo, setIntentInfo] = useState<IntentInfo | null>(null);
  const [execTime, setExecTime] = useState('');
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [showMultiTurnInfo, setShowMultiTurnInfo] = useState(false);
  const [turnCount, setTurnCount] = useState(0);
  const [clarificationInfo, setClarificationInfo] = useState<{
    show: boolean;
    missingFields: string[];
    prompts: Record<string, string>;
  } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [useStreamMode, setUseStreamMode] = useState(true); // SSE 串流模式
  const [thinkingContent, setThinkingContent] = useState('');
  const [planContent, setPlanContent] = useState('');
  const assistantMsgIdRef = useRef<string | null>(null);
  const thinkingContentRef = useRef<string>('');
  const planContentRef = useRef<string>('');
  const wsRef = useRef<WebSocket | null>(null);

  // WebSocket 連接 - 更可靠的實時通信
  const connectWebSocket = useCallback(async (sid: string, instruction: string) => {
    if (!sid || !useStreamMode) return;

    console.log('[WebSocket] 連接:', sid);
    console.log('[WebSocket] URL:', `${MM_AGENT_API.replace('http', 'ws')}/api/v1/chat/ws`);

    // 立即顯示狀態
    thinkingContentRef.current = '## 思考過程\n\n正在連接模型...\n';
    planContentRef.current = '';
    setThinkingContent(thinkingContentRef.current);
    setPlanContent(planContentRef.current);
    setCurrentStatus('processing');
    openWindow();
    console.log('[WebSocket] 窗口已打開');

    // 關閉舊連接
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(`${MM_AGENT_API.replace('http', 'ws')}/api/v1/chat/ws`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WebSocket] 已連接');
      ws.send(JSON.stringify({ session_id: sid, instruction }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('[WebSocket] 收到:', data.type);

        if (data.type === 'workflow_started') {
          thinkingContentRef.current = `#### 思考過程\n\n${data.message || '正在分析...'}\n`;
          setThinkingContent(thinkingContentRef.current);
          planContentRef.current = '';
          setPlanContent('');
          // 只創建一次消息
          const msgId = generateUniqueId();
          assistantMsgIdRef.current = msgId;
          addChatMessage({
            id: msgId,
            role: 'assistant',
            content: thinkingContentRef.current,
            timestamp: new Date().toLocaleString(),
          });
        } else if (data.type === 'thinking') {
          // 只更新狀態，不創建新消息
          thinkingContentRef.current += data.content || '';
          setThinkingContent(thinkingContentRef.current);
          if (assistantMsgIdRef.current) {
            updateChatMessage(assistantMsgIdRef.current, {
              content: `#### 思考過程\n\n${thinkingContentRef.current}`
            });
          }
        } else if (data.type === 'thinking_complete') {
          setThinkingContent(thinkingContentRef.current);
          if (assistantMsgIdRef.current) {
            updateChatMessage(assistantMsgIdRef.current, {
              content: `#### 思考過程\n\n${thinkingContentRef.current}`
            });
          }
        } else if (data.type === 'plan_started') {
          planContentRef.current = '\n\n---\n\n## 任務計劃\n\n';
          setPlanContent(planContentRef.current);
        } else if (data.type === 'plan') {
          planContentRef.current += data.content + '\n';
          setPlanContent(planContentRef.current);
        } else if (data.type === 'ready') {
          // 最終合併更新一次
          const finalContent = `#### 思考過程\n\n${thinkingContentRef.current.trim()}\n\n---\n\n## 任務計劃\n\n${planContentRef.current.replace('\n\n---\n\n## 任務計劃\n\n', '').trim()}\n\n是否開始執行？（回复「是」繼續，「否」取消）`;
          if (assistantMsgIdRef.current) {
            updateChatMessage(assistantMsgIdRef.current, {
              content: finalContent
            });
          }
          setLoading(false);
          setIsConnected(false);
          setCurrentStatus('completed');
          ws.close();
        } else if (data.type === 'complete') {
          setLoading(false);
          setIsConnected(false);
          setCurrentStatus('completed');
          ws.close();
        } else if (data.type === 'error') {
          console.error('[WebSocket] 錯誤:', data.message);
          setLoading(false);
          setIsConnected(false);
          setCurrentStatus('error');
          ws.close();
        }
      } catch (e) {
        console.error('[WebSocket] 解析錯誤:', e);
      }
    };

    ws.onerror = (error) => {
      console.error('[WebSocket] 錯誤:', error);
    };

    ws.onclose = () => {
      console.log('[WebSocket] 已關閉');
    };
  }, [useStreamMode, MM_AGENT_API, openWindow, addChatMessage]);

  // POST SSE 連接 (備用)
  const connectStreamSSE = useCallback(async (sid: string, instruction: string) => {
    if (!sid || !useStreamMode) return;

    console.log('[Stream] 連接串流 SSE (POST):', sid);
    console.log('[Stream] MM_AGENT_API:', MM_AGENT_API);
    console.log('[Stream] useStreamMode:', useStreamMode);

    // 立即顯示狀態，讓用戶知道正在處理（但不要創建消息）
    thinkingContentRef.current = '## 思考過程\n\n正在連接模型...\n';
    planContentRef.current = '';
    setThinkingContent(thinkingContentRef.current);
    setPlanContent(planContentRef.current);
    setCurrentStatus('processing');

    // 打開狀態窗口
    openWindow();
    console.log('[Stream] 窗口已打開');

    // 取消舊請求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      console.log('[Stream] 發送請求到:', `${MM_AGENT_API}/api/v1/chat/stream`);
      const response = await fetch(`${MM_AGENT_API}/api/v1/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sid, instruction }),
        signal: controller.signal,
      });
      console.log('[Stream] 收到響應:', response.status);
      console.log('[Stream] response.ok:', response.ok);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      console.log('[Stream] 開始讀取流...');
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log('[Stream] 流結束');
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        
        // 按行分割
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          const trimmedLine = line.trim();
          if (!trimmedLine) continue;
          
          // SSE 格式: event: xxx\ndata: yyy
          if (trimmedLine.startsWith('data: ')) {
            try {
              const dataStr = trimmedLine.slice(6);
              const data = JSON.parse(dataStr);
              console.log('[Stream] 收到 JSON:', data.type);

              if (data.type === 'workflow_started') {
                thinkingContentRef.current = `#### 思考過程\n\n${data.message || '正在分析...'}\n`;
                setThinkingContent(thinkingContentRef.current);
                // 創建第一條消息
                const msgId = generateUniqueId();
                assistantMsgIdRef.current = msgId;
                addChatMessage({
                  id: msgId,
                  role: 'assistant',
                  content: thinkingContentRef.current,
                  timestamp: new Date().toLocaleString(),
                });
               } else if (data.type === 'thinking') {
                  thinkingContentRef.current += data.content || '';
                  setThinkingContent(thinkingContentRef.current);
                  if (assistantMsgIdRef.current) {
                    updateChatMessage(assistantMsgIdRef.current, {
                      content: `#### 思考過程\n\n${thinkingContentRef.current}`
                    });
                  }
                } else if (data.type === 'thinking_complete') {
                  setThinkingContent(thinkingContentRef.current);
                  if (assistantMsgIdRef.current) {
                    updateChatMessage(assistantMsgIdRef.current, {
                      content: `#### 思考過程\n\n${thinkingContentRef.current}`
                    });
                  }
                } else if (data.type === 'plan_started') {
                  planContentRef.current = '\n\n---\n\n## 任務計劃\n\n';
                  setPlanContent(planContentRef.current);
                } else if (data.type === 'plan') {
                  planContentRef.current += data.content + '\n';
                  setPlanContent(planContentRef.current);
                } else if (data.type === 'ready') {
                  const finalContent = `#### 思考過程\n\n${thinkingContentRef.current.trim()}\n\n---\n\n## 任務計劃\n\n${planContentRef.current.replace('\n\n---\n\n## 任務計劃\n\n', '').trim()}\n\n是否開始執行？（回复「是」繼續，「否」取消）`;
                 if (assistantMsgIdRef.current) {
                   updateChatMessage(assistantMsgIdRef.current, {
                     content: finalContent
                   });
                 }
                 setLoading(false);
                 setIsConnected(false);
                 setCurrentStatus('completed');
                 return;
              } else if (data.type === 'complete') {
                setLoading(false);
                setIsConnected(false);
                setCurrentStatus('completed');
                return;
              } else if (data.type === 'error') {
                console.error('[Stream] 錯誤:', data.message);
                setLoading(false);
                setIsConnected(false);
                setCurrentStatus('error');
              }
            } catch (e) {
              console.error('[Stream] JSON 解析錯誤:', e);
            }
          }
        }
      }
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('[Stream] 錯誤:', error);
        setLoading(false);
        setIsConnected(false);
        setCurrentStatus('error');
      }
    }
  }, [useStreamMode, openWindow, setCurrentStatus, setIsConnected, addChatMessage, updateChatMessage]);

  // 調用意圖分類端點（使用 LLM）
  const classifyIntent = async (instruction: string): Promise<IntentClassification | null> => {
    try {
      const response = await fetch(`${MM_AGENT_API}/api/v1/chat/intent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction, session_id: sessionId }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('意圖分類失敗:', error);
      return null;
    }
  };

  // 清理
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const now = new Date().toLocaleString();
    addChatMessage({ id: generateUniqueId(), role: 'user', content: input, timestamp: now });
    setInput('');
    setLoading(true);
    setQueryStep(1);
    setQueryResult(null);
    setExecTime('');
    clearEvents();

    const currentSessionId = sessionId || `sess-${Date.now()}`;
    if (!sessionId) {
      setSessionId(currentSessionId);
    }

    // 檢測是否為回覆待確認的工作流
    // 如果的最後一條assistant消息包含"是否開始執行"或"回复「是」繼續"，視為工作流確認
    const lastAssistantMsg = chatMessages.length > 0 ? chatMessages[chatMessages.length - 1] : null;
    const isWorkflowConfirmation = lastAssistantMsg?.role === 'assistant' && 
      (lastAssistantMsg.content.includes('是否開始執行') || 
       lastAssistantMsg.content.includes('回复「是」') ||
       lastAssistantMsg.content.includes('回复"是"'));

    if (sessionId && isWorkflowConfirmation) {
      // 有進行中的工作流且用戶在回覆確認，直接執行下一步
      console.log('[HandleSend] 檢測到工作流確認，直接執行下一步');
      try {
        const response = await fetch(`${MM_AGENT_API}/api/v1/chat/intent`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            instruction: input,
            session_id: sessionId,
          }),
        });

        const result = await response.json();
        console.log('[HandleSend] 工作流執行結果:', result);

        if (result.workflow_result) {
          // 後端返回了工作流執行結果
          const workflowResult = result.workflow_result;
          addChatMessage({
            id: generateUniqueId(),
            role: 'assistant',
            content: workflowResult.response || '執行完成',
            timestamp: now,
          });

          if (workflowResult.waiting_for_user) {
            setCurrentStatus('waiting_confirmation');
          } else {
            setCurrentStatus('completed');
          }
        } else {
          // 意圖分類返回，可能是 CONTINUE_WORKFLOW 或其他
          addChatMessage({
            id: generateUniqueId(),
            role: 'assistant',
            content: result.intent === 'CONTINUE_WORKFLOW' ? 
              '正在繼續執行...' : 
              `意圖：${result.intent}`,
            timestamp: now,
          });
          setCurrentStatus('completed');
        }
      } catch (error) {
        console.error('[HandleSend] 工作流執行錯誤:', error);
        addChatMessage({
          id: generateUniqueId(),
          role: 'assistant',
          content: `執行錯誤：${error instanceof Error ? error.message : '未知錯誤'}`,
          timestamp: now,
        });
        setCurrentStatus('error');
      }
      setLoading(false);
      return;
    }

    // 使用 LLM 意圖分類替代硬編碼關鍵字匹配
    const intentResult = await classifyIntent(input);

    if (!intentResult || !intentResult.success) {
      // 分類失敗時使用簡單回退邏輯
      console.warn('意圖分類失敗，使用回退邏輯');
    }

    const intent = intentResult?.intent || 'SIMPLE_QUERY';
    const isSimpleQuery = intent === 'SIMPLE_QUERY' && !(intentResult?.needs_clarification);
    const isComplexTask = intent === 'COMPLEX_TASK';
    const isKnowledgeQuery = intent === 'KNOWLEDGE_QUERY';
    const needsClarification = intentResult?.needs_clarification || false;

    // 1. 首先檢測對話管理意圖（前端第一層 GAI 處理）
    const inputLower = input.trim().toLowerCase();
    const isCancel = /^(取消|算了|停止|不做了)/i.test(input);
    const isContinue = /^(继续|下一步|執行|执行|是|y|yes)/i.test(input);
    const isThanks = /^(谢谢|感謝|感謝|太棒了)/i.test(input);

    // 處理取消
    if (isCancel) {
      addChatMessage({
        id: generateUniqueId(),
        role: 'assistant',
        content: '**已取消**\n\n您可以輸入新的問題，我會繼續為您服務。',
        timestamp: now,
      });
      setLoading(false);
      setCurrentStatus('idle');
      return;
    }

    // 處理繼續
    if (isContinue) {
      if (sessionId) {
        addChatMessage({
          id: generateUniqueId(),
          role: 'assistant',
          content: '**繼續執行**\n\n請輸入您想繼續的任務，我會為您處理。',
          timestamp: now,
        });
      } else {
        addChatMessage({
          id: generateUniqueId(),
          role: 'assistant',
          content: '目前沒有進行中的任務。請輸入新的問題。',
          timestamp: now,
        });
      }
      setLoading(false);
      setCurrentStatus('idle');
      return;
    }

    // 處理感謝
    if (isThanks) {
      addChatMessage({
        id: generateUniqueId(),
        role: 'assistant',
        content: '不客氣！很高興能幫助您。有任何問題隨時問我。',
        timestamp: now,
      });
      setLoading(false);
      setCurrentStatus('completed');
      return;
    }

    // 處理需要澄清的情況
    if (needsClarification && intentResult?.clarification_prompts) {
      const prompts = Object.entries(intentResult.clarification_prompts);
      const clarificationItems = prompts.map(([key, value]) => `**${key}：**${value}`).join('\n\n');

      setClarificationInfo({
        show: true,
        missingFields: intentResult.missing_fields || [],
        prompts: intentResult.clarification_prompts || {},
      });

      addChatMessage({
        id: generateUniqueId(),
        role: 'assistant',
        content: `**需要澄清：**\n\n${clarificationItems}\n\n---\n\n您的輸入：「${input}」`,
        timestamp: now,
      });

      setLoading(false);
      setCurrentStatus('clarification');
      return;
    }

    // 處理問候語
    if (intent === 'GREETING') {
      addChatMessage({
        id: generateUniqueId(),
        role: 'assistant',
        content: '您好！我是庫存管理 AI Assistant。請輸入您想查詢的問題，例如：「查詢 W01 倉庫的庫存總量」、「料號 10-0001 的品名」等。',
        timestamp: now,
      });
      setLoading(false);
      setCurrentStatus('completed');
      return;
    }

    // 簡單查詢：直接調用 Data-Agent
    if (isSimpleQuery) {
      try {
        const result = await dataAgentApi.post('/execute', {
          task_id: `query-${generateUniqueId()}`,
          task_type: 'data_query',
          task_data: {
            action: 'execute_structured_query',
            natural_language_query: input,
          },
        });

        const resultData = result.data?.result || {};
        const innerResult = resultData.result || {};
        const sql = innerResult.sql_query || '';
        const rows = innerResult.rows || [];
        const rowCount = innerResult.row_count || 0;
        const error = innerResult.error;

        let responseContent = '';
        let tableData: any[] = [];

        if (error) {
          responseContent = `**查詢錯誤：**\n${error}`;
        } else if (sql) {
          responseContent = `**SQL 查詢：**\n\`\`\`sql\n${sql}\n\`\`\`\n\n`;
          responseContent += `**查詢結果：** ${rowCount} 筆資料\n`;

          if (rows.length > 0) {
            tableData = rows;
            // 如果多於一筆，計算總計
            if (rows.length > 1) {
              const totalRow: any = {};
              const keys = Object.keys(rows[0]);
              for (const key of keys) {
                const sum = rows.reduce((acc, row) => {
                  const val = parseFloat(row[key]);
                  return acc + (isNaN(val) ? 0 : val);
                }, 0);
                totalRow[key] = sum;
              }
              tableData = [...rows, { _total: true, ...totalRow }];
            }
          }
        } else {
          responseContent = '查詢完成，但未返回 SQL';
        }

        addChatMessage({
          id: generateUniqueId(),
          role: 'assistant',
          content: responseContent,
          timestamp: now,
        });

        if (tableData.length > 0) {
          setQueryResult({ result: { data: tableData } });
          setQueryStep(4);
        } else {
          setQueryStep(3);
        }

        setLoading(false);
        setCurrentStatus('completed');

      } catch (error) {
        console.error('錯誤:', error);
        addChatMessage({
          id: generateUniqueId(),
          role: 'assistant',
          content: `抱歉，處理您的查詢時發生錯誤。\n\n錯誤資訊：${error instanceof Error ? error.message : '未知錯誤'}`,
          timestamp: now,
        });
        setCurrentStatus('error');
        setLoading(false);
      }
      return;
    }

    // 知識查詢：KNOWLEDGE_QUERY
    if (isKnowledgeQuery) {
      const sourceType = intentResult?.knowledge_source_type || 'unknown';
      let sourceInfo = '';
      if (sourceType === 'internal') {
        sourceInfo = '（將查詢公司內部知識庫）';
      } else if (sourceType === 'external') {
        sourceInfo = '（將搜尋外部專業知識）';
      }

      addChatMessage({
        id: generateUniqueId(),
        role: 'assistant',
        content: `**知識查詢**${sourceInfo}\n\n正在為您查詢相關知識...`,
        timestamp: now,
      });

      // 調用知識查詢端點
      try {
        const response = await fetch(`${MM_AGENT_API}/api/v1/chat/knowledge`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            instruction: input,
            session_id: currentSessionId,
            metadata: { knowledge_source_type: sourceType }
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();

        if (result.success) {
          addChatMessage({
            id: generateUniqueId(),
            role: 'assistant',
            content: result.answer || '知識查詢完成',
            timestamp: now,
          });
        } else {
          addChatMessage({
            id: generateUniqueId(),
            role: 'assistant',
            content: `抱歉，知識查詢失敗：${result.error || '未知錯誤'}`,
            timestamp: now,
          });
        }
      } catch (error) {
        console.error('知識查詢錯誤:', error);
        addChatMessage({
          id: generateUniqueId(),
          role: 'assistant',
          content: '抱歉，知識查詢失敗。請稍後再試。',
          timestamp: now,
        });
      }

      setLoading(false);
      setCurrentStatus('completed');
      return;
    }

    // 複雜查詢或複雜任務：使用 SSE 串流模式（規範流程）
    if (useStreamMode && (isComplexTask || !isSimpleQuery)) {
      await connectStreamSSE(currentSessionId, input);
      return;
    }

    // 非串流模式（備選）
    try {
      const result = await mmAgentBusinessProcess(input, currentSessionId);

      if (result.session_id) {
        setSessionId(result.session_id);
        setShowMultiTurnInfo(true);
        setTurnCount((prev) => prev + 1);

        const planSteps = result.debug_info?.plan?.steps?.map((s: any) =>
          `Step ${s.step_id}: ${s.description} (${s.action_type})`
        ).join('\n') || '';

        const thoughtProcess = result.debug_info?.thought_process || '';

        addChatMessage({
          id: generateUniqueId(),
          role: 'assistant',
          content: `## 思考過程\n\n${thoughtProcess}\n\n---\n\n## 任務計劃\n\n${planSteps}\n\n是否開始執行？（回复「是」繼續，「否」取消）`,
          timestamp: now,
        });

        setLoading(false);
        return;
      }

      addChatMessage({
        id: generateUniqueId(),
        role: 'assistant',
        content: result.response || '處理完成',
        timestamp: now,
      });
    } catch (error) {
      console.error('錯誤:', error);
      addChatMessage({
        id: generateUniqueId(),
        role: 'assistant',
        content: '抱歉，處理您的查詢時發生錯誤。',
        timestamp: now,
      });
      setCurrentStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const handleExample = (query: string) => {
    setInput(query);
  };

  const handleClear = () => {
    clearChatMessages();
    setSessionId(undefined);
    setShowMultiTurnInfo(false);
    setTurnCount(0);
    setQueryStep(0);
    setIntentInfo(null);
    setClarificationInfo(null);
    setCurrentStatus('idle');
    clearEvents();
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setIsConnected(false);
  };

  return (
    <div className="page-container" style={{ height: '100%' }}>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={3} style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 12 }}>
            <BrainIcon />
            自然語言查詢
            {showMultiTurnInfo && (
              <Tooltip title={`多輪對話模式 - 已進行 ${turnCount} 輪對話`}>
                <Badge
                  count={<SyncOutlined spin={loading} />}
                  style={{ backgroundColor: '#52c41a' }}
                />
              </Tooltip>
            )}
          </Title>
          <Text type="secondary" style={{ marginLeft: 40 }}>
            輸入自然語言，系統自動轉換為 SQL 查詢
            {showMultiTurnInfo && sessionId && (
              <Tag color="green" style={{ marginLeft: 8 }}>
                多輪對話模式 ({turnCount} 輪)
              </Tag>
            )}
          </Text>
        </div>
        <AIStatusWindow />
        {showMultiTurnInfo && (
          <Button size="small" onClick={handleClear}>
            開始新對話
          </Button>
        )}
      </div>

      <Row gutter={16} style={{ flex: 1, minHeight: 0 }}>
        <Col span={14} style={{ height: '100%' }}>
          <Card
            styles={{
              body: {
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                padding: '12px',
                overflow: 'hidden',
              },
            }}
            style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
          >
            <Title level={5}>💬 對話</Title>
            <div
              className="chat-messages"
              style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}
            >
              {chatMessages.map((msg) => (
                <div key={msg.id} className={`chat-message ${msg.role}`}>
                  <div className="message-content">
                    <Markdown
                      components={{
                        p: ({ children }) => <p style={{ margin: '0.5em 0', lineHeight: '1.6' }}>{children}</p>,
                        h1: ({ children }) => <h1 style={{ fontSize: '1.5em', margin: '0.8em 0' }}>{children}</h1>,
                        h2: ({ children }) => <h2 style={{ fontSize: '1.3em', margin: '0.7em 0', color: '#ff4d4f' }}>{children}</h2>,
                        h3: ({ children }) => <h3 style={{ fontSize: '1.1em', margin: '0.6em 0', color: '#ff4d4f' }}>{children}</h3>,
                        h4: ({ children }) => (
                          <h4 style={{ 
                            fontSize: '1em', 
                            margin: '0.5em 0', 
                            color: '#1890ff',
                            fontWeight: 'bold',
                            fontStyle: 'italic',
                          }}>
                            {children}
                          </h4>
                        ),
                        ul: ({ children }) => <ul style={{ paddingLeft: '1.5em', margin: '0.8em 0', lineHeight: '1.8' }}>{children}</ul>,
                        ol: ({ children }) => <ol style={{ paddingLeft: '1.5em', margin: '0.8em 0', lineHeight: '1.8' }}>{children}</ol>,
                        li: ({ children }) => <li style={{ margin: '0.4em 0' }}>{children}</li>,
                        code: ({ inline, className, children, ...props }: any) => {
                          if (inline) {
                            return <code style={{ backgroundColor: '#f5f5f5', padding: '2px 6px', borderRadius: 4, fontFamily: 'monospace' }}>{children}</code>;
                          }
                          return <code className={className} style={{ display: 'block', backgroundColor: '#f5f5f5', padding: '10px', borderRadius: 4, overflowX: 'auto' }} {...props}>{children}</code>;
                        },
                        pre: ({ children }) => <pre style={{ backgroundColor: '#f5f5f5', padding: '10px', borderRadius: 4, overflowX: 'auto', margin: '0.5em 0' }}>{children}</pre>,
                        strong: ({ children }) => {
                          // 判斷是否為 clarification 內容
                          const isClarification = msg.content.includes('需要澄清');
                          // 判斷是否為 Step 標題（數字開頭）
                          const isStepTitle = typeof children === 'string' && /^Step\d+/.test(children.trim());
                          
                          return (
                            <strong style={{ 
                              fontWeight: 'bold',
                              color: isClarification ? '#ff4d4f' : '#000000',
                              backgroundColor: isClarification ? '#fff2f0' : 'transparent',
                              padding: isClarification ? '2px 6px' : '0',
                              borderRadius: isClarification ? '4px' : '0',
                              border: isClarification ? '1px solid #ffa39e' : 'none',
                            }}>
                              {children}
                            </strong>
                          );
                        },
                        em: ({ children }) => <em style={{ fontStyle: 'italic' }}>{children}</em>,
                      }}
                    >
                      {msg.content}
                    </Markdown>
                  </div>
                  <div className="message-time">{msg.timestamp}</div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            <div style={{ marginTop: 8, flexShrink: 0 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                範例查詢：
              </Text>
              {EXAMPLE_QUERIES.map((q, idx) => (
                <Tag
                  key={idx}
                  style={{ cursor: 'pointer', marginBottom: 4 }}
                  onClick={() => handleExample(q)}
                >
                  {q}
                </Tag>
              ))}
            </div>

            <div style={{ display: 'flex', gap: 8, marginTop: 8, flexShrink: 0 }}>
              <TextArea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={showMultiTurnInfo ? "繼續對話..." : "輸入您的問題..."}
                rows={2}
                style={{ flex: 1 }}
                onPressEnter={(e: any) => {
                  if (!e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
              />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={handleSend}
                  loading={loading}
                >
                  送出
                </Button>
                <Button icon={<ClearOutlined />} onClick={handleClear}>
                  清空
                </Button>
              </div>
            </div>
          </Card>
        </Col>

        <Col span={10} style={{ height: '100%' }}>
          <Card
            styles={{ body: { padding: '12px', overflowY: 'auto' } }}
            style={{ height: '100%', overflowY: 'auto' }}
          >
            <Title level={5}>📋 執行流程</Title>

            {showMultiTurnInfo && (
              <div style={{ marginBottom: 16, padding: 8, background: '#f6ffed', borderRadius: 4, border: '1px solid #b7eb8f' }}>
                <Text strong style={{ color: '#52c41a' }}>
                  <SyncOutlined style={{ marginRight: 4 }} />
                  多輪對話模式
                </Text>
                <div style={{ fontSize: 12, marginTop: 4, color: '#666' }}>
                  支持指代消解
                </div>
                {sessionId && (
                  <div style={{ fontSize: 11, marginTop: 4, color: '#999' }}>
                    ID: {sessionId.substring(0, 20)}...
                  </div>
                )}
              </div>
            )}

            <div style={{ position: 'relative' }}>
              <div style={{
                position: 'absolute', left: 15, top: 20, bottom: 20, width: 2,
                background: queryStep >= 2 ? '#52c41a' : '#e8e8e8', zIndex: 0,
              }} />
              <div style={{
                position: 'absolute', left: 15, top: 20, bottom: 20, width: 2,
                background: queryStep >= 3 ? '#52c41a' : 'transparent', zIndex: 0,
                transition: 'all 0.3s',
              }} />

              <div style={{ position: 'relative', marginBottom: 16, paddingLeft: 40, zIndex: 1 }}>
                <div style={{
                  position: 'absolute', left: 6, top: 0, width: 20, height: 20,
                  borderRadius: '50%',
                  background: queryStep >= 1 ? '#52c41a' : '#e8e8e8',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {queryStep >= 1 ? (
                    <CheckCircleOutlined style={{ color: 'white', fontSize: 12 }} />
                  ) : (
                    <FileSearchOutlined style={{ color: '#999', fontSize: 12 }} />
                  )}
                </div>
                <Text strong style={{ color: queryStep >= 1 ? '#52c41a' : '#999' }}>
                  分析查詢意圖
                </Text>
              </div>

              <div style={{ position: 'relative', marginBottom: 16, paddingLeft: 40, zIndex: 1 }}>
                <div style={{
                  position: 'absolute', left: 6, top: 0, width: 20, height: 20,
                  borderRadius: '50%',
                  background: queryStep >= 2 ? '#52c41a' : '#e8e8e8',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {queryStep >= 2 ? (
                    <CheckCircleOutlined style={{ color: 'white', fontSize: 12 }} />
                  ) : (
                    <DatabaseOutlined style={{ color: '#999', fontSize: 12 }} />
                  )}
                </div>
                <Text strong style={{ color: queryStep >= 2 ? '#52c41a' : '#999' }}>
                  生成 SQL
                </Text>
              </div>

              <div style={{ position: 'relative', marginBottom: 16, paddingLeft: 40, zIndex: 1 }}>
                <div style={{
                  position: 'absolute', left: 6, top: 0, width: 20, height: 20,
                  borderRadius: '50%',
                  background: queryStep >= 3 ? '#52c41a' : '#e8e8e8',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {queryStep >= 3 ? (
                    <CheckCircleOutlined style={{ color: 'white', fontSize: 12 }} />
                  ) : (
                    <ClockCircleOutlined style={{ color: '#999', fontSize: 12 }} />
                  )}
                </div>
                <Text strong style={{ color: queryStep >= 3 ? '#52c41a' : '#999' }}>
                  執行查詢
                </Text>
              </div>

              <div style={{ position: 'relative', paddingLeft: 40, zIndex: 1 }}>
                <div style={{
                  position: 'absolute', left: 6, top: 0, width: 20, height: 20,
                  borderRadius: '50%',
                  background: queryStep >= 4 ? '#52c41a' : '#e8e8e8',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {queryStep >= 4 ? (
                    <CheckCircleOutlined style={{ color: 'white', fontSize: 12 }} />
                  ) : (
                    <BarChartOutlined style={{ color: '#999', fontSize: 12 }} />
                  )}
                </div>
                <Text strong style={{ color: queryStep >= 4 ? '#52c41a' : '#999' }}>
                  顯示結果
                </Text>
                {queryStep >= 4 && queryResult?.result?.data && (
                  <div style={{ marginTop: 8 }}>
                    <Table
                      dataSource={queryResult.result.data.slice(0, 10)}
                      columns={Object.keys(queryResult.result.data[0] || {})
                        .map((key) => ({
                          title: key,
                          dataIndex: key,
                          key,
                          ellipsis: true,
                          width: 100,
                        }))}
                      size="small"
                      pagination={false}
                    />
                  </div>
                )}
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
