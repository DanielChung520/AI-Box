import { Card, Table, Select, Typography, Row, Col, Tag, Button, Tabs } from 'antd';
import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis } from 'recharts';
import { useDashboardStore } from '../stores/dashboardStore';
import { fetchOrderData } from '../lib/api';
import { formatNumber } from '../lib/utils';
import './pages.css';

const { Title, Text } = Typography;
const { Option } = Select;

const COLORS = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336'];

const STATUS_MAP: Record<string, string> = {
  '10': '未出貨',
  '20': '部分出貨',
  '30': '已出貨',
};

const APPROVE_MAP: Record<string, string> = {
  'Y': '已批准',
  'N': '待批准',
};

export default function OrderPage() {
  const { orderData, setOrderData } = useDashboardStore();
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('header');
  const [customerFilter, setCustomerFilter] = useState('全部');
  const [statusFilter, setStatusFilter] = useState('全部');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    const loadData = async () => {
      try {
        const data = await fetchOrderData();
        setOrderData(data);
      } catch (error) {
        console.error('載入訂單數據失敗:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const coptcData = orderData.coptc || [];
  const coptdData = orderData.coptd || [];
  const prcData = orderData.prc || [];
  const customerData = orderData.customers || [];

  const customerMap = customerData.reduce((acc: Record<string, string>, c: any) => {
    acc[c.cmc01] = c.cmc02;
    return acc;
  }, {});

  const processedCOTC = coptcData.map((item: any, idx: number) => ({
    key: idx,
    狀態名稱: STATUS_MAP[item.coptc05] || item.coptc05,
    客戶名稱: customerMap[item.coptc02] || item.coptc02,
    ...item,
  }));

  const processedCOTD = coptdData.map((item: any, idx: number) => ({
    key: idx,
    ...item,
  }));

  const processedPRC = prcData.map((item: any, idx: number) => ({
    key: idx,
    批准狀態名稱: APPROVE_MAP[item.prc04] || item.prc04,
    ...item,
  }));

  let filteredCOTC = processedCOTC;
  if (customerFilter !== '全部') {
    filteredCOTC = filteredCOTC.filter((i: any) => i.coptc02 === customerFilter);
  }
  if (statusFilter !== '全部') {
    filteredCOTC = filteredCOTC.filter((i: any) => i.coptc05 === statusFilter);
  }

  const statusStats = coptcData.reduce((acc: Record<string, number>, item: any) => {
    acc[item.coptc05] = (acc[item.coptc05] || 0) + 1;
    return acc;
  }, {});
  const pieData = Object.entries(statusStats).map(([name, value]) => ({
    name: STATUS_MAP[name] || name,
    value,
  }));

  const paginatedCOTC = filteredCOTC.slice((page - 1) * pageSize, page * pageSize);
  const paginatedCOTD = processedCOTD.slice((page - 1) * pageSize, page * pageSize);
  const paginatedPRC = processedPRC.slice((page - 1) * pageSize, page * pageSize);

  const coptcColumns = [
    { title: '訂單號', dataIndex: 'coptc01', key: 'coptc01' },
    { title: '客戶代碼', dataIndex: 'coptc02', key: 'coptc02' },
    { title: '客戶名稱', dataIndex: '客戶名稱', key: '客戶名稱' },
    { title: '單據日期', dataIndex: 'coptc03', key: 'coptc03' },
    { title: '預計出貨日', dataIndex: 'coptc04', key: 'coptc04' },
    { title: '訂單狀態', dataIndex: '狀態名稱', key: '狀態名稱', render: (v: string) => <Tag color={v === '已出貨' ? 'green' : v === '部分出貨' ? 'orange' : 'blue'}>{v}</Tag> },
    { title: '業務人員', dataIndex: 'coptc06', key: 'coptc06' },
  ];

  const coptdColumns = [
    { title: '訂單號', dataIndex: 'coptd01', key: 'coptd01' },
    { title: '項次', dataIndex: 'coptd02', key: 'coptd02' },
    { title: '料號', dataIndex: 'coptd04', key: 'coptd04' },
    { title: '訂購數量', dataIndex: 'coptd20', key: 'coptd20', render: (v: number) => formatNumber(v) },
    { title: '單價', dataIndex: 'coptd30', key: 'coptd30', render: (v: number) => formatNumber(v) },
    { title: '已出貨數量', dataIndex: 'coptd31', key: 'coptd31', render: (v: number) => formatNumber(v) },
    { title: '訂單批次', dataIndex: 'coptd32', key: 'coptd32' },
  ];

  const prcColumns = [
    { title: '料號', dataIndex: 'prc01', key: 'prc01' },
    { title: '單價', dataIndex: 'prc02', key: 'prc02', render: (v: number) => formatNumber(v) },
    { title: '批准日期', dataIndex: 'prc03', key: 'prc03' },
    { title: '批准狀態', dataIndex: '批准狀態名稱', key: '批准狀態名稱', render: (v: string) => <Tag color={v === '已批准' ? 'green' : 'red'}>{v}</Tag> },
    { title: '生效日', dataIndex: 'prc05', key: 'prc05' },
    { title: '失效日', dataIndex: 'prc06', key: 'prc06' },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={3} style={{ margin: 0 }}>📤 訂單分析</Title>
        <Text type="secondary">分析客戶訂單、訂單明細與報價情況</Text>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, gap: 16 }}>
        <Row gutter={16} className="chart-grid">
          <Col span={12}>
            <Card size="small" title="訂單趨勢">
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
          <Col span={12}>
            <Card size="small" title="訂單狀態分佈">
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
        </Row>

        <div className="table-section">
          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            <Tabs.TabPane tab="📋 訂單單頭" key="header">
              <div className="table-filters">
                <Select value={customerFilter} onChange={setCustomerFilter} style={{ width: 200 }}>
                  <Option value="全部">全部客戶</Option>
                  {Object.keys(customerMap).map((c) => (
                    <Option key={c} value={c}>{customerMap[c] || c}</Option>
                  ))}
                </Select>
                <Select value={statusFilter} onChange={setStatusFilter} style={{ width: 120 }}>
                  <Option value="全部">全部狀態</Option>
                  {Object.entries(STATUS_MAP).map(([k, v]) => (
                    <Option key={k} value={k}>{v}</Option>
                  ))}
                </Select>
              </div>
              <Table loading={loading} columns={coptcColumns} dataSource={paginatedCOTC} pagination={false} size="small" />
              <div className="pagination-row">
                <Text>共 {filteredCOTC.length} 筆</Text>
                <Button size="small" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>上一頁</Button>
                <Text>{page} / {Math.ceil(filteredCOTC.length / pageSize)}</Text>
                <Button size="small" onClick={() => setPage((p) => p + 1)} disabled={page >= Math.ceil(filteredCOTC.length / pageSize)}>下一頁</Button>
              </div>
            </Tabs.TabPane>

            <Tabs.TabPane tab="📦 訂單單身" key="detail">
              <Table loading={loading} columns={coptdColumns} dataSource={paginatedCOTD} pagination={false} size="small" />
              <div className="pagination-row">
                <Text>共 {processedCOTD.length} 筆</Text>
                <Button size="small" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>上一頁</Button>
                <Text>{page} / {Math.ceil(processedCOTD.length / pageSize)}</Text>
                <Button size="small" onClick={() => setPage((p) => p + 1)} disabled={page >= Math.ceil(processedCOTD.length / pageSize)}>下一頁</Button>
              </div>
            </Tabs.TabPane>

            <Tabs.TabPane tab="💰 訂價單" key="pricing">
              <Table loading={loading} columns={prcColumns} dataSource={paginatedPRC} pagination={false} size="small" />
              <div className="pagination-row">
                <Text>共 {processedPRC.length} 筆</Text>
                <Button size="small" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>上一頁</Button>
                <Text>{page} / {Math.ceil(processedPRC.length / pageSize)}</Text>
                <Button size="small" onClick={() => setPage((p) => p + 1)} disabled={page >= Math.ceil(processedPRC.length / pageSize)}>下一頁</Button>
              </div>
            </Tabs.TabPane>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
