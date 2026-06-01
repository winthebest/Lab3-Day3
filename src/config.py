from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_project_env() -> None:
    """Load .env from project root; override stale OS-level API keys."""
    load_dotenv(PROJECT_ROOT / ".env", override=True)
