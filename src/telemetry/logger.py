import logging
import json
import os
from datetime import datetime
from typing import Any, Dict, List

class IndustryLogger:
    """
    Structured logger that simulates industry practices.
    Logs to both console and a file in JSON format.
    """
    def __init__(self, name: str = "AI-Lab-Agent", log_dir: str = "logs"):
        self.logger = logging.getLogger(name)
        self._session_events: List[Dict[str, Any]] = []
        if self.logger.handlers:
            return
        self.logger.setLevel(logging.INFO)

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # File only — JSON trace cho báo cáo / RCA (không spam terminal)
        log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        self.logger.addHandler(file_handler)

        if os.getenv("LOG_TO_CONSOLE", "").lower() in ("1", "true", "yes"):
            self.logger.addHandler(logging.StreamHandler())

    def clear_session(self) -> None:
        """Reset in-memory log buffer (e.g. before a new Streamlit run)."""
        self._session_events.clear()

    def get_session_events(self) -> List[Dict[str, Any]]:
        return list(self._session_events)

    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Logs an event with a timestamp and type."""
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event_type,
            "data": data
        }
        self._session_events.append(payload)
        self.logger.info(json.dumps(payload, ensure_ascii=False))

    def info(self, msg: str):
        self.logger.info(msg)

    def error(self, msg: str, exc_info=True):
        self.logger.error(msg, exc_info=exc_info)

# Global logger instance
logger = IndustryLogger()
