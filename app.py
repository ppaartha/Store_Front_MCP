"""Streamlit teaching dashboard using the shared service layer."""

from __future__ import annotations

import json
from decimal import Decimal

import pandas as pd
import streamlit as st

from chat.chat_service import ChatService
from chat.conversation_service import ConversationService, ConversationState
from chat.entity_service import EntityService
from chat.intent_service import IntentService
from chat.openai_client import OpenAIClientWrapper, OpenAISettings
from chat.prompt_builder import list_templates
from chat.prompt_service import PromptService
from chat.summary_service import SummaryService
from chat.tool_executor import MCPToolExecutor
from config import get_settings
from seed import bootstrap
from server import ServiceFactory

st.set_page_config(page_title="Customer & Order MCP Dashboard", layout="wide")


@st.cache_resource
def initialize_data() -> bool:
    """Ensure migrations and seed data exist before the UI is used."""
    bootstrap(migrate=True, force_reseed=False)
    return True


initialize_data()
settings = get_settings()


def _as_df(items: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(items) if items else pd.DataFrame()


def _money(value: Decimal | float | int) -> str:
    return f"${float(value):,.2f}"


def _find_stage_payload(pipeline_result, stage_name: str) -> dict:
    if pipeline_result is None:
        return {}
    for stage in pipeline_result.stages:
        if stage.name == stage_name:
            return stage.payload
    return {}


def _render_ai_assistant_developer_panel(conversation_service: ConversationService, pipeline_result, goal_text: str) -> None:
    inspector_tab, devtools_tab = st.tabs(["AI Inspector", "Developer Tools"])

    with inspector_tab:
        st.subheader("AI Execution Pipeline")
        st.caption("Each stage is expanded for teaching visibility.")

        if pipeline_result is None:
            st.info("No pipeline run yet. Send a message to generate plan, delegation, and tool logs.")
        else:
            timeline_lines = []
            for idx, item in enumerate(pipeline_result.timeline):
                timeline_lines.append(f"✓ {item}")
                if idx < len(pipeline_result.timeline) - 1:
                    timeline_lines.append("↓")
            st.markdown("\n\n".join(timeline_lines))

            for stage in pipeline_result.stages:
                with st.expander(stage.name, expanded=True):
                    st.json(stage.payload)

            planning_payload = _find_stage_payload(pipeline_result, "Planning")
            delegation_payload = _find_stage_payload(pipeline_result, "Task Delegation")
            execution_payload = _find_stage_payload(pipeline_result, "Agent Execution")
            tool_selection_payload = _find_stage_payload(pipeline_result, "Tool Selection")

            st.subheader("Current Plan")
            st.json(planning_payload.get("plan", []))

            st.subheader("Planning Card")
            plan_steps = planning_payload.get("plan", [])
            if plan_steps:
                lines = [f"Goal: {goal_text}", ""]
                for step in plan_steps:
                    lines.append(f"Step {step.get('step_id')}: {step.get('agent')} -> {step.get('objective')}")
                st.markdown("\n\n".join(lines))

            st.subheader("Agent Collaboration View")
            collab = delegation_payload.get("collaboration_messages", [])
            if collab:
                for msg in collab:
                    st.markdown(f"**{msg.get('from')}** -> **{msg.get('to')}**: {msg.get('message')}")
            else:
                st.info("No collaboration messages captured yet.")

            st.subheader("Delegation Status")
            status_snapshot = conversation_service.analytics_snapshot().get("agent_status", {})
            if status_snapshot:
                st.json(status_snapshot)

            st.subheader("Completed Agent Outputs")
            st.json(execution_payload.get("agent_outputs", []))

            st.subheader("Selected Tools")
            st.json(tool_selection_payload.get("selected_tools", []))

        st.subheader("Memory")
        st.json(
            {
                "conversation_summary": conversation_service.state.current_summary,
                "referenced_customers": conversation_service.state.referenced_customers,
                "referenced_orders": conversation_service.state.referenced_orders,
                "execution_plan": conversation_service.state.execution_plan,
                "agent_outputs": conversation_service.state.agent_outputs[-8:],
                "intermediate_results": conversation_service.state.intermediate_results[-10:],
            }
        )

        analytics = conversation_service.analytics_snapshot()
        st.subheader("Assistant Analytics")
        st.metric("Conversation Count", analytics["conversation_count"])
        st.metric("Average Response Time (ms)", analytics["average_response_time_ms"])
        st.metric("Average Planning Time (ms)", analytics.get("average_planning_time_ms", 0.0))
        st.metric("Most Used Agent", analytics.get("most_used_agent", ""))
        st.metric("Most Used Tool", analytics.get("most_used_tool", ""))
        st.markdown("Agent Usage Frequency")
        st.json(analytics.get("agent_usage_frequency", {}))
        st.markdown("Tool Usage Frequency")
        st.json(analytics["tool_usage_frequency"])
        st.markdown("Intent Distribution")
        st.json(analytics["intent_distribution"])
        st.markdown("Token Usage")
        st.json(analytics["token_usage"])

    with devtools_tab:
        st.subheader("Developer Tools - AI Assistant")
        st.caption("Live debugging stream for agent orchestration and MCP tool usage.")

        events = list(conversation_service.state.debug_events)
        col1, col2 = st.columns(2)
        with col1:
            event_type = st.selectbox(
                "Event Type",
                ["all", "stage", "planning", "delegation", "agent_execution", "tool_call", "error"],
                index=0,
                key="ai_devtools_event_type",
            )
        with col2:
            last_n = st.slider(
                "Latest N",
                min_value=10,
                max_value=300,
                value=80,
                step=10,
                key="ai_devtools_last_n",
            )

        filtered = events
        if event_type != "all":
            filtered = [event for event in events if str(event.get("event_type")) == event_type]
        filtered = filtered[-last_n:]

        st.markdown("**Agent Event Stream**")
        if filtered:
            st.dataframe(_as_df(filtered), use_container_width=True)
        else:
            st.info("No events match current filters.")

        st.markdown("**Latest Tool Calls**")
        st.json(conversation_service.state.previous_tool_calls[-20:])

        st.markdown("**Latest Agent Outputs**")
        st.json(conversation_service.state.agent_outputs[-12:])

        st.download_button(
            label="Download AI Assistant Developer Log",
            data=json.dumps(filtered, indent=2),
            file_name="ai_assistant_developer_log.json",
            mime="application/json",
            key="ai_devtools_download",
        )


@st.cache_resource
def get_ai_components() -> dict:
    openai_settings = OpenAISettings(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        max_retries=settings.openai_max_retries,
    )
    openai_client = OpenAIClientWrapper(openai_settings)
    prompt_service = PromptService()
    tool_executor = MCPToolExecutor(settings.mcp_server_url)
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


def get_conversation_service() -> ConversationService:
    if "ai_conversation_state" not in st.session_state:
        st.session_state.ai_conversation_state = ConversationState()
    return ConversationService(st.session_state.ai_conversation_state)


def dashboard_page() -> None:
    st.title("Customer & Order Management Dashboard")
    with ServiceFactory() as factory:
        summary = factory.analytics_service.dashboard_summary()
        recent_orders = [o.model_dump(mode="json") for o in factory.order_service.recent_orders(7)]

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Customers", summary.total_customers)
    col2.metric("Total Orders", summary.total_orders)
    col3.metric("Revenue", _money(summary.revenue))
    col4.metric("Active Customers", summary.active_customers)
    col5.metric("Inactive Customers", summary.inactive_customers)

    st.subheader("Recent Orders")
    st.dataframe(_as_df(recent_orders), use_container_width=True)


def customer_management_page() -> None:
    st.title("Customer Management")

    tab1, tab2, tab3, tab4 = st.tabs(["List", "Search", "Add", "Edit/Delete"])

    with tab1:
        with ServiceFactory() as factory:
            customers = [c.model_dump(mode="json") for c in factory.customer_service.list_customers()]
        st.dataframe(_as_df(customers), use_container_width=True)

    with tab2:
        query = st.text_input("Search customer by name")
        if st.button("Search"):
            with ServiceFactory() as factory:
                customers = [
                    c.model_dump(mode="json") for c in factory.customer_service.search_customer(query)
                ]
            st.dataframe(_as_df(customers), use_container_width=True)

    with tab3:
        with st.form("add_customer_form"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            city = st.text_input("City")
            country = st.text_input("Country")
            status = st.selectbox("Status", ["active", "inactive"])
            submit = st.form_submit_button("Create Customer")

            if submit:
                try:
                    with ServiceFactory() as factory:
                        created = factory.customer_service.create_customer(
                            {
                                "name": name,
                                "email": email,
                                "phone": phone,
                                "city": city,
                                "country": country,
                                "status": status,
                            }
                        )
                    st.success(f"Customer created with id={created.id}")
                except Exception as exc:
                    st.error(str(exc))

    with tab4:
        customer_id = st.number_input("Customer ID", min_value=1, value=1)
        if st.button("Load Customer"):
            try:
                with ServiceFactory() as factory:
                    customer = factory.customer_service.get_customer(int(customer_id))
                st.json(customer.model_dump(mode="json"))
            except Exception as exc:
                st.error(str(exc))

        with st.form("update_customer_form"):
            updated_name = st.text_input("New Name")
            updated_email = st.text_input("New Email")
            updated_phone = st.text_input("New Phone")
            updated_city = st.text_input("New City")
            updated_country = st.text_input("New Country")
            updated_status = st.selectbox("New Status", ["", "active", "inactive"])
            update_submit = st.form_submit_button("Update Customer")

            if update_submit:
                payload = {
                    "name": updated_name or None,
                    "email": updated_email or None,
                    "phone": updated_phone or None,
                    "city": updated_city or None,
                    "country": updated_country or None,
                    "status": updated_status or None,
                }
                payload = {k: v for k, v in payload.items() if v is not None}
                try:
                    with ServiceFactory() as factory:
                        updated = factory.customer_service.update_customer(int(customer_id), payload)
                    st.success("Customer updated")
                    st.json(updated.model_dump(mode="json"))
                except Exception as exc:
                    st.error(str(exc))

        if st.button("Delete Customer"):
            try:
                with ServiceFactory() as factory:
                    result = factory.customer_service.delete_customer(int(customer_id))
                st.success(json.dumps(result))
            except Exception as exc:
                st.error(str(exc))


def order_management_page() -> None:
    st.title("Order Management")

    tab1, tab2, tab3, tab4 = st.tabs(["List", "Create", "Delete", "Customer Orders"])

    with tab1:
        with ServiceFactory() as factory:
            orders = [o.model_dump(mode="json") for o in factory.order_service.list_orders()]
        st.dataframe(_as_df(orders), use_container_width=True)

    with tab2:
        with st.form("create_order_form"):
            customer_id = st.number_input("Customer ID", min_value=1, value=1)
            product_name = st.text_input("Product Name")
            quantity = st.number_input("Quantity", min_value=1, value=1)
            unit_price = st.number_input("Unit Price", min_value=0.01, value=99.99)
            submit = st.form_submit_button("Create Order")
            if submit:
                try:
                    with ServiceFactory() as factory:
                        order = factory.order_service.create_order(
                            {
                                "customer_id": int(customer_id),
                                "product_name": product_name,
                                "quantity": int(quantity),
                                "unit_price": Decimal(str(unit_price)),
                            }
                        )
                    st.success(f"Order created with id={order.id}")
                except Exception as exc:
                    st.error(str(exc))

    with tab3:
        order_id = st.number_input("Order ID", min_value=1, value=1)
        if st.button("Delete Order"):
            try:
                with ServiceFactory() as factory:
                    result = factory.order_service.delete_order(int(order_id))
                st.success(json.dumps(result))
            except Exception as exc:
                st.error(str(exc))

    with tab4:
        customer_id = st.number_input("Customer ID for Orders", min_value=1, value=1)
        if st.button("Fetch Customer Orders"):
            try:
                with ServiceFactory() as factory:
                    orders = [
                        o.model_dump(mode="json")
                        for o in factory.order_service.customer_orders(int(customer_id))
                    ]
                st.dataframe(_as_df(orders), use_container_width=True)
            except Exception as exc:
                st.error(str(exc))


def analytics_page() -> None:
    st.title("Analytics")

    with ServiceFactory() as factory:
        by_country = factory.analytics_service.revenue_by_country()
        by_customer = factory.analytics_service.revenue_by_customer()
        orders_per_customer = factory.analytics_service.orders_per_customer()
        status_distribution = {
            "active": len(factory.customer_service.customers_by_status("active")),
            "inactive": len(factory.customer_service.customers_by_status("inactive")),
        }
        recent_orders = [o.model_dump(mode="json") for o in factory.order_service.recent_orders(30)]

    st.subheader("Revenue by Country")
    st.bar_chart(_as_df(by_country).set_index("country") if by_country else pd.DataFrame())

    st.subheader("Revenue by Customer")
    st.dataframe(_as_df(by_customer), use_container_width=True)

    st.subheader("Orders per Customer")
    st.dataframe(_as_df(orders_per_customer), use_container_width=True)

    st.subheader("Customer Status Distribution")
    st.bar_chart(_as_df([{"status": k, "count": v} for k, v in status_distribution.items()]).set_index("status"))

    st.subheader("Recent Orders")
    st.dataframe(_as_df(recent_orders), use_container_width=True)


def mcp_playground_page() -> None:
    st.title("MCP Playground")
    st.caption("Simulates MCP client behavior by invoking registered business operations and showing raw JSON.")

    tool_name = st.selectbox(
        "Select Tool",
        [
            "search_customer",
            "get_customer",
            "create_customer",
            "update_customer",
            "delete_customer",
            "list_customers",
            "customers_by_country",
            "customers_by_status",
            "count_customers",
            "search_customer_email",
            "list_orders",
            "get_order",
            "customer_orders",
            "create_order",
            "delete_order",
            "recent_orders",
            "highest_order",
            "calculate_customer_total",
            "list_sales",
            "sales_summary",
            "generate_sales_insights",
        ],
    )

    params_json = st.text_area(
        "Parameters (JSON)",
        value="{}",
        help="Example: {\"customer_id\": 1}",
    )

    if st.button("Execute Tool"):
        try:
            params = json.loads(params_json)
            with ServiceFactory() as factory:
                customer_service = factory.customer_service
                order_service = factory.order_service
                analytics_service = factory.analytics_service

                result = {
                    "search_customer": lambda p: [
                        c.model_dump(mode="json") for c in customer_service.search_customer(p["name"])
                    ],
                    "get_customer": lambda p: customer_service.get_customer(p["customer_id"]).model_dump(mode="json"),
                    "create_customer": lambda p: customer_service.create_customer(p).model_dump(mode="json"),
                    "update_customer": lambda p: customer_service.update_customer(
                        p["customer_id"], p["updates"]
                    ).model_dump(mode="json"),
                    "delete_customer": lambda p: customer_service.delete_customer(p["customer_id"]),
                    "list_customers": lambda p: [
                        c.model_dump(mode="json") for c in customer_service.list_customers()
                    ],
                    "customers_by_country": lambda p: [
                        c.model_dump(mode="json")
                        for c in customer_service.customers_by_country(p["country"])
                    ],
                    "customers_by_status": lambda p: [
                        c.model_dump(mode="json") for c in customer_service.customers_by_status(p["status"])
                    ],
                    "count_customers": lambda p: {"count": customer_service.count_customers()},
                    "search_customer_email": lambda p: customer_service.search_customer_email(
                        p["email"]
                    ).model_dump(mode="json"),
                    "list_orders": lambda p: [o.model_dump(mode="json") for o in order_service.list_orders()],
                    "get_order": lambda p: order_service.get_order(p["order_id"]).model_dump(mode="json"),
                    "customer_orders": lambda p: [
                        o.model_dump(mode="json") for o in order_service.customer_orders(p["customer_id"])
                    ],
                    "create_order": lambda p: order_service.create_order(p).model_dump(mode="json"),
                    "delete_order": lambda p: order_service.delete_order(p["order_id"]),
                    "recent_orders": lambda p: [
                        o.model_dump(mode="json")
                        for o in order_service.recent_orders(int(p.get("days", 30)))
                    ],
                    "highest_order": lambda p: (
                        order_service.highest_order().model_dump(mode="json")
                        if order_service.highest_order()
                        else None
                    ),
                    "calculate_customer_total": lambda p: {
                        "customer_id": p["customer_id"],
                        "total": str(order_service.calculate_customer_total(p["customer_id"])),
                    },
                    "list_sales": lambda p: [
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
                            "gross_amount": str(s.gross_amount),
                            "discount_amount": str(s.discount_amount),
                            "refund_amount": str(s.refund_amount),
                            "net_amount": str(s.net_amount),
                            "cost_amount": str(s.cost_amount),
                            "profit_amount": str(s.profit_amount),
                            "sale_date": s.sale_date.isoformat(),
                        }
                        for s in analytics_service.sales_repo.list_all()
                    ],
                    "sales_summary": lambda p: analytics_service.sales_summary(),
                    "generate_sales_insights": lambda p: analytics_service.generate_sales_insights(),
                }[tool_name](params)

            st.subheader("Raw JSON Response")
            st.json(result)
        except Exception as exc:
            st.error(f"Tool execution failed: {exc}")


def database_viewer_page() -> None:
    st.title("Database Viewer")
    if st.button("Refresh"):
        st.rerun()

    with ServiceFactory() as factory:
        customers = [c.model_dump(mode="json") for c in factory.customer_service.list_customers()]
        orders = [o.model_dump(mode="json") for o in factory.order_service.list_orders()]

    st.subheader("Customers Table")
    st.dataframe(_as_df(customers), use_container_width=True)

    st.subheader("Orders Table")
    st.dataframe(_as_df(orders), use_container_width=True)


def ai_customer_assistant_page() -> None:
    st.title("AI Customer Assistant")
    st.caption("Explainable LLM Pipeline: OpenAI + MCP Tool Calling + Conversation Memory")

    if not settings.openai_api_key:
        st.warning("OPENAI_API_KEY is not configured. Add it to your .env file to use the assistant.")
        return

    template_options = {template.label: template.key for template in list_templates()}
    selected_template_label = st.selectbox("Prompt Template", list(template_options.keys()), index=0)
    developer_mode = st.toggle("Developer Mode", value=True)

    conversation_service = get_conversation_service()
    components = get_ai_components()
    openai_client: OpenAIClientWrapper = components["openai_client"]
    chat_service: ChatService = components["chat_service"]

    if developer_mode:
        left_panel, right_panel = st.columns([1.25, 1.0])
    else:
        left_panel = st.container()
        right_panel = None

    example_prompts = [
        "Show all customers",
        "Show customers from Bangladesh",
        "Who spent the most money?",
        "Create a customer named John Doe",
        "List recent orders",
        "Generate sales insights",
    ]

    with left_panel:
        st.subheader("Chat Interface")
        prompt_cols = st.columns(3)
        for idx, prompt in enumerate(example_prompts):
            if prompt_cols[idx % 3].button(prompt, key=f"example_prompt_{idx}"):
                st.session_state.pending_prompt = prompt

        if st.button("Clear Conversation", type="secondary"):
            conversation_service.clear()
            st.session_state.pop("last_pipeline_result", None)
            st.rerun()

        for message in conversation_service.state.conversation.messages:
            with st.chat_message(message.role):
                st.markdown(message.content)

    user_prompt = st.chat_input("Ask about customers, orders, analytics, or workflow details")
    if not user_prompt and st.session_state.get("pending_prompt"):
        user_prompt = st.session_state.pop("pending_prompt")

    pipeline_result = st.session_state.get("last_pipeline_result")

    if not user_prompt:
        if developer_mode and right_panel:
            with right_panel:
                _render_ai_assistant_developer_panel(
                    conversation_service=conversation_service,
                    pipeline_result=pipeline_result,
                    goal_text="No active goal yet",
                )
        return

    started_at = conversation_service.start_timer()
    conversation_service.state.conversation.add_user(user_prompt)

    with left_panel:
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Running summary, intent, entities, planning, delegation, agent execution, and response generation..."):
                try:
                    pipeline_result = chat_service.process_turn(
                        conversation_service=conversation_service,
                        latest_user_message=user_prompt,
                        template_key=template_options[selected_template_label],
                    )
                except Exception as exc:
                    st.error(f"Assistant failed: {exc}")
                    return

            rendered = st.write_stream(openai_client.stream_text_response(pipeline_result.response_prompt))
            final_text = (rendered or "").strip()
            if not final_text:
                final_text = "I could not generate a final answer. Please try rephrasing your question."
                st.markdown(final_text)

            conversation_service.state.conversation.add_assistant(final_text)

    conversation_service.finish_turn(
        started_at=started_at,
        tool_count=len(pipeline_result.tool_records),
        prompt_tokens=int(pipeline_result.usage.get("prompt_tokens", 0)),
        completion_tokens=int(pipeline_result.usage.get("completion_tokens", 0)),
        total_tokens=int(pipeline_result.usage.get("total_tokens", 0)),
    )

    for stage in pipeline_result.stages:
        if stage.name == "Response Generation":
            stage.payload["final_response"] = final_text
            break

    st.session_state.last_pipeline_result = pipeline_result

    if developer_mode and right_panel:
        with right_panel:
            _render_ai_assistant_developer_panel(
                conversation_service=conversation_service,
                pipeline_result=pipeline_result,
                goal_text=user_prompt,
            )


def agent_monitor_page() -> None:
    st.title("Agent Monitor")
    st.caption("Runtime status and utilization of supervisor + specialist agents.")

    components = get_ai_components()
    chat_service: ChatService = components["chat_service"]
    conversation_service = get_conversation_service()
    analytics = conversation_service.analytics_snapshot()

    st.subheader("Registered Agents")
    st.json(chat_service.agent_catalog())

    col1, col2, col3 = st.columns(3)
    col1.metric("Conversation Count", analytics.get("conversation_count", 0))
    col2.metric("Avg Response Time (ms)", analytics.get("average_response_time_ms", 0.0))
    col3.metric("Avg Planning Time (ms)", analytics.get("average_planning_time_ms", 0.0))

    st.subheader("Current Agent Status")
    st.json(analytics.get("agent_status", {}))

    st.subheader("Agent Utilization")
    st.json(analytics.get("agent_usage_frequency", {}))

    st.subheader("Tools Used")
    st.json(analytics.get("tool_usage_frequency", {}))

    st.subheader("Tasks Completed")
    st.json(conversation_service.state.agent_outputs[-20:])

    st.subheader("Latest Plan")
    st.json(conversation_service.state.execution_plan)

    st.subheader("Collaboration Messages")
    st.json(analytics.get("collaboration_messages", []))

    st.subheader("Latest Agent Events")
    st.dataframe(_as_df(conversation_service.state.debug_events[-40:]), use_container_width=True)


def developer_tools_page() -> None:
    st.title("Developer Tools")
    st.caption("Deep observability for agent orchestration, planning, and MCP tool execution.")

    conversation_service = get_conversation_service()
    events = list(conversation_service.state.debug_events)

    col1, col2 = st.columns(2)
    with col1:
        event_type = st.selectbox(
            "Filter by event type",
            ["all", "stage", "planning", "delegation", "agent_execution", "tool_call", "error"],
            index=0,
        )
    with col2:
        last_n = st.slider("Show latest N events", min_value=10, max_value=500, value=100, step=10)

    filtered = events
    if event_type != "all":
        filtered = [event for event in events if str(event.get("event_type")) == event_type]
    filtered = filtered[-last_n:]

    st.subheader("Event Stream")
    if filtered:
        st.dataframe(_as_df(filtered), use_container_width=True)
    else:
        st.info("No events match the selected filters.")

    st.subheader("Structured JSON")
    st.json(filtered[-30:])

    st.download_button(
        label="Download Event Log JSON",
        data=json.dumps(filtered, indent=2),
        file_name="agent_event_log.json",
        mime="application/json",
    )

    st.subheader("Memory Snapshots")
    st.json(
        {
            "execution_plan": conversation_service.state.execution_plan,
            "agent_outputs": conversation_service.state.agent_outputs[-15:],
            "intermediate_results": conversation_service.state.intermediate_results[-20:],
            "collaboration_messages": conversation_service.state.collaboration_messages[-20:],
            "previous_tool_calls": conversation_service.state.previous_tool_calls[-20:],
        }
    )


def main() -> None:
    pages = {
        "Dashboard": dashboard_page,
        "Customer Management": customer_management_page,
        "Order Management": order_management_page,
        "Analytics": analytics_page,
        "AI Customer Assistant": ai_customer_assistant_page,
        "Agent Monitor": agent_monitor_page,
        "Developer Tools": developer_tools_page,
        "MCP Playground": mcp_playground_page,
        "Database Viewer": database_viewer_page,
    }

    selection = st.sidebar.radio("Navigation", list(pages.keys()))
    pages[selection]()


if __name__ == "__main__":
    main()
