import re
from typing import Any, Dict, List, Optional, Tuple

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker
from src.tools.registry import execute_tool, get_tool_specs


class ReActAgent:
    """ReAct agent — chủ đề Travel Concierge (vé, khách sạn, promo)."""

    def __init__(
        self,
        llm: LLMProvider,
        tools: Optional[List[Dict[str, str]]] = None,
        max_steps: int = 8,
    ):
        self.llm = llm
        self.tools = tools or get_tool_specs()
        self.max_steps = max_steps
        self.history: List[Dict[str, str]] = []
        self.react_trace: List[Dict[str, Any]] = []

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join(
            f"- {t['name']}: {t['description']}" for t in self.tools
        )
        return f"""You are a Travel Concierge agent for Vietnam domestic trips.
You MUST use tools for prices, hotels, and promo codes — do not invent numbers.

Available tools:
{tool_descriptions}

Rules:
- Map cities: HCM/Ho Chi Minh → SGN, Đà Nẵng/Da Nang → DAD, Hà Nội → HAN.
- Dates: YYYY-MM-DD. "3 ngày 2 đêm" means nights=2 for hotel.
- Multiply flight price by passengers; hotel by nights (not days).
- For full trip total (vé + khách sạn + promo), prefer estimate_trip_cost in one call.
- Otherwise: search_flights + get_hotel_rate, then apply_promo if user gave a code.
- If the user asks about places to visit, attractions, landmarks, or sightseeing, use search_attractions.
- If the user asks about weather, rain, temperature, or what to wear, use get_weather_forecast for the destination.

Output format (no markdown fences) — ALWAYS include Thought before Action or Final Answer:
Thought: <reasoning>
Action: tool_name(arg=value, ...)

When finished:
Thought: <brief summary>
Final Answer: <clear answer in Vietnamese with VND amounts>

Do NOT write "Observation:" — the system appends it after each Action.
One Action per turn only.
"""

    def run(self, user_input: str, *, print_trace: bool = False) -> str:
        self.react_trace = []
        logger.log_event(
            "AGENT_START",
            {"input": user_input, "model": self.llm.model_name, "theme": "travel"},
        )

        transcript = f"User question: {user_input}\n"
        steps = 0
        final_answer: Optional[str] = None

        while steps < self.max_steps:
            result = self.llm.generate(
                transcript,
                system_prompt=self.get_system_prompt(),
            )
            content = result.get("content", "")
            usage = result.get("usage", {})
            latency = result.get("latency_ms", 0)
            provider = result.get("provider", "unknown")
            tracker.track_request(provider, self.llm.model_name, usage, latency)

            thought = self._extract_thought(content)
            final = self._extract_final_answer(content)
            action = self._extract_action(content)

            cycle: Dict[str, Any] = {
                "cycle": steps + 1,
                "thought": thought,
                "llm_raw": content.strip(),
            }

            if final:
                cycle["final_answer"] = final
                self.react_trace.append(cycle)
                self._log_react_cycle(cycle)
                final_answer = final
                break

            if action:
                tool_name, arg_string = action
                action_str = f"{tool_name}({arg_string})"
                observation = execute_tool(tool_name, arg_string)
                cycle["action"] = action_str
                cycle["observation"] = observation
                self.react_trace.append(cycle)
                self._log_react_cycle(cycle)

                transcript += f"\n{content.strip()}\nObservation: {observation}\n"
            else:
                cycle["note"] = "No Action parsed"
                self.react_trace.append(cycle)
                self._log_react_cycle(cycle)
                transcript += f"\n{content.strip()}\n"
                if steps >= self.max_steps - 1:
                    final_answer = content.strip()
                    break

            steps += 1

        if not final_answer:
            final_answer = (
                "Không hoàn thành trong số bước cho phép. "
                "Vui lòng thử lại hoặc tăng max_steps."
            )

        logger.log_event(
            "AGENT_END",
            {"steps": len(self.react_trace), "cycles": len(self.react_trace)},
        )
        if print_trace:
            print(self.format_react_trace(user_input))
        return final_answer

    def _log_react_cycle(self, cycle: Dict[str, Any]) -> None:
        """Structured log theo ReAct Mechanics cho báo cáo / logs/."""
        payload = {
            "cycle": cycle.get("cycle"),
            "thought": cycle.get("thought"),
            "action": cycle.get("action"),
            "observation": cycle.get("observation"),
            "final_answer": cycle.get("final_answer"),
        }
        logger.log_event("REACT_CYCLE", payload)

    def format_react_trace(self, user_input: Optional[str] = None) -> str:
        """In trace dạng Thought → Action → Observation (ReAct)."""
        lines = ["=" * 50, "ReAct Mechanics Trace", "=" * 50]
        if user_input:
            lines.append(f"User: {user_input}\n")

        for cycle in self.react_trace:
            n = cycle["cycle"]
            lines.append(f"--- Cycle {n} ---")
            thought = cycle.get("thought")
            if thought:
                lines.append(f"Thought: {thought}")
            elif cycle.get("action"):
                lines.append(
                    "Thought: (LLM không ghi Thought — chỉ có Action trong bước này)"
                )
            if cycle.get("action"):
                lines.append(f"Action: {cycle['action']}")
                lines.append(f"Observation: {cycle['observation']}")
            if cycle.get("final_answer"):
                lines.append(f"Final Answer: {cycle['final_answer']}")
            if cycle.get("note"):
                lines.append(f"Note: {cycle['note']}")
            lines.append("")

        lines.append("=" * 50)
        return "\n".join(lines)

    def _extract_thought(self, text: str) -> Optional[str]:
        match = re.search(
            r"Thought:\s*(.+?)(?=\n\s*Action:|\n\s*Final Answer:|$)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()
        return None

    def _extract_final_answer(self, text: str) -> Optional[str]:
        match = re.search(
            r"Final Answer:\s*(.+)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()
        return None

    def _extract_action(self, text: str) -> Optional[Tuple[str, str]]:
        match = re.search(
            r"Action:\s*(\w+)\s*\((.*)\)\s*$",
            text,
            re.IGNORECASE | re.MULTILINE | re.DOTALL,
        )
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return None

    def _execute_tool(self, tool_name: str, args: str) -> str:
        return execute_tool(tool_name, args)
