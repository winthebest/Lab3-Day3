import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import load_project_env
from src.core.provider_factory import get_llm_provider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker

TRAVEL_CHATBOT_SYSTEM = """You are a friendly Vietnam travel assistant.
Answer in Vietnamese. You do NOT have access to live prices or booking APIs.
If asked for exact total trip cost (flights + hotel + promo), give a rough estimate
and say you cannot verify real-time fares."""


def run_chatbot(query: str) -> str:
    load_project_env()
    llm = get_llm_provider()
    logger.log_event("CHATBOT_START", {"input": query, "model": llm.model_name})

    result = llm.generate(query, system_prompt=TRAVEL_CHATBOT_SYSTEM)
    tracker.track_request(
        result.get("provider", "unknown"),
        llm.model_name,
        result.get("usage", {}),
        result.get("latency_ms", 0),
    )
    answer = result.get("content", "")
    logger.log_event("CHATBOT_END", {"latency_ms": result.get("latency_ms")})
    return answer


def main():
    parser = argparse.ArgumentParser(description="Travel chatbot baseline")
    parser.add_argument(
        "--query",
        "-q",
        default=(
            "Tôi ở HCM, muốn đi Đà Nẵng 3 ngày 2 đêm, 2 người, "
            "khởi hành 15/07/2026, dùng mã SUMMER. Tổng chi phí ước tính?"
        ),
    )
    args = parser.parse_args()
    print("--- Travel Chatbot (no tools) ---\n")
    print(run_chatbot(args.query))


if __name__ == "__main__":
    main()
