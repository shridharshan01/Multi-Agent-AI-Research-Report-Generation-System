"""
Workaround for a known upstream CrewAI bug (crewAI 1.14.4+ as of mid-2026):
https://github.com/crewAIInc/crewAI/issues/5886

CrewAI added a provider-agnostic prompt-caching helper, mark_cache_breakpoint(),
that stamps a "cache_breakpoint": true field onto messages. Only the Anthropic
adapter knows to read and strip that field -- every other provider (Groq,
plain OpenAI-compatible endpoints, and apparently Gemini/Ollama too, since
none of those adapters reference the flag at all) sends it straight through
as a raw JSON field, and strict providers like Groq reject the request:

    litellm.BadRequestError: GroqException - {"error": {"message":
    "'messages.0': for 'role:system' the following must be satisfied
    [('messages.0': property 'cache_breakpoint' is unsupported)]", ...}}

Fix: turn mark_cache_breakpoint() into a no-op so messages go out clean.
This only disables an optimization (prompt-cache reuse) for providers that
support it (Anthropic) -- it does not affect correctness, and this project
doesn't use the Anthropic provider by default anyway.

Each call site inside crewai does a *local* `from crewai.llms.cache import
mark_cache_breakpoint` right before calling it, so patching the attribute on
the `crewai.llms.cache` module (rather than something already bound to a
name elsewhere) is enough -- verified against crewai 1.14.7.

Safe no-op if a future crewai release removes/renames this internal helper:
wrapped in try/except so it never breaks startup.
"""

import logging

logger = logging.getLogger(__name__)


def apply_compat_patches() -> None:
    try:
        import crewai.llms.cache as _cache_module
    except ImportError:
        return

    if hasattr(_cache_module, "mark_cache_breakpoint"):
        _cache_module.mark_cache_breakpoint = lambda message: message
        logger.debug(
            "Applied workaround for crewAI issue #5886 "
            "(cache_breakpoint sent to non-Anthropic providers)."
        )
