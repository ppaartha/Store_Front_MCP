"""FastAPI backend bridge for React frontend and MCP AI Assistant."""

from __future__ import annotations

import json
import logging
import os
import socket
from decimal import Decimal
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Fallback for POSTGRES_HOST when running on local machine outside Docker network
if os.environ.get("POSTGRES_HOST") == "postgres":
    try:
        socket.gethostbyname("postgres")
    except socket.gaierror:
        # Not running inside docker network, point to localhost where docker mapped 5432
        os.environ["POSTGRES_HOST"] = "localhost"

from config import get_settings
from database import get_session
from seed import bootstrap
from server import ServiceFactory
from chat.chat_service import ChatService
from chat.conversation_service import ConversationService, ConversationState
from chat.entity_service import EntityService
from chat.intent_service import IntentService
from chat.openai_client import OpenAIClientWrapper, OpenAISettings
from chat.prompt_builder import list_templates
from chat.prompt_service import PromptService
from chat.summary_service import SummaryService
from chat.tool_executor import MCPToolExecutor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("api.backend")

settings = get_settings()

app = FastAPI(
    title="Customer & Order MCP API",
    description="REST API bridging React Frontend with MCP Server, PostgreSQL DB, and AI Assistant Pipeline",
    version="1.0.0",
)

# Enable CORS for React Frontend (Vite, local development, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for AI Conversation session (can be extended per session_id)
session_conversations: dict[str, ConversationService] = {}

def get_session_conversation(session_id: str = "default") -> ConversationService:
    if session_id not in session_conversations:
        session_conversations[session_id] = ConversationService(ConversationState())
    return session_conversations[session_id]

def get_ai_components() -> dict[str, Any]:
    # Use docker container hostname if in docker, or localhost if outside
    mcp_url = settings.mcp_server_url
    if "mcp-server" in mcp_url:
        try:
            socket.gethostbyname("mcp-server")
        except socket.gaierror:
            mcp_url = mcp_url.replace("mcp-server", "localhost")

    openai_settings = OpenAISettings(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        temperature=None,
        max_retries=settings.openai_max_retries,
    )
    openai_client = OpenAIClientWrapper(openai_settings)
    prompt_service = PromptService()
    tool_executor = MCPToolExecutor(mcp_url)
    chat_service = ChatService(
        openai_client=openai_client,
        prompt_service=prompt_service,
        summary_service=SummaryService(openai_client, prompt_service),
        intent_service=IntentService(openai_client, prompt_service),
        entity_service=EntityService(openai_client, prompt_service),
        tool_executor=tool_executor,
    )
    return {
        "openai_client": openai_client,
        "chat_service": chat_service,
    }


# ---------------------------------------------------------
# Pydantic Schemas for Requests & Responses
# ---------------------------------------------------------

class CustomerCreateRequest(BaseModel):
    name: str
    email: str
    phone: str
    city: str
    country: str
    status: str = "active"

class CustomerUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    status: Optional[str] = None

class OrderCreateRequest(BaseModel):
    customer_id: int
    product_name: str
    quantity: int = Field(gt=0)
    unit_price: float = Field(gt=0.0)

class ChatTurnRequest(BaseModel):
    message: str
    template_key: str = "standard_assistant"
    session_id: str = "default"

