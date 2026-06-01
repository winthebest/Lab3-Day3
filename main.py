"""
Chạy Travel ReAct Agent hoặc so sánh với chatbot baseline.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import load_project_env
from chatbot import run_chatbot
from src.agent.agent import ReActAgent
from src.core.provider_factory import get_llm_provider
from src.tools.failure_simulation import SIMULATION_OPTIONS, failure_simulation


DEFAULT_QUERY = (
    "Tôi ở HCM, muốn đi Đà Nẵng 3 ngày 2 đêm, 2 người, "
    "khởi hành 15/07/2026, dùng mã SUMMER. Tổng chi phí ước tính?"
)


def run_agent(
    query: str,
    max_steps: int = 8,
    show_react: bool = True,
    simulate: str = "none",
) -> str:
    load_project_env()
    llm = get_llm_provider()
    agent = ReActAgent(llm=llm, max_steps=max_steps)
    with failure_simulation(simulate):
        return agent.run(query, print_trace=show_react)


def main():
    parser = argparse.ArgumentParser(description="Lab 3 — Travel Concierge")
    parser.add_argument(
        "--mode",
        "-m",
        choices=["agent", "chatbot", "compare"],
        default="agent",
    )
    parser.add_argument("--query", "-q", default=DEFAULT_QUERY)
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument(
        "--simulate",
        choices=list(SIMULATION_OPTIONS.keys()),
        default="none",
        help="Force a tool failure scenario for ReAct agent runs.",
    )
    parser.add_argument(
        "--no-react-trace",
        action="store_true",
        help="Ẩn trace Thought/Action/Observation trên console",
    )
    args = parser.parse_args()
    show_react = not args.no_react_trace

    if args.mode == "chatbot":
        print("--- Mode: Chatbot ---\n")
        print(run_chatbot(args.query))
    elif args.mode == "agent":
        print("--- Mode: ReAct Travel Agent ---\n")
        answer = run_agent(args.query, args.max_steps, show_react, args.simulate)
        if show_react:
            print("\n--- Kết quả ---\n")
        print(answer)
    else:
        print("=== CHATBOT ===\n")
        print(run_chatbot(args.query))
        print("\n=== REACT AGENT ===\n")
        answer = run_agent(args.query, args.max_steps, show_react, args.simulate)
        if show_react:
            print("\n--- Kết quả ---\n")
        print(answer)


if __name__ == "__main__":
    main()
