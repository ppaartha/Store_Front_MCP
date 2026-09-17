import React from 'react';
import { ShoppingBag, Cpu, Sparkles, RefreshCw } from 'lucide-react';

export default function Header({ onRefresh, loading }) {
  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-logo-icon">
          <ShoppingBag size={20} />
        </div>
        <div>
          <h1 className="brand-title">MCP Commerce Hub</h1>
          <p className="brand-subtitle">Autonomous MCP Agent Pipeline & Customer Order Engine</p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <button
          onClick={onRefresh}
          className="btn-secondary"
          style={{ padding: '0.35rem 0.75rem', fontSize: '0.78rem' }}
          disabled={loading}
          title="Refresh Data"
        >
          <RefreshCw size={14} className={loading ? 'spin' : ''} />
          <span>Refresh</span>
        </button>

        <div className="header-status-badge">
          <div className="status-dot"></div>
          <Cpu size={14} />
          <span>FastMCP Live</span>
        </div>
      </div>
    </header>
  );
}