# Catalog definition matching seed data
PRODUCT_CATALOG = [
    {
        "id": "laptop-pro-14",
        "name": "Laptop Pro 14",
        "category": "Computers",
        "price": 1299.99,
        "description": "High-performance laptop with 14-inch retina display, M-series processing, and all-day battery life.",
        "image": "/images/products/laptop_pro_14.png",
        "in_stock": True,
        "rating": 4.9,
    },
    {
        "id": "mechanical-keyboard",
        "name": "Mechanical Keyboard",
        "category": "Accessories",
        "price": 149.50,
        "description": "Tactile mechanical switches, aerospace aluminum chassis, RGB backlighting, and Bluetooth 5.2.",
        "image": "/images/products/mechanical_keyboard.png",
        "in_stock": True,
        "rating": 4.8,
    },
    {
        "id": "monitor-4k",
        "name": "4K Monitor",
        "category": "Displays",
        "price": 499.00,
        "description": "Ultra-sharp 32-inch IPS panel, 99% DCI-P3 color gamut, USB-C 90W power delivery, HDR600.",
        "image": "/images/products/monitor_4k.png",
        "in_stock": True,
        "rating": 4.7,
    },
    {
        "id": "wireless-mouse",
        "name": "Wireless Mouse",
        "category": "Accessories",
        "price": 79.99,
        "description": "Ergonomic precision mouse with silent magnetic scroll, 4000 DPI darkfield sensor, rechargeable.",
        "image": "/images/products/wireless_mouse.png",
        "in_stock": True,
        "rating": 4.6,
    },
    {
        "id": "headphones-anc",
        "name": "Noise Cancelling Headphones",
        "category": "Audio",
        "price": 299.00,
        "description": "Active noise cancelling wireless headphones with spatial audio, memory foam cups, 30h battery.",
        "image": "/images/products/headphones_anc.png",
        "in_stock": True,
        "rating": 4.9,
    },
    {
        "id": "usbc-dock",
        "name": "USB-C Dock",
        "category": "Connectivity",
        "price": 189.00,
        "description": "12-in-1 dual 4K display dock, 100W PD passthrough, Gigabit Ethernet, SD card readers.",
        "image": "/images/products/usbc_dock.png",
        "in_stock": True,
        "rating": 4.5,
    },
    {
        "id": "cloud-subscription",
        "name": "Cloud Subscription",
        "category": "Software & Services",
        "price": 240.00,
        "description": "Annual enterprise cloud tier with 5TB encrypted cloud storage, team workspace, automated backups.",
        "image": "/images/products/cloud_subscription.png",
        "in_stock": True,
        "rating": 4.7,
    },
    {
        "id": "office-chair",
        "name": "Office Chair",
        "category": "Furniture",
        "price": 450.00,
        "description": "Ergonomic mesh task chair with 4D adjustable armrests, lumbar support, and aluminum base.",
        "image": "/images/products/office_chair.png",
        "in_stock": True,
        "rating": 4.8,
    },
    {
        "id": "webcam-hd",
        "name": "Webcam HD",
        "category": "Accessories",
        "price": 119.00,
        "description": "1080p 60fps streaming webcam with autofocus, dual omnidirectional stereo mics, and privacy shutter.",
        "image": "/images/products/webcam_hd.png",
        "in_stock": True,
        "rating": 4.4,
    },
    {
        "id": "external-ssd",
        "name": "External SSD",
        "category": "Storage",
        "price": 159.00,
        "description": "2TB rugged portable NVMe SSD, read speeds up to 1050MB/s, IP55 dust and water resistance.",
        "image": "/images/products/external_ssd.png",
        "in_stock": True,
        "rating": 4.9,
    },
]


# ---------------------------------------------------------
# Health & Products
# ---------------------------------------------------------

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Customer & Order MCP REST API"}

@app.get("/api/products")
def get_products():
    return PRODUCT_CATALOG


# ---------------------------------------------------------
# Dashboard & Analytics Endpoints
# ---------------------------------------------------------

@app.get("/api/dashboard")
def get_dashboard():
    try:
        with ServiceFactory() as factory:
            summary = factory.analytics_service.dashboard_summary()
            recent_orders = [o.model_dump(mode="json") for o in factory.order_service.recent_orders(10)]
            total_customers = factory.customer_service.count_customers()
            customers = factory.customer_service.list_customers()
            active_count = len([c for c in customers if c.status == "active"])
            inactive_count = len([c for c in customers if c.status == "inactive"])

        return {
            "summary": {
                "total_customers": total_customers,
                "total_orders": summary.total_orders,
                "revenue": float(summary.revenue),
                "active_customers": active_count,
                "inactive_customers": inactive_count,
            },
            "recent_orders": recent_orders,
            "featured_products": PRODUCT_CATALOG[:4],
        }
    except Exception as exc:
        logger.exception("Failed to load dashboard")
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/analytics")
def get_analytics():
    try:
        with ServiceFactory() as factory:
            by_country = factory.analytics_service.revenue_by_country()
            by_customer = factory.analytics_service.revenue_by_customer()
            orders_per_customer = factory.analytics_service.orders_per_customer()
            status_distribution = {
                "active": len(factory.customer_service.customers_by_status("active")),
                "inactive": len(factory.customer_service.customers_by_status("inactive")),
            }
            sales_summary = factory.analytics_service.sales_summary()
            sales_insights = factory.analytics_service.generate_sales_insights()

        orders_lookup = {row["customer_id"]: row.get("order_count", 0) for row in orders_per_customer}

        clean_by_country = [
            {
                "country": row["country"],
                "revenue": float(row["revenue"]),
                "orders": row.get("orders") or row.get("order_count") or 0,
            }
            for row in by_country
        ]
        clean_by_customer = [
            {
                "customer_id": row["customer_id"],
                "name": row.get("name") or row.get("customer_name") or f"Customer #{row['customer_id']}",
                "revenue": float(row["revenue"]) if "revenue" in row else float(row.get("total_spend", 0)),
                "orders": orders_lookup.get(row["customer_id"], 0),
            }
            for row in by_customer
        ]

        return {
            "revenue_by_country": clean_by_country,
            "revenue_by_customer": clean_by_customer,
            "orders_per_customer": orders_per_customer,
            "status_distribution": status_distribution,
            "sales_summary": sales_summary,
            "sales_insights": sales_insights,
        }
    except Exception as exc:
        logger.exception("Failed to load analytics")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------
