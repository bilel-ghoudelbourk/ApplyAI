from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable


_SKILL_SPLIT_PATTERN = re.compile(r"[,;|\n•]+")
_PAREN_CONTENT_PATTERN = re.compile(r"\(([^)]*)\)")
_PAREN_PATTERN = re.compile(r"\([^)]*\)")
_WHITESPACE_PATTERN = re.compile(r"\s+")

_GENERIC_SKILL_TOKENS = {
    "adaptabilite",
    "adaptability",
    "analyse",
    "analysis",
    "apprentissagecontinu",
    "autonomie",
    "communication",
    "competence",
    "competences",
    "competencestechniques",
    "centresdinteret",
    "espritdequipe",
    "frameworksetbibliotheques",
    "frameworks",
    "languages",
    "langagesdeprogrammation",
    "langues",
    "logiciels",
    "mobilite",
    "notion",
    "notions",
    "outils",
    "outilsetlogiciels",
    "outilsgeospatiaux",
    "portfolio",
    "problemes",
    "profil",
    "projects",
    "softskills",
    "technologies",
    "technologiesutilisees",
}

_PROTECTED_SLASH_KEYS = {
    "ci cd",
}

_NOISY_SKILL_MARKERS = {
    "vous",
    "profil",
    "poste",
    "missions",
    "experience",
    "environnement",
    "developper",
    "concevoir",
    "participer",
    "assurer",
    "mettre",
    "fournir",
    "recherche",
}

_RAW_SKILL_ALIASES = {
    "AI": {"ai", "ia", "artificial intelligence", "intelligence artificielle"},
    "Generative AI": {"generative ai", "gen ai", "genai", "ia generative"},
    "Machine Learning": {"machine learning", "ml", "apprentissage automatique"},
    "Deep Learning": {"deep learning", "dl", "apprentissage profond"},
    "Computer Vision": {"computer vision", "vision par ordinateur"},
    "NLP": {
        "nlp",
        "natural language processing",
        "traitement du langage naturel",
        "traitement automatique du langage naturel",
    },
    "LLM": {"llm", "llms", "large language model", "large language models"},
    "RAG": {"rag", "retrieval augmented generation"},
    "MLOps": {"mlops", "ml ops"},
    "Data Science": {"data science", "science des donnees"},
    "Data Engineering": {"data engineering", "ingenierie des donnees"},
    "ETL": {"etl"},
    "Python": {"python"},
    "R": {"r"},
    "SQL": {"sql"},
    "MySQL": {"mysql"},
    "PostgreSQL": {"postgres", "postgresql", "postgre sql"},
    "MongoDB": {"mongodb", "mongo db"},
    "Java": {"java", "j2ee"},
    "JavaScript": {"javascript", "js"},
    "TypeScript": {"typescript", "ts"},
    "Bash": {"bash", "shell", "bash shell", "shell scripting"},
    "HTML": {"html"},
    "CSS": {"css"},
    "PyTorch": {"pytorch", "py torch"},
    "TensorFlow": {"tensorflow", "tensor flow"},
    "Scikit-learn": {"scikit-learn", "scikit learn", "sklearn"},
    "Pandas": {"pandas"},
    "NumPy": {"numpy"},
    "Matplotlib": {"matplotlib"},
    "Seaborn": {"seaborn"},
    "OpenCV": {"opencv", "open cv"},
    "Hugging Face": {"hugging face", "huggingface"},
    "Transformers": {"transformers", "transformer"},
    "Vision Transformers": {"vision transformers", "vision transformer", "vit"},
    "LangChain": {"langchain"},
    "LlamaIndex": {"llamaindex", "llama index"},
    "FastAPI": {"fastapi", "fast api"},
    "Flask": {"flask"},
    "Django": {"django"},
    "Node.js": {"node.js", "node js", "nodejs"},
    "React": {"react", "react.js", "reactjs"},
    "Next.js": {"next.js", "next js", "nextjs"},
    "Vue.js": {"vue.js", "vue js", "vuejs"},
    "Nuxt.js": {"nuxt.js", "nuxt js", "nuxtjs", "nuxt"},
    "Docker": {"docker"},
    "Docker Compose": {"docker compose", "docker-compose", "dockercompose"},
    "Kubernetes": {"kubernetes", "k8s"},
    "Apache Airflow": {"airflow", "apache airflow"},
    "MLflow": {"mlflow", "ml flow"},
    "ChromaDB": {"chromadb", "chroma db"},
    "FAISS": {"faiss"},
    "Vector Database": {"vector db", "vector database", "vectordb"},
    "Amazon Web Services": {"aws", "amazon web services"},
    "Amazon S3": {"s3", "amazon s3"},
    "Amazon Bedrock": {"bedrock", "amazon bedrock"},
    "Microsoft Azure": {"azure", "microsoft azure"},
    "Google Cloud Platform": {"gcp", "google cloud", "google cloud platform"},
    "Git": {"git"},
    "GitHub": {"github", "git hub"},
    "GitLab": {"gitlab", "git lab"},
    "CI/CD": {
        "ci/cd",
        "ci cd",
        "cicd",
        "continuous integration continuous deployment",
        "continuous integration continuous delivery",
    },
    "Jupyter": {"jupyter", "jupyter notebook"},
    "Google Colab": {"colab", "google colab"},
    "CircleCI": {"circleci", "circle ci"},
    "Power BI": {"powerbi", "power bi"},
    "Tableau": {"tableau"},
    "Label Studio": {"label studio", "labelstudio"},
    "Rasterio": {"rasterio"},
    "Shapely": {"shapely"},
    "Agile": {"agile", "agile scrum", "scrum"},
    ".NET": {".net", "dotnet"},
    "C#": {"c#", "c sharp", "csharp"},
    "C++": {"c++", "cplusplus", "cpp"},
}


