import { Card, Input, Button, Typography, Row, Col, Tag, Table, Badge, Tooltip } from 'antd';
import { useState, useEffect, useRef } from 'react';
import { SendOutlined, ClearOutlined, ClockCircleOutlined, DatabaseOutlined, CheckCircleOutlined, FileSearchOutlined, BarChartOutlined, SyncOutlined } from '@ant-design/icons';
import { useDashboardStore } from '../stores/dashboardStore';
import { mmAgentChat, executeSqlQuery, nlpQuery } from '../lib/api';

const FRONTEND_API = 'http://localhost:8005';
import './pages.css';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface IntentInfo {
  intent_type?: string;
  description?: string;
  table?: string;
  warehouse?: string;
}

const EXAMPLE_QUERIES = [
  '查詢 W01 倉庫的庫存總量',
  '列出所有負庫存的物料',
  '統計 2024 年的採購進貨筆數',
  '查詢料號 10-0001 的庫存信息',
  'RM05-008 上月買進多少',
  '這個料號庫存還有多少',  // 多輪對話範例
];

export default function NLPPage() {
  const { chatMessages, addChatMessage, clearChatMessages } = useDashboardStore();
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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // 檢測是否為工作流程回覆
  const isWorkflowMessage = (content: string): boolean => {
    return content.includes('Step ');
  };

  // 格式化工作流程內容
  const formatWorkflowContent = (content: string): { title: string; steps: string[] } => {
    const lines = content.split('\n');
    const steps: string[] = [];
    let title = '';
    let currentStep = '';
    let inStep = false;

    for (const line of lines) {
      if (line.match(/^(?!◼)\S/) && !line.includes('Step')) {
        title += line + '\n';
      } else if (line.includes('Step')) {
        if (inStep && currentStep) {
          steps.push(currentStep.trim());
        }
        currentStep = line + '\n';
        inStep = true;
      } else if (inStep) {
        currentStep += line + '\n';
      }
    }

    if (inStep && currentStep) {
      steps.push(currentStep.trim());
    }

    return { title: title.trim(), steps };
  };

  // 渲染工作流程步驟
  const renderWorkflowSteps = (content: string) => {
    const { title, steps } = formatWorkflowContent(content);

    return (
      <div>
        {title && (
          <div style={{ marginBottom: 16, fontWeight: 500, whiteSpace: 'pre-wrap' }}>
            {title}
          </div>
        )}
        {steps.map((step, idx) => (
          <div
            key={idx}
            style={{
              marginBottom: 12,
              padding: '12px',
              background: '#f8f9fa',
              borderRadius: 6,
              borderLeft: '3px solid #1890ff',
            }}
          >
            {step.split('\n').map((line, lineIdx) => (
              <div
                key={lineIdx}
                style={{
                  color: line.includes('Step') ? '#1890ff' : '#666',
                  fontWeight: line.includes('Step') ? 600 : 400,
                  marginBottom: lineIdx < step.split('\n').length - 1 ? 4 : 0,
                  whiteSpace: 'pre-wrap',
                }}
              >
                {line}
              </div>
            ))}
          </div>
        ))}
      </div>
    );
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const now = new Date().toLocaleString();
    addChatMessage({ id: Date.now().toString(), role: 'user', content: input, timestamp: now });
    setInput('');
    setLoading(true);
    setQueryStep(1);
    setIntentInfo(null);
    setExecTime('');
    setQueryResult(null);

    const startTime = Date.now();

    // 輔助函數：獲取庫存數據並過濾塑料件
    const fetchPlasticInventory = async (warehouseCode?: string) => {
      try {
        const response = await fetch(`${FRONTEND_API}/api/v1/datalake/inventory`);
        const data = await response.json();
        
        // 過濾塑料件（ima02 包含 "塑料" 或 "塑膠"）
        let filtered = data.filter((item: any) => {
          const itemName = item.ima02 || '';
          return itemName.includes('塑料') || itemName.includes('塑膠');
        });

        // 如果指定了倉庫，進一步過濾
        if (warehouseCode) {
          filtered = filtered.filter((item: any) => item.img02 === warehouseCode);
        }

        // 按庫存數量排序
        filtered.sort((a: any, b: any) => (b.img10 || 0) - (a.img10 || 0));

        return filtered.slice(0, 20);
      } catch (error) {
        console.error('獲取庫存數據錯誤:', error);
        return [];
      }
    };

    try {
      // 調用 MM-Agent API（支持多輪對話）
      const result = await mmAgentChat(input, sessionId);
      const endTime = Date.now();
      const duration = ((endTime - startTime) / 1000).toFixed(2);

      // 保存 sessionId 用於多輪對話
      if (result.session_id) {
        setSessionId(result.session_id);
        setShowMultiTurnInfo(true);
        setTurnCount((prev) => prev + 1);
      }

      // 檢查是否需要回問/回覆
      if (result.needs_clarification) {
        // 提取澄清信息
        const semanticResult = result.debug_info?.semantic_result;
        const validation = semanticResult?.validation || {};
        
        setClarificationInfo({
          show: true,
          missingFields: validation.missing_fields || [],
          prompts: validation.clarification_prompt || {},
        });
        
        setQueryStep(1);
        setIntentInfo({
          intent_type: 'needs_clarification',
          description: '需要澄清',
          table: '',
          warehouse: '',
        });
        setSqlQuery('');
        setExecTime(`${duration} 秒`);
        setQueryStep(4);

        addChatMessage({
          id: Date.now().toString(),
          role: 'assistant',
          content: result.clarification_message || '請重新描述您的問題',
          timestamp: new Date().toLocaleString(),
        });
        setLoading(false);
        return;
      }

      // 顯示指代消解信息
      if (result.resolved_query) {
        setShowMultiTurnInfo(true);
      }

      // 從轉譯結果提取 SQL 和信息
      const translation = result.translation || {};
      const debugInfo = result.debug_info || {};
      const semanticResult = debugInfo.semantic_result;
      
      // 使用新架構的語義分析結果
      const intent = semanticResult?.intent || debugInfo?.intent || 'unknown';
      const constraints = semanticResult?.constraints || translation;
      const validation = semanticResult?.validation || {};
      
      const materialCategory = constraints.material_category;
      const tableName = semanticResult?.schema_binding?.primary_table || translation.table_name || 'img_file';
      const tlf19 = constraints.tlf19;
      const partNumber = constraints.material_id || translation.part_number;
      const warehouse = constraints.inventory_location || constraints.warehouse || translation.warehouse;
      
      // 構建 SQL 顯示
      let sql = '';
      let queryResultData: any = { result: { data: [], rowCount: 0 } };

      // 優先使用後端返回的 generated_sql（新架構）
      if (debugInfo.generated_sql) {
        sql = debugInfo.generated_sql;
        console.log('使用後端生成的 SQL:', sql);
      } else {
        // 回退到舊的客戶端組裝邏輯
        console.log('後端未返回 SQL，使用客戶端組裝');

        // 處理物料類別查詢（如塑料件）- 使用客戶端過濾
        if (materialCategory === 'plastic') {
          sql = '-- 塑料件庫存查詢（客戶端過濾）\nSELECT * FROM img_file WHERE ...';
          
          try {
            // 從 API 獲取庫存數據並過濾
            const warehouseCode = warehouse || null;
            const plasticItems = await fetchPlasticInventory(warehouseCode);
            
            if (plasticItems.length > 0) {
              queryResultData = {
                result: {
                  data: plasticItems,
                  rowCount: plasticItems.length,
                }
              };
            }
          } catch (execError) {
            console.error('塑料件查詢錯誤:', execError);
          }
        } else if (tableName === 'img_file' && partNumber) {
          sql = `SELECT * FROM img_file WHERE img01 = '${partNumber}' LIMIT 10`;
        } else if (tableName === 'tlf_file' && tlf19) {
          sql = `SELECT * FROM tlf_file WHERE tlf02 = '${partNumber}' AND tlf19 = '${tlf19}' ORDER BY tlf06 DESC LIMIT 50`;
        }
      }

      setSqlQuery(sql);
      setQueryStep(2);

      // 設置意圖信息
      const intentMap: Record<string, string> = {
        'QUERY_STOCK': '庫存查詢',
        'QUERY_PURCHASE': '採購交易查詢',
        'QUERY_SALES': '銷售交易查詢',
        'ANALYZE_SHORTAGE': '缺料分析',
        'GENERATE_ORDER': '生成訂單',
        'purchase': '採購交易查詢',
        'sales': '銷售查詢',
        'inventory': '庫存查詢',
        'material_issue': '生產領料查詢',
        'scrapping': '報廢查詢',
        'unknown': '未知查詢',
      };

      // 設置倉庫信息
      let warehouseDisplay = '全部';
      if (warehouse) {
        const warehouseNames: Record<string, string> = {
          'W01': '原料倉',
          'W02': '成品倉',
          'W03': '半成品倉',
          'W04': '不良品倉',
          'W05': '回收倉',
        };
        warehouseDisplay = warehouseNames[warehouse] || warehouse;
      }

      setIntentInfo({
        intent_type: intent,
        description: intentMap[intent] || (materialCategory === 'plastic' ? '塑料件庫存查詢' : '查詢完成'),
        table: tableName,
        warehouse: warehouseDisplay,
      });

      await new Promise((r) => setTimeout(r, 800));
      setQueryStep(3);

      // 如果還沒有執行查詢（針對非塑料件查詢），則執行 SQL
      if (!queryResultData.result?.data?.length && sql && !sql.includes('--')) {
        try {
          const execResult = await executeSqlQuery(sql);
          if (execResult.result?.success) {
            queryResultData = {
              result: {
                data: execResult.result.rows || [],
                rowCount: execResult.result.row_count || 0,
              }
            };
          }
        } catch (execError) {
          console.error('SQL 執行錯誤:', execError);
        }
      }

      setQueryResult(queryResultData);
      setExecTime(`${duration} 秒`);
      setQueryStep(4);

      // 構建回覆內容
      let responseContent = result.response || '查詢完成！';
      
      // 如果有指代消解，顯示提示
      if (result.resolved_query && result.resolved_query !== input) {
        responseContent += `\n\n（指代消解：「${result.resolved_query}」）`;
      }

      addChatMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: responseContent,
        timestamp: new Date().toLocaleString(),
      });
    } catch (error) {
      console.error('MM-Agent 調用錯誤:', error);
      addChatMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: '抱歉，處理您的查詢時發生錯誤。請檢查 MM-Agent 服務是否正常運行（端口 8003）。',
        timestamp: new Date().toLocaleString(),
      });
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
  };

  return (
    <div className="page-container" style={{ height: '100%' }}>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>
            🤖 自然語言查詢
            {showMultiTurnInfo && (
              <Tooltip title={`多輪對話模式 - 已進行 ${turnCount} 輪對話`}>
                <Badge 
                  count={<SyncOutlined spin={loading} />} 
                  style={{ backgroundColor: '#52c41a', marginLeft: 12 }}
                />
              </Tooltip>
            )}
          </Title>
          <Text type="secondary">
            輸入自然語言，系統自動轉換為 SQL 查詢
            {showMultiTurnInfo && sessionId && (
              <Tag color="green" style={{ marginLeft: 8 }}>
                多輪對話模式 ({turnCount} 輪)
              </Tag>
            )}
          </Text>
        </div>
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
                  {isWorkflowMessage(msg.content) ? (
                    renderWorkflowSteps(msg.content)
                  ) : (
                    <div className="message-content" style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                  )}
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
                placeholder={showMultiTurnInfo ? "繼續對話，可使用「這個」、「那個」等指代詞..." : "輸入您的問題..."}
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

            {/* 多輪對話狀態提示 */}
            {showMultiTurnInfo && (
              <div style={{ marginBottom: 16, padding: 8, background: '#f6ffed', borderRadius: 4, border: '1px solid #b7eb8f' }}>
                <Text strong style={{ color: '#52c41a' }}>
                  <SyncOutlined style={{ marginRight: 4 }} />
                  多輪對話模式
                </Text>
                <div style={{ fontSize: 12, marginTop: 4, color: '#666' }}>
                  支持指代消解：「這個」、「那個」、「它」
                </div>
                {sessionId && (
                  <div style={{ fontSize: 11, marginTop: 4, color: '#999' }}>
                    會話 ID: {sessionId.substring(0, 20)}...
                  </div>
                )}
              </div>
            )}

            {/* 澄清對話提示 */}
            {clarificationInfo?.show && (
              <div style={{ marginBottom: 16, padding: 12, background: '#fff7e6', borderRadius: 4, border: '1px solid #ffd591' }}>
                <Text strong style={{ color: '#fa8c16' }}>
                  💡 需要更多資訊
                </Text>
                <div style={{ marginTop: 8 }}>
                  {clarificationInfo.missingFields.map((field: string) => (
                    <div key={field} style={{ marginBottom: 4 }}>
                      <Text style={{ color: '#666' }}>• </Text>
                      <Text>{clarificationInfo.prompts[field] || `請提供 ${field}`}</Text>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div style={{ position: 'relative' }}>
              <div
                style={{
                  position: 'absolute',
                  left: 15,
                  top: 20,
                  bottom: 20,
                  width: 2,
                  background: queryStep >= 2 ? '#52c41a' : '#e8e8e8',
                  zIndex: 0,
                }}
              />
              <div
                style={{
                  position: 'absolute',
                  left: 15,
                  top: 20,
                  bottom: 20,
                  width: 2,
                  background: queryStep >= 3 ? '#52c41a' : 'transparent',
                  zIndex: 0,
                  transition: 'all 0.3s',
                }}
              />

              <div style={{ position: 'relative', marginBottom: 16, paddingLeft: 40, zIndex: 1 }}>
                <div
                  style={{
                    position: 'absolute',
                    left: 6,
                    top: 0,
                    width: 20,
                    height: 20,
                    borderRadius: '50%',
                    background: queryStep >= 1 ? '#52c41a' : '#e8e8e8',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {queryStep >= 1 ? (
                    <CheckCircleOutlined style={{ color: 'white', fontSize: 12 }} />
                  ) : (
                    <FileSearchOutlined style={{ color: '#999', fontSize: 12 }} />
                  )}
                </div>
                <Text strong style={{ color: queryStep >= 1 ? '#52c41a' : '#999' }}>
                  分析查詢意圖
                </Text>
                {queryStep >= 1 && intentInfo && (
                  <div
                    style={{
                      marginTop: 8,
                      padding: 10,
                      background: intentInfo?.intent_type === 'needs_clarification' ? '#fff7e6' : '#f5f5f5',
                      borderRadius: 4,
                      border: intentInfo?.intent_type === 'needs_clarification' ? '1px solid #ffbb96' : '1px solid #e8e8e8',
                    }}
                  >
                    {intentInfo?.intent_type === 'needs_clarification' ? (
                      <div>
                        <Tag color="orange" style={{ marginRight: 4 }}>💡 需要澄清</Tag>
                        <Text style={{ display: 'block', marginTop: 8, whiteSpace: 'pre-wrap' }}>
                          {intentInfo.description || '請重新描述您的問題'}
                        </Text>
                      </div>
                    ) : (
                      <>
                        <div style={{ marginBottom: 4 }}>
                          <Tag color="blue" style={{ marginRight: 4 }}>意圖類型</Tag>
                          <Text>{intentInfo?.intent_type === 'QUERY_STOCK' ? '庫存查詢' :
                                 intentInfo?.intent_type === 'QUERY_PURCHASE' ? '採購交易查詢' :
                                 intentInfo?.intent_type === 'QUERY_SALES' ? '銷售交易查詢' :
                                 intentInfo?.intent_type === 'ANALYZE_SHORTAGE' ? '缺料分析' :
                                 intentInfo?.intent_type === 'GENERATE_ORDER' ? '生成訂單' :
                                 intentInfo?.intent_type === 'purchase' ? '採購交易查詢' :
                                 intentInfo?.intent_type === 'sales' ? '銷售查詢' :
                                 intentInfo?.intent_type === 'inventory' ? '庫存查詢' :
                                 intentInfo?.intent_type === 'material_issue' ? '生產領料查詢' :
                                 intentInfo?.intent_type === 'scrapping' ? '報廢查詢' : '未知查詢'}</Text>
                        </div>
                        <div style={{ marginBottom: 4 }}>
                          <Tag color="green" style={{ marginRight: 4 }}>查詢目標</Tag>
                          <Text>{intentInfo.description || input.substring(0, 20)}</Text>
                        </div>
                        <div style={{ marginBottom: 4 }}>
                          <Tag color="orange" style={{ marginRight: 4 }}>涉及表</Tag>
                          <Text>{intentInfo?.table === 'tlf_file' ? '交易明細 (tlf19 採購進貨)' : 
                                 intentInfo?.table === 'img_file' ? '庫存表' : intentInfo?.table}</Text>
                        </div>
                        {intentInfo?.warehouse && (
                          <div>
                            <Tag color="purple" style={{ marginRight: 4 }}>倉庫</Tag>
                            <Text strong>{intentInfo.warehouse}</Text>
                          </div>
                        )}
                        {/* 顯示約束條件 */}
                        <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #e8e8e8' }}>
                          <Text type="secondary" style={{ fontSize: 11 }}>約束條件</Text>
                          <div style={{ marginTop: 4 }}>
                            {intentInfo?.intent_type?.includes('QUERY') && (
                              <Tag color="cyan" style={{ marginRight: 4, marginBottom: 4 }}>庫存查詢</Tag>
                            )}
                            {intentInfo?.intent_type?.includes('PURCHASE') && (
                              <Tag color="cyan" style={{ marginRight: 4, marginBottom: 4 }}>採購查詢</Tag>
                            )}
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>

              <div style={{ position: 'relative', marginBottom: 16, paddingLeft: 40, zIndex: 1 }}>
                <div
                  style={{
                    position: 'absolute',
                    left: 6,
                    top: 0,
                    width: 20,
                    height: 20,
                    borderRadius: '50%',
                    background: queryStep >= 2 ? '#52c41a' : '#e8e8e8',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {queryStep >= 2 ? (
                    <CheckCircleOutlined style={{ color: 'white', fontSize: 12 }} />
                  ) : (
                    <DatabaseOutlined style={{ color: '#999', fontSize: 12 }} />
                  )}
                </div>
                <Text strong style={{ color: queryStep >= 2 ? '#52c41a' : '#999' }}>
                  生成 SQL
                </Text>
                {queryStep >= 2 && (
                  <div style={{ marginTop: 8 }}>
                    <pre
                      style={{
                        background: '#1e1e1e',
                        color: '#d4d4d4',
                        padding: 10,
                        borderRadius: 4,
                        fontSize: 11,
                        overflow: 'auto',
                        maxHeight: 120,
                        margin: 0,
                      }}
                    >
                      {sqlQuery}
                    </pre>
                  </div>
                )}
              </div>

              <div style={{ position: 'relative', marginBottom: 16, paddingLeft: 40, zIndex: 1 }}>
                <div
                  style={{
                    position: 'absolute',
                    left: 6,
                    top: 0,
                    width: 20,
                    height: 20,
                    borderRadius: '50%',
                    background: queryStep >= 3 ? '#52c41a' : '#e8e8e8',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {queryStep >= 3 ? (
                    <CheckCircleOutlined style={{ color: 'white', fontSize: 12 }} />
                  ) : (
                    <ClockCircleOutlined style={{ color: '#999', fontSize: 12 }} />
                  )}
                </div>
                <Text strong style={{ color: queryStep >= 3 ? '#52c41a' : '#999' }}>
                  執行查詢
                </Text>
                {queryStep >= 3 && (
                  <div
                    style={{
                      marginTop: 8,
                      padding: 8,
                      background: '#e6f7ff',
                      borderRadius: 4,
                      border: '1px solid #91d5ff',
                    }}
                  >
                    <ClockCircleOutlined style={{ color: '#1890ff', marginRight: 4 }} />
                    <Text strong style={{ color: '#1890ff' }}>
                      執行時間: {execTime}
                    </Text>
                  </div>
                )}
              </div>

              <div style={{ position: 'relative', paddingLeft: 40, zIndex: 1 }}>
                <div
                  style={{
                    position: 'absolute',
                    left: 6,
                    top: 0,
                    width: 20,
                    height: 20,
                    borderRadius: '50%',
                    background: queryStep >= 4 ? '#52c41a' : '#e8e8e8',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
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
                    <div
                      style={{
                        marginBottom: 8,
                        padding: 6,
                        background: '#f6ffed',
                        borderRadius: 4,
                        border: '1px solid #b7eb8f',
                      }}
                    >
                      <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 4 }} />
                      <Text strong style={{ color: '#52c41a' }}>
                        返回 {queryResult.result.rowCount} 筆記錄
                      </Text>
                    </div>
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
                    {queryResult.result.rowCount > 10 && (
                      <Text type="secondary" style={{ fontSize: 12, marginTop: 8, display: 'block' }}>
                        * 只顯示前 10 筆，共 {queryResult.result.rowCount} 筆記錄
                      </Text>
                    )}
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
