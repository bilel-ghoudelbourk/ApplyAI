import os
import re
from typing import Optional

from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from src.agent.llm_utils import get_llm
from src.config import get_settings
from src.utils.document_text_extractor import extract_text_from_document
from src.utils.normalization import (
    clean_text,
    clean_text_list,
    extract_skills_from_text,
    merge_skill_sources,
    normalize_skill_key,
)


class CVData(BaseModel):
    skills: list[str] = Field(description="A comprehensive list of technical and soft skills extracted from the CV.")
    experience: list[str] = Field(description="A list of professional experience entries or job titles.")
    education: list[str] = Field(description="A list of educational degrees, schools, or certifications.")
    contact_info: Optional[str] = Field(description="Email or phone number, if present.")
    location: Optional[str] = Field(default=None, description="Inferred city or country of the candidate.")
    job_title: Optional[str] = Field(default=None, description="The primary job title or role on the CV.")


_SECTION_MARKERS = {
    "profile": {"profil", "profile"},
    "skills": {"competencestechniques", "competences", "technicalskills", "skills"},
    "experience": {
        "experiencesprofessionnelles",
        "experienceprofessionnelle",
        "professionalexperience",
        "experience",
    },
    "projects": {"projetsacademiques", "projets", "academicprojects", "projects"},
    "education": {"diplomesetformations", "formations", "education", "diplomes"},
    "soft_skills": {"softskills", "competencescomportementales"},
    "languages": {"langues", "languages"},
    "interests": {"centresdinteret", "interests"},
}

_DISPLAY_ACRONYMS = ("AI", "IA", "ML", "LLM", "NLP", "MLOps", "AWS", "GCP", "API")


def _normalize_section_marker(value: str) -> str:
    return normalize_skill_key(value).replace(" ", "")


