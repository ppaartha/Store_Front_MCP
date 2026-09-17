# MCP Commerce Hub - React Frontend

A modern, high-performance React frontend designed to replace Streamlit for the Customer & Order MCP system.

## Key Features

- **Split Screen Layout**:
  - **Left Side (Control Center)**:
    - **Dashboard**: Executive summary KPI cards, recent orders, and featured product showcase with high-definition generated product imagery.
    - **Order Management**: Complete order tracking, product catalog cards, interactive modal for placing orders with real-time price calculation, and order deletion.
    - **Customer Management**: Customer directory, search, status filters (Active/Inactive), Add Customer, and Edit/Delete.
    - **Analytics**: Visual interactive charts for Revenue by Country, Top Customers by Revenue, and AI-Generated Sales Insights.
    - **Database Viewer**: Raw interactive table viewer for `customers`, `orders`, and `sales` tables with live refresh and JSON export.
  - **Right Side (AI Assistant Chatbot)**:
    - MCP-powered conversational AI assistant.
    - Strictly text & formatted markdown (no images inside chat messages, as designed).
    - Prompt template selector (Standard Assistant, Customer Care, Sales Specialist, Executive Brief).
    - Quick prompt pills for one-click questions.
    - **AI Inspector**: Interactive modal showing the multi-agent execution pipeline, stages (Summary, Intent, Entity Extraction, Planning, Specialist Delegation, Tool Selection, Response Generation), MCP tool execution logs with durations, and memory snapshot.

## Getting Started

### 1. Start the Backend API
Make sure Docker Compose or the local services are running:
```bash
# In the root project directory:
uvicorn api:app --host 0.0.0.0 --port 8001 --reload
```
Or via Docker:
```bash
docker compose up --build api
```

### 2. Start the React Frontend
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.
