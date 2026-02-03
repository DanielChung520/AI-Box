import { Card, Table, Input, Radio, Typography, Button } from 'antd';
import { useEffect, useState } from 'react';
import { useDashboardStore } from '../stores/dashboardStore';
import { fetchItemsData, fetchInventoryData, fetchTransactionData } from '../lib/api';
import { formatNumber } from '../lib/utils';
import './pages.css';

const { Title, Text } = Typography;
const { Search } = Input;

export default function QueryPage() {
  const { itemsData, setItemsData, inventoryData, setInventoryData, transactionData, setTransactionData } = useDashboardStore();
  const [loading, setLoading] = useState(true);
  const [tableType, setTableType] = useState('items');
  const [searchText, setSearchText] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    const loadData = async () => {
      try {
        const [items, inv, tx] = await Promise.all([
          fetchItemsData(),
          fetchInventoryData(),
          fetchTransactionData(),
        ]);
        setItemsData(items);
        setInventoryData(inv);
        setTransactionData(tx);
      } catch (error) {
        console.error('載入數據失敗:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const getColumns = () => {
    switch (tableType) {
      case 'items':
        return [
          { title: '料號', dataIndex: 'ima01', key: 'ima01' },
          { title: '品名', dataIndex: 'ima02', key: 'ima02' },
          { title: '規格', dataIndex: 'ima021', key: 'ima021' },
          { title: '單位', dataIndex: 'ima25', key: 'ima25' },
        ];
      case 'inventory':
        return [
          { title: '料號', dataIndex: 'img01', key: 'img01' },
          { title: '倉庫', dataIndex: 'img02', key: 'img02' },
          { title: '儲位', dataIndex: 'img03', key: 'img03' },
          { title: '庫存量', dataIndex: 'img10', key: 'img10', render: (v: number) => formatNumber(v) },
        ];
      case 'transaction':
        return [
          { title: '料號', dataIndex: 'tlf01', key: 'tlf01' },
          { title: '交易類別', dataIndex: 'tlf19', key: 'tlf19' },
          { title: '日期', dataIndex: 'tlf06', key: 'tlf06' },
          { title: '數量', dataIndex: 'tlf10', key: 'tlf10', render: (v: number) => formatNumber(v) },
        ];
      default:
        return [];
    }
  };

  const getData = () => {
    let data = [];
    switch (tableType) {
      case 'items':
        data = itemsData.map((i, idx) => ({ ...i, key: idx }));
        break;
      case 'inventory':
        data = inventoryData.map((i, idx) => ({ ...i, key: idx }));
        break;
      case 'transaction':
        data = transactionData.slice(0, 1000).map((i, idx) => ({ ...i, key: idx }));
        break;
    }

    if (searchText) {
      const lower = searchText.toLowerCase();
      const key = tableType === 'items' ? 'ima01' : tableType === 'inventory' ? 'img01' : 'tlf01';
      data = data.filter((i) => String(i[key] || '').toLowerCase().includes(lower));
    }

    return data;
  };

  const data = getData();
  const paginatedData = data.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={3} style={{ margin: 0 }}>📋 數據查詢</Title>
        <Text type="secondary">瀏覽和檢索各資料表</Text>
      </div>

      <Card>
        <Radio.Group value={tableType} onChange={(e) => { setTableType(e.target.value); setPage(1); }} style={{ marginBottom: 16 }}>
          <Radio.Button value="items">料號主檔</Radio.Button>
          <Radio.Button value="inventory">庫存主檔</Radio.Button>
          <Radio.Button value="transaction">庫存交易檔</Radio.Button>
        </Radio.Group>

        <Search placeholder="搜尋料號/倉庫..." allowClear onChange={(e) => setSearchText(e.target.value)} style={{ width: 300, marginBottom: 16 }} />

        <Table loading={loading} columns={getColumns()} dataSource={paginatedData} pagination={false} size="small" />

        <div className="pagination-row">
          <Text>共 {data.length} 筆</Text>
          <div>
            <Button size="small" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>上一頁</Button>
            <Text style={{ margin: '0 8px' }}>{page} / {Math.ceil(data.length / pageSize)}</Text>
            <Button size="small" onClick={() => setPage((p) => p + 1)} disabled={page >= Math.ceil(data.length / pageSize)}>下一頁</Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