class CVParser:
    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.settings = settings.cv_parser
        self.llm_settings = settings.llm
        self.model_name = model_name or self.settings.model_name
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            self._llm = get_llm(
                temperature=self.llm_settings.temperatures.cv_parser,
                task="cv_parser",
            )
        return self._llm

    def extract_text_from_document(self, document_path: str) -> str:
        if not os.path.exists(document_path):
            raise FileNotFoundError(f"Document file not found at {document_path}")
        return extract_text_from_document(document_path)

    def parse_cv(self, document_path: str, use_llm: bool | None = None) -> CVData:
        raw_text = self.extract_text_from_document(document_path)
        if not raw_text.strip():
            raise ValueError("No text could be extracted from the document.")

        heuristic_data = self._parse_with_heuristics(raw_text)
        should_use_llm = self.settings.use_llm if use_llm is None else use_llm
        if not should_use_llm:
            return heuristic_data

        llm_data = self._parse_with_llm(raw_text)

        if llm_data is None:
            return heuristic_data

        return CVData(
            skills=merge_skill_sources(heuristic_data.skills, llm_data.skills),
            experience=clean_text_list([*llm_data.experience, *heuristic_data.experience]),
            education=clean_text_list([*llm_data.education, *heuristic_data.education]),
            contact_info=heuristic_data.contact_info or clean_text(llm_data.contact_info),
            location=heuristic_data.location or (clean_text(llm_data.location) if getattr(llm_data, "location", None) else None),
            job_title=heuristic_data.job_title or (clean_text(llm_data.job_title) if getattr(llm_data, "job_title", None) else None),
        )

    def _parse_with_llm(self, raw_text: str) -> CVData | None:
        try:
            structured_llm = self._get_llm().with_structured_output(CVData)
            prompt = PromptTemplate.from_template(
                "You are an expert HR recruiter and data extraction engine.\n"
                "Analyze the following CV text and extract the required information into the specified structure.\n"
                "Be exhaustive on technologies, frameworks, cloud tools, data tooling, and programming languages.\n"
                "Do not merge related but distinct tools or platforms.\n"
                "Keep experience and education concise.\n\n"
                "CV Text:\n"
                "{cv_text}"
            )
            chain = prompt | structured_llm
            result: CVData = chain.invoke({"cv_text": raw_text})
            return CVData(
                skills=merge_skill_sources(result.skills),
                experience=clean_text_list(result.experience),
                education=clean_text_list(result.education),
                contact_info=clean_text(result.contact_info) if result.contact_info else None,
                location=clean_text(result.location) if result.location else None,
                job_title=clean_text(result.job_title) if result.job_title else None,
            )
        except Exception:
            return None

    def _parse_with_heuristics(self, raw_text: str) -> CVData:
        sections = self._extract_sections(raw_text)
        return CVData(
            skills=extract_skills_from_text(raw_text),
            experience=self._extract_experience_entries(sections),
            education=self._extract_education_entries(sections),
            contact_info=self._extract_contact_info(raw_text),
            location=self._extract_location(sections, raw_text),
            job_title=self._extract_job_title(sections),
        )

    def _extract_sections(self, raw_text: str) -> dict[str, list[str]]:
        sections: dict[str, list[str]] = {"header": []}
        current_section = "header"

        for raw_line in raw_text.splitlines():
            line = clean_text(raw_line)
            if not line:
                continue

            detected_section = self._detect_section(line)
            if detected_section is not None:
                current_section = detected_section
                sections.setdefault(current_section, [])
                continue

            sections.setdefault(current_section, []).append(line)

        return sections

    def _detect_section(self, line: str) -> str | None:
        compact = _normalize_section_marker(line)
        for section, markers in _SECTION_MARKERS.items():
            if compact in markers:
                return section
        return None

    def _extract_experience_entries(self, sections: dict[str, list[str]]) -> list[str]:
        entries: list[str] = []
        for section_name in ("experience", "projects"):
            for line in sections.get(section_name, []):
                compact = _normalize_section_marker(line)
                if compact.startswith("technologiesutilisees"):
                    continue
                if line.count(",") >= 3 and len(extract_skills_from_text(line)) >= 3:
                    continue
                if line.startswith("-") and len(line) < 25:
                    continue
                entries.append(self._prettify_cv_entry(line))
        return clean_text_list(entries[: self.settings.max_experience_entries])

    def _extract_education_entries(self, sections: dict[str, list[str]]) -> list[str]:
        entries: list[str] = []
        for line in sections.get("education", []):
            compact = _normalize_section_marker(line)
            if compact.startswith("technologiesutilisees"):
                continue
            entries.append(self._prettify_cv_entry(line))
        return clean_text_list(entries[: self.settings.max_education_entries])

    def _prettify_cv_entry(self, value: str) -> str:
        text = clean_text(value)
        if not text:
            return ""

        text = text.replace("—", " - ").replace("–", " - ")
        text = re.sub(r"\s*\|\s*", " | ", text)
        text = re.sub(r"\s*,\s*", ", ", text)
        text = re.sub(r"\s*-\s*", " - ", text)
        text = re.sub(r"(?<=[A-Za-zÀ-ÿ])(?=\d)", " ", text)
        text = re.sub(r"(?<=\d)(?=[A-Za-zÀ-ÿ])", " ", text)
        text = re.sub(r"(?<=[a-zà-ÿ])(?=[A-ZÀ-Ý])", " ", text)

        for acronym in _DISPLAY_ACRONYMS:
            text = re.sub(rf"({re.escape(acronym)})(?=[a-zà-ÿ])", r"\1 ", text)

        replacements = {
            "enalternance": "en alternance",
            "enstage": "en stage",
            "enapprentissage": "en apprentissage",
            "intelligenceartificielle": "intelligence artificielle",
            "datascience": "data science",
            "machinelearning": "machine learning",
        }
        lowered = text.casefold()
        for source, target in replacements.items():
            if source in lowered:
                text = re.sub(source, target, text, flags=re.IGNORECASE)

        return clean_text(text)

    def _extract_contact_info(self, raw_text: str) -> str | None:
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", raw_text)
        phone_match = re.search(r"(?:\+?\d[\d .()-]{7,}\d)", raw_text)

        details: list[str] = []
        if phone_match:
            details.append(clean_text(phone_match.group(0)))
        if email_match:
            details.append(clean_text(email_match.group(0)))

        return " | ".join(details) if details else None

    def _extract_location(self, sections: dict[str, list[str]], raw_text: str) -> str | None:
        # Simple heuristic: Look for known major cities or zip code patterns in the header
        header_lines = sections.get("header", [])[:15]
        for line in header_lines:
            if re.search(r"\b\d{5}\b", line) or any(city in line.lower() for city in ["paris", "lyon", "marseille", "toulouse", "bordeaux", "nantes", "lille", "strasbourg", "montpellier", "rennes", "remote", "télétravail"]):
                cleaned = re.sub(r"[\d]+", "", line).replace(",", "").strip()
                # If it's short, it's likely a location
                if 2 <= len(cleaned) <= 30 and "@" not in cleaned and not re.search(r"\d", cleaned):
                    return cleaned.title()
        return None

    def _extract_job_title(self, sections: dict[str, list[str]]) -> str | None:
        # Common titles
        known_titles = ["developpeur", "développeur", "developer", "engineer", "ingénieur", "ingenieur", "architect", "manager", "data scientist", "data analyst", "consultant", "designer"]
        
        # Look in the header first
        for line in sections.get("header", []):
            lower_line = line.lower()
            if any(title in lower_line for title in known_titles) and len(line) < 50 and "@" not in line:
                return line.title().strip()
                
        # If not in header, look for a profile title
        for line in sections.get("profile", []):
            lower_line = line.lower()
            if any(title in lower_line for title in known_titles) and len(line) < 60:
                return line.title().strip()
        return None


if __name__ == "__main__":
    pass
