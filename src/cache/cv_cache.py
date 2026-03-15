from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timedelta
from threading import Lock
from typing import Literal

from pydantic import BaseModel, Field

from src.analyzer.cv_parser import CVData
from src.config import get_settings
from src.utils.normalization import clean_text, extract_skills_from_text, merge_skill_sources


class CVMatchChunk(BaseModel):
    text: str
    source: Literal["skills", "experience", "education"]
    skills: list[str] = Field(default_factory=list)


def _build_chunk(
    text: str,
    source: Literal["skills", "experience", "education"],
    *,
    seed_skills: list[str] | None = None,
) -> CVMatchChunk | None:
    normalized_text = clean_text(text)
    if not normalized_text:
        return None

    chunk_skills = merge_skill_sources(seed_skills or [], extract_skills_from_text(normalized_text))
    return CVMatchChunk(text=normalized_text, source=source, skills=chunk_skills)


def build_match_chunks(cv_data: CVData) -> list[CVMatchChunk]:
    chunks: list[CVMatchChunk] = []

    if cv_data.skills:
        skills_chunk = _build_chunk(
            f"Skills: {', '.join(cv_data.skills)}",
            "skills",
            seed_skills=cv_data.skills,
        )
        if skills_chunk is not None:
            chunks.append(skills_chunk)

    for value in cv_data.experience:
        experience_chunk = _build_chunk(value, "experience")
        if experience_chunk is not None:
            chunks.append(experience_chunk)

    for value in cv_data.education:
        education_chunk = _build_chunk(value, "education")
        if education_chunk is not None:
            chunks.append(education_chunk)

    deduped_chunks: list[CVMatchChunk] = []
    seen_chunks: set[str] = set()
    for chunk in chunks:
        normalized_chunk = clean_text(chunk.text)
        if not normalized_chunk or normalized_chunk in seen_chunks:
            continue
        seen_chunks.add(normalized_chunk)
        deduped_chunks.append(chunk)

    return deduped_chunks


class CachedCVProfile(BaseModel):
    cache_id: str
    filename: str
    uploaded_at: datetime
    last_accessed_at: datetime
    cv_data: CVData
    file_bytes: bytes = Field(default=b"", exclude=True, repr=False)
    match_chunks: list[CVMatchChunk] = Field(default_factory=list)

    def touch(self) -> "CachedCVProfile":
        return self.model_copy(update={"last_accessed_at": datetime.utcnow()})


class CVCacheStore:
    def __init__(self, max_entries: int | None = None, ttl_hours: int | None = None):
        cache_settings = get_settings().cache.cv
        self.max_entries = max_entries if max_entries is not None else cache_settings.max_entries
        resolved_ttl_hours = ttl_hours if ttl_hours is not None else cache_settings.ttl_hours
        self.ttl = timedelta(hours=resolved_ttl_hours)
        self._entries: OrderedDict[str, CachedCVProfile] = OrderedDict()
        self._lock = Lock()

    def get(self, cache_id: str) -> CachedCVProfile | None:
        with self._lock:
            self._purge_locked()
            entry = self._entries.get(cache_id)
            if entry is None:
                return None

            touched_entry = entry.touch()
            self._entries[cache_id] = touched_entry
            self._entries.move_to_end(cache_id)
            return touched_entry

    def store(self, cache_id: str, filename: str, cv_data: CVData, file_bytes: bytes) -> CachedCVProfile:
        with self._lock:
            self._purge_locked()

            now = datetime.utcnow()
            entry = CachedCVProfile(
                cache_id=cache_id,
                filename=filename,
                uploaded_at=now,
                last_accessed_at=now,
                cv_data=cv_data,
                file_bytes=file_bytes,
                match_chunks=build_match_chunks(cv_data),
            )
            self._entries[cache_id] = entry
            self._entries.move_to_end(cache_id)
            self._purge_locked()
            return entry

    def _purge_locked(self) -> None:
        now = datetime.utcnow()
        expired_ids = [
            cache_id
            for cache_id, entry in self._entries.items()
            if now - entry.last_accessed_at > self.ttl
        ]
        for cache_id in expired_ids:
            self._entries.pop(cache_id, None)

        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)
