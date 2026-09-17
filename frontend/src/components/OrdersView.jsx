import React, { useState } from 'react';
import { ShoppingBag, Search, Plus, Trash2, Filter } from 'lucide-react';

export default function OrdersView({ orders, products, onOpenOrderModal, onDeleteOrder }) {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const filteredOrders = orders.filter((order) => {
    const matchesSearch =
      order.product_name.toLowerCase().includes(search.toLowerCase()) ||
      String(order.id).includes(search) ||
      String(order.customer_id).includes(search);
    return matchesSearch;
  });

  const categories = ['all', ...new Set(products.map((p) => p.category))];
  const filteredProducts = selectedCategory === 'all'
    ? products
    : products.filter((p) => p.category === selectedCategory);

  return (
    <div>
      {/* Product Catalog Grid with Images */}
      <div className="section-header">
        <div>
          <h2 className="section-title">
            <ShoppingBag size={18} color="var(--accent-primary)" />
            <span>Product Catalog</span>
          </h2>
          <p className="section-caption">Select any item to quickly issue a new customer order</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {categories.map((cat) => (
            <button
              key={cat}
              className={`prompt-pill ${selectedCategory === cat ? 'active' : ''}`}
              style={{
                textTransform: 'capitalize',
                background: selectedCategory === cat ? 'rgba(99, 102, 241, 0.2)' : undefined,
                borderColor: selectedCategory === cat ? 'var(--accent-primary)' : undefined,
                color: selectedCategory === cat ? '#fff' : undefined,
              }}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      <div className="products-grid" style={{ marginBottom: '2rem' }}>
        {filteredProducts.map((product) => (
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
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <h3 className="product-name">{product.name}</h3>
                <span style={{ fontSize: '0.75rem', color: 'var(--accent-amber)', fontWeight: 600 }}>★ {product.rating}</span>
              </div>
              <p className="product-desc">{product.description}</p>
              <div className="product-meta-row">
                <span className="product-price">${product.price.toFixed(2)}</span>
                <button
                  className="quick-order-btn"
                  onClick={() => onOpenOrderModal(product)}
                >
                  <Plus size={13} />
                  <span>Create Order</span>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Orders List & Management */}
      <div className="table-card">
        <div className="table-toolbar">
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Customer Orders History</h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Showing {filteredOrders.length} of {orders.length} total orders
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <div className="search-input-wrapper">
              <Search size={15} color="var(--text-muted)" />
              <input
                type="text"
                placeholder="Search product or customer ID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            <button className="btn-primary" onClick={() => onOpenOrderModal()}>
              <Plus size={14} />
              <span>Create Order</span>
            </button>
          </div>
        </div>

        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Order ID</th>
                <th>Customer</th>
                <th>Item Ordered</th>
                <th>Quantity</th>
                <th>Unit Price</th>
                <th>Total Price</th>
                <th>Date Placed</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrders.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>
                    No orders match your filter criteria
                  </td>
                </tr>
              ) : (
                filteredOrders.map((order) => {
                  const productInfo = products.find((p) => p.name.toLowerCase() === order.product_name.toLowerCase());
                  return (
                    <tr key={order.id}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>#{order.id}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                        Customer #{order.customer_id}
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                          {productInfo && (
                            <img
                              src={productInfo.image}
                              alt=""
                              style={{ width: 28, height: 28, borderRadius: 4, objectFit: 'cover' }}
                            />
                          )}
                          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{order.product_name}</span>
                        </div>
                      </td>
                      <td>
                        <span className="badge badge-active" style={{ background: 'rgba(99,102,241,0.1)', color: '#818cf8', borderColor: 'rgba(99,102,241,0.3)' }}>
                          x{order.quantity}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>${Number(order.unit_price).toFixed(2)}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#34d399' }}>
                        ${Number(order.total_price).toFixed(2)}
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        {order.order_date ? new Date(order.order_date).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : 'N/A'}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          className="btn-danger"
                          title="Delete Order"
                          onClick={() => {
                            if (window.confirm(`Are you sure you want to delete order #${order.id}?`)) {
                              onDeleteOrder(order.id);
                            }
                          }}
                        >
                          <Trash2 size={13} />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
