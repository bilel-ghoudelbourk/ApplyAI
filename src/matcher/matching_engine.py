from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate

from src.agent.llm_utils import get_llm
from src.analyzer.cv_parser import CVData
from src.cache.cv_cache import CVMatchChunk
from src.config import get_settings
from src.scraper.job_scraper import JobDetails
from src.utils.normalization import clean_text, compare_skill_lists, extract_skills_from_text, merge_skill_sources, normalize_skill_key


class MatchResult(BaseModel):
    score: int = Field(description="A compatibility score between 0 and 100 based on how well the CV matches the job description.")
    missing_skills: list[str] = Field(description="A list of important skills required by the job that are missing from the CV.")
    reasoning: str = Field(description="A brief explanation of why the score was given.")


class MatchReasoning(BaseModel):
    reasoning: str = Field(description="A concise explanation of the match score.")


class MatchingEngine:
    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.settings = settings.matching
        self.llm_settings = settings.llm
        self.model_name = model_name or self.settings.model_name
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            self._llm = get_llm(
                temperature=self.llm_settings.temperatures.matcher,
                task="matcher",
            )
        return self._llm

    def calculate_match(
        self,
        cv_data: CVData,
        job_data: JobDetails,
        *,
        cv_chunks: list[CVMatchChunk] | None = None,
        use_llm_reasoning: bool | None = None,
        preferred_language: str | None = None,
    ) -> MatchResult:
        resolved_cv_chunks = cv_chunks or []
        cv_context = "\n".join(chunk.text for chunk in resolved_cv_chunks) or "\n".join(
            [*cv_data.skills, *cv_data.experience, *cv_data.education]
        )
        job_context = "\n".join([job_data.title, *job_data.skills_required, job_data.description])
        precomputed_cv_skills = merge_skill_sources(
            *(chunk.skills for chunk in resolved_cv_chunks),
        ) if resolved_cv_chunks else []
        skill_analysis = compare_skill_lists(
            job_data.skills_required,
            cv_data.skills,
            job_text=job_context,
            cv_text="" if resolved_cv_chunks else cv_context,
            precomputed_cv_skills=precomputed_cv_skills,
        )
        skill_evidence = self._collect_skill_evidence(
            skill_analysis["matched_skills"],
            resolved_cv_chunks,
            cv_data,
        )

        score = self._calculate_score(skill_analysis, skill_evidence)
        reasoning = self._generate_reasoning(
            score,
            skill_analysis,
            job_data,
            skill_evidence=skill_evidence,
            cv_data=cv_data,
            preferred_language=preferred_language,
            use_llm_reasoning=(
                self.settings.reasoning.default_use_llm
                if use_llm_reasoning is None
                else use_llm_reasoning
            ),
        )

        return MatchResult(
            score=score,
            missing_skills=skill_analysis["missing_skills"],
            reasoning=reasoning,
        )

    def _collect_skill_evidence(
        self,
        matched_skills: list[str],
        cv_chunks: list[CVMatchChunk],
        cv_data: CVData,
    ) -> dict[str, set[str]]:
        evidence_map: dict[str, set[str]] = {
            normalize_skill_key(skill): set()
            for skill in matched_skills
        }
        if cv_chunks:
            for chunk in cv_chunks:
                chunk_skill_keys = {normalize_skill_key(skill) for skill in chunk.skills}
                for skill in matched_skills:
                    skill_key = normalize_skill_key(skill)
                    if skill_key in chunk_skill_keys:
                        evidence_map.setdefault(skill_key, set()).add(chunk.source)
            return evidence_map

        experience_context = "\n".join(cv_data.experience)
        experience_skill_keys = {
            normalize_skill_key(skill)
            for skill in extract_skills_from_text(experience_context, matched_skills)
        }
        for skill in matched_skills:
            skill_key = normalize_skill_key(skill)
            if skill_key in experience_skill_keys:
                evidence_map.setdefault(skill_key, set()).add("experience")
        return evidence_map

    def _calculate_score(
        self,
        skill_analysis: dict[str, list[str] | int],
        skill_evidence: dict[str, set[str]],
    ) -> int:
        job_skills = skill_analysis["job_skills"]
        matched_skills = skill_analysis["matched_skills"]
        if not job_skills:
            return self.settings.score.empty_job_score

        coverage = int(skill_analysis["skill_coverage"])
        matched_count = len(matched_skills)
        experience_hits = sum(
            1
            for skill in matched_skills
            if "experience" in skill_evidence.get(normalize_skill_key(skill), set())
        )
        education_hits = sum(
            1
            for skill in matched_skills
            if "education" in skill_evidence.get(normalize_skill_key(skill), set())
        )

        breadth_bonus = min(
            self.settings.score.breadth_bonus_cap,
            round(matched_count * self.settings.score.breadth_bonus_multiplier),
        )
        experience_bonus = min(
            self.settings.score.experience_bonus_cap,
            experience_hits * self.settings.score.experience_bonus_per_hit,
        )
        education_bonus = min(
            self.settings.score.education_bonus_cap,
            education_hits * self.settings.score.education_bonus_per_hit,
        )
        score = round((coverage * self.settings.score.coverage_weight) + breadth_bonus + experience_bonus + education_bonus)
        return max(0, min(100, score))

    def _generate_reasoning(
        self,
        score: int,
        skill_analysis: dict[str, list[str] | int],
        job_data: JobDetails,
        *,
        skill_evidence: dict[str, set[str]],
        cv_data: CVData,
        preferred_language: str | None = None,
        use_llm_reasoning: bool = False,
    ) -> str:
        if not use_llm_reasoning:
            return self._build_fallback_reasoning(
                score,
                skill_analysis,
                job_data,
                skill_evidence,
                preferred_language=preferred_language,
            )

        try:
            structured_llm = self._get_llm().with_structured_output(MatchReasoning)
            prompt = PromptTemplate.from_template(
                "You are an expert technical recruiter.\n"
                "Explain the precomputed match score between the CV and the job.\n"
                "Do not change the score, do not invent missing skills, and do not contradict the normalized analysis.\n"
                "Your reasoning must be concise, concrete, and in the exact same language as the job description.\n\n"
                "--- Precomputed Score ---\n"
                "Score: {score}/100\n"
                "Skill Coverage: {skill_coverage}\n"
                "Matched Skills: {matched_skills}\n"
                "Missing Skills: {missing_skills}\n\n"
                "Experience Evidence: {experience_evidence}\n\n"
                "--- Job ---\n"
                "Title: {job_title}\n"
                "Description: {job_desc}\n\n"
                "--- CV ---\n"
                "Skills: {cv_skills}\n"
                "Experience: {cv_exp}\n"
                "Education: {cv_edu}\n"
            )

            chain = prompt | structured_llm
            result: MatchReasoning = chain.invoke(
                {
                    "score": score,
                    "skill_coverage": f"{skill_analysis['skill_coverage']}%",
                    "matched_skills": ", ".join(skill_analysis["matched_skills"]) or "None",
                    "missing_skills": ", ".join(skill_analysis["missing_skills"]) or "None",
                    "experience_evidence": ", ".join(
                        skill
                        for skill in skill_analysis["matched_skills"]
                        if "experience" in skill_evidence.get(normalize_skill_key(skill), set())
                    )
                    or "None",
                    "job_title": job_data.title,
                    "job_desc": job_data.description,
                    "cv_skills": ", ".join(skill_analysis["cv_skills"]),
                    "cv_exp": "\n".join(cv_data.experience),
                    "cv_edu": "\n".join(cv_data.education),
                }
            )
            return clean_text(result.reasoning)
        except Exception:
            return self._build_fallback_reasoning(
                score,
                skill_analysis,
                job_data,
                skill_evidence,
                preferred_language=preferred_language,
            )

    def _build_fallback_reasoning(
        self,
        score: int,
        skill_analysis: dict[str, list[str] | int],
        job_data: JobDetails,
        skill_evidence: dict[str, set[str]],
        *,
        preferred_language: str | None = None,
    ) -> str:
        matched = ", ".join(
            skill_analysis["matched_skills"][: self.settings.reasoning.matched_skill_limit]
        ) or "none"
        missing = ", ".join(
            skill_analysis["missing_skills"][: self.settings.reasoning.missing_skill_limit]
        ) or "none"
        experience_evidence = [
            skill
            for skill in skill_analysis["matched_skills"]
            if "experience" in skill_evidence.get(normalize_skill_key(skill), set())
        ]
        evidence_text = ", ".join(
            experience_evidence[: self.settings.reasoning.experience_evidence_limit]
        ) or "none"
        language = (preferred_language or "en").strip().lower()
        if language.startswith("fr"):
            return (
                f"Score {score}/100. Les competences les mieux alignees sont {matched}. "
                f"Les ecarts principaux concernent {missing}. "
                f"Les preuves les plus claires dans l'experience concernent {evidence_text}. "
                "Le score combine couverture des competences requises et preuves explicites dans les chunks du CV."
            )
        return (
            f"Score {score}/100. The strongest aligned skills are {matched}. "
            f"The main gaps are {missing}. "
            f"The clearest experience evidence is {evidence_text}. "
            "The score combines required-skill coverage and explicit evidence in the CV chunks."
        )

    def _looks_french(self, text: str) -> bool:
        sample = f" {clean_text(text).casefold()} "
        french_markers = [
            " le ",
            " la ",
            " les ",
            " des ",
            " une ",
            " vous ",
            " poste ",
            " profil ",
            " competences ",
            " missions ",
        ]
        return sum(marker in sample for marker in french_markers) >= 2


if __name__ == "__main__":
    pass
