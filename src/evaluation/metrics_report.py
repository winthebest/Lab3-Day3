"""
Industry evaluation metrics — aligned with EVALUATION.md
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _sum_metrics(metrics: List[Dict[str, Any]], key: str) -> int:
    return sum(int(m.get(key, 0) or 0) for m in metrics)


def analyze_token_efficiency(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    prompt = _sum_metrics(metrics, "prompt_tokens")
    completion = _sum_metrics(metrics, "completion_tokens")
    total = _sum_metrics(metrics, "total_tokens")
    cost = sum(float(m.get("cost_estimate", 0) or 0) for m in metrics)
    ratio = round(prompt / total * 100, 1) if total else 0.0
    return {
        "llm_calls": len(metrics),
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
        "prompt_share_pct": ratio,
        "completion_share_pct": round(100 - ratio, 1) if total else 0.0,
        "cost_estimate_usd": round(cost, 4),
        "note": (
            "Completion cao → LLM 'nói nhiều' trước Action. "
            "Prompt cao → system prompt + transcript dài qua các cycle."
        ),
    }


def analyze_latency(
    metrics: List[Dict[str, Any]],
    wall_ms: Optional[int] = None,
) -> Dict[str, Any]:
    step_latencies = [int(m.get("latency_ms", 0) or 0) for m in metrics]
    total_llm_ms = sum(step_latencies)
    avg_ms = round(total_llm_ms / len(step_latencies)) if step_latencies else 0
    p99 = max(step_latencies) if step_latencies else 0

    production_goal_ms = 2000
    status = "within_goal" if total_llm_ms <= production_goal_ms else "above_goal"

    return {
        "per_step_latency_ms": step_latencies,
        "total_llm_latency_ms": total_llm_ms,
        "wall_clock_ms": wall_ms,
        "avg_step_ms": avg_ms,
        "p99_step_ms": p99,
        "ttft_ms": step_latencies[0] if step_latencies else None,
        "ttft_note": "Ước lượng = latency LLM call đầu (chưa streaming thật).",
        "production_goal_ms": production_goal_ms,
        "latency_status": status,
    }


def classify_failures(
    react_trace: List[Dict[str, Any]],
    session_log: List[Dict[str, Any]],
    max_steps: int,
    final_answer: str = "",
) -> List[Dict[str, str]]:
    errors: List[Dict[str, str]] = []

    for cycle in react_trace:
        obs = str(cycle.get("observation") or "")
        raw = str(cycle.get("llm_raw") or "")
        n = cycle.get("cycle", "?")

        if cycle.get("note") == "No Action parsed":
            errors.append(
                {
                    "code": "PARSER_ERROR",
                    "cycle": str(n),
                    "detail": "Không parse được Action từ output LLM.",
                }
            )
        if "```" in raw and "Action:" in raw:
            errors.append(
                {
                    "code": "JSON_MARKDOWN",
                    "cycle": str(n),
                    "detail": "LLM bọc output trong markdown code fence.",
                }
            )
        if "Tool '" in obs and "not found" in obs:
            errors.append(
                {
                    "code": "HALLUCINATION_TOOL",
                    "cycle": str(n),
                    "detail": obs[:120],
                }
            )
        if any(
            x in obs.lower()
            for x in ("no flights", "no hotels", "invalid promo", "not found")
        ):
            errors.append(
                {
                    "code": "DATA_OR_TOOL_ERROR",
                    "cycle": str(n),
                    "detail": obs[:120],
                }
            )
        if not cycle.get("thought") and cycle.get("action"):
            errors.append(
                {
                    "code": "REACT_FORMAT",
                    "cycle": str(n),
                    "detail": "Thiếu Thought trước Action.",
                }
            )

    has_final = any(c.get("final_answer") for c in react_trace)
    if react_trace and not has_final:
        if len(react_trace) >= max_steps or "Không hoàn thành" in final_answer:
            errors.append(
                {
                    "code": "TIMEOUT_MAX_STEPS",
                    "cycle": "-",
                    "detail": f"Vượt hoặc chạm max_steps={max_steps}, không có Final Answer hợp lệ.",
                }
            )

    for ev in session_log:
        if ev.get("event") == "APP_ERROR":
            errors.append(
                {
                    "code": "APP_ERROR",
                    "cycle": "-",
                    "detail": str((ev.get("data") or {}).get("error", ""))[:120],
                }
            )

    # dedupe by code+cycle+detail prefix
    seen = set()
    unique: List[Dict[str, str]] = []
    for e in errors:
        key = (e["code"], e["cycle"], e["detail"][:40])
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique


def analyze_loop_termination(
    react_trace: List[Dict[str, Any]],
    max_steps: int,
    final_answer: str,
) -> Dict[str, Any]:
    tool_cycles = [c for c in react_trace if c.get("action")]
    has_final = any(c.get("final_answer") for c in react_trace)
    terminated_cleanly = has_final and "Không hoàn thành" not in (final_answer or "")

    if not react_trace:
        termination = "N/A (chatbot)"
    elif terminated_cleanly:
        termination = "FINAL_ANSWER"
    elif len(react_trace) >= max_steps:
        termination = "MAX_STEPS"
    else:
        termination = "INCOMPLETE"

    return {
        "react_cycles": len(react_trace),
        "tool_call_cycles": len(tool_cycles),
        "max_steps": max_steps,
        "termination": termination,
        "terminated_cleanly": terminated_cleanly,
        "multi_step_reasoning": len(tool_cycles) >= 2,
    }


def build_evaluation_report(
    *,
    mode: str,
    metrics: List[Dict[str, Any]],
    react_trace: List[Dict[str, Any]],
    session_log: List[Dict[str, Any]],
    max_steps: int = 8,
    final_answer: str = "",
    wall_ms: Optional[int] = None,
    query: str = "",
) -> Dict[str, Any]:
    tokens = analyze_token_efficiency(metrics)
    latency = analyze_latency(metrics, wall_ms)
    loops = analyze_loop_termination(react_trace, max_steps, final_answer)
    failures = classify_failures(react_trace, session_log, max_steps, final_answer)

    reliability = "PASS"
    if failures:
        reliability = "FAIL" if any(
            f["code"] in ("TIMEOUT_MAX_STEPS", "PARSER_ERROR", "HALLUCINATION_TOOL")
            for f in failures
        ) else "DEGRADED"

    return {
        "query": query[:200],
        "mode": mode,
        "reliability": reliability,
        "token_efficiency": tokens,
        "latency": latency,
        "loop_termination": loops,
        "failures": failures,
        "failure_count": len(failures),
    }


def aggregate_history_reports(
    history: List[Dict[str, Any]],
    max_steps_default: int = 8,
) -> Dict[str, Any]:
    """Aggregate reliability across Streamlit session runs."""
    reports = []
    for h in history:
        if h.get("mode") == "error":
            continue
        ev = h.get("evaluation") or build_evaluation_report(
            mode=h.get("mode", "?"),
            metrics=h.get("metrics") or [],
            react_trace=h.get("react_trace") or [],
            session_log=h.get("session_log") or [],
            max_steps=h.get("max_steps", max_steps_default),
            final_answer=h.get("answer", ""),
            wall_ms=h.get("wall_ms"),
            query=h.get("query", ""),
        )
        reports.append(ev)

    if not reports:
        return {"runs": 0}

    pass_n = sum(1 for r in reports if r["reliability"] == "PASS")
    return {
        "runs": len(reports),
        "pass_count": pass_n,
        "reliability_pct": round(pass_n / len(reports) * 100, 1),
        "avg_total_tokens": round(
            sum(r["token_efficiency"]["total_tokens"] for r in reports) / len(reports)
        ),
        "avg_wall_ms": round(
            sum(r["latency"].get("wall_clock_ms") or 0 for r in reports) / len(reports)
        ),
        "reports": reports,
    }
