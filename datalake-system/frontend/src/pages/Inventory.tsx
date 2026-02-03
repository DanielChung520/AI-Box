import { Card, Table, Input, Select, Button, Typography, Row, Col, Tag } from 'antd';
import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis } from 'recharts';
import { useDashboardStore } from '../stores/dashboardStore';
import { fetchInventoryData } from '../lib/api';
import { formatNumber } from '../lib/utils';
import './pages.css';

const { Title, Text } = Typography;
const { Option } = Select;

const COLORS = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336'];

export default function InventoryPage() {
  const { inventoryData, setInventoryData, itemsData } = useDashboardStore();
  const [loading, setLoading] = useState(true);
  const [warehouse, setWarehouse] = useState('全部');
  const [status, setStatus] = useState('全部');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    const loadData = async () => {
      try {
        const data = await fetchInventoryData();
        setInventoryData(data);
      } catch (error) {
        console.error('載入庫存數據失敗:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const mergedData = inventoryData.map((item, idx) => ({
    ...item,
    key: idx,
    品名: itemsData.find((i) => i.ima01 === item.img01)?.ima02 || '',
  }));

  let filteredData = mergedData;
  if (warehouse !== '全部') {
    filteredData = filteredData.filter((i) => i.img02 === warehouse);
  }
  if (status !== '全部') {
    if (status === '正常') filteredData = filteredData.filter((i) => i.img10 > 0 && i.img10 <= 10000);
    else if (status === '低於安全庫存') filteredData = filteredData.filter((i) => i.img10 > 0 && i.img10 < 100);
    else if (status === '過高') filteredData = filteredData.filter((i) => i.img10 > 10000);
    else if (status === '負庫存') filteredData = filteredData.filter((i) => i.img10 < 0);
  }

  const warehouses = [...new Set(inventoryData.map((i) => i.img02))];
  const pieData = warehouses.map((w) => ({
    name: w,
    value: inventoryData.filter((i) => i.img02 === w).reduce((sum, i) => sum + i.img10, 0),
  }));

  const barData = pieData.sort((a, b) => b.value - a.value).slice(0, 5);

  const paginatedData = filteredData.slice((page - 1) * pageSize, page * pageSize);

  const columns = [
    { title: '料號', dataIndex: 'img01', key: 'img01' },
    { title: '品名', dataIndex: '品名', key: '品名' },
    { title: '倉庫', dataIndex: 'img02', key: 'img02' },
    {
      title: '庫存量',
      dataIndex: 'img10',
      key: 'img10',
      render: (v: number) => {
        let color = 'green';
        if (v < 0) color = 'red';
        else if (v < 100) color = 'orange';
        else if (v > 10000) color = 'blue';
        return <Tag color={color}>{formatNumber(v)}</Tag>;
      },
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={3} style={{ margin: 0 }}>📦 庫存分析</Title>
        <Text type="secondary">分析庫存分佈、週轉狀況與異常警示</Text>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, gap: 16 }}>
        <Row gutter={16} className="chart-grid">
          <Col span={12}>
            <Card size="small" title="各倉庫庫存分佈">
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
            <Card size="small" title="庫存排行 Top 5">
              <div style={{ flex: 1, minHeight: 0 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={barData}>
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" fill="#4CAF50" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </Col>
        </Row>

        <div className="table-section">
          <Title level={4}>📋 庫存明細</Title>
          <div className="table-filters">
            <Select value={warehouse} onChange={setWarehouse} style={{ width: 150 }}>
              <Option value="全部">全部倉庫</Option>
              {warehouses.map((w) => (
                <Option key={w} value={w}>{w}</Option>
              ))}
            </Select>
            <Select value={status} onChange={setStatus} style={{ width: 150 }}>
              <Option value="全部">全部狀態</Option>
              <Option value="正常">正常</Option>
              <Option value="低於安全庫存">低於安全庫存</Option>
              <Option value="過高">過高</Option>
              <Option value="負庫存">負庫存</Option>
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
