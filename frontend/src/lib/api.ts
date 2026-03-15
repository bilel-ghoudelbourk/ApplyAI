const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8010/api";

export const AVAILABLE_SEARCH_SOURCES = [
    "company_pages",
    "curated_feed",
    "partner_feed",
    "remote_hub",
    "community_board",
    "talent_pool",
] as const;

export type SearchSource = (typeof AVAILABLE_SEARCH_SOURCES)[number];

export type JobListing = {
    source: string;
    title: string;
    company: string;
    location: string;
    url: string;
    posted_at_text?: string | null;
    summary?: string | null;
};

export type MatchListingData = {
    source?: string;
    title?: string;
    company?: string;
    location?: string;
    url?: string;
    posted_at_text?: string | null;
    summary?: string | null;
    analysis_source?: string;
    job_title?: string;
    job_company?: string;
    job_required_skills?: string[];
    job_description?: string;
    match_score?: number;
    missing_skills?: string[];
    reasoning?: string;
    analysis_error?: string;
};

export type AnalyzeMatchData = {
    cv_skills?: string[];
    job_title?: string;
    job_company?: string;
    job_location?: string;
    job_required_skills?: string[];
    match_score?: number;
    missing_skills?: string[];
    reasoning?: string;
};

export type CVMetadata = {
    location: string | null;
    job_title: string | null;
    top_skills: string[];
    suggested_keywords: string;
};

export type SearchResponse = {
    status: string;
    data: {
        results: JobListing[];
        errors: Record<string, string>;
    };
};

type JobListingPayload = Partial<JobListing>;

type MockSearchParams = {
    keywords: string;
    location: string;
    postedWithin: string;
    sources: string[];
    language: string;
    limit: number;
};

const MOCK_COMPANIES = [
    "Northline Studio",
    "Harbor Stack",
    "Atlas Forge",
    "Signal Works",
    "Blue Meadow Labs",
    "Cinder Cloud",
    "Lattice House",
    "Pinefield Systems",
] as const;

const MOCK_SUMMARY_SKILLS = [
    ["React", "TypeScript", "Next.js", "API integration"],
    ["Python", "FastAPI", "SQL", "Docker"],
    ["Product strategy", "Roadmapping", "Stakeholder management"],
    ["Data analysis", "SQL", "Python", "Dashboarding"],
    ["Node.js", "TypeScript", "Testing", "CI/CD"],
    ["Cloud operations", "Kubernetes", "Terraform", "Monitoring"],
] as const;

