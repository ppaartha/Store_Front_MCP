import React, { useState } from 'react';
import { Users, Search, Plus, Edit2, Trash2, Mail, Phone, MapPin, CheckCircle, XCircle } from 'lucide-react';

export default function CustomersView({ customers, onOpenCustomerModal, onDeleteCustomer, onViewOrders }) {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const filtered = customers.filter((cust) => {
    const matchesSearch =
      cust.name.toLowerCase().includes(search.toLowerCase()) ||
      cust.email.toLowerCase().includes(search.toLowerCase()) ||
      cust.country.toLowerCase().includes(search.toLowerCase()) ||
      cust.city.toLowerCase().includes(search.toLowerCase()) ||
      String(cust.id).includes(search);

    const matchesStatus = statusFilter === 'all' || cust.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div>
      <div className="section-header">
        <div>
          <h2 className="section-title">
            <Users size={18} color="var(--accent-cyan)" />
            <span>Customer Management</span>
          </h2>
          <p className="section-caption">Manage client directories, geographic regions, and account statuses</p>
        </div>
        <button className="btn-primary" onClick={() => onOpenCustomerModal()}>
          <Plus size={14} />
          <span>Add Customer</span>
        </button>
      </div>

      <div className="table-card">
        <div className="table-toolbar">
          <div className="search-input-wrapper">
            <Search size={15} color="var(--text-muted)" />
            <input
              type="text"
              placeholder="Search customer, email, city, country..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {['all', 'active', 'inactive'].map((st) => (
              <button
                key={st}
                className={`prompt-pill ${statusFilter === st ? 'active' : ''}`}
                style={{
                  textTransform: 'capitalize',
                  background: statusFilter === st ? 'rgba(6, 182, 212, 0.2)' : undefined,
                  borderColor: statusFilter === st ? 'var(--accent-cyan)' : undefined,
                  color: statusFilter === st ? '#fff' : undefined,
                }}
                onClick={() => setStatusFilter(st)}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Customer Name</th>
                <th>Contact</th>
                <th>Location</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>
                    No customers found matching filter
                  </td>
                </tr>
              ) : (
                filtered.map((cust) => (
                  <tr key={cust.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>#{cust.id}</td>
                    <td>
                      <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{cust.name}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Joined: {cust.created_at ? new Date(cust.created_at).toLocaleDateString() : 'Active Member'}
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.78rem' }}>
                        <Mail size={12} color="var(--text-muted)" />
                        <span>{cust.email}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                        <Phone size={11} />
                        <span>{cust.phone}</span>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                        <MapPin size={13} color="var(--accent-primary)" />
                        <span>{cust.city}, <strong>{cust.country}</strong></span>
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${cust.status === 'active' ? 'badge-active' : 'badge-inactive'}`}>
                        {cust.status === 'active' ? <CheckCircle size={11} /> : <XCircle size={11} />}
                        {cust.status}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'flex-end' }}>
                        <button
                          className="btn-secondary"
                          style={{ padding: '0.3rem 0.55rem', fontSize: '0.75rem' }}
                          title="Edit Customer"
                          onClick={() => onOpenCustomerModal(cust)}
                        >
                          <Edit2 size={12} />
                        </button>
                        <button
                          className="btn-danger"
                          title="Delete Customer"
                          onClick={() => {
                            if (window.confirm(`Are you sure you want to delete customer ${cust.name}? Associated orders will also be removed.`)) {
                              onDeleteCustomer(cust.id);
                            }
                          }}
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
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
