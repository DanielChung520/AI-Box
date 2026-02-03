import { Card, Table, Select, Typography, Row, Col, Tag, Button, Tabs } from 'antd';
import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis } from 'recharts';
import { useDashboardStore } from '../stores/dashboardStore';
import { fetchPurchaseData } from '../lib/api';
import { formatNumber } from '../lib/utils';
import './pages.css';

const { Title, Text } = Typography;
const { Option } = Select;

const COLORS = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336'];

interface PurchaseOrder {
  pmm01?: string;
  pmm02?: string;
  pmm04?: string;
  pmm09?: string;
  pmn01?: string;
  pmn02?: number;
  pmn04?: string;
  pmn20?: number;
  pmn31?: number;
  pmn33?: string;
  rvb01?: string;
  rvb05?: string;
  rvb07?: string;
  rvb33?: number;
}

export default function PurchasePage() {
  const { purchaseData, setPurchaseData } = useDashboardStore();
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('header');
  const [vendorFilter, setVendorFilter] = useState('全部');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    const loadData = async () => {
      try {
        const data = await fetchPurchaseData();
        setPurchaseData(data);
      } catch (error) {
        console.error('載入採購數據失敗:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const pmmData = purchaseData.pmm || [];
  const pmnData = purchaseData.pmn || [];
  const rvbData = purchaseData.rvb || [];
  const vendorData = purchaseData.vendors || [];

  const vendorMap = vendorData.reduce((acc: Record<string, string>, v: any) => {
    acc[v.pmc01] = v.pmc03;
    return acc;
  }, {});

  const processedPMM = pmmData.map((item: any, idx: number) => ({
    key: idx,
    供應商名稱: vendorMap[item.pmm04] || item.pmm04,
    ...item,
  }));

  const processedPMN = pmnData.map((item: any, idx: number) => ({
    key: idx,
    ...item,
  }));

  const processedRVB = rvbData.map((item: any, idx: number) => ({
    key: idx,
    ...item,
  }));

  let filteredPMM = processedPMM;
  if (vendorFilter !== '全部') {
    filteredPMM = filteredPMM.filter((i: any) => i.pmm04 === vendorFilter);
  }

  const vendorStats = pmmData.reduce((acc: Record<string, number>, item: any) => {
    acc[item.pmm04] = (acc[item.pmm04] || 0) + 1;
    return acc;
  }, {});
  const pieData = Object.entries(vendorStats).map(([name, value]) => ({
    name: vendorMap[name] || name,
    value,
  }));

  const paginatedPMM = filteredPMM.slice((page - 1) * pageSize, page * pageSize);
  const paginatedPMN = processedPMN.slice((page - 1) * pageSize, page * pageSize);
  const paginatedRVB = processedRVB.slice((page - 1) * pageSize, page * pageSize);

  const pmmColumns = [
    { title: '採購單號', dataIndex: 'pmm01', key: 'pmm01' },
    { title: '單據日期', dataIndex: 'pmm02', key: 'pmm02' },
    { title: '供應商', dataIndex: 'pmm04', key: 'pmm04' },
    { title: '供應商名稱', dataIndex: '供應商名稱', key: '供應商名稱' },
    { title: '採購人員', dataIndex: 'pmm09', key: 'pmm09' },
  ];

  const pmnColumns = [
    { title: '採購單號', dataIndex: 'pmn01', key: 'pmn01' },
    { title: '項次', dataIndex: 'pmn02', key: 'pmn02' },
    { title: '料號', dataIndex: 'pmn04', key: 'pmn04' },
    { title: '採購數量', dataIndex: 'pmn20', key: 'pmn20', render: (v: number) => formatNumber(v) },
    { title: '已交數量', dataIndex: 'pmn31', key: 'pmn31', render: (v: number) => formatNumber(v) },
    { title: '預計到貨日', dataIndex: 'pmn33', key: 'pmn33' },
  ];

  const rvbColumns = [
    { title: '收料單號', dataIndex: 'rvb01', key: 'rvb01' },
    { title: '料號', dataIndex: 'rvb05', key: 'rvb05' },
    { title: '採購單號', dataIndex: 'rvb07', key: 'rvb07' },
    { title: '驗收數量', dataIndex: 'rvb33', key: 'rvb33', render: (v: number) => formatNumber(v) },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={3} style={{ margin: 0 }}>📥 採購交易分析</Title>
        <Text type="secondary">分析採購單據、收料情況與供應商表現</Text>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, gap: 16 }}>
        <Row gutter={16} className="chart-grid">
          <Col span={12}>
            <Card size="small" title="採購單分佈">
              <div style={{ flex: 1, minHeight: 0 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={pieData}>
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" fill="#4CAF50" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small" title="供應商分佈">
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
            <Tabs.TabPane tab="📋 採購單頭" key="header">
              <div className="table-filters">
                <Select value={vendorFilter} onChange={setVendorFilter} style={{ width: 200 }}>
                  <Option value="全部">全部供應商</Option>
                  {Object.keys(vendorStats).map((v) => (
                    <Option key={v} value={v}>{vendorMap[v] || v}</Option>
                  ))}
                </Select>
              </div>
              <Table loading={loading} columns={pmmColumns} dataSource={paginatedPMM} pagination={false} size="small" />
              <div className="pagination-row">
                <Text>共 {filteredPMM.length} 筆</Text>
                <Button size="small" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>上一頁</Button>
                <Text>{page} / {Math.ceil(filteredPMM.length / pageSize)}</Text>
                <Button size="small" onClick={() => setPage((p) => p + 1)} disabled={page >= Math.ceil(filteredPMM.length / pageSize)}>下一頁</Button>
              </div>
            </Tabs.TabPane>

            <Tabs.TabPane tab="📦 採購單身" key="detail">
              <Table loading={loading} columns={pmnColumns} dataSource={paginatedPMN} pagination={false} size="small" />
              <div className="pagination-row">
                <Text>共 {processedPMN.length} 筆</Text>
                <Button size="small" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>上一頁</Button>
                <Text>{page} / {Math.ceil(processedPMN.length / pageSize)}</Text>
                <Button size="small" onClick={() => setPage((p) => p + 1)} disabled={page >= Math.ceil(processedPMN.length / pageSize)}>下一頁</Button>
              </div>
            </Tabs.TabPane>

            <Tabs.TabPane tab="📨 收料記錄" key="receipt">
              <Table loading={loading} columns={rvbColumns} dataSource={paginatedRVB} pagination={false} size="small" />
              <div className="pagination-row">
                <Text>共 {processedRVB.length} 筆</Text>
                <Button size="small" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>上一頁</Button>
                <Text>{page} / {Math.ceil(processedRVB.length / pageSize)}</Text>
                <Button size="small" onClick={() => setPage((p) => p + 1)} disabled={page >= Math.ceil(processedRVB.length / pageSize)}>下一頁</Button>
              </div>
            </Tabs.TabPane>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