function sleep(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function slugify(value: string) {
    return value
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
}

function toDisplayCase(value: string) {
    return value
        .split(/[\s,/+-]+/)
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
}

function getKeywordBase(keywords: string, language: string) {
    const normalized = keywords.trim();
    if (normalized) {
        return toDisplayCase(normalized);
    }
    return language === "fr" ? "Profil cible" : "Target role";
}

function getMockPostedAt(postedWithin: string, index: number, language: string) {
    const french = language === "fr";
    if (postedWithin === "24h") {
        return french ? `${index + 2} h` : `${index + 2}h ago`;
    }
    if (postedWithin === "30d") {
        return french ? `Il y a ${index + 3} jours` : `${index + 3} days ago`;
    }
    if (postedWithin === "all") {
        return french ? "Archive recente" : "Recent archive";
    }
    return french ? `Il y a ${index + 1} jours` : `${index + 1} days ago`;
}

export function getSearchSourceLabel(source: string, language: string) {
    const labels: Record<string, { fr: string; en: string }> = {
        company_pages: { fr: "Pages entreprises", en: "Company pages" },
        curated_feed: { fr: "Flux curatif", en: "Curated feed" },
        partner_feed: { fr: "Flux partenaire", en: "Partner feed" },
        remote_hub: { fr: "Hub remote", en: "Remote hub" },
        community_board: { fr: "Board communaute", en: "Community board" },
        talent_pool: { fr: "Talent pool", en: "Talent pool" },
    };
    const fallback = source.replace(/_/g, " ");
    return labels[source]?.[language === "fr" ? "fr" : "en"] ?? fallback;
}

function buildMockListings({
    keywords,
    location,
    postedWithin,
    sources,
    language,
    limit,
}: MockSearchParams): JobListing[] {
    const safeSources = sources.length > 0 ? sources : [...AVAILABLE_SEARCH_SOURCES];
    const safeLimit = Math.max(1, Math.min(limit, 12));
    const keywordBase = getKeywordBase(keywords, language);
    const safeLocation = location.trim() || (language === "fr" ? "Remote" : "Remote");
    const roleVariants =
        language === "fr"
            ? ["Senior", "Lead", "Confirme", "Platform", "Produit", "Data"]
            : ["Senior", "Lead", "Staff", "Platform", "Product", "Data"];

    return Array.from({ length: safeLimit }, (_, index) => {
        const company = MOCK_COMPANIES[index % MOCK_COMPANIES.length];
        const source = safeSources[index % safeSources.length];
        const skills = MOCK_SUMMARY_SKILLS[index % MOCK_SUMMARY_SKILLS.length];
        const prefix = roleVariants[index % roleVariants.length];
        const title = `${keywordBase} ${prefix}`.trim();
        const summary =
            language === "fr"
                ? `Offre demo ${getSearchSourceLabel(source, language).toLowerCase()} autour de ${keywordBase.toLowerCase()}, avec un focus sur ${skills.join(", ")}.`
                : `Demo listing from ${getSearchSourceLabel(source, language).toLowerCase()} focused on ${keywordBase.toLowerCase()} with emphasis on ${skills.join(", ")}.`;

        return {
            source,
            title,
            company,
            location: safeLocation,
            url: `https://example.com/jobs/${slugify(`${company}-${title}-${index + 1}`)}`,
            posted_at_text: getMockPostedAt(postedWithin, index, language),
            summary,
        };
    });
}

function buildListingContextText(listing: JobListingPayload) {
    return [
        `Title: ${listing.title || "Not specified"}`,
        `Company: ${listing.company || "Not specified"}`,
        `Location: ${listing.location || "Not specified"}`,
        listing.summary ? `Summary: ${listing.summary}` : "",
        listing.source ? `Source: ${listing.source}` : "",
        listing.url ? `Reference URL: ${listing.url}` : "",
    ]
        .filter(Boolean)
        .join("\n");
}

export async function uploadCVPdf(file: File) {
    const formData = new FormData();
    formData.append("cv_file", file);

    const res = await fetch(`${API_BASE_URL}/cv/upload`, {
        method: "POST",
        body: formData,
    });

    if (!res.ok) {
        const errorData = await res.json().catch(() => null);
        throw new Error(errorData?.detail || "Failed to upload CV");
    }

    return res.json();
}

export async function analyzeJob(
    cvCacheId: string,
    jobUrlText: string,
    jobFile?: File | null,
    responseLanguage: string = "en"
) {
    const formData = new FormData();
    formData.append("cv_cache_id", cvCacheId);
    if (jobUrlText) formData.append("job_offer_text", jobUrlText);
    if (jobFile) formData.append("job_offer_file", jobFile);
    formData.append("response_language", responseLanguage);

    const res = await fetch(`${API_BASE_URL}/match`, {
        method: "POST",
        body: formData,
    });

    if (!res.ok) {
        const errorData = await res.json().catch(() => null);
        throw new Error(errorData?.detail || "Failed to analyze job");
    }

    return res.json();
}

export async function generateCoverLetter(cvCacheId: string, jobUrlText: string, jobFile?: File | null) {
    const formData = new FormData();
    formData.append("cv_cache_id", cvCacheId);
    if (jobUrlText) formData.append("job_offer_text", jobUrlText);
    if (jobFile) formData.append("job_offer_file", jobFile);

    const res = await fetch(`${API_BASE_URL}/match/cover-letter`, {
        method: "POST",
        body: formData,
    });

    if (!res.ok) {
        const errorData = await res.json().catch(() => null);
        throw new Error(errorData?.detail || "Failed to generate cover letter");
    }

    return res.json();
}

export async function searchJobs(
    keywords: string,
    location: string,
    postedWithin: string,
    sources: string[],
    language: string,
    limit: number = 20
): Promise<SearchResponse> {
    await sleep(250);
    return {
        status: "success",
        data: {
            results: buildMockListings({ keywords, location, postedWithin, sources, language, limit }),
            errors: {},
        },
    };
}

export async function searchByCV(
    cvCacheId: string,
    keywords: string | null = null,
    location: string | null = null,
    postedWithin: string = "all",
    sources: string[] = [],
    language: string = "en",
    limit: number = 20
): Promise<SearchResponse> {
    void cvCacheId;
    await sleep(250);
    return {
        status: "success",
        data: {
            results: buildMockListings({
                keywords: keywords ?? "",
                location: location ?? "",
                postedWithin,
                sources,
                language,
                limit,
            }),
            errors: {},
        },
    };
}

export async function matchListing(
    cvCacheId: string,
    listing: JobListingPayload,
    responseLanguage: string = "en"
) {
    const formData = new FormData();
    formData.append("cv_cache_id", cvCacheId);
    formData.append("job_offer_text", buildListingContextText(listing));
    formData.append("response_language", responseLanguage);

    const res = await fetch(`${API_BASE_URL}/match`, {
        method: "POST",
        body: formData,
    });

    if (!res.ok) {
        const errorData = await res.json().catch(() => null);
        throw new Error(errorData?.detail || "Failed to match listing");
    }

    const payload = await res.json();
    return {
        status: payload.status,
        data: {
            source: listing.source,
            title: listing.title,
            company: listing.company,
            location: listing.location,
            url: listing.url,
            posted_at_text: listing.posted_at_text,
            summary: listing.summary,
            analysis_source: "mock_listing_context",
            ...payload.data,
            job_description: listing.summary || "",
        } satisfies MatchListingData,
    };
}
