import os
from typing import Literal

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from src.config import get_settings

try:
    from langchain_ollama import ChatOllama
except ImportError:  # pragma: no cover - optional dependency during bootstrap
    ChatOllama = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:  # pragma: no cover - optional dependency during bootstrap
    ChatAnthropic = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:  # pragma: no cover - optional dependency during bootstrap
    ChatGoogleGenerativeAI = None

try:
    from langchain_mistralai import ChatMistralAI
except ImportError:  # pragma: no cover - optional dependency during bootstrap
    ChatMistralAI = None


LLMTask = Literal["cv_parser", "job_scraper", "matcher", "document_generator"]

_PROVIDER_ALIASES = {
    "gpt": "openai",
}


def normalize_provider_name(provider: str) -> str:
    normalized = provider.strip().lower()
    return _PROVIDER_ALIASES.get(normalized, normalized)


def resolve_llm_provider(task: LLMTask | None = None) -> str:
    settings = get_settings().llm
    provider = settings.provider
    if task is not None and settings.routing.mode == "by_task":
        task_provider = getattr(settings.routing.task_providers, task, None)
        if task_provider:
            provider = task_provider
    return normalize_provider_name(provider)


def get_llm(temperature: float = 0.0, *, task: LLMTask | None = None):
    """
    Returns the configured LLM.

    Provider selection order:
    1. Configured routing for the current task when llm.routing.mode=by_task
    2. APPLYAI_LLM_PROVIDER / llm.provider
    3. Defaults to local Ollama for testing

    Supported providers:
    - ollama
    - groq
    - openai
    - anthropic
    - gemini
    - mistral

    GPU / CUDA notes:
    - CUDA forcing only applies to the local Ollama provider.
    - Set APPLYAI_FORCE_CUDA=1 to require GPU usage for Ollama requests only.
    - Optionally set OLLAMA_NUM_GPU to the number of GPUs to use.
    """

    settings = get_settings().llm
    provider = resolve_llm_provider(task)
    force_cuda = settings.force_cuda

    if force_cuda and provider != "ollama":
        raise RuntimeError(
            "APPLYAI_FORCE_CUDA=1 requires APPLYAI_LLM_PROVIDER=ollama. "
            "Remote providers like groq/openai/anthropic/gemini/mistral manage GPU execution on their side."
        )

    if provider == "ollama":
        if ChatOllama is None:
            raise RuntimeError(
                "Local LLM provider 'ollama' requires the package 'langchain-ollama'. "
                "Install dependencies from requirements.txt."
            )

        num_gpu = settings.ollama.num_gpu
        if force_cuda and num_gpu is None:
            num_gpu = 1

        ollama_kwargs = {
            "model": settings.ollama.model,
            "base_url": settings.ollama.base_url,
            "temperature": temperature,
            "num_ctx": settings.ollama.num_ctx,
        }
        if num_gpu is not None:
            ollama_kwargs["num_gpu"] = num_gpu

        return ChatOllama(
            **ollama_kwargs,
        )

    if provider == "groq":
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise RuntimeError("APPLYAI_LLM_PROVIDER=groq but GROQ_API_KEY is not set.")

        return ChatGroq(
            model=settings.groq.model,
            api_key=groq_key,
            temperature=temperature,
        )

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("APPLYAI_LLM_PROVIDER=openai but OPENAI_API_KEY is not set.")

        return ChatOpenAI(
            model=settings.openai.model,
            temperature=temperature,
        )

    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("APPLYAI_LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set.")
        if ChatAnthropic is None:
            raise RuntimeError(
                "Provider 'anthropic' requires the package 'langchain-anthropic'. "
                "Install dependencies from requirements.txt."
            )

        return ChatAnthropic(
            model=settings.anthropic.model,
            api_key=api_key,
            temperature=temperature,
        )

    if provider == "gemini":
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("APPLYAI_LLM_PROVIDER=gemini but GOOGLE_API_KEY or GEMINI_API_KEY is not set.")
        if ChatGoogleGenerativeAI is None:
            raise RuntimeError(
                "Provider 'gemini' requires the package 'langchain-google-genai'. "
                "Install dependencies from requirements.txt."
            )

        return ChatGoogleGenerativeAI(
            model=settings.gemini.model,
            google_api_key=api_key,
            temperature=temperature,
        )

    if provider == "mistral":
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise RuntimeError("APPLYAI_LLM_PROVIDER=mistral but MISTRAL_API_KEY is not set.")
        if ChatMistralAI is None:
            raise RuntimeError(
                "Provider 'mistral' requires the package 'langchain-mistralai'. "
                "Install dependencies from requirements.txt."
            )

        return ChatMistralAI(
            model=settings.mistral.model,
            api_key=api_key,
            temperature=temperature,
        )

    raise RuntimeError(
        f"Unsupported LLM provider '{provider}'. "
        "Use one of: ollama, groq, openai, anthropic, gemini, mistral."
    )
