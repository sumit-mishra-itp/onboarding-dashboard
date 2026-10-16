"""AI drafting. `provider` is the vendor chosen by AI_PROVIDER at startup (fails fast on a bad value)."""
from .planner import draft_tasks
from .providers import PROVIDERS, AIError, Anthropic, Gemini, Groq, OpenAICompatible, Provider, create_provider

provider = create_provider()
ENABLED = bool(provider.key)

__all__ = ["AIError", "Anthropic", "ENABLED", "Gemini", "Groq", "OpenAICompatible", "PROVIDERS", "Provider",
           "create_provider", "draft_tasks", "provider"]
