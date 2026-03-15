from __future__ import annotations

from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate

from src.agent.llm_utils import get_llm
from src.analyzer.cv_parser import CVData
from src.config import get_settings
from src.scraper.job_scraper import JobDetails
from src.utils.normalization import compare_skill_lists

_PLACEHOLDER_VALUES = {
    "",
    "not specified",
    "not provided",
    "unknown company",
}


class OptimizedDocument(BaseModel):
    optimized_cv_summary: str = Field(
        description="A highly tailored abstract/summary emphasizing matching skills for the job."
    )
    cover_letter: str = Field(
        description="A professionally worded cover letter addressing the job description given the applicant's CV."
    )


class DocumentGenerator:
    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.settings = settings.documents
        self.llm_settings = settings.llm
        self.model_name = model_name or self.settings.model_name
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            self._llm = get_llm(
                temperature=self.llm_settings.temperatures.document_generator,
                task="document_generator",
            )
        return self._llm

    def detect_language(self, text: str) -> str:
        return self._detect_language(text)

    def generate_optimized_summary(
        self,
        cv_data: CVData,
        job_data: JobDetails,
        *,
        target_language: str | None = None,
    ) -> str:
        resolved_language = self._resolve_language(job_data, preferred_language=target_language)
        return self._build_optimized_summary(cv_data, job_data, language=resolved_language)

    def generate_cover_letter(
        self,
        cv_data: CVData,
        job_data: JobDetails,
        *,
        optimized_summary: str | None = None,
        use_llm_cover_letter: bool | None = None,
        target_language: str | None = None,
    ) -> str:
        resolved_language = self._resolve_language(job_data, preferred_language=target_language)
        summary = optimized_summary or self._build_optimized_summary(cv_data, job_data, language=resolved_language)
        return self._generate_cover_letter(
            cv_data,
            job_data,
            summary,
            use_llm_cover_letter=(
                self.settings.default_use_llm_cover_letter
                if use_llm_cover_letter is None
                else use_llm_cover_letter
            ),
            language=resolved_language,
        )

    def generate_documents(
        self,
        cv_data: CVData,
        job_data: JobDetails,
        *,
        use_llm_cover_letter: bool | None = None,
        target_language: str | None = None,
    ) -> OptimizedDocument:
        """
        Build the optimized summary deterministically and use the LLM only for the cover letter.
        """
        optimized_summary = self.generate_optimized_summary(
            cv_data,
            job_data,
            target_language=target_language,
        )
        cover_letter = self.generate_cover_letter(
            cv_data,
            job_data,
            optimized_summary=optimized_summary,
            use_llm_cover_letter=use_llm_cover_letter,
            target_language=target_language,
        )
        return OptimizedDocument(
            optimized_cv_summary=optimized_summary,
            cover_letter=cover_letter,
        )

    def _build_optimized_summary(self, cv_data: CVData, job_data: JobDetails, *, language: str) -> str:
        cv_context = "\n".join([*cv_data.skills, *cv_data.experience, *cv_data.education])
        job_context = "\n".join([job_data.title, *job_data.skills_required, job_data.description])
        skill_analysis = compare_skill_lists(
            job_data.skills_required,
            cv_data.skills,
            job_text=job_context,
            cv_text=cv_context,
        )

        matched_skills = skill_analysis["matched_skills"][: self.settings.summary_matched_skill_limit]
        missing_skills = skill_analysis["missing_skills"][: self.settings.summary_missing_skill_limit]
        experience_highlights = self._select_readable_entries(
            cv_data.experience,
            limit=self.settings.summary_experience_limit,
        )
        education_highlight = self._select_readable_entries(
            cv_data.education,
            limit=self.settings.summary_education_limit,
        )
        is_french = language == "fr"
        display_title = self._safe_value(job_data.title, fallback="ce poste" if is_french else "this role")
        display_company = self._safe_value(job_data.company)

        if is_french:
            parts = [
                (
                    f"Profil ciblé pour le poste de {display_title} chez {display_company}."
                    if display_company
                    else f"Profil ciblé pour le poste de {display_title}."
                ),
                (
                    "Compétences directement alignées : "
                    + ", ".join(matched_skills)
                    + "."
                    if matched_skills
                    else "Compétences transférables identifiées à partir du CV."
                ),
            ]
            if experience_highlights:
                parts.append("Expériences pertinentes : " + " | ".join(experience_highlights) + ".")
            if education_highlight:
                parts.append(f"Formation notable : {education_highlight[0]}.")
            if missing_skills:
                parts.append(
                    "Points à renforcer ou à vérifier selon l'offre : " + ", ".join(missing_skills) + "."
                )
            return " ".join(parts)

        parts = [
            (
                f"Targeted profile for the {display_title} role at {display_company}."
                if display_company
                else f"Targeted profile for the {display_title} role."
            ),
            (
                "Directly aligned skills: " + ", ".join(matched_skills) + "."
                if matched_skills
                else "Transferable strengths identified from the CV."
            ),
        ]
        if experience_highlights:
            parts.append("Relevant experience: " + " | ".join(experience_highlights) + ".")
        if education_highlight:
            parts.append(f"Notable education: {education_highlight[0]}.")
        if missing_skills:
            parts.append("Areas to validate or strengthen for the role: " + ", ".join(missing_skills) + ".")
        return " ".join(parts)

    def _generate_cover_letter(
        self,
        cv_data: CVData,
        job_data: JobDetails,
        optimized_summary: str,
        *,
        use_llm_cover_letter: bool,
        language: str,
    ) -> str:
        if not use_llm_cover_letter:
            return self._build_fallback_cover_letter(cv_data, job_data, optimized_summary, language=language)

        try:
            is_french = language == "fr"
            prompt = PromptTemplate.from_template(
                "You are an expert recruiter and career writer.\n"
                "Write only the final cover letter text.\n"
                "Do not return JSON, labels, notes, explanations, or markdown fences.\n"
                "Do not invent companies, achievements, years, or tools not present in the data.\n"
                "Write in the exact target language requested below.\n"
                "Use a natural, strong, human tone.\n"
                "The letter must contain:\n"
                "- a subject line\n"
                "- a greeting\n"
                "- 3 short body paragraphs\n"
                "- a closing line\n"
                "Avoid repeating the optimized summary verbatim.\n"
                "Avoid placeholders like 'Not specified'.\n\n"
                "Target language: {target_language}\n\n"
                "--- Target Job ---\n"
                "Title: {job_title}\n"
                "Company: {job_company}\n"
                "Required Skills: {job_skills}\n"
                "Job Description Context: {job_desc}\n\n"
                "--- Candidate Background ---\n"
                "Optimized Summary: {optimized_summary}\n"
                "Skills: {cv_skills}\n"
                "Experience: {cv_exp}\n"
                "Education: {cv_edu}\n"
                "Contact info: {cv_contact}\n"
            )

            prompt_text = prompt.format(
                target_language="French" if is_french else "English",
                job_title=job_data.title,
                job_company=self._safe_value(
                    job_data.company,
                    fallback="Entreprise non mentionnée dans l'offre"
                    if is_french
                    else "Company not specified in the posting",
                ),
                job_skills=", ".join(job_data.skills_required),
                job_desc=job_data.description,
                optimized_summary=optimized_summary,
                cv_skills=", ".join(cv_data.skills),
                cv_exp="\n".join(cv_data.experience),
                cv_edu="\n".join(cv_data.education),
                cv_contact=cv_data.contact_info if cv_data.contact_info else "Not provided",
            )

            result = self._get_llm().invoke(prompt_text)
            cover_letter = self._cleanup_cover_letter(self._extract_text_response(result))
            if (
                self._looks_incomplete(cover_letter)
                or self._looks_generic(cover_letter)
                or not self._matches_language(cover_letter, language)
            ):
                return self._build_fallback_cover_letter(cv_data, job_data, optimized_summary, language=language)
            return cover_letter
        except Exception:
            return self._build_fallback_cover_letter(cv_data, job_data, optimized_summary, language=language)

    def _build_fallback_cover_letter(
        self,
        cv_data: CVData,
        job_data: JobDetails,
        optimized_summary: str,
        *,
        language: str,
    ) -> str:
        matched_experience = self._select_readable_entries(
            cv_data.experience,
            limit=self.settings.fallback_cover_letter_experience_limit,
        )
        matched_education = self._select_readable_entries(
            cv_data.education,
            limit=self.settings.fallback_cover_letter_education_limit,
        )
        skill_analysis = compare_skill_lists(
            job_data.skills_required,
            cv_data.skills,
            job_text="\n".join([job_data.title, *job_data.skills_required, job_data.description]),
            cv_text="\n".join([*cv_data.skills, *cv_data.experience, *cv_data.education]),
        )
        matched_skills = skill_analysis["matched_skills"][: self.settings.fallback_cover_letter_skill_limit]
        is_french = language == "fr"
        display_title = self._safe_value(job_data.title, fallback="ce poste" if is_french else "this role")
        display_company = self._safe_value(
            job_data.company,
            fallback="votre entreprise" if is_french else "your company",
        )

        if is_french:
            skill_sentence = (
                "Mes compétences les plus directement pertinentes pour ce poste sont "
                + ", ".join(matched_skills[:-1])
                + f" et {matched_skills[-1]}."
                if len(matched_skills) >= 2
                else (
                    f"Ma compétence la plus directement pertinente pour ce poste est {matched_skills[0]}."
                    if matched_skills
                    else "Mon parcours me permet d'aborder rapidement les enjeux techniques de ce poste."
                )
            )
            paragraphs = [
                f"Objet : Candidature au poste de {display_title}",
                (
                    f"Madame, Monsieur,\n\nJe souhaite vous proposer ma candidature pour le poste de "
                    f"{display_title} au sein de {display_company}."
                ),
                (
                    skill_sentence
                    + (
                        f" Mon expérience la plus proche de vos attentes est {matched_experience[0]}."
                        if matched_experience
                        else ""
                    )
                ).strip(),
                (
                    (
                        f"Cette expérience, complétée par ma formation {matched_education[0]}, "
                        if matched_education
                        else "Ma formation et mes projets m'ont amené à travailler sur des sujets proches de vos attentes, "
                    )
                    + "me permet de contribuer avec méthode, autonomie et sens du résultat sur des projets IA en production."
                ).strip(),
                (
                    "Je serais ravi d'échanger avec vous afin de détailler ma motivation et la manière "
                    "dont je peux contribuer rapidement à vos objectifs."
                ),
                "Cordialement,",
            ]
            return "\n\n".join(paragraphs)

        skill_sentence = (
            "My strongest skills for this role are "
            + ", ".join(matched_skills[:-1])
            + f", and {matched_skills[-1]}."
            if len(matched_skills) >= 2
            else (
                f"My strongest skill for this role is {matched_skills[0]}."
                if matched_skills
                else "My background gives me a solid base to contribute to this role quickly."
            )
        )
        paragraphs = [
            f"Subject: Application for the {display_title} role",
            (
                f"Dear Hiring Team,\n\nI would like to submit my application for the "
                f"{display_title} position at {display_company}."
            ),
            (
                skill_sentence
                + (
                    f" My most relevant experience for this role is {matched_experience[0]}."
                    if matched_experience
                    else ""
                )
            ).strip(),
            (
                (
                    f"Combined with my education in {matched_education[0]}, "
                    if matched_education
                    else "Combined with my academic background and hands-on projects, "
                )
                + "this allows me to contribute in a structured, reliable way on applied AI initiatives."
            ).strip(),
            (
                "I would welcome the opportunity to discuss how I can contribute quickly and effectively "
                "to your team."
            ),
            "Sincerely,",
        ]
        return "\n\n".join(paragraphs)

    def _safe_value(
        self,
        value: str | None,
        *,
        fallback: str = "",
    ) -> str:
        cleaned = (value or "").strip()
        if cleaned.casefold() in _PLACEHOLDER_VALUES:
            return fallback
        return cleaned

    def _select_readable_entries(self, values: list[str], *, limit: int) -> list[str]:
        entries: list[str] = []
        for value in values:
            cleaned = self._normalize_entry(value)
            if not cleaned or self._looks_noisy(cleaned):
                continue
            entries.append(cleaned)
            if len(entries) >= limit:
                break
        return entries

    def _normalize_entry(self, value: str) -> str:
        return " ".join((value or "").replace("—", " - ").replace("–", " - ").split())

    def _looks_noisy(self, value: str) -> bool:
        if len(value) < 18:
            return False
        spaces = value.count(" ")
        pipes = value.count("|")
        if spaces <= 1 and pipes == 0:
            return True
        return False

    def _looks_incomplete(self, text: str) -> bool:
        stripped = text.strip()
        if len(stripped) < self.settings.incomplete_min_length:
            return True
        if stripped.count("\n") < self.settings.incomplete_min_line_breaks:
            return True
        return False

    def _looks_generic(self, text: str) -> bool:
        lowered = text.casefold()
        generic_markers = [
            "profil cible pour le poste",
            "optimized summary",
            "not specified",
            "entreprise non mentionnée",
        ]
        return any(marker in lowered for marker in generic_markers)

    def _extract_text_response(self, response: object) -> str:
        content = getattr(response, "content", response)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                else:
                    parts.append(str(item))
            return "\n".join(part for part in parts if part).strip()
        return str(content).strip()

    def _cleanup_cover_letter(self, text: str) -> str:
        cleaned = text.strip().strip("`")
        prefixes = [
            "Voici une lettre de motivation :",
            "Voici votre lettre de motivation :",
            "Cover letter:",
            "Lettre de motivation :",
        ]
        for prefix in prefixes:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()
        return cleaned

    def _resolve_language(self, job_data: JobDetails, *, preferred_language: str | None = None) -> str:
        preferred = (preferred_language or "").strip().lower()
        if preferred in {"fr", "en"}:
            return preferred
        sample = "\n".join(
            value for value in [job_data.title, job_data.company, job_data.location, job_data.description] if value
        )
        return self._detect_language(sample)

    def _detect_language(self, text: str) -> str:
        sample = f" {self._normalize_language_sample(text)} "
        french_markers = [
            " le ",
            " la ",
            " les ",
            " des ",
            " une ",
            " vous ",
            " votre ",
            " poste ",
            " profil ",
            " competences ",
            " missions ",
            " candidature ",
            " developp",
            " ingenieur ",
            " entreprise ",
            " formation ",
            " experience ",
        ]
        english_markers = [
            " the ",
            " and ",
            " with ",
            " role ",
            " job ",
            " skills ",
            " experience ",
            " company ",
            " team ",
            " position ",
            " application ",
            " responsibilities ",
            " requirements ",
        ]
        french_score = sum(sample.count(marker) for marker in french_markers)
        english_score = sum(sample.count(marker) for marker in english_markers)
        return "fr" if french_score >= english_score else "en"

    def _matches_language(self, text: str, language: str) -> bool:
        return self._detect_language(text) == language

    def _normalize_language_sample(self, text: str) -> str:
        sample = f" {text.casefold()} "
        replacements = {
            "ã©": "e",
            "ã¨": "e",
            "ãª": "e",
            "ã ": "a",
            "ã§": "c",
            "â€™": "'",
            "â€": '"',
            "Ã©": "e",
            "Ã¨": "e",
            "Ãª": "e",
            "Ã ": "a",
            "Ã§": "c",
            "Ã»": "u",
            "Ã´": "o",
            "Ã®": "i",
        }
        for source, target in replacements.items():
            sample = sample.replace(source.casefold(), target)
        return sample

    def _looks_french(self, text: str) -> bool:
        sample = f" {self._normalize_language_sample(text)} "
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
