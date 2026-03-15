import re
from typing import List

from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from src.agent.llm_utils import get_llm
from src.config import get_settings
from src.utils.normalization import clean_text, extract_skills_from_text, merge_skill_sources, normalize_skill_key


class JobDetails(BaseModel):
    title: str = Field(description="The job title from the posting.")
    company: str = Field(description="The company name offering the job.")
    skills_required: List[str] = Field(description="A list of technical and soft skills required for the job.")
    location: str = Field(description="The location (city, remote, etc.) of the job.")
    description: str = Field(description="A brief summary of the job description.")


class JobScraper:
    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.settings = settings.job_scraper
        self.llm_settings = settings.llm
        self.model_name = model_name or self.settings.model_name
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            self._llm = get_llm(
                temperature=self.llm_settings.temperatures.job_scraper,
                task="job_scraper",
            )
        return self._llm

    def parse_job_text(
        self,
        job_text: str,
        use_llm: bool | None = None,
        allow_llm_refinement: bool | None = None,
    ) -> JobDetails:
        normalized_job_text = self._normalize_job_text(job_text)
        heuristic_result = self._parse_job_text_heuristically(normalized_job_text)
        resolved_use_llm = self.settings.default_use_llm if use_llm is None else use_llm
        resolved_allow_refinement = (
            self.settings.default_allow_llm_refinement
            if allow_llm_refinement is None
            else allow_llm_refinement
        )
        should_use_llm = resolved_use_llm or (
            resolved_allow_refinement and self._needs_llm_refinement(heuristic_result, normalized_job_text)
        )
        if not should_use_llm:
            return heuristic_result

        llm_result = self._parse_job_text_with_llm(normalized_job_text)
        if llm_result is None:
            return heuristic_result

        return self._merge_job_details(heuristic_result, llm_result)

    def _parse_job_text_with_llm(self, job_text: str) -> JobDetails | None:
        try:
            structured_llm = self._get_llm().with_structured_output(JobDetails)
            prompt = PromptTemplate.from_template(
                "You are an expert technical recruiter analyzing a job posting.\n"
                "Extract the key details into the required structure.\n"
                "Return a clean job title only, not a marketing sentence.\n"
                "Return only the company name for company.\n"
                "Return only the location for location.\n"
                "Be exhaustive for programming languages, frameworks, cloud tooling, data tooling, and deployment tooling.\n"
                "Do not merge related but distinct tools or platforms.\n"
                "Ignore emojis, marketing copy, CTA text, accessibility text, and decorative bullets.\n"
                'If some information is completely missing, return "Not specified".\n\n'
                "Job Posting Text:\n{job_text}"
            )
            chain = prompt | structured_llm
            result: JobDetails = chain.invoke({"job_text": job_text[: self.settings.llm_max_input_chars]})
            return JobDetails(
                title=clean_text(result.title),
                company=clean_text(result.company),
                skills_required=merge_skill_sources(result.skills_required),
                location=clean_text(result.location),
                description=clean_text(result.description),
            )
        except Exception:
            return None

    def _parse_job_text_heuristically(self, job_text: str) -> JobDetails:
        lines = [clean_text(line) for line in job_text.splitlines() if clean_text(line)]
        title = self._guess_title(lines)
        company = self._guess_company(lines, title)
        location = self._guess_location(lines, title, company)
        description = self._guess_description(lines)
        skills_required = extract_skills_from_text(job_text)

        return JobDetails(
            title=title or "Not specified",
            company=company or "Not specified",
            skills_required=skills_required,
            location=location or "Not specified",
            description=description or clean_text(job_text[: self.settings.fallback_description_chars]),
        )

    def _merge_job_details(self, heuristic_result: JobDetails, llm_result: JobDetails) -> JobDetails:
        return JobDetails(
            title=self._prefer_clean_value(llm_result.title, heuristic_result.title),
            company=self._prefer_clean_value(llm_result.company, heuristic_result.company),
            skills_required=merge_skill_sources(heuristic_result.skills_required, llm_result.skills_required),
            location=self._prefer_clean_value(llm_result.location, heuristic_result.location),
            description=self._prefer_clean_value(llm_result.description, heuristic_result.description),
        )

    def _normalize_job_text(self, job_text: str) -> str:
        text = self._fix_mojibake(job_text)
        replacements = {
            "âœ”ï¸": "\n- ",
            "ðŸ‘‰": " ",
            "ðŸ‘ˆ": " ",
            "ðŸš€": " ",
            "âœ¨": " ",
            "ðŸ‘Œ": " ",
            "â˜˜ï¸": " ",
            "âš™ï¸": "\n",
            "ðŸŽ“": "\n",
            "â˜‘ï¸": "\n",
            "â–ª": "\n- ",
            "ðŸ”¸": "\n- ",
            "â€¢": "\n- ",
        }
        for source, target in replacements.items():
            text = text.replace(source, target)
        text = re.sub(r"\s*[|]+\s*", " | ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _fix_mojibake(self, text: str) -> str:
        if "Ãƒ" not in text and "Ã¢" not in text:
            return text
        try:
            repaired = text.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
            return repaired or text
        except Exception:
            return text

    def _needs_llm_refinement(self, job_data: JobDetails, job_text: str) -> bool:
        title = clean_text(job_data.title)
        company = clean_text(job_data.company)
        skills = job_data.skills_required

        if self._is_placeholder(title):
            return True
        if len(title) > self.settings.title_max_length or self._looks_like_sentence(title) or self._contains_noise(title):
            return True
        if self._is_placeholder(company) or len(company) > self.settings.company_max_length or self._looks_like_sentence(company):
            return True
        if len(skills) < self.settings.min_skill_count_for_no_refinement:
            return True
        if any(self._looks_bad_skill(skill) for skill in skills):
            return True
        if (
            job_text.count("\n- ") >= self.settings.noisy_bullet_count_threshold
            and len(skills) < self.settings.min_skill_count_for_no_refinement
        ):
            return True
        return False

    def _prefer_clean_value(self, primary: str, fallback: str) -> str:
        primary_clean = clean_text(primary)
        fallback_clean = clean_text(fallback)
        if self._is_placeholder(primary_clean):
            return fallback_clean or "Not specified"
        if self._contains_noise(primary_clean) and not self._contains_noise(fallback_clean):
            return fallback_clean or primary_clean
        if len(primary_clean) > self.settings.max_clean_value_length and fallback_clean:
            return fallback_clean
        return primary_clean or fallback_clean or "Not specified"

    def _looks_bad_skill(self, skill: str) -> bool:
        cleaned = clean_text(skill)
        if not cleaned:
            return True
        if len(cleaned) > self.settings.bad_skill_max_length:
            return True
        if len(cleaned.split()) > self.settings.bad_skill_max_words:
            return True
        if self._contains_noise(cleaned):
            return True
        return False

    def _contains_noise(self, value: str) -> bool:
        lowered = normalize_skill_key(value)
        noisy_markers = (
            "recrute",
            "souhaitez",
            "missions suivantes",
            "profil recherche",
            "tous nos postes",
            "si vous souhaitez",
            "nous avons",
            "developper le front end",
        )
        return any(marker in lowered for marker in noisy_markers)

    def _looks_like_sentence(self, value: str) -> bool:
        cleaned = clean_text(value)
        return len(cleaned.split()) > self.settings.sentence_max_words or cleaned.count(".") >= 1

    def _is_placeholder(self, value: str) -> bool:
        return value.casefold() in {"", "not specified", "unknown company"}

    def _guess_title(self, lines: list[str]) -> str:
        sample = "\n".join(lines[: self.settings.title_sample_lines])
        inline_patterns = (
            r"\ben tant que\s+([A-ZA-Za-zÃ€-Ã¿0-9/+ -]{4,80})",
            r"\bposte de\s+([A-ZA-Za-zÃ€-Ã¿0-9/+ -]{4,80})",
            r"\bprofil recherche[: ]+([A-ZA-Za-zÃ€-Ã¿0-9/+ -]{4,80})",
        )
        for pattern in inline_patterns:
            match = re.search(pattern, sample, re.IGNORECASE)
            if match:
                return clean_text(match.group(1))

        for line in lines[: self.settings.title_scan_lines]:
            compact = normalize_skill_key(line).replace(" ", "")
            if compact in {"lesmissionsduposte", "leprofilrecherche", "profil", "missions"}:
                continue
            if len(line) <= 100:
                return line
        return "Not specified"

    def _guess_company(self, lines: list[str], title: str) -> str:
        company_patterns = (
            r"\bchez\s+([A-Z][\w&.\- ]+)",
            r"\bau sein de\s+([A-Z][\w&.\- ]+)",
            r"\bcompany[: ]+([A-Z][\w&.\- ]+)",
            r"\bentreprise[: ]+([A-Z][\w&.\- ]+)",
            r"\bsociete[: ]+([A-Z][\w&.\- ]+)",
            r"\bclient[: ]+([A-Z][\w&.\- ]+)",
        )
        sample = "\n".join(lines[: self.settings.company_sample_lines])
        for pattern in company_patterns:
            match = re.search(pattern, sample, re.IGNORECASE)
            if match:
                return clean_text(match.group(1))

        for line in lines[: self.settings.company_scan_lines]:
            if line == title:
                continue
            if self._looks_like_metadata_heading(line):
                continue
            if self._looks_like_location_line(line):
                continue
            if 2 <= len(line.split()) <= 6 and len(line) <= 60 and not line.startswith("-"):
                if any(character.isupper() for character in line):
                    return line
        return "Not specified"

    def _guess_location(self, lines: list[str], title: str, company: str) -> str:
        location_patterns = (
            r"\b(remote|hybride|hybrid|teletravail)\b",
            r"\b(paris|lyon|marseille|toulouse|lille|nantes|france)\b",
        )
        sample = "\n".join(lines[: self.settings.location_sample_lines])
        for pattern in location_patterns:
            match = re.search(pattern, sample, re.IGNORECASE)
            if match:
                return clean_text(match.group(1))

        for line in lines[: self.settings.location_scan_lines]:
            if line in {title, company}:
                continue
            if self._looks_like_location_line(line):
                return line
        return "Not specified"

    def _guess_description(self, lines: list[str]) -> str:
        kept_lines: list[str] = []
        for line in lines:
            compact = normalize_skill_key(line).replace(" ", "")
            if compact in {"lesmissionsduposte", "leprofilrecherche", "competencesappreciees"}:
                continue
            kept_lines.append(line)
            if len(kept_lines) >= self.settings.heuristic_description_max_lines:
                break
        return clean_text(" ".join(kept_lines))

    def _looks_like_metadata_heading(self, value: str) -> bool:
        compact = normalize_skill_key(value).replace(" ", "")
        headings = {
            "lesmissionsduposte",
            "leprofilrecherche",
            "profil",
            "missions",
            "descriptionduposte",
            "aboutthejob",
        }
        return compact in headings

    def _looks_like_location_line(self, value: str) -> bool:
        sample = normalize_skill_key(value)
        if not sample:
            return False
        location_markers = (
            "remote",
            "hybrid",
            "hybride",
            "teletravail",
            "france",
            "paris",
            "lyon",
            "marseille",
            "toulouse",
            "lille",
            "nantes",
            "avignon",
            "bordeaux",
            "rennes",
            "nice",
        )
        return "," in value or any(marker in sample for marker in location_markers)
