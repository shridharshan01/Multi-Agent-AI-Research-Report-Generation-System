"""
LLM factory. Reads LLM_PROVIDER (and the matching API key / base URL) from
the environment and returns a configured crewai.LLM instance.

Supported providers: gemini, groq, ollama
"""

import os

from crewai import LLM


def get_llm() -> LLM:
    provider = os.getenv("LLM_PROVIDER", "groq").lower().strip()

    if provider == "gemini":
        model = os.getenv("MODEL_NAME") or "gemini/gemini-2.0-flash"
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "LLM_PROVIDER=gemini but GEMINI_API_KEY is not set. Add it to your .env file."
            )
        return LLM(model=model, api_key=api_key, temperature=0.4)

    if provider == "groq":
        model = os.getenv("MODEL_NAME") or "groq/llama-3.3-70b-versatile"
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "LLM_PROVIDER=groq but GROQ_API_KEY is not set. Add it to your .env file."
            )
        return LLM(model=model, api_key=api_key, temperature=0.4)

    if provider == "ollama":
        model = os.getenv("MODEL_NAME") or "ollama/nemotron-3-super:cloud"
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        # Ollama doesn't need an API key, just a reachable local server.
        return LLM(model=model, base_url=base_url, temperature=0.4)

    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider}'. Use 'gemini', 'groq', or 'ollama'."
    )
