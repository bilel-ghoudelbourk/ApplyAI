from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.json"


class AppSettings(BaseModel):
    title: str
    description: str
    version: str
    default_cv_path: str


class ServerSettings(BaseModel):
    host: str
    port: int
    reload: bool


class LoggingSettings(BaseModel):
    level: str = "INFO"


class CorsSettings(BaseModel):
    allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])
    allow_credentials: bool = False
    allow_methods: list[str] = Field(default_factory=lambda: ["GET", "POST"])
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])


class ApiSearchDefaults(BaseModel):
    language: str = "fr"
    posted_within: str = "7d"
    limit: int = 20


class ApiSettings(BaseModel):
    cors: CorsSettings
    search_defaults: ApiSearchDefaults


class CVCacheSettings(BaseModel):
    max_entries: int = 32
    ttl_hours: int = 12


class CacheSettings(BaseModel):
    cv: CVCacheSettings


class DocumentIngestionSettings(BaseModel):
    enable_ocr: bool = True
    pdf_extension: str = ".pdf"
    word_extensions: list[str] = Field(default_factory=lambda: [".docx"])
    text_extensions: list[str] = Field(default_factory=lambda: [".txt", ".md", ".rtf"])
    image_extensions: list[str] = Field(
        default_factory=lambda: [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"]
    )
    pdf_text_min_chars_before_ocr: int = 120
    pdf_ocr_max_pages: int = 10
    pdf_ocr_zoom: float = 2.0
    ocr_max_image_side: int = 2200
    ocr_binarize_threshold: int = 180


class LLMTemperatureSettings(BaseModel):
    cv_parser: float = 0.0
    job_scraper: float = 0.0
    matcher: float = 0.0
    document_generator: float = 0.7


class OllamaSettings(BaseModel):
    model: str = "llama3:8b"
    base_url: str = "http://127.0.0.1:11434"
    num_ctx: int = 8192
    num_gpu: int | None = None


class GroqSettings(BaseModel):
    model: str = "llama-3.3-70b-versatile"


class OpenAISettings(BaseModel):
    model: str = "gpt-4o-mini"


class AnthropicSettings(BaseModel):
    model: str = "claude-3-5-haiku-latest"


class GeminiSettings(BaseModel):
    model: str = "gemini-2.0-flash"


class MistralSettings(BaseModel):
    model: str = "mistral-small-latest"


class LLMTaskProviders(BaseModel):
    cv_parser: str | None = None
    job_scraper: str | None = None
    matcher: str | None = None
    document_generator: str | None = None


class LLMRoutingSettings(BaseModel):
    mode: Literal["single", "by_task"] = "single"
    task_providers: LLMTaskProviders = Field(default_factory=LLMTaskProviders)


class LLMSettings(BaseModel):
    provider: Literal["ollama", "groq", "openai", "gpt", "anthropic", "gemini", "mistral"] = "ollama"
    force_cuda: bool = False
    routing: LLMRoutingSettings = Field(default_factory=LLMRoutingSettings)
    temperatures: LLMTemperatureSettings
    ollama: OllamaSettings
    groq: GroqSettings
    openai: OpenAISettings
    anthropic: AnthropicSettings
    gemini: GeminiSettings
    mistral: MistralSettings


class CVParserSettings(BaseModel):
    model_name: str = "gpt-4o-mini"
    use_llm: bool = False
    max_experience_entries: int = 18
    max_education_entries: int = 10


class JobScraperSettings(BaseModel):
    model_name: str = "gpt-4o-mini"
    default_use_llm: bool = False
    default_allow_llm_refinement: bool = False
    llm_max_input_chars: int = 15_000
    fallback_description_chars: int = 500
    heuristic_description_max_lines: int = 5
    title_sample_lines: int = 15
    title_scan_lines: int = 8
    company_sample_lines: int = 25
    company_scan_lines: int = 12
    location_sample_lines: int = 40
    location_scan_lines: int = 15
    title_max_length: int = 90
    company_max_length: int = 70
    max_clean_value_length: int = 110
    sentence_max_words: int = 8
    min_skill_count_for_no_refinement: int = 3
    noisy_bullet_count_threshold: int = 4
    bad_skill_max_length: int = 48
    bad_skill_max_words: int = 5


class MatchingScoreSettings(BaseModel):
    empty_job_score: int = 50
    coverage_weight: float = 0.84
    breadth_bonus_multiplier: float = 1.5
    breadth_bonus_cap: int = 8
    experience_bonus_per_hit: int = 2
    experience_bonus_cap: int = 10
    education_bonus_per_hit: int = 1
    education_bonus_cap: int = 4


class MatchingReasoningSettings(BaseModel):
    default_use_llm: bool = False
    matched_skill_limit: int = 6
    missing_skill_limit: int = 6
    experience_evidence_limit: int = 5


class MatchingSettings(BaseModel):
    model_name: str = "gpt-4o-mini"
    score: MatchingScoreSettings
    reasoning: MatchingReasoningSettings


class DocumentGeneratorSettings(BaseModel):
    model_name: str = "gpt-4o"
    default_use_llm_cover_letter: bool = True
    summary_matched_skill_limit: int = 6
    summary_missing_skill_limit: int = 4
    summary_experience_limit: int = 2
    summary_education_limit: int = 1
    fallback_cover_letter_skill_limit: int = 4
    fallback_cover_letter_experience_limit: int = 1
    fallback_cover_letter_education_limit: int = 1
    incomplete_min_length: int = 180
    incomplete_min_line_breaks: int = 2


class TextMatchPipelineSettings(BaseModel):
    job_scraper_use_llm: bool = False
    allow_llm_refinement: bool = True
    matcher_use_llm_reasoning: bool = False
    document_use_llm_cover_letter: bool = True


class PipelineSettings(BaseModel):
    text_match: TextMatchPipelineSettings


class Settings(BaseModel):
    app: AppSettings
    server: ServerSettings
    logging: LoggingSettings
    api: ApiSettings
    cache: CacheSettings
    document_ingestion: DocumentIngestionSettings
    llm: LLMSettings
    cv_parser: CVParserSettings
    job_scraper: JobScraperSettings
    matching: MatchingSettings
    documents: DocumentGeneratorSettings
    pipeline: PipelineSettings


def resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _env_flag(name: str) -> bool | None:
    value = (os.getenv(name) or "").strip().lower()
    if not value:
        return None
    return value in {"1", "true", "yes", "on"}


def _env_int(name: str) -> int | None:
    value = (os.getenv(name) or "").strip()
    if not value:
        return None
    return int(value)


def _set_nested(payload: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    cursor = payload
    for key in path[:-1]:
        cursor = cursor.setdefault(key, {})
    cursor[path[-1]] = value


def _apply_env_override(payload: dict[str, Any], env_name: str, path: tuple[str, ...], caster=None) -> None:
    value = os.getenv(env_name)
    if value is None or value == "":
        return
    resolved_value = caster(value) if caster is not None else value
    _set_nested(payload, path, resolved_value)


def _load_raw_config() -> dict[str, Any]:
    configured_path = os.getenv("APPLYAI_CONFIG_PATH")
    config_path = resolve_project_path(configured_path) if configured_path else DEFAULT_CONFIG_PATH
    with config_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    _apply_env_override(payload, "APPLYAI_DEFAULT_CV_PATH", ("app", "default_cv_path"))
    _apply_env_override(payload, "APPLYAI_LOG_LEVEL", ("logging", "level"), lambda value: value.upper())
    _apply_env_override(payload, "APPLYAI_LLM_PROVIDER", ("llm", "provider"), lambda value: value.strip().lower())
    _apply_env_override(
        payload,
        "APPLYAI_LLM_ROUTING_MODE",
        ("llm", "routing", "mode"),
        lambda value: value.strip().lower(),
    )
    _apply_env_override(
        payload,
        "APPLYAI_CV_PARSER_PROVIDER",
        ("llm", "routing", "task_providers", "cv_parser"),
        lambda value: value.strip().lower(),
    )
    _apply_env_override(
        payload,
        "APPLYAI_JOB_SCRAPER_PROVIDER",
        ("llm", "routing", "task_providers", "job_scraper"),
        lambda value: value.strip().lower(),
    )
    _apply_env_override(
        payload,
        "APPLYAI_MATCHER_PROVIDER",
        ("llm", "routing", "task_providers", "matcher"),
        lambda value: value.strip().lower(),
    )
    _apply_env_override(
        payload,
        "APPLYAI_DOCUMENT_PROVIDER",
        ("llm", "routing", "task_providers", "document_generator"),
        lambda value: value.strip().lower(),
    )

    force_cuda = _env_flag("APPLYAI_FORCE_CUDA")
    if force_cuda is not None:
        _set_nested(payload, ("llm", "force_cuda"), force_cuda)

    _apply_env_override(payload, "OLLAMA_MODEL", ("llm", "ollama", "model"))
    _apply_env_override(payload, "OLLAMA_BASE_URL", ("llm", "ollama", "base_url"))
    _apply_env_override(payload, "OLLAMA_NUM_CTX", ("llm", "ollama", "num_ctx"), int)

    ollama_num_gpu = _env_int("OLLAMA_NUM_GPU")
    if ollama_num_gpu is not None:
        _set_nested(payload, ("llm", "ollama", "num_gpu"), ollama_num_gpu)

    _apply_env_override(payload, "GROQ_MODEL", ("llm", "groq", "model"))
    _apply_env_override(payload, "OPENAI_MODEL", ("llm", "openai", "model"))
    _apply_env_override(payload, "ANTHROPIC_MODEL", ("llm", "anthropic", "model"))
    _apply_env_override(payload, "GEMINI_MODEL", ("llm", "gemini", "model"))
    _apply_env_override(payload, "MISTRAL_MODEL", ("llm", "mistral", "model"))

    return payload


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.model_validate(_load_raw_config())
