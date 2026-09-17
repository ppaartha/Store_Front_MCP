import React from 'react';
import { BarChart3, TrendingUp, Globe, Award, Sparkles, PieChart, DollarSign } from 'lucide-react';

export default function AnalyticsView({ analyticsData }) {
  if (!analyticsData) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        Loading analytics metrics...
      </div>
    );
  }

  const {
    revenue_by_country = [],
    revenue_by_customer = [],
    status_distribution = { active: 0, inactive: 0 },
    sales_summary = {},
    sales_insights = '',
  } = analyticsData;

  const maxCountryRev = Math.max(...revenue_by_country.map((c) => c.revenue), 1);
  const maxCustRev = Math.max(...revenue_by_customer.map((c) => c.revenue), 1);

  return (
    <div>
      <div className="section-header">
        <div>
          <h2 className="section-title">
            <BarChart3 size={18} color="var(--accent-purple)" />
            <span>Commerce Analytics & Intelligence</span>
          </h2>
          <p className="section-caption">Comprehensive revenue breakdown, geographical reach, and automated sales insights</p>
        </div>
      </div>

      {/* Financial Summary KPI Cards */}
      <div className="kpi-grid" style={{ marginBottom: '1.5rem' }}>
        <div className="kpi-card">
          <div className="kpi-header">
            <span>Gross Sales</span>
            <DollarSign size={15} color="var(--accent-primary)" />
          </div>
          <div className="kpi-value">${Number(sales_summary.gross_sales || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
          <div className="kpi-footer">
            <span>Pre-discount total</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span>Net Revenue</span>
            <TrendingUp size={15} color="var(--accent-emerald)" />
          </div>
          <div className="kpi-value" style={{ color: 'var(--accent-emerald)' }}>
            ${Number(sales_summary.net_revenue || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <div className="kpi-footer">
            <span>After discounts & refunds</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span>Total Profit</span>
            <Award size={15} color="var(--accent-cyan)" />
          </div>
          <div className="kpi-value" style={{ color: 'var(--accent-cyan)' }}>
            ${Number(sales_summary.total_profit || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <div className="kpi-footer">
            <span>Margin: {sales_summary.profit_margin_pct || 0}%</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span>Active Ratio</span>
            <PieChart size={15} color="var(--accent-amber)" />
          </div>
          <div className="kpi-value">
            {Math.round(
              ((status_distribution.active || 0) /
                Math.max((status_distribution.active || 0) + (status_distribution.inactive || 0), 1)) *
                100
            )}%
          </div>
          <div className="kpi-footer">
            <span>{status_distribution.active} active / {status_distribution.inactive} inactive</span>
          </div>
        </div>
      </div>

      {/* AI Sales Insights Banner */}
      {sales_insights && (
        <div
          style={{
            background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.1))',
            border: '1px solid rgba(99, 102, 241, 0.3)',
            borderRadius: 'var(--radius-lg)',
            padding: '1.25rem 1.5rem',
            marginBottom: '1.5rem',
            boxShadow: '0 4px 20px rgba(99, 102, 241, 0.15)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem' }}>
            <Sparkles size={18} color="var(--accent-purple)" />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#fff' }}>Automated Sales Intelligence</h3>
            <span className="badge badge-active" style={{ fontSize: '0.7rem' }}>AI Generated</span>
          </div>
          <div style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.6', whiteSpace: 'pre-line' }}>
            {sales_insights}
          </div>
        </div>
      )}

      {/* Charts Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.5rem' }}>
        {/* Revenue by Country */}
        <div className="analytics-chart-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
            <Globe size={16} color="var(--accent-cyan)" />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Revenue by Country</h3>
          </div>
          {revenue_by_country.slice(0, 8).map((item) => {
            const pct = Math.round((item.revenue / maxCountryRev) * 100);
            return (
              <div key={item.country} className="bar-chart-row">
                <div className="bar-label">{item.country}</div>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${pct}%` }}></div>
                </div>
                <div className="bar-value">${item.revenue.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>
              </div>
            );
          })}
        </div>

        {/* Top Customers by Spend */}
        <div className="analytics-chart-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
            <Award size={16} color="var(--accent-amber)" />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Top Customers by Spend</h3>
          </div>
          {revenue_by_customer.slice(0, 8).map((cust) => {
            const pct = Math.round((cust.revenue / maxCustRev) * 100);
            return (
              <div key={cust.customer_id} className="bar-chart-row">
                <div className="bar-label">{cust.name}</div>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{
                      width: `${pct}%`,
                      background: 'linear-gradient(90deg, var(--accent-purple), var(--accent-primary))',
                    }}
                  ></div>
                </div>
                <div className="bar-value">${cust.revenue.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