def clean_text(value: str | None) -> str:
    if value is None:
        return ""
    return _WHITESPACE_PATTERN.sub(" ", value).strip()


def clean_text_list(values: Iterable[str]) -> list[str]:
    cleaned_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = clean_text(value)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned_values.append(cleaned)
    return cleaned_values


def normalize_skill_key(value: str) -> str:
    normalized = clean_text(value).casefold()
    replacements = {
        "c++": "cplusplus",
        "c#": "csharp",
        ".net": "dotnet",
        "node.js": "nodejs",
        "next.js": "nextjs",
        "react.js": "reactjs",
        "vue.js": "vuejs",
        "nuxt.js": "nuxtjs",
        "docker-compose": "dockercompose",
        "fast api": "fastapi",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = normalized.encode("ascii", errors="ignore").decode("ascii")
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9+/#.\s-]+", " ", normalized)
    normalized = re.sub(r"[\s/_-]+", " ", normalized)
    return normalized.strip()


_SKILL_ALIAS_MAP = {
    normalize_skill_key(variant): canonical
    for canonical, variants in _RAW_SKILL_ALIASES.items()
    for variant in {canonical, *variants}
}


def _build_search_patterns() -> dict[str, list[re.Pattern[str]]]:
    patterns: dict[str, list[re.Pattern[str]]] = {}
    for canonical, variants in _RAW_SKILL_ALIASES.items():
        compiled_patterns: list[re.Pattern[str]] = []
        for variant in {canonical, *variants}:
            key = normalize_skill_key(variant)
            if not key:
                continue
            pattern = re.escape(key).replace(r"\ ", r"\s+")
            compiled_patterns.append(re.compile(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])"))
        patterns[canonical] = compiled_patterns
    return patterns


_SKILL_SEARCH_PATTERNS = _build_search_patterns()


def _unique_in_order(values: Iterable[str]) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = clean_text(value)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        items.append(cleaned)
    return items


def _build_compact_search_keys() -> dict[str, list[str]]:
    compact_keys: dict[str, list[str]] = {}
    for canonical, variants in _RAW_SKILL_ALIASES.items():
        keys: list[str] = []
        for variant in {canonical, *variants}:
            normalized = normalize_skill_key(variant)
            compact = normalized.replace(" ", "")
            if len(compact) >= 6:
                keys.append(compact)
        compact_keys[canonical] = _unique_in_order(keys)
    return compact_keys


_SKILL_COMPACT_SEARCH_KEYS = _build_compact_search_keys()


def _split_fragment_on_slash(value: str) -> list[str]:
    cleaned = clean_text(value)
    if not cleaned or "/" not in cleaned:
        return [cleaned] if cleaned else []
    if normalize_skill_key(cleaned) in _PROTECTED_SLASH_KEYS:
        return [cleaned]
    return [part for part in (clean_text(item) for item in cleaned.split("/")) if part]


def _expand_skill_fragments(entry: str) -> list[str]:
    cleaned = clean_text(entry)
    if not cleaned:
        return []

    seed_fragments: list[str] = []
    without_parentheses = clean_text(_PAREN_PATTERN.sub(" ", cleaned))
    if without_parentheses:
        seed_fragments.append(without_parentheses)

    for match in _PAREN_CONTENT_PATTERN.finditer(cleaned):
        inner = clean_text(match.group(1))
        if inner:
            seed_fragments.append(inner)

    expanded_fragments: list[str] = []
    for fragment in seed_fragments or [cleaned]:
        for item in _SKILL_SPLIT_PATTERN.split(fragment):
            part = clean_text(item)
            if not part:
                continue
            expanded_fragments.extend(_split_fragment_on_slash(part))

    return _unique_in_order(expanded_fragments)


def _skill_candidates(skill: str) -> list[str]:
    cleaned = clean_text(skill)
    if not cleaned:
        return []

    candidates = [cleaned]
    without_parentheses = clean_text(_PAREN_PATTERN.sub(" ", cleaned))
    if without_parentheses and without_parentheses not in candidates:
        candidates.append(without_parentheses)

    for segment in re.split(r"[()/]", cleaned):
        candidate = clean_text(segment)
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    return candidates


def _is_generic_skill_token(skill: str) -> bool:
    compact = normalize_skill_key(skill).replace(" ", "")
    if not compact:
        return True
    if compact in _GENERIC_SKILL_TOKENS:
        return True
    if compact.isdigit():
        return True
    return False


def _is_noisy_skill_phrase(skill: str) -> bool:
    cleaned = clean_text(skill)
    if not cleaned:
        return True

    normalized = normalize_skill_key(cleaned)
    words = [word for word in normalized.split() if word]
    if not words:
        return True

    if len(cleaned) > 64:
        return True
    if len(words) > 6:
        return True
    if any(marker in words for marker in _NOISY_SKILL_MARKERS):
        return True
    if cleaned.count(".") >= 2 or cleaned.count(",") >= 3:
        return True
    return False


def canonical_skill_name(skill: str) -> str:
    for candidate in _skill_candidates(skill):
        key = normalize_skill_key(candidate)
        if key in _SKILL_ALIAS_MAP:
            return _SKILL_ALIAS_MAP[key]
    return clean_text(skill)


def normalize_skill_list(skills: Iterable[str]) -> list[str]:
    normalized_skills: list[str] = []
    seen: set[str] = set()

    for entry in skills:
        for raw_skill in _expand_skill_fragments(entry):
            canonical = canonical_skill_name(raw_skill)
            if not canonical or _is_generic_skill_token(canonical):
                continue
            if canonical == clean_text(raw_skill) and _is_noisy_skill_phrase(canonical):
                continue
            key = normalize_skill_key(canonical)
            if key in seen:
                continue
            seen.add(key)
            normalized_skills.append(canonical)

    return normalized_skills


def _looks_like_skill_list_prefix(prefix: str) -> bool:
    compact = normalize_skill_key(prefix).replace(" ", "")
    markers = {
        "competences",
        "competencestechniques",
        "frameworks",
        "frameworksetbibliotheques",
        "langages",
        "langagesdeprogrammation",
        "logiciels",
        "outils",
        "outilsetlogiciels",
        "skills",
        "stack",
        "technologies",
        "technologiesutilisees",
    }
    return any(marker in compact for marker in markers)


def _extract_list_like_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    for raw_line in text.splitlines():
        line = clean_text(raw_line)
        if not line:
            continue

        candidate_payload = ""
        if ":" in line:
            prefix, suffix = line.split(":", 1)
            if _looks_like_skill_list_prefix(prefix):
                candidate_payload = suffix
        if not candidate_payload:
            continue
        if len(candidate_payload) > 180:
            continue
        if candidate_payload.count(".") >= 2:
            continue

        candidates.extend(_expand_skill_fragments(candidate_payload))

    return _unique_in_order(candidates)


def extract_skills_from_text(text: str, seed_skills: Iterable[str] = ()) -> list[str]:
    cleaned_text = clean_text(text)
    if not cleaned_text:
        return normalize_skill_list(seed_skills)

    normalized_text = normalize_skill_key(cleaned_text)
    compact_text = normalized_text.replace(" ", "")
    detected_skills: list[str] = list(seed_skills)

    for canonical, patterns in _SKILL_SEARCH_PATTERNS.items():
        compact_match = any(
            key in compact_text
            for key in _SKILL_COMPACT_SEARCH_KEYS.get(canonical, [])
        )
        if compact_match or any(pattern.search(normalized_text) for pattern in patterns):
            detected_skills.append(canonical)

    detected_skills.extend(_extract_list_like_candidates(cleaned_text))
    return normalize_skill_list(detected_skills)


def merge_skill_sources(*sources: Iterable[str]) -> list[str]:
    merged: list[str] = []
    for source in sources:
        merged.extend(source)
    return normalize_skill_list(merged)


def compare_skill_lists(
    job_skills: Iterable[str],
    cv_skills: Iterable[str],
    *,
    job_text: str = "",
    cv_text: str = "",
    precomputed_cv_skills: Iterable[str] = (),
) -> dict[str, list[str] | int]:
    normalized_job_skills = merge_skill_sources(job_skills, extract_skills_from_text(job_text, job_skills))
    normalized_cv_skills = merge_skill_sources(
        cv_skills,
        precomputed_cv_skills,
        extract_skills_from_text(cv_text, cv_skills) if cv_text else [],
    )
    cv_skill_keys = {normalize_skill_key(skill) for skill in normalized_cv_skills}

    matched_skills = [skill for skill in normalized_job_skills if normalize_skill_key(skill) in cv_skill_keys]
    missing_skills = [skill for skill in normalized_job_skills if normalize_skill_key(skill) not in cv_skill_keys]
    coverage = round((len(matched_skills) / len(normalized_job_skills)) * 100) if normalized_job_skills else 0

    return {
        "job_skills": normalized_job_skills,
        "cv_skills": normalized_cv_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "skill_coverage": coverage,
    }