# Customer Management Endpoints
# ---------------------------------------------------------

@app.get("/api/customers")
def list_customers():
    try:
        with ServiceFactory() as factory:
            customers = [c.model_dump(mode="json") for c in factory.customer_service.list_customers()]
        return customers
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/customers/search")
def search_customers(q: str = Query(..., min_length=1)):
    try:
        with ServiceFactory() as factory:
            customers = [c.model_dump(mode="json") for c in factory.customer_service.search_customer(q)]
        return customers
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: int):
    try:
        with ServiceFactory() as factory:
            customer = factory.customer_service.get_customer(customer_id)
            orders = [o.model_dump(mode="json") for o in factory.order_service.customer_orders(customer_id)]
            total_spend = factory.order_service.calculate_customer_total(customer_id)
        data = customer.model_dump(mode="json")
        data["orders"] = orders
        data["total_spend"] = float(total_spend)
        return data
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found: {exc}")

@app.post("/api/customers")
def create_customer(req: CustomerCreateRequest):
    try:
        with ServiceFactory() as factory:
            created = factory.customer_service.create_customer(req.model_dump())
        return created.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.put("/api/customers/{customer_id}")
def update_customer(customer_id: int, req: CustomerUpdateRequest):
    try:
        payload = {k: v for k, v in req.model_dump().items() if v is not None}
        with ServiceFactory() as factory:
            updated = factory.customer_service.update_customer(customer_id, payload)
        return updated.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.delete("/api/customers/{customer_id}")
def delete_customer(customer_id: int):
    try:
        with ServiceFactory() as factory:
            result = factory.customer_service.delete_customer(customer_id)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------
# Order Management Endpoints
# ---------------------------------------------------------

@app.get("/api/orders")
def list_orders():
    try:
        with ServiceFactory() as factory:
            orders = [o.model_dump(mode="json") for o in factory.order_service.list_orders()]
        return orders
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/orders/{order_id}")
def get_order(order_id: int):
    try:
        with ServiceFactory() as factory:
            order = factory.order_service.get_order(order_id)
        return order.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@app.get("/api/orders/customer/{customer_id}")
def get_customer_orders(customer_id: int):
    try:
        with ServiceFactory() as factory:
            orders = [o.model_dump(mode="json") for o in factory.order_service.customer_orders(customer_id)]
            total = factory.order_service.calculate_customer_total(customer_id)
        return {"customer_id": customer_id, "orders": orders, "total_spent": float(total)}
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@app.post("/api/orders")
def create_order(req: OrderCreateRequest):
    try:
        with ServiceFactory() as factory:
            order = factory.order_service.create_order(
                {
                    "customer_id": req.customer_id,
                    "product_name": req.product_name,
                    "quantity": req.quantity,
                    "unit_price": Decimal(str(req.unit_price)),
                }
            )
        return order.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.delete("/api/orders/{order_id}")
def delete_order(order_id: int):
    try:
        with ServiceFactory() as factory:
            result = factory.order_service.delete_order(order_id)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------
# Database Viewer Endpoints
# ---------------------------------------------------------

