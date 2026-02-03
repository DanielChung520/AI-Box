import { Layout, Menu, Typography } from 'antd';
import {
  HomeOutlined,
  BarChartOutlined,
  SwapOutlined,
  DownloadOutlined,
  UploadOutlined,
  SearchOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { useDashboardStore } from '../../stores/dashboardStore';
import './Sidebar.css';

const { Sider } = Layout;
const { Text } = Typography;

interface SidebarProps {
  width?: number;
}

const menuItems = [
  {
    key: 'home',
    icon: <HomeOutlined />,
    label: '數據湖總覽',
  },
  {
    key: 'inventory',
    icon: <BarChartOutlined />,
    label: '庫存分析',
  },
  {
    key: 'transaction',
    icon: <SwapOutlined />,
    label: '交易類別',
  },
  {
    key: 'purchase',
    icon: <DownloadOutlined />,
    label: '採購交易分析',
  },
  {
    key: 'order',
    icon: <UploadOutlined />,
    label: '訂單分析',
  },
  {
    key: 'query',
    icon: <SearchOutlined />,
    label: '數據查詢',
  },
  {
    key: 'nlp',
    icon: <RobotOutlined />,
    label: '自然語言',
  },
];

export default function Sidebar({ width = 200 }: SidebarProps) {
  const { currentPage, setCurrentPage, sidebarCollapsed } = useDashboardStore();

  return (
    <Sider
      width={width}
      collapsedWidth={64}
      collapsed={sidebarCollapsed}
      className="dashboard-sider"
      theme="dark"
    >
      <div className="sider-header">
        <div className="logo">
          <RobotOutlined className="logo-icon" />
          {!sidebarCollapsed && <Text className="logo-text">Data-Agent</Text>}
        </div>
      </div>
      <Menu
        mode="inline"
        selectedKeys={[currentPage]}
        items={menuItems}
        onClick={({ key }) => setCurrentPage(key)}
        className="sider-menu"
      />
      {!sidebarCollapsed && (
        <div className="sider-footer">
          <Text className="version">v1.2</Text>
        </div>
      )}
    </Sider>
  );
}
