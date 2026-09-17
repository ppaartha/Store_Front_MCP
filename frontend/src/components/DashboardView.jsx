import React from 'react';
import { Users, ShoppingCart, DollarSign, UserCheck, ArrowUpRight, Star, Plus } from 'lucide-react';

export default function DashboardView({ dashboardData, products, onOpenOrderModal }) {
  const summary = dashboardData?.summary || {
    total_customers: 0,
    total_orders: 0,
    revenue: 0,
    active_customers: 0,
    inactive_customers: 0,
  };

  const recentOrders = dashboardData?.recent_orders || [];
  const featured = products?.slice(0, 4) || [];

  return (
    <div>
      {/* Top KPI Cards */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-header">
            <span>Total Revenue</span>
            <DollarSign size={16} color="var(--accent-emerald)" />
          </div>
          <div className="kpi-value">${summary.revenue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
          <div className="kpi-footer">
            <ArrowUpRight size={14} color="var(--accent-emerald)" />
            <span>Cumulative sales</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span>Total Orders</span>
            <ShoppingCart size={16} color="var(--accent-primary)" />
          </div>
          <div className="kpi-value">{summary.total_orders}</div>
          <div className="kpi-footer">
            <span>Completed orders</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span>Total Customers</span>
            <Users size={16} color="var(--accent-cyan)" />
          </div>
          <div className="kpi-value">{summary.total_customers}</div>
          <div className="kpi-footer">
            <span>Registered profiles</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span>Active Customers</span>
            <UserCheck size={16} color="var(--accent-amber)" />
          </div>
          <div className="kpi-value">{summary.active_customers}</div>
          <div className="kpi-footer">
            <span style={{ color: 'var(--text-muted)' }}>{summary.inactive_customers} inactive</span>
          </div>
        </div>
      </div>

      {/* Featured Products Showcase with Generated Images */}
      <div className="section-header">
        <div>
          <h2 className="section-title">
            <Star size={18} color="var(--accent-amber)" />
            <span>Featured Product Catalog</span>
          </h2>
          <p className="section-caption">High-demand items ready for instant customer ordering via UI or MCP Chatbot</p>
        </div>
        <button
          className="btn-primary"
          onClick={() => onOpenOrderModal()}
          style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
        >
          <Plus size={14} />
          <span>New Order</span>
        </button>
      </div>

      <div className="products-grid">
        {featured.map((product) => (
          <div key={product.id} className="product-card">
            <div className="product-image-container">
              <img
                src={product.image}
                alt={product.name}
                className="product-img"
                onError={(e) => {
                  e.target.src = 'https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=600&auto=format&fit=crop&q=80';
                }}
              />
              <span className="product-badge">{product.category}</span>
            </div>
            <div className="product-info">
              <h3 className="product-name">{product.name}</h3>
              <p className="product-desc">{product.description}</p>
              <div className="product-meta-row">
                <span className="product-price">${product.price.toFixed(2)}</span>
                <button
                  className="quick-order-btn"
                  onClick={() => onOpenOrderModal(product)}
                >
                  <Plus size={13} />
                  <span>Order</span>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Orders Table */}
      <div className="table-card">
        <div className="table-toolbar">
          <div>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Recent Customer Orders</h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Latest transactions recorded in PostgreSQL database</p>
          </div>
        </div>
        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Order ID</th>
                <th>Customer ID</th>
                <th>Product</th>
                <th>Qty</th>
                <th>Unit Price</th>
                <th>Total</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {recentOrders.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    No recent orders found
                  </td>
                </tr>
              ) : (
                recentOrders.map((order) => (
                  <tr key={order.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>#{order.id}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>Cust #{order.customer_id}</td>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{order.product_name}</td>
                    <td>{order.quantity}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>${Number(order.unit_price).toFixed(2)}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#34d399' }}>
                      ${Number(order.total_price).toFixed(2)}
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                      {order.order_date ? new Date(order.order_date).toLocaleDateString() : 'Recent'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
