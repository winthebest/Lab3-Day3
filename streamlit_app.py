"""
Streamlit UI — Travel Concierge Lab (Chatbot vs ReAct Agent + log chi tiết).

Chạy:
    conda activate vinai
    pip install streamlit
    streamlit run streamlit_app.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from chatbot import run_chatbot
from src.agent.agent import ReActAgent
from src.config import PROJECT_ROOT, load_project_env
from src.core.provider_factory import get_llm_provider
from src.evaluation.metrics_report import (
    aggregate_history_reports,
    build_evaluation_report,
)
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker
from src.tools.failure_simulation import SIMULATION_OPTIONS, failure_simulation
from src.tools.registry import get_tool_specs

load_project_env()

SIMULATION_LABELS = {
    "Tắt mô phỏng": "none",
    "Tool timeout": "tool_timeout",
    "Không tìm thấy flight": "flight_not_found",
    "Không tìm thấy hotel": "hotel_not_found",
    "Không tìm thấy promo": "promo_not_found",
}

EXAMPLE_QUERIES = {
    "✅ Đà Nẵng + SUMMER (tính tổng chi phí)": (
        "Tôi ở HCM, muốn đi Đà Nẵng 3 ngày 2 đêm, 2 người, "
        "khởi hành 15/07/2026, dùng mã SUMMER. Tổng chi phí ước tính?"
    ),
    "❌ Fail: route không có (CXR)": (
        "Tìm vé máy bay từ SGN đến Nha Trang (CXR) ngày 2026-07-15 cho 2 người."
    ),
    "❌ Fail: mã promo sai": (
        "Tôi đi Đà Nẵng, tổng đơn 5.400.000 VND, áp dụng mã khuyến mãi WINTER."
    ),
    "❌ Fail: tool ảo book_hotel": (
        "Đặt khách sạn Đà Nẵng 2 đêm, dùng tool book_hotel ngay."
    ),
    "🔎 SerpAPI: địa điểm tham quan": (
        "Tôi muốn đi Đà Nẵng, hãy tìm vài địa danh và khu tham quan nổi bật."
    ),
    "💬 Tư vấn chung": "Đà Nẵng tháng 7 có gì hay, nên đi mấy ngày?",
}


def _log_path() -> Path:
    return PROJECT_ROOT / "logs" / f"{datetime.now().strftime('%Y-%m-%d')}.log"


def _read_log_tail(max_lines: int = 80) -> str:
    path = _log_path()
    if not path.exists():
        return "(Chưa có file log hôm nay.)"
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return "\n".join(lines[-max_lines:])


def _is_fail_observation(obs: str) -> bool:
    if not obs:
        return False
    markers = (
        "not found",
        "Invalid",
        "No flights",
        "No hotels",
        "error",
        "failed",
        "timeout",
    )
    low = obs.lower()
    return any(m.lower() in low for m in markers)


def _render_react_cycles(cycles: List[Dict[str, Any]]) -> None:
    if not cycles:
        st.info("Không có ReAct cycle (chế độ chatbot hoặc lỗi trước khi gọi LLM).")
        return

    for cycle in cycles:
        n = cycle.get("cycle", "?")
        obs = cycle.get("observation") or ""
        is_fail = _is_fail_observation(obs)
        label = f"Cycle {n}" + (" ⚠️" if is_fail else "")
        with st.expander(label, expanded=is_fail or n == 1):
            if cycle.get("thought"):
                st.markdown("**Thought**")
                st.write(cycle["thought"])
            elif cycle.get("action"):
                st.caption("Thought: *(không có trong output LLM)*")

            if cycle.get("action"):
                st.markdown("**Action**")
                st.code(cycle["action"], language=None)

            if cycle.get("observation"):
                st.markdown("**Observation**")
                if is_fail:
                    st.error(cycle["observation"])
                else:
                    st.success(cycle["observation"])

            if cycle.get("final_answer"):
                st.markdown("**Final Answer**")
                st.write(cycle["final_answer"])

            if cycle.get("note"):
                st.warning(cycle["note"])

            with st.popover("LLM raw"):
                st.text(cycle.get("llm_raw", ""))


def _attach_evaluation(
    payload: Dict[str, Any],
    *,
    query: str,
    max_steps: int,
    wall_ms: int,
    session_log: List[Dict[str, Any]],
    metrics: List[Dict[str, Any]],
) -> Dict[str, Any]:
    payload["wall_ms"] = wall_ms
    payload["max_steps"] = max_steps
    payload["session_log"] = session_log
    payload["metrics"] = metrics
    payload["evaluation"] = build_evaluation_report(
        mode=payload.get("mode", "?"),
        metrics=metrics,
        react_trace=payload.get("react_trace") or [],
        session_log=session_log,
        max_steps=max_steps,
        final_answer=payload.get("answer", ""),
        wall_ms=wall_ms,
        query=query,
    )
    return payload


def _run_agent(query: str, max_steps: int, simulate: str = "none") -> Dict[str, Any]:
    t0 = time.perf_counter()
    llm = get_llm_provider()
    agent = ReActAgent(llm=llm, max_steps=max_steps)
    with failure_simulation(simulate):
        answer = agent.run(query, print_trace=False)
    wall_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "mode": "agent",
        "answer": answer,
        "react_trace": agent.react_trace,
        "react_text": agent.format_react_trace(query),
        "model": llm.model_name,
        "wall_ms": wall_ms,
        "simulation": simulate,
    }


def _run_chatbot_mode(query: str) -> Dict[str, Any]:
    t0 = time.perf_counter()
    llm = get_llm_provider()
    answer = run_chatbot(query)
    wall_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "mode": "chatbot",
        "answer": answer,
        "react_trace": [],
        "react_text": "",
        "model": llm.model_name,
        "wall_ms": wall_ms,
    }


def _render_evaluation_panel(report: Dict[str, Any], *, title: str = "") -> None:
    if title:
        st.markdown(f"#### {title}")

    rel = report.get("reliability", "?")
    rel_color = {"PASS": "🟢", "DEGRADED": "🟡", "FAIL": "🔴"}.get(rel, "⚪")
    st.markdown(f"**Reliability:** {rel_color} `{rel}` · **Failures:** {report.get('failure_count', 0)}")

    st.markdown("##### 1. Token efficiency *(EVALUATION.md)*")
    tok = report["token_efficiency"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prompt tokens", tok["prompt_tokens"])
    c2.metric("Completion tokens", tok["completion_tokens"])
    c3.metric("Total tokens", tok["total_tokens"])
    c4.metric("Cost (ước tính $)", tok["cost_estimate_usd"])
    st.caption(
        f"LLM calls: {tok['llm_calls']} · "
        f"Prompt {tok['prompt_share_pct']}% / Completion {tok['completion_share_pct']}% — {tok['note']}"
    )

    st.markdown("##### 2. Latency")
    lat = report["latency"]
    l1, l2, l3, l4 = st.columns(4)
    l1.metric("Tổng LLM (ms)", lat["total_llm_latency_ms"])
    l2.metric("Wall clock (ms)", lat.get("wall_clock_ms") or "-")
    l3.metric("TTFT ước lượng (ms)", lat.get("ttft_ms") or "-")
    l4.metric("P99 step (ms)", lat["p99_step_ms"])
    if lat["per_step_latency_ms"]:
        st.bar_chart(
            {"latency_ms": lat["per_step_latency_ms"]},
            x_label="LLM call #",
            y_label="ms",
        )
    goal = lat["production_goal_ms"]
    if lat["total_llm_latency_ms"] > goal:
        st.warning(f"Vượt mục tiêu production ~{goal}ms (tổng các vòng ReAct).")
    else:
        st.success(f"Trong mục tiêu ~{goal}ms (tổng LLM).")
    st.caption(lat.get("ttft_note", ""))

    st.markdown("##### 3. Loop count & termination")
    loop = report["loop_termination"]
    t1, t2, t3 = st.columns(3)
    t1.metric("ReAct cycles", loop["react_cycles"])
    t2.metric("Tool calls", loop["tool_call_cycles"])
    t3.metric("Termination", loop["termination"])
    if loop.get("multi_step_reasoning"):
        st.info("Multi-step reasoning: ≥2 tool calls.")
    if loop.get("terminated_cleanly"):
        st.success("Kết thúc bằng Final Answer.")
    else:
        st.warning("Chưa dừng sạch (timeout / thiếu Final Answer).")

    st.markdown("##### 4. Failure analysis")
    failures = report.get("failures") or []
    if failures:
        st.dataframe(failures, use_container_width=True, hide_index=True)
    else:
        st.success("Không phát hiện lỗi phân loại (parser / hallucination / timeout / data).")

    with st.expander("JSON evaluation report"):
        st.json(report)


def main() -> None:
    st.set_page_config(
        page_title="Travel Agent Lab",
        page_icon="✈️",
        layout="wide",
    )

    st.title("✈️ Travel Concierge — Lab 3")
    st.caption("Chatbot vs ReAct Agent · Log JSON + ReAct Mechanics")

    if "history" not in st.session_state:
        st.session_state.history = []

    with st.sidebar:
        st.header("Cấu hình")
        provider = os.getenv("DEFAULT_PROVIDER", "?")
        model = os.getenv("DEFAULT_MODEL", "?")
        st.text(f"Provider: {provider}")
        st.text(f"Model: {model}")
        st.text(f"Log file: logs/{datetime.now():%Y-%m-%d}.log")

        mode = st.radio("Chế độ", ["ReAct Agent", "Chatbot baseline"], index=0)
        max_steps = st.slider("max_steps (agent)", 2, 12, 8)
        simulation_label = st.selectbox(
            "Mô phỏng lỗi (agent)",
            list(SIMULATION_LABELS.keys()),
            index=0,
        )
        simulation_mode = SIMULATION_LABELS[simulation_label]
        if simulation_mode != "none":
            st.warning(f"Simulation active: {SIMULATION_OPTIONS[simulation_mode]}")

        st.divider()
        st.subheader("Câu mẫu")
        picked = st.selectbox("Chọn ví dụ", list(EXAMPLE_QUERIES.keys()))
        if st.button("Dùng câu mẫu"):
            st.session_state["query_box"] = EXAMPLE_QUERIES[picked]
            st.rerun()

        st.divider()
        if st.button("Xóa lịch sử phiên"):
            st.session_state.history = []
            st.rerun()

    default_q = EXAMPLE_QUERIES["✅ Đà Nẵng + SUMMER (tính tổng chi phí)"]
    query = st.text_area(
        "Câu hỏi",
        value=st.session_state.get("query_box", default_q),
        height=100,
        key="query_box",
    )

    col_run, col_cmp = st.columns([1, 1])
    run_clicked = col_run.button("▶ Chạy", type="primary", use_container_width=True)
    compare_clicked = col_cmp.button("⇄ So sánh Chatbot + Agent", use_container_width=True)

    if run_clicked or compare_clicked:
        logger.clear_session()
        tracker.session_metrics.clear()

        runs: List[Dict[str, Any]] = []
        try:
            with st.spinner("Đang gọi LLM..."):
                if compare_clicked:
                    logger.clear_session()
                    tracker.session_metrics.clear()
                    r_bot = _run_chatbot_mode(query)
                    log_bot = logger.get_session_events()
                    m_bot = list(tracker.session_metrics)

                    logger.clear_session()
                    tracker.session_metrics.clear()
                    r_agent = _run_agent(query, max_steps, simulation_mode)
                    log_agent = logger.get_session_events()
                    m_agent = list(tracker.session_metrics)

                    ts = datetime.now().isoformat(timespec="seconds")
                    st.session_state.history.insert(
                        0,
                        _attach_evaluation(
                            {**r_agent, "time": ts, "query": query},
                            query=query,
                            max_steps=max_steps,
                            wall_ms=r_agent.get("wall_ms", 0),
                            session_log=log_agent,
                            metrics=m_agent,
                        ),
                    )
                    st.session_state.history.insert(
                        0,
                        _attach_evaluation(
                            {**r_bot, "time": ts, "query": query},
                            query=query,
                            max_steps=max_steps,
                            wall_ms=r_bot.get("wall_ms", 0),
                            session_log=log_bot,
                            metrics=m_bot,
                        ),
                    )
                    st.session_state.last_compare = True
                    runs = []  # already saved
                else:
                    st.session_state.last_compare = False
                    if mode.startswith("ReAct"):
                        runs.append(_run_agent(query, max_steps, simulation_mode))
                    else:
                        runs.append(_run_chatbot_mode(query))

            for r in runs:
                st.session_state.history.insert(
                    0,
                    _attach_evaluation(
                        {
                            "time": datetime.now().isoformat(timespec="seconds"),
                            "query": query,
                            **r,
                        },
                        query=query,
                        max_steps=max_steps,
                        wall_ms=r.get("wall_ms", 0),
                        session_log=logger.get_session_events(),
                        metrics=list(tracker.session_metrics),
                    ),
                )
        except Exception as e:
            st.error(f"Lỗi: {e}")
            logger.log_event("APP_ERROR", {"error": str(e)})
            st.session_state.history.insert(
                0,
                {
                    "time": datetime.now().isoformat(timespec="seconds"),
                    "query": query,
                    "mode": "error",
                    "answer": str(e),
                    "react_trace": [],
                    "session_log": logger.get_session_events(),
                    "metrics": [],
                },
            )

    if st.session_state.history:
        latest = st.session_state.history[0]
        st.divider()
        st.subheader("Kết quả mới nhất")

        if st.session_state.get("last_compare") and len(st.session_state.history) >= 2:
            bot = next((h for h in st.session_state.history if h.get("mode") == "chatbot"), None)
            ag = next((h for h in st.session_state.history if h.get("mode") == "agent"), None)
            if bot and ag:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("### Chatbot")
                    st.write(bot.get("answer", ""))
                with c2:
                    st.markdown("### ReAct Agent")
                    if ag.get("simulation") and ag.get("simulation") != "none":
                        st.caption(f"Simulation: `{ag.get('simulation')}`")
                    st.write(ag.get("answer", ""))
                latest = ag
        else:
            meta = f"**Chế độ:** `{latest.get('mode')}` · **Model:** `{latest.get('model', '-')}`"
            if latest.get("simulation") and latest.get("simulation") != "none":
                meta += f" · **Simulation:** `{latest.get('simulation')}`"
            st.markdown(meta)
            st.write(latest.get("answer", ""))

        tab_react, tab_eval, tab_log, tab_file = st.tabs(
            [
                "🔄 ReAct Trace",
                "📊 Evaluation (EVALUATION.md)",
                "📋 Log phiên (JSON)",
                "📁 File log (tail)",
            ]
        )

        with tab_react:
            if latest.get("react_text"):
                st.code(latest["react_text"], language=None)
            _render_react_cycles(latest.get("react_trace") or [])

        with tab_eval:
            st.caption(
                "Theo EVALUATION.md: Token efficiency · Latency · Loop count · Failure analysis"
            )
            if st.session_state.get("last_compare"):
                bot = next((h for h in st.session_state.history if h.get("mode") == "chatbot"), None)
                ag = next((h for h in st.session_state.history if h.get("mode") == "agent"), None)
                if bot and ag and bot.get("evaluation") and ag.get("evaluation"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        _render_evaluation_panel(bot["evaluation"], title="Chatbot")
                    with ec2:
                        _render_evaluation_panel(ag["evaluation"], title="ReAct Agent")
                    st.markdown("##### So sánh nhanh")
                    st.table(
                        {
                            "Metric": [
                                "Total tokens",
                                "Wall clock (ms)",
                                "LLM calls",
                                "Failures",
                                "Reliability",
                            ],
                            "Chatbot": [
                                bot["evaluation"]["token_efficiency"]["total_tokens"],
                                bot["evaluation"]["latency"].get("wall_clock_ms"),
                                bot["evaluation"]["token_efficiency"]["llm_calls"],
                                bot["evaluation"]["failure_count"],
                                bot["evaluation"]["reliability"],
                            ],
                            "Agent": [
                                ag["evaluation"]["token_efficiency"]["total_tokens"],
                                ag["evaluation"]["latency"].get("wall_clock_ms"),
                                ag["evaluation"]["token_efficiency"]["llm_calls"],
                                ag["evaluation"]["failure_count"],
                                ag["evaluation"]["reliability"],
                            ],
                        }
                    )
            elif latest.get("evaluation"):
                _render_evaluation_panel(latest["evaluation"])

            agg = aggregate_history_reports(st.session_state.history, max_steps)
            if agg.get("runs", 0) > 1:
                st.divider()
                st.markdown("##### Aggregate reliability (phiên Streamlit)")
                a1, a2, a3 = st.columns(3)
                a1.metric("Runs", agg["runs"])
                a2.metric("Pass %", f"{agg.get('reliability_pct', 0)}%")
                a3.metric("Avg tokens", agg.get("avg_total_tokens", 0))

        with tab_log:
            events = latest.get("session_log") or []
            st.caption(f"{len(events)} events — đã ghi vào `logs/`")
            for ev in events:
                etype = ev.get("event", "?")
                icon = "🔴" if "ERROR" in etype or (
                    etype == "REACT_CYCLE"
                    and _is_fail_observation(
                        str((ev.get("data") or {}).get("observation", ""))
                    )
                ) else "🟢"
                with st.expander(f"{icon} `{etype}` · {ev.get('timestamp', '')[:19]}"):
                    st.json(ev.get("data", {}))

            st.download_button(
                "Tải log phiên (.json)",
                data=json.dumps(events, ensure_ascii=False, indent=2),
                file_name=f"session_log_{datetime.now():%H%M%S}.json",
                mime="application/json",
            )

        with tab_file:
            st.code(_read_log_tail(100), language="json")

        with st.expander("Lịch sử phiên Streamlit"):
            for i, h in enumerate(st.session_state.history[:5]):
                st.markdown(f"**#{i + 1}** `{h.get('time')}` · {h.get('mode')} — {h.get('query', '')[:60]}...")

    else:
        st.info("Nhập câu hỏi và bấm **Chạy** hoặc **So sánh Chatbot + Agent**.")

    with st.sidebar:
        st.divider()
        st.markdown("**Tools**")
        for t in get_tool_specs():
            st.caption(f"`{t['name']}`")


if __name__ == "__main__":
    main()
