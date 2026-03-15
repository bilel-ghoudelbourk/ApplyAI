"use client";

import { useState, useRef } from "react";
import { motion } from "framer-motion";
import { Crosshair, ArrowRight, FileText, CheckCircle, AlertCircle, FilePlus, Sparkles } from "lucide-react";
import { analyzeJob, AnalyzeMatchData, generateCoverLetter } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/components/LanguageContext";
import { useTheme } from "@/components/ThemeContext";

type MatchOfferPanelProps = {
    cvCacheId: string;
};

export function MatchOfferPanel({ cvCacheId }: MatchOfferPanelProps) {
    const { t, lang } = useLanguage();
    const { theme } = useTheme();
    const [jobText, setJobText] = useState("");
    const [jobFile, setJobFile] = useState<File | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [results, setResults] = useState<AnalyzeMatchData | null>(null);
    const [isGeneratingLetter, setIsGeneratingLetter] = useState(false);
    const [coverLetter, setCoverLetter] = useState<string | null>(null);

    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleAnalyze = async () => {
        if (!jobText && !jobFile) return;

        setIsAnalyzing(true);
        try {
            const resp = await analyzeJob(cvCacheId, jobText, jobFile, lang);
            if (resp.status === "success") {
                setResults(resp.data);
            }
        } catch (err) {
            console.error(err);
            alert(t("analysisFailed"));
        } finally {
            setIsAnalyzing(false);
        }
    };

    const handleGenerateLetter = async () => {
        setIsGeneratingLetter(true);
        try {
            const resp = await generateCoverLetter(cvCacheId, jobText, jobFile);
            if (resp.status === "success") {
                setCoverLetter(resp.data.cover_letter);
            }
        } catch (err) {
            console.error(err);
            alert(t("letterFailed"));
        } finally {
            setIsGeneratingLetter(false);
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setJobFile(file);
        }
    };

    if (results) {
        return (
            <motion.div
                key="results-view"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full flex flex-col items-center mt-8"
            >
                <h2 className={cn("text-4xl font-bold tracking-tight mb-2", theme === "dark" && "glow-text-purple")} style={{ color: "var(--text-primary)" }}>
                    {t("matchScoreTitle")}
                </h2>

                <div className="relative flex items-center justify-center w-48 h-48 my-12">
                    {theme === "dark" && <div className="absolute inset-0 bg-neon-purple/20 rounded-full blur-2xl" />}
                    <div className="absolute inset-0 border-[6px] rounded-full" style={{ borderColor: "var(--border)" }} />
                    <svg className="absolute inset-0 w-full h-full transform -rotate-90">
                        <circle
                            cx="96" cy="96" r="90"
                            fill="none"
                            stroke="var(--color-neon-purple)"
                            strokeWidth="6"
                            strokeDasharray={565.48}
                            strokeDashoffset={565.48 - (565.48 * (results.match_score || 0)) / 100}
                            strokeLinecap="round"
                            className={cn(
                                "transition-all duration-1000 origin-center",
                                theme === "dark" && "drop-shadow-[0_0_10px_rgba(157,0,255,0.8)]"
                            )}
                        />
                    </svg>
                    <div className="relative flex flex-col items-center">
                        <span className="text-5xl font-bold" style={{ color: "var(--text-primary)" }}>{results.match_score || 0}%</span>
                        <span className="text-xs uppercase tracking-widest mt-1" style={{ color: "var(--text-muted)" }}>{t("matchLabel")}</span>
                    </div>
                </div>

                {results.job_required_skills && results.job_required_skills.length > 0 && (
                    <div className="w-full mb-6">
                        <h3 className="text-green-500 text-xs font-bold uppercase tracking-widest mb-3 flex items-center gap-2">
                            <CheckCircle className="w-3.5 h-3.5" /> {t("matchedSkills")}
                        </h3>
                        <div className="flex flex-wrap gap-2">
                            {(results.job_required_skills as string[])
                                .filter(skill => !results.missing_skills?.includes(skill))
                                .map((skill, i) => (
                                    <span key={i} className="px-2.5 py-1 bg-green-500/10 border border-green-500/20 text-green-500 rounded text-[10px] font-bold uppercase">
                                        {skill}
                                    </span>
                                ))}
                            {(results.job_required_skills as string[]).filter(skill => !results.missing_skills?.includes(skill)).length === 0 && (
                                <span className="text-xs italic" style={{ color: "var(--text-muted)" }}>{t("noDirectMatch")}</span>
                            )}
                        </div>
                    </div>
                )}

                {results.missing_skills && results.missing_skills.length > 0 && (
                    <div className="w-full mb-8">
                        <h3 className="text-red-500 text-xs font-bold uppercase tracking-widest mb-3 flex items-center gap-2">
                            <AlertCircle className="w-3.5 h-3.5" /> {t("missingSkills")}
                        </h3>
                        <div className="flex flex-wrap gap-2">
                            {results.missing_skills.map((skill: string, i: number) => (
                                <span key={i} className="px-2.5 py-1 bg-red-500/10 border border-red-500/20 text-red-500 rounded text-[10px] font-bold uppercase">
                                    {skill}
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                {!coverLetter ? (
                    <button
                        onClick={handleGenerateLetter}
                        disabled={isGeneratingLetter}
                        className={cn(
                            "group relative flex items-center justify-center gap-2 w-full max-sm py-4 rounded-xl font-bold tracking-wide transition-all transform hover:scale-[1.02] active:scale-95 disabled:opacity-70 disabled:pointer-events-none",
                            theme === "dark"
                                ? "bg-gradient-to-r from-neon-purple to-neon-pink text-white"
                                : "bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-[0_4px_15px_rgba(99,102,241,0.2)] hover:shadow-[0_6px_20px_rgba(99,102,241,0.3)] border-transparent"
                        )}
                    >
                        {isGeneratingLetter ? (
                            <div className="w-5 h-5 border-2 border-white/50 border-t-white rounded-full animate-spin" />
                        ) : (
                            <Sparkles className="w-5 h-5 group-hover:animate-pulse" />
                        )}
                        {isGeneratingLetter ? t("generatingLetter") : t("generateLetterButton")}
                    </button>
                ) : (
                    <div
                        className="w-full border rounded-2xl p-8 backdrop-blur-md leading-relaxed max-h-[500px] overflow-y-auto custom-scrollbar"
                        style={{ backgroundColor: "var(--surface-card)", borderColor: "var(--border)", color: "var(--text-secondary)" }}
                    >
                        <h3 className="text-xl font-bold mb-6 flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
                            <FileText className="text-neon-purple w-6 h-6" />
                            {t("coverLetterTitle")}
                        </h3>
                        <div className="whitespace-pre-wrap">{coverLetter}</div>
                    </div>
                )}

                <button
                    onClick={() => { setResults(null); setJobText(""); setJobFile(null); setCoverLetter(null); }}
                    className="hover:text-neon-purple transition-colors mt-8 text-sm uppercase tracking-widest flex items-center gap-2"
                    style={{ color: "var(--text-muted)" }}
                >
                    {t("analyzeAnotherOffer")}
                </button>
            </motion.div>
        )
    }

    return (
        <motion.div
            key="match-inputs"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="w-full flex flex-col gap-6"
        >
            <div className="w-full relative group">
                {theme === "dark" && (
                    <div className="absolute -inset-1 bg-gradient-to-r from-neon-purple/50 to-neon-pink/50 rounded-xl blur-lg opacity-30 group-focus-within:opacity-60 transition duration-500" />
                )}
                <div
                    className={cn(
                        "relative flex flex-col border rounded-xl overflow-hidden p-3 transition-colors",
                        theme === "dark"
                            ? "focus-within:border-neon-purple/60 shadow-xl"
                            : "shadow-[0_2px_10px_rgba(0,0,0,0.03)] focus-within:shadow-[0_4px_15px_rgba(0,0,0,0.06)]"
                    )}
                    style={{ backgroundColor: "var(--surface-input)", borderColor: theme === "light" ? "var(--border)" : "var(--border-strong)" }}
                >
                    <label className="text-xs font-bold uppercase tracking-widest mb-2 ml-2 flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
                        <Crosshair className="w-3.5 h-3.5 text-neon-purple" />
                        {t("matchLabelText")}
                    </label>
                    <textarea
                        value={jobText}
                        onChange={e => setJobText(e.target.value)}
                        placeholder={t("matchPlaceholderText")}
                        className="flex-1 bg-transparent border-none outline-none px-2 py-2 min-h-[140px] resize-none custom-scrollbar"
                        style={{ color: "var(--text-primary)", caretColor: "#9d00ff" }}
                        disabled={isAnalyzing || jobFile !== null}
                    />
                </div>
            </div>

            <div className="text-center text-sm font-bold tracking-widest" style={{ color: "var(--text-muted)" }}>{t("matchOr")}</div>

            <div className="w-full">
                <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isAnalyzing || jobText.length > 0}
                    className="w-full flex items-center justify-center gap-3 py-4 rounded-xl border border-dashed transition-colors disabled:opacity-50 disabled:cursor-not-allowed group"
                    style={{
                        borderColor: "var(--border-strong)",
                        backgroundColor: "var(--surface)",
                        color: "var(--text-primary)",
                    }}
                    onMouseEnter={e => (e.currentTarget.style.borderColor = "rgba(157,0,255,0.5)")}
                    onMouseLeave={e => (e.currentTarget.style.borderColor = "var(--border-strong)")}
                >
                    {jobFile ? (
                        <>
                            <CheckCircle className="w-5 h-5 text-neon-pink" />
                            <span className="font-bold">{jobFile.name} {t("matchFileSelected")}</span>
                        </>
                    ) : (
                        <>
                            <FilePlus className="w-5 h-5 text-neon-purple group-hover:scale-110 transition-transform" />
                            <span className="font-bold">{t("matchUploadFile")}</span>
                        </>
                    )}
                </button>
                <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    className="hidden"
                    accept=".pdf,.doc,.docx,.txt"
                />
            </div>

            <button
                onClick={handleAnalyze}
                disabled={(!jobText && !jobFile) || isAnalyzing}
                className={cn(
                    "mt-4 w-full font-bold disabled:opacity-50 p-4 rounded-xl transition-all flex items-center justify-center gap-2 hover:opacity-90",
                    theme === "dark"
                        ? "shadow-[0_0_20px_rgba(157,0,255,0.15)] hover:shadow-[0_0_30px_rgba(157,0,255,0.35)] disabled:shadow-none bg-gradient-to-r from-neon-purple to-neon-pink text-white"
                        : "bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-[0_4px_15px_rgba(99,102,241,0.2)] hover:shadow-[0_6px_20px_rgba(99,102,241,0.3)] disabled:shadow-none border-transparent"
                )}
            >
                {isAnalyzing ? (
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                    <>
                        {t("matchAnalyzeButton")}
                        <ArrowRight className="w-5 h-5" />
                    </>
                )}
            </button>
        </motion.div>
    );
}
