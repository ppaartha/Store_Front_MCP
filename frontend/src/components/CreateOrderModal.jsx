import React, { useState, useEffect } from 'react';
import { X, ShoppingBag, Plus, Minus, DollarSign, User } from 'lucide-react';

export default function CreateOrderModal({ isOpen, onClose, products, customers, preselectedProduct, onSubmitOrder }) {
  const [customerId, setCustomerId] = useState('');
  const [productName, setProductName] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [unitPrice, setUnitPrice] = useState(99.99);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (preselectedProduct) {
      setProductName(preselectedProduct.name);
      setUnitPrice(preselectedProduct.price);
    } else if (products.length > 0 && !productName) {
      setProductName(products[0].name);
      setUnitPrice(products[0].price);
    }

    if (customers.length > 0 && !customerId) {
      setCustomerId(customers[0].id);
    }
  }, [preselectedProduct, products, customers]);

  if (!isOpen) return null;

  const currentProduct = products.find((p) => p.name === productName);
  const totalPrice = (quantity * unitPrice).toFixed(2);

  const handleProductChange = (name) => {
    setProductName(name);
    const prod = products.find((p) => p.name === name);
    if (prod) {
      setUnitPrice(prod.price);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!customerId || !productName || quantity <= 0 || unitPrice <= 0) {
      setError('Please provide valid customer, product, quantity, and price');
      return;
    }

    setLoading(true);
    setError('');
    try {
      await onSubmitOrder({
        customer_id: Number(customerId),
        product_name: productName,
        quantity: Number(quantity),
        unit_price: Number(unitPrice),
      });
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to place order');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" style={{ maxWidth: 520 }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <ShoppingBag size={18} color="var(--accent-primary)" />
            <h3 className="modal-title">Create Customer Order</h3>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div style={{ background: 'rgba(244,63,94,0.15)', border: '1px solid rgba(244,63,94,0.3)', color: '#fb7185', padding: '0.65rem 1rem', borderRadius: 'var(--radius-sm)', marginBottom: '1rem', fontSize: '0.82rem' }}>
                {error}
              </div>
            )}

            {/* Select Customer */}
            <div className="form-group">
              <label className="form-label">Customer</label>
              <select
                className="form-select"
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                required
              >
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    #{c.id} - {c.name} ({c.email})
                  </option>
                ))}
              </select>
            </div>

            {/* Select Product */}
            <div className="form-group">
              <label className="form-label">Product Item</label>
              <select
                className="form-select"
                value={productName}
                onChange={(e) => handleProductChange(e.target.value)}
                required
              >
                {products.map((p) => (
                  <option key={p.id} value={p.name}>
                    {p.name} - ${p.price.toFixed(2)}
                  </option>
                ))}
              </select>
            </div>

            {/* Selected Product Preview Card */}
            {currentProduct && (
              <div
                style={{
                  display: 'flex',
                  gap: '0.85rem',
                  padding: '0.75rem',
                  background: 'rgba(255,255,255,0.03)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-color)',
                  marginBottom: '1.25rem',
                  alignItems: 'center',
                }}
              >
                <img
                  src={currentProduct.image}
                  alt={currentProduct.name}
                  style={{ width: 64, height: 64, borderRadius: 'var(--radius-sm)', objectFit: 'cover' }}
                  onError={(e) => {
                    e.target.src = 'https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=600&auto=format&fit=crop&q=80';
                  }}
                />
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>{currentProduct.name}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{currentProduct.category}</div>
                  <div style={{ fontSize: '0.85rem', color: '#34d399', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                    ${currentProduct.price.toFixed(2)}
                  </div>
                </div>
              </div>
            )}

            {/* Quantity Stepper & Unit Price */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Quantity</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <button
                    type="button"
                    className="btn-secondary"
                    style={{ padding: '0.55rem' }}
                    onClick={() => setQuantity(Math.max(1, quantity - 1))}
                  >
                    <Minus size={14} />
                  </button>
                  <input
                    type="number"
                    min="1"
                    className="form-input"
                    style={{ textAlign: 'center', fontWeight: 700 }}
                    value={quantity}
                    onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                  />
                  <button
                    type="button"
                    className="btn-secondary"
                    style={{ padding: '0.55rem' }}
                    onClick={() => setQuantity(quantity + 1)}
                  >
                    <Plus size={14} />
                  </button>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Unit Price ($)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  className="form-input"
                  value={unitPrice}
                  onChange={(e) => setUnitPrice(parseFloat(e.target.value) || 0)}
                  required
                />
              </div>
            </div>

            {/* Calculated Order Total */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '0.85rem 1.25rem',
                background: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.25)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                Total Order Amount
              </span>
              <span style={{ fontSize: '1.25rem', fontWeight: 800, color: '#34d399', fontFamily: 'var(--font-mono)' }}>
                ${totalPrice}
              </span>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Submitting...' : 'Confirm Order'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
