import { Card, Input, Button, Typography, Row, Col, Tag, Table, Badge, Tooltip } from 'antd';
import { useState, useEffect, useRef } from 'react';
import { SendOutlined, ClearOutlined, ClockCircleOutlined, DatabaseOutlined, CheckCircleOutlined, FileSearchOutlined, BarChartOutlined, SyncOutlined } from '@ant-design/icons';
import { useDashboardStore } from '../stores/dashboardStore';
import { mmAgentChat } from '../lib/api';
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
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

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
      const intent = result.debug_info?.intent || 'unknown';
      
      // 構建 SQL 顯示（實際項目中這裡應該調用 Data-Agent 執行）
      const tableName = translation.table_name || 'img_file';
      const tlf19 = translation.tlf19;
      const partNumber = translation.part_number;
      
      // 模擬 SQL（實際項目中應該從 Data-Agent 返回）
      let sql = '';
      if (tableName === 'img_file') {
        sql = `SELECT * FROM img_file WHERE img01 = '${partNumber}' LIMIT 10`;
      } else if (tableName === 'tlf_file' && tlf19) {
        sql = `SELECT * FROM tlf_file WHERE tlf02 = '${partNumber}' AND tlf19 = '${tlf19}' ORDER BY tlf06 DESC LIMIT 50`;
      }
      setSqlQuery(sql);
      setQueryStep(2);

      // 設置意圖信息
      const intentMap: Record<string, string> = {
        'purchase': '採購交易查詢',
        'sales': '銷售查詢',
        'inventory': '庫存查詢',
        'material_issue': '生產領料查詢',
        'scrapping': '報廢查詢',
      };

      setIntentInfo({
        intent_type: intent,
        description: intentMap[intent] || '查詢完成',
        table: tableName,
        warehouse: input.includes('W01') ? 'W01' : input.includes('W02') ? 'W02' : input.includes('W03') ? 'W03' : '全部',
      });

      await new Promise((r) => setTimeout(r, 800));
      setQueryStep(3);

      setQueryResult({
        result: {
          data: [],
          rowCount: 0,
        }
      });
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
                  <div className="message-content">{msg.content}</div>
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
                          <Text>{intentInfo?.intent_type === 'purchase' ? '採購交易查詢' :
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
