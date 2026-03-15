import hashlib
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from src.agent.llm_utils import resolve_llm_provider
from src.analyzer.cv_parser import CVData, CVParser
from src.cache.cv_cache import CVCacheStore, CVMatchChunk, CachedCVProfile
from src.config import get_settings
from src.generator.document_generator import DocumentGenerator
from src.matcher.matching_engine import MatchingEngine
from src.scraper.job_scraper import JobScraper
from src.utils.document_text_extractor import (
    describe_supported_document_formats,
    extract_text_from_bytes,
    is_supported_document_filename,
    resolve_upload_filename,
)
from src.utils.logging_utils import configure_logging

load_dotenv()
configure_logging()
SETTINGS = get_settings()

app = FastAPI(
    title=SETTINGS.app.title,
    description=SETTINGS.app.description,
    version=SETTINGS.app.version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=SETTINGS.api.cors.allow_origins,
    allow_credentials=SETTINGS.api.cors.allow_credentials,
    allow_methods=SETTINGS.api.cors.allow_methods,
    allow_headers=SETTINGS.api.cors.allow_headers,
)

CV_CACHE = CVCacheStore()


def ensure_supported_document_upload(upload: UploadFile, *, kind_label: str) -> str:
    resolved_filename = resolve_upload_filename(
        upload.filename,
        upload.content_type,
        default_stem=kind_label.lower().replace(" ", "_"),
    )
    if not is_supported_document_filename(resolved_filename):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported {kind_label} format. Accepted formats: "
                f"{describe_supported_document_formats()}"
            ),
        )
    return resolved_filename


async def read_uploaded_cv_bytes(cv_file: UploadFile) -> tuple[str, bytes]:
    resolved_filename = ensure_supported_document_upload(cv_file, kind_label="CV")
    file_bytes = await cv_file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded CV file is empty.")

    return resolved_filename, file_bytes


def parse_cv_bytes(filename: str, file_bytes: bytes) -> CVData:
    parser = CVParser()
    suffix = Path(filename).suffix.lower() or ".txt"
    handle, temp_path = tempfile.mkstemp(suffix=suffix)
    try:
        os.close(handle)
        Path(temp_path).write_bytes(file_bytes)
        return parser.parse_cv(temp_path, use_llm=SETTINGS.cv_parser.use_llm)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def get_or_create_cached_cv_profile(filename: str, file_bytes: bytes) -> tuple[CachedCVProfile, bool]:
    cache_id = hashlib.sha256(file_bytes).hexdigest()
    cached_profile = CV_CACHE.get(cache_id)
    if cached_profile is not None:
        return cached_profile, True

    cv_data = parse_cv_bytes(filename, file_bytes)
    profile = CV_CACHE.store(cache_id, filename, cv_data, file_bytes)
    return profile, False


async def resolve_cv_profile(
    cv_cache_id: str = "",
    cv_file: UploadFile | None = None,
) -> tuple[CachedCVProfile, bool]:
    normalized_cache_id = cv_cache_id.strip()
    if normalized_cache_id:
        cached_profile = CV_CACHE.get(normalized_cache_id)
        if cached_profile is None:
            raise HTTPException(
                status_code=404,
                detail="The cached CV could not be found or has expired. Upload the document again.",
            )
        return cached_profile, True

    if cv_file is None:
        raise HTTPException(status_code=400, detail="A cached CV or an uploaded CV document is required.")

    filename, file_bytes = await read_uploaded_cv_bytes(cv_file)
    return await run_in_threadpool(get_or_create_cached_cv_profile, filename, file_bytes)


async def resolve_job_offer_text(
    *,
    job_offer_text: str = "",
    job_offer_file: UploadFile | None = None,
) -> str:
    text_value = job_offer_text.strip()
    if text_value:
        return text_value

    if job_offer_file is None:
        raise HTTPException(
            status_code=400,
            detail="Provide either job offer text or a job offer file.",
        )

    filename = ensure_supported_document_upload(job_offer_file, kind_label="job offer file")
    file_bytes = await job_offer_file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded job offer file is empty.")

    try:
        return await run_in_threadpool(extract_text_from_bytes, file_bytes, filename)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def build_cv_search_keywords(job_title: str | None, skills: list[str] | None) -> str:
    title = (job_title or "").strip()
    if title:
        return title

    if skills:
        return (skills[0] or "").strip()

    return ""


