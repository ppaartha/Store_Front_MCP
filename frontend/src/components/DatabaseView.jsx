import React, { useState } from 'react';
import { Database, Download, RefreshCw, Search, Table } from 'lucide-react';

export default function DatabaseView({ tablesData, onRefresh, loading }) {
  const [activeTab, setActiveTab] = useState('customers');
  const [search, setSearch] = useState('');

  const customers = tablesData?.customers || [];
  const orders = tablesData?.orders || [];
  const sales = tablesData?.sales || [];

  const handleDownloadJson = (tableName, data) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${tableName}_dump.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filterData = (list) => {
    if (!search.trim()) return list;
    return list.filter((item) =>
      JSON.stringify(item).toLowerCase().includes(search.toLowerCase())
    );
  };

  return (
    <div>
      <div className="section-header">
        <div>
          <h2 className="section-title">
            <Database size={18} color="var(--accent-cyan)" />
            <span>Database Viewer & Inspector</span>
          </h2>
          <p className="section-caption">Direct read-only inspection of PostgreSQL tables backing the MCP server</p>
        </div>

        <div style={{ display: 'flex', gap: '0.6rem' }}>
          <button
            className="btn-secondary"
            onClick={onRefresh}
            disabled={loading}
          >
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
            <span>Reload DB</span>
          </button>

          <button
            className="btn-secondary"
            onClick={() => {
              const currentData = activeTab === 'customers' ? customers : activeTab === 'orders' ? orders : sales;
              handleDownloadJson(activeTab, currentData);
            }}
          >
            <Download size={13} />
            <span>Export JSON</span>
          </button>
        </div>
      </div>

      <div className="table-card">
        {/* Table Selector Tabs */}
        <div className="table-toolbar" style={{ borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', gap: '0.4rem' }}>
            <button
              className={`nav-tab-btn ${activeTab === 'customers' ? 'active' : ''}`}
              onClick={() => setActiveTab('customers')}
            >
              <Table size={14} />
              <span>customers ({customers.length})</span>
            </button>
            <button
              className={`nav-tab-btn ${activeTab === 'orders' ? 'active' : ''}`}
              onClick={() => setActiveTab('orders')}
            >
              <Table size={14} />
              <span>orders ({orders.length})</span>
            </button>
            <button
              className={`nav-tab-btn ${activeTab === 'sales' ? 'active' : ''}`}
              onClick={() => setActiveTab('sales')}
            >
              <Table size={14} />
              <span>sales ({sales.length})</span>
            </button>
          </div>

          <div className="search-input-wrapper">
            <Search size={14} color="var(--text-muted)" />
            <input
              type="text"
              placeholder={`Search in ${activeTab}...`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        {/* Render Table */}
        <div className="table-responsive">
          {activeTab === 'customers' && (
            <table className="custom-table">
              <thead>
                <tr>
                  <th>id</th>
                  <th>name</th>
                  <th>email</th>
                  <th>phone</th>
                  <th>city</th>
                  <th>country</th>
                  <th>status</th>
                  <th>created_at</th>
                </tr>
              </thead>
              <tbody>
                {filterData(customers).map((row) => (
                  <tr key={row.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{row.id}</td>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{row.name}</td>
                    <td>{row.email}</td>
                    <td>{row.phone}</td>
                    <td>{row.city}</td>
                    <td>{row.country}</td>
                    <td>
                      <span className={`badge ${row.status === 'active' ? 'badge-active' : 'badge-inactive'}`}>
                        {row.status}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{row.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {activeTab === 'orders' && (
            <table className="custom-table">
              <thead>
                <tr>
                  <th>id</th>
                  <th>customer_id</th>
                  <th>product_name</th>
                  <th>quantity</th>
                  <th>unit_price</th>
                  <th>total_price</th>
                  <th>order_date</th>
                </tr>
              </thead>
              <tbody>
                {filterData(orders).map((row) => (
                  <tr key={row.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{row.id}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>{row.customer_id}</td>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{row.product_name}</td>
                    <td>{row.quantity}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>${Number(row.unit_price).toFixed(2)}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#34d399' }}>
                      ${Number(row.total_price).toFixed(2)}
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{row.order_date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {activeTab === 'sales' && (
            <table className="custom-table">
              <thead>
                <tr>
                  <th>id</th>
                  <th>order_id</th>
                  <th>customer_id</th>
                  <th>product</th>
                  <th>channel</th>
                  <th>region</th>
                  <th>gross</th>
                  <th>discount</th>
                  <th>net</th>
                  <th>profit</th>
                  <th>status</th>
                  <th>sale_date</th>
                </tr>
              </thead>
              <tbody>
                {filterData(sales).map((row) => (
                  <tr key={row.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{row.id}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>#{row.order_id}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>#{row.customer_id}</td>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{row.product_name}</td>
                    <td>{row.channel}</td>
                    <td>{row.region}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>${Number(row.gross_amount).toFixed(2)}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-rose)' }}>${Number(row.discount_amount).toFixed(2)}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: '#34d399', fontWeight: 600 }}>${Number(row.net_amount).toFixed(2)}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)', fontWeight: 700 }}>${Number(row.profit_amount).toFixed(2)}</td>
                    <td>
                      <span className="badge badge-completed">{row.status}</span>
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{row.sale_date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
