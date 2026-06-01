import os
from typing import Optional

from src.config import load_project_env
from src.core.llm_provider import LLMProvider
from src.core.llm_runtime import get_effective_config


def get_llm_provider(
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMProvider:
    """Load only the selected provider (avoids importing llama_cpp when using cloud APIs)."""
    load_project_env()
    if provider is None and model is None:
        provider, model = get_effective_config()
    else:
        provider = (provider or os.getenv("DEFAULT_PROVIDER", "openai")).lower()
        model = model or os.getenv("DEFAULT_MODEL", "gpt-4o")

    if provider == "openai":
        from src.core.openai_provider import OpenAIProvider

        return OpenAIProvider(
            model_name=model,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    if provider == "google":
        from src.core.gemini_provider import GeminiProvider

        return GeminiProvider(
            model_name=model,
            api_key=os.getenv("GEMINI_API_KEY"),
        )
    if provider == "local":
        from src.core.local_provider import LocalProvider

        return LocalProvider(
            model_path=os.getenv(
                "LOCAL_MODEL_PATH",
                "./models/Phi-3-mini-4k-instruct-q4.gguf",
            )
        )
    raise ValueError(f"Unknown provider: {provider}. Use openai | google | local")
