import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import DashboardView from './components/DashboardView';
import OrdersView from './components/OrdersView';
import CustomersView from './components/CustomersView';
import AnalyticsView from './components/AnalyticsView';
import DatabaseView from './components/DatabaseView';
import ChatbotPanel from './components/ChatbotPanel';
import CreateOrderModal from './components/CreateOrderModal';
import CustomerModal from './components/CustomerModal';
import AiInspectorModal from './components/AiInspectorModal';

import {
  fetchDashboard,
  fetchProducts,
  fetchOrders,
  fetchCustomers,
  fetchAnalytics,
  fetchDatabaseTables,
  fetchChatTemplates,
  fetchChatHistory,
  clearChatHistory,
  fetchDeveloperStatus,
  sendChatMessage,
  createOrder,
  deleteOrder,
  createCustomer,
  updateCustomer,
  deleteCustomer,
} from './services/api';

import { LayoutDashboard, ShoppingBag, Users, BarChart3, Database } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);

  // Business Data
  const [dashboardData, setDashboardData] = useState(null);
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [tablesData, setTablesData] = useState(null);

  // Chatbot State
  const [chatMessages, setChatMessages] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState('standard_assistant');
  const [lastPipelineResult, setLastPipelineResult] = useState(null);
  const [developerStatus, setDeveloperStatus] = useState(null);

  // Modals
  const [isOrderModalOpen, setIsOrderModalOpen] = useState(false);
  const [preselectedProduct, setPreselectedProduct] = useState(null);

  const [isCustomerModalOpen, setIsCustomerModalOpen] = useState(false);
  const [customerToEdit, setCustomerToEdit] = useState(null);

  const [isInspectorOpen, setIsInspectorOpen] = useState(false);

  // Load all business data
  const loadBusinessData = useCallback(async () => {
    setLoading(true);
    try {
      const [dash, prods, ords, custs, anal, tabs] = await Promise.all([
        fetchDashboard().catch(() => null),
        fetchProducts().catch(() => []),
        fetchOrders().catch(() => []),
        fetchCustomers().catch(() => []),
        fetchAnalytics().catch(() => null),
        fetchDatabaseTables().catch(() => null),
      ]);

      if (dash) setDashboardData(dash);
      if (prods) setProducts(prods);
      if (ords) setOrders(ords);
      if (custs) setCustomers(custs);
      if (anal) setAnalyticsData(anal);
      if (tabs) setTablesData(tabs);
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load chat initial state
  const loadChatData = useCallback(async () => {
    try {
      const [tmplList, hist, dev] = await Promise.all([
        fetchChatTemplates().catch(() => []),
        fetchChatHistory().catch(() => ({ messages: [] })),
        fetchDeveloperStatus().catch(() => null),
      ]);

      setTemplates(tmplList);
      if (hist && hist.messages) {
        setChatMessages(hist.messages);
      }
      if (dev) {
        setDeveloperStatus(dev);
      }
    } catch (err) {
      console.error('Failed to load chat setup:', err);
    }
  }, []);

  useEffect(() => {
    loadBusinessData();
    loadChatData();
  }, [loadBusinessData, loadChatData]);

  // Handle Chat Message
  const handleSendMessage = async (text) => {
    // Optimistically append user message
    const updatedMessages = [...chatMessages, { role: 'user', content: text }];
    setChatMessages(updatedMessages);
    setChatLoading(true);

    try {
      const result = await sendChatMessage(text, selectedTemplate);
      setLastPipelineResult(result);

      if (result.response) {
        setChatMessages([...updatedMessages, { role: 'assistant', content: result.response }]);
      }

      // If an order or customer modification was done by agent, reload business tables
      loadBusinessData();
    } catch (err) {
      setChatMessages([
        ...updatedMessages,
        { role: 'assistant', content: `⚠️ Error executing request: ${err.message}` },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleClearChat = async () => {
    try {
      await clearChatHistory();
      setChatMessages([]);
      setLastPipelineResult(null);
    } catch (err) {
      console.error('Failed to clear chat:', err);
    }
  };

  // Order Handlers
  const handleOpenOrderModal = (product = null) => {
    setPreselectedProduct(product);
    setIsOrderModalOpen(true);
  };

  const handleSubmitOrder = async (orderPayload) => {
    await createOrder(orderPayload);
    await loadBusinessData();
  };

  const handleDeleteOrder = async (orderId) => {
    try {
      await deleteOrder(orderId);
      await loadBusinessData();
    } catch (err) {
      alert(`Error deleting order: ${err.message}`);
    }
  };

  // Customer Handlers
  const handleOpenCustomerModal = (customer = null) => {
    setCustomerToEdit(customer);
    setIsCustomerModalOpen(true);
  };

  const handleSubmitCustomer = async (custPayload) => {
    if (custPayload.id) {
      await updateCustomer(custPayload.id, custPayload);
    } else {
      await createCustomer(custPayload);
    }
    await loadBusinessData();
  };

  const handleDeleteCustomer = async (customerId) => {
    try {
      await deleteCustomer(customerId);
      await loadBusinessData();
    } catch (err) {
      alert(`Error deleting customer: ${err.message}`);
    }
  };

  return (
    <div className="app-container">
      {/* Top Application Header */}
      <Header onRefresh={loadBusinessData} loading={loading} />

      {/* Main Split Layout */}
      <div className="main-split-container">
        {/* Left Side: Order Management, Analytics, Dashboard, Database Viewer */}
        <section className="left-panel">
          {/* Navigation Bar */}
          <nav className="left-panel-nav">
            <button
              className={`nav-tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => setActiveTab('dashboard')}
            >
              <LayoutDashboard size={15} />
              <span>Dashboard</span>
            </button>
            <button
              className={`nav-tab-btn ${activeTab === 'orders' ? 'active' : ''}`}
              onClick={() => setActiveTab('orders')}
            >
              <ShoppingBag size={15} />
              <span>Order Management</span>
            </button>
            <button
              className={`nav-tab-btn ${activeTab === 'customers' ? 'active' : ''}`}
              onClick={() => setActiveTab('customers')}
            >
              <Users size={15} />
              <span>Customers</span>
            </button>
            <button
              className={`nav-tab-btn ${activeTab === 'analytics' ? 'active' : ''}`}
              onClick={() => setActiveTab('analytics')}
            >
              <BarChart3 size={15} />
              <span>Analytics</span>
            </button>
            <button
              className={`nav-tab-btn ${activeTab === 'database' ? 'active' : ''}`}
              onClick={() => setActiveTab('database')}
            >
              <Database size={15} />
              <span>Database Viewer</span>
            </button>
          </nav>

          {/* Left Panel Content */}
          <div className="left-panel-content">
            {activeTab === 'dashboard' && (
              <DashboardView
                dashboardData={dashboardData}
                products={products}
                onOpenOrderModal={handleOpenOrderModal}
              />
            )}

            {activeTab === 'orders' && (
              <OrdersView
                orders={orders}
                products={products}
                onOpenOrderModal={handleOpenOrderModal}
                onDeleteOrder={handleDeleteOrder}
              />
            )}

            {activeTab === 'customers' && (
              <CustomersView
                customers={customers}
                onOpenCustomerModal={handleOpenCustomerModal}
                onDeleteCustomer={handleDeleteCustomer}
              />
            )}

            {activeTab === 'analytics' && (
              <AnalyticsView analyticsData={analyticsData} />
            )}

            {activeTab === 'database' && (
              <DatabaseView
                tablesData={tablesData}
                onRefresh={loadBusinessData}
                loading={loading}
              />
            )}
          </div>
        </section>

        {/* Right Side: AI Assistant Chatbot (strictly text, no images) */}
        <section className="right-panel">
          <ChatbotPanel
            messages={chatMessages}
            onSendMessage={handleSendMessage}
            onClearChat={handleClearChat}
            onOpenInspector={() => setIsInspectorOpen(true)}
            templates={templates}
            selectedTemplate={selectedTemplate}
            setSelectedTemplate={setSelectedTemplate}
            loading={chatLoading}
            lastPipelineResult={lastPipelineResult}
          />
        </section>
      </div>

      {/* Modals */}
      <CreateOrderModal
        isOpen={isOrderModalOpen}
        onClose={() => setIsOrderModalOpen(false)}
        products={products}
        customers={customers}
        preselectedProduct={preselectedProduct}
        onSubmitOrder={handleSubmitOrder}
      />

      <CustomerModal
        isOpen={isCustomerModalOpen}
        onClose={() => setIsCustomerModalOpen(false)}
        customerToEdit={customerToEdit}
        onSubmitCustomer={handleSubmitCustomer}
      />

      <AiInspectorModal
        isOpen={isInspectorOpen}
        onClose={() => setIsInspectorOpen(false)}
        pipelineResult={lastPipelineResult}
        developerStatus={developerStatus}
      />
    </div>
  );
}
