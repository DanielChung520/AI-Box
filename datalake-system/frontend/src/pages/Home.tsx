import { Card, Statistic, Row, Col, Table, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { formatNumber } from '../lib/utils';
import { useDashboardStore } from '../stores/dashboardStore';
import { fetchInventoryData, fetchTransactionData, fetchItemsData } from '../lib/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import './pages.css';

const { Title, Text } = Typography;

export default function HomePage() {
  const { inventoryData, setInventoryData, transactionData, setTransactionData, itemsData, setItemsData } = useDashboardStore();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [inv, tx, items] = await Promise.all([
          fetchInventoryData(),
          fetchTransactionData(),
          fetchItemsData(),
        ]);
        setInventoryData(inv);
        setTransactionData(tx);
        setItemsData(items);
      } catch (error) {
        console.error('載入數據失敗:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const totalItems = itemsData.length;
  const totalTransactions = transactionData.length;
  const uniqueWarehouses = [...new Set(inventoryData.map((i) => i.img02))].length;
  const abnormalCount = inventoryData.filter((i) => i.img10 < 0).length;

  const recentTrend = transactionData.slice(-30).map((tx, idx) => ({
    day: idx + 1,
    count: 1,
  }));

  const warehouseData = [...new Map(inventoryData.map((item) => [item.img02, item])).values()].map((i) => ({
    warehouse: i.img02,
    quantity: i.img10,
  }));

  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={3} style={{ margin: 0 }}>📊 數據湖總覽</Title>
        <Text type="secondary">快速掌握系統狀態與關鍵指標</Text>
      </div>

      <Row gutter={16} className="metrics-row">
        <Col span={6}>
          <Card className="metric-card">
            <Statistic title="總品項數" value={totalItems} formatter={(v) => formatNumber(v)} />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="metric-card">
            <Statistic title="總交易筆數" value={totalTransactions} formatter={(v) => formatNumber(v)} />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="metric-card">
            <Statistic title="總倉庫數" value={uniqueWarehouses} />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="metric-card">
            <Statistic title="庫存異常數" value={abnormalCount} styles={{ content: { color: abnormalCount > 0 ? '#ff4d4f' : '#52c41a' } }} />
          </Card>
        </Col>
      </Row>

      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, gap: 16 }}>
        <div className="chart-section">
          <Title level={4}>📈 最近交易趨勢</Title>
          <div style={{ flex: 1, minHeight: 0 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={recentTrend}>
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="count" stroke="#4CAF50" fill="#4CAF50" fillOpacity={0.3} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="table-section">
          <Title level={4}>📋 各表記錄統計</Title>
          <Table
            loading={loading}
            dataSource={[
              { key: '1', table: '料號主檔 (ima_file)', count: totalItems, status: '正常' },
              { key: '2', table: '庫存主檔 (img_file)', count: inventoryData.length, status: '正常' },
              { key: '3', table: '庫存交易檔 (tlf_file)', count: totalTransactions, status: '正常' },
            ]}
            columns={[
              { title: '資料表', dataIndex: 'table', key: 'table' },
              { title: '記錄筆數', dataIndex: 'count', key: 'count', render: (v) => formatNumber(v) },
              { title: '狀態', dataIndex: 'status', key: 'status' },
            ]}
            pagination={false}
          />
        </div>
      </div>
    </div>
  );
}
