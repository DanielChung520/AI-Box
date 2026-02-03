import { useState, useEffect } from 'react';
import { Layout } from 'antd';
import Sidebar from './components/Sidebar';
import HomePage from './pages/Home';
import InventoryPage from './pages/Inventory';
import TransactionPage from './pages/Transaction';
import PurchasePage from './pages/Purchase';
import OrderPage from './pages/Order';
import QueryPage from './pages/Query';
import NLPPage from './pages/NLP';
import BrainIcon from './components/BrainIcon';
import AIStatusWindow from './components/AIStatusWindow';
import { useDashboardStore } from './stores/dashboardStore';
import './Layout.css';

const { Content } = Layout;

export default function DashboardLayout() {
  const { currentPage, sidebarCollapsed } = useDashboardStore();

  const renderPage = () => {
    switch (currentPage) {
      case 'home':
        return <HomePage />;
      case 'inventory':
        return <InventoryPage />;
      case 'transaction':
        return <TransactionPage />;
      case 'purchase':
        return <PurchasePage />;
      case 'order':
        return <OrderPage />;
      case 'query':
        return <QueryPage />;
      case 'nlp':
        return <NLPPage />;
      default:
        return <HomePage />;
    }
  };

  return (
    <Layout className="dashboard-layout" style={{ marginLeft: sidebarCollapsed ? 64 : 200 }}>
      <Sidebar width={200} />
      <Content className="dashboard-content">{renderPage()}</Content>
      <div className="ai-status-container">
        <BrainIcon />
        <AIStatusWindow />
      </div>
    </Layout>
  );
}