@app.get("/api/database/tables")
def get_database_tables():
    try:
        with ServiceFactory() as factory:
            customers = [c.model_dump(mode="json") for c in factory.customer_service.list_customers()]
            orders = [o.model_dump(mode="json") for o in factory.order_service.list_orders()]
            sales = [
                {
                    "id": s.id,
                    "order_id": s.order_id,
                    "customer_id": s.customer_id,
                    "product_name": s.product_name,
                    "quantity": s.quantity,
                    "channel": s.channel,
                    "region": s.region,
                    "currency": s.currency,
                    "status": s.status,
                    "gross_amount": float(s.gross_amount),
                    "discount_amount": float(s.discount_amount),
                    "refund_amount": float(s.refund_amount),
                    "net_amount": float(s.net_amount),
                    "cost_amount": float(s.cost_amount),
                    "profit_amount": float(s.profit_amount),
                    "sale_date": s.sale_date.isoformat() if s.sale_date else None,
                }
                for s in factory.analytics_service.sales_repo.list_all()
            ]
        return {
            "customers": customers,
            "orders": orders,
            "sales": sales,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------
# MCP AI Chatbot Endpoints
# ---------------------------------------------------------

@app.get("/api/chat/templates")
def get_chat_templates():
    templates = [{"key": t.key, "label": t.label, "description": getattr(t, "description", "")} for t in list_templates()]
    return templates

@app.get("/api/chat/history")
def get_chat_history(session_id: str = "default"):
    conv_service = get_session_conversation(session_id)
    messages = [{"role": m.role, "content": m.content} for m in conv_service.state.conversation.messages]
    return {
        "session_id": session_id,
        "messages": messages,
        "summary": conv_service.state.current_summary,
        "referenced_customers": conv_service.state.referenced_customers,
        "referenced_orders": conv_service.state.referenced_orders,
        "execution_plan": conv_service.state.execution_plan,
        "latest_agent_outputs": conv_service.state.agent_outputs[-10:],
    }

@app.post("/api/chat/clear")
def clear_chat_history(session_id: str = "default"):
    conv_service = get_session_conversation(session_id)
    conv_service.clear()
    return {"status": "cleared", "session_id": session_id}

@app.get("/api/chat/developer-status")
def get_developer_status(session_id: str = "default"):
    conv_service = get_session_conversation(session_id)
    components = get_ai_components()
    chat_service: ChatService = components["chat_service"]
    analytics = conv_service.analytics_snapshot()

    return {
        "catalog": chat_service.agent_catalog(),
        "analytics": analytics,
        "debug_events": list(conv_service.state.debug_events)[-50:],
        "tool_calls": conv_service.state.previous_tool_calls[-20:],
        "agent_outputs": conv_service.state.agent_outputs[-15:],
        "execution_plan": conv_service.state.execution_plan,
    }

@app.post("/api/chat")
def chat_turn(req: ChatTurnRequest):
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured on server.")

    conv_service = get_session_conversation(req.session_id)
    components = get_ai_components()
    chat_service: ChatService = components["chat_service"]
    openai_client: OpenAIClientWrapper = components["openai_client"]

    started_at = conv_service.start_timer()
    conv_service.state.conversation.add_user(req.message)

    try:
        pipeline_result = chat_service.process_turn(
            conversation_service=conv_service,
            latest_user_message=req.message,
            template_key=req.template_key,
        )

        stream_chunks = list(openai_client.stream_text_response(pipeline_result.response_prompt))
        final_text = "".join(stream_chunks).strip()
        if not final_text:
            final_text = pipeline_result.fallback_response_text or "I processed your request using the MCP pipeline."

        conv_service.state.conversation.add_assistant(final_text)

        conv_service.finish_turn(
            started_at=started_at,
            tool_count=len(pipeline_result.tool_records),
            prompt_tokens=int(pipeline_result.usage.get("prompt_tokens", 0)),
            completion_tokens=int(pipeline_result.usage.get("completion_tokens", 0)),
            total_tokens=int(pipeline_result.usage.get("total_tokens", 0)),
        )

        stages_serialized = []
        for stage in pipeline_result.stages:
            stages_serialized.append({"name": stage.name, "payload": stage.payload})

        tool_records_serialized = []
        for tool_rec in pipeline_result.tool_records:
            resp_val = getattr(tool_rec, "response", None)
            try:
                json.dumps(resp_val)
            except (TypeError, OverflowError):
                resp_val = str(resp_val) if resp_val is not None else None

            tool_records_serialized.append(
                {
                    "tool_name": tool_rec.tool_name,
                    "arguments": tool_rec.arguments,
                    "result": resp_val,
                    "response": resp_val,
                    "duration_ms": tool_rec.duration_ms,
                    "success": tool_rec.success,
                    "error": tool_rec.error,
                }
            )

        return {
            "response": final_text,
            "timeline": pipeline_result.timeline,
            "stages": stages_serialized,
            "tool_records": tool_records_serialized,
            "usage": pipeline_result.usage,
            "memory": {
                "summary": conv_service.state.current_summary,
                "referenced_customers": conv_service.state.referenced_customers,
                "referenced_orders": conv_service.state.referenced_orders,
                "execution_plan": conv_service.state.execution_plan,
            },
        }

    except Exception as exc:
        logger.exception("Chat processing error")
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Customer & Order MCP FastAPI server on port 8001...")
    uvicorn.run("api:app", host="0.0.0.0", port=8001, reload=True)
