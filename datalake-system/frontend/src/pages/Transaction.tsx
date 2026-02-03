import { Card, Table, Select, Typography, Row, Col, Tag, Button } from 'antd';
import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis } from 'recharts';
import { useDashboardStore } from '../stores/dashboardStore';
import { fetchTransactionData } from '../lib/api';
import { formatNumber } from '../lib/utils';
import './pages.css';

const { Title, Text } = Typography;
const { Option } = Select;

const COLORS = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336'];
const TYPE_MAP: Record<string, string> = {
  '101': '採購進貨',
  '102': '完工入庫',
  '201': '生產領料',
  '202': '銷售出庫',
  '301': '庫存報廢',
};

export default function TransactionPage() {
  const { transactionData, setTransactionData, itemsData } = useDashboardStore();
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState('全部');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    const loadData = async () => {
      try {
        const data = await fetchTransactionData();
        setTransactionData(data);
      } catch (error) {
        console.error('載入交易數據失敗:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const processedData = transactionData.map((tx, idx) => ({
    ...tx,
    key: idx,
    交易名稱: TYPE_MAP[tx.tlf19] || tx.tlf19,
    品名: itemsData.find((i) => i.ima01 === tx.tlf01)?.ima02 || '',
  }));

  let filteredData = processedData;
  if (typeFilter !== '全部') {
    filteredData = filteredData.filter((i) => i.交易名稱 === typeFilter);
  }

  const typeStats = [...new Set(processedData.map((i) => i.交易名稱))].map((name) => ({
    name,
    count: processedData.filter((i) => i.交易名稱 === name).length,
  }));

  const pieData = typeStats.map((item, idx) => ({
    ...item,
    value: item.count,
  }));

  const paginatedData = filteredData.slice((page - 1) * pageSize, page * pageSize);

  const columns = [
    { title: '料號', dataIndex: 'tlf01', key: 'tlf01' },
    { title: '品名', dataIndex: '品名', key: '品名' },
    { title: '交易類別', dataIndex: '交易名稱', key: '交易名稱' },
    { title: '日期', dataIndex: 'tlf06', key: 'tlf06' },
    {
      title: '數量',
      dataIndex: 'tlf10',
      key: 'tlf10',
      render: (v: number) => <Tag color={v < 0 ? 'red' : 'green'}>{formatNumber(v)}</Tag>,
    },
    { title: '倉庫', dataIndex: 'tlf061', key: 'tlf061' },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={3} style={{ margin: 0 }}>🔄 交易類別</Title>
        <Text type="secondary">分析交易趨勢與類別分佈</Text>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, gap: 16 }}>
        <Row gutter={16} className="chart-grid">
          <Col span={12}>
            <Card size="small" title="業務類型佔比">
              <div style={{ flex: 1, minHeight: 0 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                      {pieData.map((_, idx) => (
                        <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small" title="交易趨勢">
              <div style={{ flex: 1, minHeight: 0 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={pieData}>
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" fill="#2196F3" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </Col>
        </Row>

        <div className="table-section">
          <Title level={4}>📋 交易明細</Title>
          <div className="table-filters">
            <Select value={typeFilter} onChange={setTypeFilter} style={{ width: 150 }}>
              <Option value="全部">全部類別</Option>
              {Object.values(TYPE_MAP).map((name) => (
                <Option key={name} value={name}>{name}</Option>
              ))}
            </Select>
          </div>
          <Table loading={loading} columns={columns} dataSource={paginatedData} pagination={false} size="small" />
          <div className="pagination-row">
            <Text>共 {filteredData.length} 筆</Text>
            <Button size="small" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>上一頁</Button>
            <Text>{page} / {Math.ceil(filteredData.length / pageSize)}</Text>
            <Button size="small" onClick={() => setPage((p) => p + 1)} disabled={page >= Math.ceil(filteredData.length / pageSize)}>下一頁</Button>
          </div>
        </div>
      </div>
    </div>
  );
}