def run_match_pipeline(
    profile: CachedCVProfile,
    job_offer_text: str,
    response_language: str = "en",
) -> dict[str, object]:
    text_match_settings = SETTINGS.pipeline.text_match
    job_scraper = JobScraper()
    matcher = MatchingEngine()

    job_data = job_scraper.parse_job_text(
        job_offer_text,
        use_llm=False,
        allow_llm_refinement=False,
    )
    match = matcher.calculate_match(
        profile.cv_data,
        job_data,
        cv_chunks=profile.match_chunks,
        use_llm_reasoning=text_match_settings.matcher_use_llm_reasoning,
        preferred_language=response_language,
    )

    return {
        "cv_skills": profile.cv_data.skills,
        "job_title": job_data.title,
        "job_company": job_data.company,
        "job_location": job_data.location,
        "job_required_skills": job_data.skills_required,
        "match_score": match.score,
        "missing_skills": match.missing_skills,
        "reasoning": match.reasoning,
    }


def run_cover_letter_pipeline(profile: CachedCVProfile, job_offer_text: str) -> dict[str, object]:
    text_match_settings = SETTINGS.pipeline.text_match
    job_scraper = JobScraper()
    generator = DocumentGenerator()

    job_data = job_scraper.parse_job_text(
        job_offer_text,
        use_llm=text_match_settings.job_scraper_use_llm,
        allow_llm_refinement=text_match_settings.allow_llm_refinement,
    )
    target_language = generator.detect_language(job_offer_text)
    optimized_summary = generator.generate_optimized_summary(
        profile.cv_data,
        job_data,
        target_language=target_language,
    )
    cover_letter = generator.generate_cover_letter(
        profile.cv_data,
        job_data,
        optimized_summary=optimized_summary,
        use_llm_cover_letter=text_match_settings.document_use_llm_cover_letter,
        target_language=target_language,
    )

    return {
        "job_title": job_data.title,
        "job_company": job_data.company,
        "cover_letter": cover_letter,
    }


@app.get("/")
def read_root():
    return {
        "message": "ApplyAI API",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
        "health_url": "/api/health",
    }


@app.get("/api")
def read_api_root():
    return {"message": "Welcome to ApplyAI API"}


@app.get("/health")
@app.get("/api/health")
def read_health():
    return {
        "status": "ok",
        "service": SETTINGS.app.title,
        "version": SETTINGS.app.version,
        "llm_provider": SETTINGS.llm.provider,
        "llm_routing_mode": SETTINGS.llm.routing.mode,
        "llm_task_providers": {
            "cv_parser": resolve_llm_provider("cv_parser"),
            "job_scraper": resolve_llm_provider("job_scraper"),
            "matcher": resolve_llm_provider("matcher"),
            "document_generator": resolve_llm_provider("document_generator"),
        },
    }


@app.post("/api/cv/upload")
async def upload_cv(cv_file: UploadFile = File(...)):
    try:
        profile, cached = await resolve_cv_profile(cv_file=cv_file)
        return {
            "status": "success",
            "data": {
                "cv_cache_id": profile.cache_id,
                "filename": profile.filename,
                "cached": cached,
                "skill_count": len(profile.cv_data.skills),
                "experience_count": len(profile.cv_data.experience),
                "education_count": len(profile.cv_data.education),
                "chunk_count": len(profile.match_chunks),
                "location": profile.cv_data.location,
                "job_title": profile.cv_data.job_title,
                "top_skills": profile.cv_data.skills[:10] if profile.cv_data.skills else [],
                "suggested_keywords": build_cv_search_keywords(profile.cv_data.job_title, profile.cv_data.skills),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/match")
async def match_cv_with_text_offer(
    cv_file: UploadFile | None = File(None),
    cv_cache_id: str = Form(""),
    job_offer_text: str = Form(""),
    job_offer_file: UploadFile | None = File(None),
    response_language: str = Form("en"),
):
    try:
        profile, _ = await resolve_cv_profile(cv_cache_id=cv_cache_id, cv_file=cv_file)
        resolved_offer_text = await resolve_job_offer_text(
            job_offer_text=job_offer_text,
            job_offer_file=job_offer_file,
        )
        data = await run_in_threadpool(run_match_pipeline, profile, resolved_offer_text, response_language)
        return {
            "status": "success",
            "data": data,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/match/cover-letter")
async def generate_cover_letter_for_text_offer(
    cv_file: UploadFile | None = File(None),
    cv_cache_id: str = Form(""),
    job_offer_text: str = Form(""),
    job_offer_file: UploadFile | None = File(None),
):
    try:
        profile, _ = await resolve_cv_profile(cv_cache_id=cv_cache_id, cv_file=cv_file)
        resolved_offer_text = await resolve_job_offer_text(
            job_offer_text=job_offer_text,
            job_offer_file=job_offer_file,
        )
        data = await run_in_threadpool(run_cover_letter_pipeline, profile, resolved_offer_text)
        return {
            "status": "success",
            "data": data,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=SETTINGS.server.host,
        port=SETTINGS.server.port,
        reload=SETTINGS.server.reload,
    )
