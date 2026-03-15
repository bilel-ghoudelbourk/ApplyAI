"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
    AlertCircle,
    Briefcase,
    Calendar,
    CheckCircle,
    ChevronRight,
    ExternalLink,
    FileText,
    MapPin,
    Search,
    Sparkles,
} from "lucide-react";
import {
    AVAILABLE_SEARCH_SOURCES,
    generateCoverLetter,
    getSearchSourceLabel,
    JobListing,
    MatchListingData,
    matchListing,
    searchJobs,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/components/LanguageContext";
import { useTheme } from "@/components/ThemeContext";

type SearchJobsPanelProps = {
    cvCacheId: string;
};

const AVAILABLE_SOURCES = [...AVAILABLE_SEARCH_SOURCES];

function buildListingContextText(listing: JobListing, matchData?: MatchListingData) {
    return [
        `Title: ${listing.title}`,
        `Company: ${listing.company}`,
        `Location: ${listing.location}`,
        listing.summary ? `Summary: ${listing.summary}` : "",
        matchData?.job_title ? `Structured title: ${matchData.job_title}` : "",
        matchData?.job_company ? `Structured company: ${matchData.job_company}` : "",
        matchData?.job_description ? `Description: ${matchData.job_description}` : "",
        matchData?.job_required_skills?.length ? `Required skills: ${matchData.job_required_skills.join(", ")}` : "",
        `Source URL: ${listing.url}`,
    ]
        .filter(Boolean)
        .join("\n");
}

export function SearchJobsPanel({ cvCacheId }: SearchJobsPanelProps) {
    const { t, lang } = useLanguage();
    const { theme } = useTheme();
    const [keywords, setKeywords] = useState("");
    const [location, setLocation] = useState("");
    const [postedWithin, setPostedWithin] = useState("7d");
    const [sources, setSources] = useState<string[]>([...AVAILABLE_SOURCES]);
    const [limit, setLimit] = useState(20);

    const [isSearching, setIsSearching] = useState(false);
    const [jobs, setJobs] = useState<JobListing[]>([]);
    const [searchFeedback, setSearchFeedback] = useState<{ hasSourceErrors: boolean } | null>(null);

    const [matchingJobIdx, setMatchingJobIdx] = useState<number | null>(null);
    const [matchedResults, setMatchedResults] = useState<Record<number, MatchListingData>>({});

    const [generatingLetterIdx, setGeneratingLetterIdx] = useState<number | null>(null);
    const [coverLetters, setCoverLetters] = useState<Record<number, string>>({});

    const toggleSource = (source: string) => {
        setSearchFeedback(null);
        setSources((prev) => (prev.includes(source) ? prev.filter((item) => item !== source) : [...prev, source]));
    };

    const toggleAllSources = () => {
        setSearchFeedback(null);
        setSources((prev) => (prev.length === AVAILABLE_SOURCES.length ? [] : [...AVAILABLE_SOURCES]));
    };

    const handleSearch = async () => {
        if (!keywords || !location || sources.length === 0) {
            alert(t("searchFailed") + ": Please fill keywords, location and select at least one source.");
            return;
        }

        setIsSearching(true);
        setSearchFeedback(null);
        try {
            const resp = await searchJobs(keywords, location, postedWithin, sources, lang, limit);
            if (resp.status === "success") {
                const results = resp.data.results || [];
                const hasSourceErrors = Object.keys(resp.data.errors || {}).length > 0;
                setJobs(results);
                setMatchedResults({});
                setCoverLetters({});
                setSearchFeedback(results.length === 0 ? { hasSourceErrors } : null);
            }
        } catch (err) {
            console.error(err);
            setSearchFeedback(null);
            alert(t("searchFailed"));
        } finally {
            setIsSearching(false);
        }
    };

    const handleMatch = async (listing: JobListing, index: number) => {
        setMatchingJobIdx(index);
        try {
            const resp = await matchListing(cvCacheId, listing, lang);
            if (resp.status === "success") {
                setMatchedResults((prev) => ({ ...prev, [index]: resp.data as MatchListingData }));
            }
        } catch (err) {
            console.error(err);
            alert(t("analysisFailed2"));
        } finally {
            setMatchingJobIdx(null);
        }
    };



    const handleGenerateLetter = async (listing: JobListing, index: number) => {
        setGeneratingLetterIdx(index);
        try {
            const resp = await generateCoverLetter(
                cvCacheId,
                buildListingContextText(listing, matchedResults[index])
            );
            if (resp.status === "success") {
                setCoverLetters((prev) => ({ ...prev, [index]: resp.data.cover_letter }));
            }
        } catch (err) {
            console.error(err);
            alert(t("letterFailed2"));
        } finally {
            setGeneratingLetterIdx(null);
        }
    };

    if (jobs.length > 0) {
        return (
            <motion.div
                key="search-results"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full flex flex-col gap-6"
            >
                <div className="flex items-center justify-between mb-2">
                    <h3
                        className={cn("text-2xl font-bold", theme === "dark" && "glow-text-purple")}
                        style={{ color: "var(--text-primary)" }}
                    >
                        {t("searchResultsTitle")} ({jobs.length})
                    </h3>
                    <button
                        onClick={() => setJobs([])}
                        className="transition-colors text-sm uppercase tracking-widest hover:text-neon-purple"
                        style={{ color: "var(--text-muted)" }}
                    >
                        {t("newSearch")}
                    </button>
                </div>

                <div className="flex flex-col gap-4">
                    {jobs.map((job, idx) => {
                        const isMatchingThis = matchingJobIdx === idx;
                        const isGeneratingThis = generatingLetterIdx === idx;
                        const matchData = matchedResults[idx];
                        const letter = coverLetters[idx];

                        return (
                            <div
                                key={`${job.url}-${idx}`}
                                className={cn(
                                    "border rounded-2xl p-6 backdrop-blur-md transition-all",
                                    matchData && theme === "dark" && "shadow-[0_0_30px_rgba(157,0,255,0.1)]",
                                    !matchData && theme === "dark" && "hover:border-neon-purple/50",
                                    !matchData && theme === "light" && "hover:shadow-[0_4px_20px_rgba(0,0,0,0.04)]"
                                )}
                                style={{
                                    backgroundColor: "var(--surface-card)",
                                    borderColor: matchData ? "var(--border-focus)" : "var(--border)",
                                }}
                            >
                                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                                    <div className="flex-1">
                                        <h4
                                            className="text-xl font-bold mb-1 group-hover:text-neon-pink transition-colors"
                                            style={{ color: "var(--text-primary)" }}
                                        >
                                            {job.title}
                                        </h4>
                                        <div
                                            className="flex flex-wrap items-center gap-3 text-sm mb-4"
                                            style={{ color: "var(--text-secondary)" }}
                                        >
                                            <span className="flex items-center gap-1">
                                                <Briefcase className="w-3.5 h-3.5" /> {job.company}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <MapPin className="w-3.5 h-3.5" /> {job.location}
                                            </span>
                                            <span
                                                className="px-2 py-0.5 rounded-full uppercase text-xs"
                                                style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}
                                            >
                                                {getSearchSourceLabel(job.source, lang)}
                                            </span>
                                        </div>
                                        {job.summary && (
                                            <p className="text-sm line-clamp-2" style={{ color: "var(--text-muted)" }}>
                                                {job.summary}
                                            </p>
                                        )}
                                    </div>

                                    <div className="flex flex-col gap-3 min-w-[160px]">
                                        <a
                                            href={job.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="flex items-center justify-center gap-2 p-3 rounded-lg border text-sm font-medium transition-colors hover:border-neon-purple"
                                            style={{
                                                backgroundColor: "var(--surface)",
                                                borderColor: "var(--border)",
                                                color: "var(--text-primary)",
                                            }}
                                        >
                                            <ExternalLink className="w-4 h-4" /> {t("viewOffer")}
                                        </a>



                                        {!matchData && (
                                            <button
                                                onClick={() => handleMatch(job, idx)}
                                                disabled={isMatchingThis}
                                                className={cn(
                                                    "flex items-center justify-center gap-2 p-3 rounded-lg disabled:opacity-50 text-sm font-bold transition-all",
                                                    theme === "dark"
                                                        ? "bg-neon-purple text-white hover:bg-neon-pink shadow-[0_0_15px_rgba(157,0,255,0.4)]"
                                                        : "bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-[0_4px_15px_rgba(99,102,241,0.2)] hover:shadow-[0_6px_20px_rgba(99,102,241,0.3)] hover:opacity-90 border-transparent"
                                                )}
                                            >
                                                {isMatchingThis ? (
                                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                                ) : (
                                                    t("calculateScore")
                                                )}
                                            </button>
                                        )}
                                    </div>
                                </div>

                                {matchData && (
                                    <motion.div
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: "auto" }}
                                        className="mt-6 pt-6 border-t flex flex-col md:flex-row gap-8 items-center md:items-start"
                                        style={{ borderColor: "var(--border)" }}
                                    >
                                        <div className="relative flex items-center justify-center w-32 h-32 shrink-0">
                                            {theme === "dark" && <div className="absolute inset-0 bg-neon-purple/10 rounded-full blur-xl" />}
                                            <svg className="absolute inset-0 w-full h-full transform -rotate-90">
                                                <circle cx="64" cy="64" r="60" fill="none" style={{ stroke: "var(--border)" }} strokeWidth="6" />
                                                <circle
                                                    cx="64"
                                                    cy="64"
                                                    r="60"
                                                    fill="none"
                                                    stroke="var(--color-neon-purple)"
                                                    strokeWidth="6"
                                                    strokeDasharray={376.99}
                                                    strokeDashoffset={376.99 - (376.99 * (matchData.match_score || 0)) / 100}
                                                    strokeLinecap="round"
                                                    className={cn(
                                                        "transition-all duration-1000 origin-center",
                                                        theme === "dark" && "drop-shadow-[0_0_8px_rgba(157,0,255,0.8)]"
                                                    )}
                                                />
                                            </svg>
                                            <div className="relative flex flex-col items-center">
                                                <span className="text-3xl font-bold" style={{ color: "var(--text-primary)" }}>
                                                    {matchData.match_score || 0}%
                                                </span>
                                            </div>
                                        </div>

                                        <div className="flex-1 w-full">

                                            
                                            {matchData.job_required_skills && (
                                                <div className="mb-4">
                                                    <h5 className="text-green-500 text-xs font-bold uppercase tracking-widest mb-3 flex items-center gap-2">
                                                        <CheckCircle className="w-3.5 h-3.5" /> {t("matchedSkills")}
                                                    </h5>
                                                    <div className="flex flex-wrap gap-2">
                                                        {matchData.job_required_skills
                                                            .filter((skill) => !matchData.missing_skills?.includes(skill))
                                                            .map((skill, skillIndex) => (
                                                                <span
                                                                    key={`${skill}-${skillIndex}`}
                                                                    className="px-2.5 py-1 bg-green-500/10 border border-green-500/20 text-green-500 rounded text-[10px] font-bold uppercase"
                                                                >
                                                                    {skill}
                                                                </span>
                                                            ))}
                                                    </div>
                                                </div>
                                            )}

                                            {matchData.missing_skills && matchData.missing_skills.length > 0 && (
                                                <div className="mb-6">
                                                    <h5 className="text-red-500 text-xs font-bold uppercase tracking-widest mb-3 flex items-center gap-2">
                                                        <AlertCircle className="w-3.5 h-3.5" /> {t("missingSkills")}
                                                    </h5>
                                                    <div className="flex flex-wrap gap-2">
                                                        {matchData.missing_skills.map((skill, skillIndex) => (
                                                            <span
                                                                key={`${skill}-${skillIndex}`}
                                                                className="px-2.5 py-1 bg-red-500/10 border border-red-500/20 text-red-500 rounded text-[10px] font-bold uppercase"
                                                            >
                                                                {skill}
                                                            </span>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            {!letter ? (
                                                <button
                                                    onClick={() => handleGenerateLetter(job, idx)}
                                                    disabled={isGeneratingThis}
                                                    className={cn(
                                                        "flex items-center justify-center gap-2 w-full md:w-auto px-6 py-3 rounded-lg font-bold tracking-wide transition-all hover:opacity-90 disabled:opacity-50",
                                                        theme === "dark"
                                                            ? "bg-gradient-to-r from-neon-purple to-neon-pink text-white"
                                                            : "bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-[0_4px_15px_rgba(99,102,241,0.2)] hover:shadow-[0_6px_20px_rgba(99,102,241,0.3)] border-transparent"
                                                    )}
                                                >
                                                    {isGeneratingThis ? (
                                                        <div className="w-4 h-4 border-2 border-white/50 border-t-white rounded-full animate-spin" />
                                                    ) : (
                                                        <Sparkles className="w-4 h-4" />
                                                    )}
                                                    {isGeneratingThis ? t("generating") : t("generateLetter")}
                                                </button>
                                            ) : (
                                                <div
                                                    className="mt-4 border rounded-xl p-4 md:p-6 leading-relaxed text-sm max-h-[300px] overflow-y-auto custom-scrollbar"
                                                    style={{
                                                        backgroundColor: "var(--surface)",
                                                        borderColor: "var(--border)",
                                                        color: "var(--text-secondary)",
                                                    }}
                                                >
                                                    <h6
                                                        className="font-bold mb-4 flex items-center gap-2"
                                                        style={{ color: "var(--text-primary)" }}
                                                    >
                                                        <FileText className="text-neon-purple w-5 h-5" /> {t("coverLetterTitle")}
                                                    </h6>
                                                    <div className="whitespace-pre-wrap">{letter}</div>
                                                </div>
                                            )}
                                        </div>
                                    </motion.div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </motion.div>
        );
    }

    return (
        <motion.div
            key="search-inputs"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="w-full flex flex-col gap-5"
        >
            <div className="flex flex-col md:flex-row gap-4">
                <div
                    className="flex-1 border rounded-xl overflow-hidden p-3 transition-colors focus-within:border-neon-purple/80 shadow-inner"
                    style={{ backgroundColor: "var(--surface-input)", borderColor: "var(--border)" }}
                >
                    <label
                        className="text-xs font-bold uppercase tracking-widest mb-2 ml-2 flex items-center gap-2"
                        style={{ color: "var(--text-primary)" }}
                    >
                        <Search className="w-3.5 h-3.5 text-neon-purple" /> {t("searchKeywordsLabel")}
                    </label>
                    <input
                        value={keywords}
                        onChange={(event) => {
                            setKeywords(event.target.value);
                            setSearchFeedback(null);
                        }}
                        placeholder={t("searchKeywordsPlaceholder")}
                        className="w-full bg-transparent border-none outline-none px-2 py-1 font-medium"
                        style={{ color: "var(--text-primary)", caretColor: "#9d00ff" }}
                        disabled={isSearching}
                    />
                </div>
                <div
                    className="flex-1 border rounded-xl overflow-hidden p-3 transition-colors focus-within:border-neon-purple/80 shadow-inner"
                    style={{ backgroundColor: "var(--surface-input)", borderColor: "var(--border)" }}
                >
                    <label
                        className="text-xs font-bold uppercase tracking-widest mb-2 ml-2 flex items-center gap-2"
                        style={{ color: "var(--text-primary)" }}
                    >
                        <MapPin className="w-3.5 h-3.5 text-neon-purple" /> {t("searchLocationLabel")}
                    </label>
                    <input
                        value={location}
                        onChange={(event) => {
                            setLocation(event.target.value);
                            setSearchFeedback(null);
                        }}
                        placeholder={t("searchLocationPlaceholder")}
                        className="w-full bg-transparent border-none outline-none px-2 py-1 font-medium"
                        style={{ color: "var(--text-primary)", caretColor: "#9d00ff" }}
                        disabled={isSearching}
                    />
                </div>
            </div>

            <div className="flex flex-col md:flex-row gap-4">
                <div
                    className="flex-1 border rounded-xl overflow-hidden p-4"
                    style={{ backgroundColor: "var(--surface-input)", borderColor: "var(--border)" }}
                >
                    <label
                        className="text-xs font-bold uppercase tracking-widest mb-4 flex items-center gap-2"
                        style={{ color: "var(--text-primary)" }}
                    >
                        <Calendar className="w-3.5 h-3.5 text-neon-purple" /> {t("searchDateLabel")}
                    </label>
                    <div className="flex flex-wrap gap-2">
                        {["24h", "7d", "30d", "all"].map((value) => (
                            <button
                                key={value}
                                onClick={() => {
                                    setPostedWithin(value);
                                    setSearchFeedback(null);
                                }}
                                className={cn(
                                    "px-4 py-2 rounded-lg text-sm font-bold transition-all border",
                                    postedWithin === value
                                        ? theme === "dark"
                                            ? "bg-neon-purple border-neon-purple text-white shadow-[0_0_20px_rgba(157,0,255,0.5)]"
                                            : "bg-white border-white text-gray-900 shadow-[0_2px_8px_rgba(0,0,0,0.06)]"
                                        : theme === "dark"
                                          ? "hover:border-neon-purple"
                                          : "hover:shadow-[0_2px_8px_rgba(0,0,0,0.04)]"
                                )}
                                style={
                                    postedWithin !== value
                                        ? { backgroundColor: "var(--surface)", borderColor: "var(--border)", color: "var(--text-secondary)" }
                                        : {}
                                }
                            >
                                {value === "24h"
                                    ? t("searchDate24h")
                                    : value === "7d"
                                      ? t("searchDate7d")
                                      : value === "30d"
                                        ? t("searchDate30d")
                                        : t("searchDateAll")}
                            </button>
                        ))}
                    </div>
                </div>

                <div
                    className="flex-1 border rounded-xl overflow-hidden p-4"
                    style={{ backgroundColor: "var(--surface-input)", borderColor: "var(--border)" }}
                >
                    <label
                        className="text-xs font-bold uppercase tracking-widest mb-4 flex items-center justify-between gap-2"
                        style={{ color: "var(--text-primary)" }}
                    >
                        <span className="flex items-center gap-2">
                            <Briefcase className="w-3.5 h-3.5 text-neon-purple" /> {t("searchLimitLabel")}
                        </span>
                        <span className="text-neon-pink font-extrabold text-sm bg-neon-pink/20 px-3 py-1 rounded-full border border-neon-pink/30">
                            {limit}
                        </span>
                    </label>
                    <div className="flex items-center gap-4 mt-2">
                        <span className="text-xs font-bold" style={{ color: "var(--text-muted)" }}>
                            1
                        </span>
                        <input
                            type="range"
                            min="1"
                            max="150"
                            value={limit}
                            onChange={(event) => {
                                setLimit(parseInt(event.target.value, 10));
                                setSearchFeedback(null);
                            }}
                            className="flex-1 accent-neon-purple h-2 rounded-lg appearance-none cursor-pointer hover:opacity-100 opacity-80 transition-opacity"
                            style={{ backgroundColor: "var(--border-strong)" }}
                            disabled={isSearching}
                        />
                        <span className="text-xs font-bold" style={{ color: "var(--text-muted)" }}>
                            150
                        </span>
                    </div>
                </div>
            </div>

            <div
                className="border rounded-xl overflow-hidden p-4"
                style={{ backgroundColor: "var(--surface-input)", borderColor: "var(--border)" }}
            >
                <label
                    className="text-xs font-bold uppercase tracking-widest mb-4 flex items-center gap-2"
                    style={{ color: "var(--text-primary)" }}
                >
                    <ChevronRight className="w-3.5 h-3.5 text-neon-purple" /> {t("searchSourcesLabel")}
                </label>
                <div className="flex flex-wrap gap-2">
                    <button
                        onClick={toggleAllSources}
                        className={cn(
                            "px-4 py-2 rounded-lg text-sm font-bold transition-all border",
                            sources.length === AVAILABLE_SOURCES.length
                                ? theme === "dark"
                                    ? "bg-neon-purple/20 border-neon-purple text-neon-purple shadow-[0_0_15px_rgba(157,0,255,0.2)]"
                                    : "bg-white border-white text-gray-900 shadow-[0_2px_8px_rgba(0,0,0,0.06)]"
                                : theme === "dark"
                                  ? "bg-transparent hover:border-neon-purple"
                                  : "bg-transparent hover:shadow-[0_2px_8px_rgba(0,0,0,0.04)]"
                        )}
                        style={
                            sources.length !== AVAILABLE_SOURCES.length
                                ? { borderColor: "var(--border)", color: "var(--text-secondary)" }
                                : {}
                        }
                    >
                        {lang === "fr" ? "Tout" : "All"}
                    </button>
                    {AVAILABLE_SOURCES.map((source) => {
                        const active = sources.includes(source);
                        return (
                            <button
                                key={source}
                                onClick={() => toggleSource(source)}
                                className={cn(
                                    "px-4 py-2 rounded-lg text-sm font-bold transition-all border",
                                    active
                                        ? theme === "dark"
                                            ? "bg-neon-purple/20 border-neon-purple text-neon-purple shadow-[0_0_15px_rgba(157,0,255,0.2)]"
                                            : "bg-white border-white text-gray-900 shadow-[0_2px_8px_rgba(0,0,0,0.06)]"
                                        : theme === "dark"
                                          ? "bg-transparent hover:border-neon-purple"
                                          : "bg-transparent hover:shadow-[0_2px_8px_rgba(0,0,0,0.04)]"
                                )}
                                style={!active ? { borderColor: "var(--border)", color: "var(--text-secondary)" } : {}}
                            >
                                {getSearchSourceLabel(source, lang)}
                            </button>
                        );
                    })}
                </div>
            </div>

            <div
                className="rounded-xl border px-4 py-3"
                style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
                role="note"
            >
                <div className="flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 mt-0.5 shrink-0 text-sky-500" />
                    <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                        {t("searchDemoNotice")}
                    </p>
                </div>
            </div>

            <button
                onClick={handleSearch}
                disabled={isSearching}
                className={cn(
                    "mt-2 w-full font-bold disabled:opacity-50 p-4 rounded-xl transition-all flex items-center justify-center gap-2 hover:opacity-90",
                    theme === "dark"
                        ? "shadow-[0_0_20px_rgba(157,0,255,0.15)] hover:shadow-[0_0_30px_rgba(157,0,255,0.35)] disabled:shadow-none bg-gradient-to-r from-neon-purple to-neon-pink text-white"
                        : "bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-[0_4px_15px_rgba(99,102,241,0.2)] hover:shadow-[0_6px_20px_rgba(99,102,241,0.3)] disabled:shadow-none border-transparent"
                )}
            >
                {isSearching ? (
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                    <>
                        {t("searchButton")}
                        <Search className="w-5 h-5" />
                    </>
                )}
            </button>

            {searchFeedback && (
                <div
                    className="rounded-xl border px-4 py-3"
                    style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
                    role="status"
                    aria-live="polite"
                >
                    <div className="flex items-start gap-3">
                        <AlertCircle className="w-5 h-5 mt-0.5 shrink-0 text-amber-500" />
                        <div className="flex flex-col gap-1 text-sm" style={{ color: "var(--text-secondary)" }}>
                            <p className="font-semibold" style={{ color: "var(--text-primary)" }}>
                                {t("noSearchResultsTitle")}
                            </p>
                            <p>{t("noSearchResultsHint")}</p>
                            {searchFeedback.hasSourceErrors && <p>{t("searchSourceErrorsHint")}</p>}
                        </div>
                    </div>
                </div>
            )}
        </motion.div>
    );
}
