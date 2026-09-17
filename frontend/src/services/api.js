// API service connecting React frontend to FastAPI backend

const API_BASE = '/api';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Failed to reach backend API');
  return res.json();
}

export async function fetchProducts() {
  const res = await fetch(`${API_BASE}/products`);
  if (!res.ok) throw new Error('Failed to fetch product catalog');
  return res.json();
}

export async function fetchDashboard() {
  const res = await fetch(`${API_BASE}/dashboard`);
  if (!res.ok) throw new Error('Failed to fetch dashboard data');
  return res.json();
}

export async function fetchAnalytics() {
  const res = await fetch(`${API_BASE}/analytics`);
  if (!res.ok) throw new Error('Failed to fetch analytics');
  return res.json();
}

export async function fetchCustomers() {
  const res = await fetch(`${API_BASE}/customers`);
  if (!res.ok) throw new Error('Failed to fetch customers');
  return res.json();
}

export async function searchCustomers(query) {
  const res = await fetch(`${API_BASE}/customers/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error('Failed to search customers');
  return res.json();
}

export async function fetchCustomer(id) {
  const res = await fetch(`${API_BASE}/customers/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch customer ${id}`);
  return res.json();
}

export async function createCustomer(data) {
  const res = await fetch(`${API_BASE}/customers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create customer');
  }
  return res.json();
}

export async function updateCustomer(id, data) {
  const res = await fetch(`${API_BASE}/customers/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update customer');
  }
  return res.json();
}

export async function deleteCustomer(id) {
  const res = await fetch(`${API_BASE}/customers/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete customer');
  }
  return res.json();
}

export async function fetchOrders() {
  const res = await fetch(`${API_BASE}/orders`);
  if (!res.ok) throw new Error('Failed to fetch orders');
  return res.json();
}

export async function fetchCustomerOrders(customerId) {
  const res = await fetch(`${API_BASE}/orders/customer/${customerId}`);
  if (!res.ok) throw new Error(`Failed to fetch orders for customer ${customerId}`);
  return res.json();
}

export async function createOrder(data) {
  const res = await fetch(`${API_BASE}/orders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create order');
  }
  return res.json();
}

export async function deleteOrder(id) {
  const res = await fetch(`${API_BASE}/orders/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete order');
  }
  return res.json();
}

export async function fetchDatabaseTables() {
  const res = await fetch(`${API_BASE}/database/tables`);
  if (!res.ok) throw new Error('Failed to fetch database tables');
  return res.json();
}

// Chatbot & MCP Agent Endpoints
export async function fetchChatTemplates() {
  const res = await fetch(`${API_BASE}/chat/templates`);
  if (!res.ok) throw new Error('Failed to fetch prompt templates');
  return res.json();
}

export async function fetchChatHistory(sessionId = 'default') {
  const res = await fetch(`${API_BASE}/chat/history?session_id=${sessionId}`);
  if (!res.ok) throw new Error('Failed to fetch chat history');
  return res.json();
}

export async function clearChatHistory(sessionId = 'default') {
  const res = await fetch(`${API_BASE}/chat/clear?session_id=${sessionId}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to clear chat history');
  return res.json();
}

export async function fetchDeveloperStatus(sessionId = 'default') {
  const res = await fetch(`${API_BASE}/chat/developer-status?session_id=${sessionId}`);
  if (!res.ok) throw new Error('Failed to fetch developer status');
  return res.json();
}

export async function sendChatMessage(message, templateKey = 'standard_assistant', sessionId = 'default') {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      template_key: templateKey,
      session_id: sessionId,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Chat assistant request failed');
  }
  return res.json();
}
