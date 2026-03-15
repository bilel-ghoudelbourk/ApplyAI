"use client";

import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, Sparkles, CheckCircle, Search, Target } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { uploadCVPdf, CVMetadata } from "@/lib/api";
import { cn } from "@/lib/utils";
import { MatchOfferPanel } from "@/components/MatchOfferPanel";
import { SearchJobsPanel } from "@/components/SearchJobsPanel";
import { SearchByCVPanel } from "@/components/SearchByCVPanel";
import { useBackground } from "@/components/BackgroundContext";
import { useLanguage } from "@/components/LanguageContext";
import { useTheme } from "@/components/ThemeContext";

export default function Home() {
  const { setInteractive } = useBackground();
  const { t } = useLanguage();
  const { theme } = useTheme();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [cvCacheId, setCvCacheId] = useState<string | null>(null);
  const [cvMetadata, setCvMetadata] = useState<CVMetadata | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const [resetKey, setResetKey] = useState(0);
  const [activeWorkflow, setActiveWorkflow] = useState<"match" | "search" | "search_cv" | null>(null);

  useEffect(() => {
    setInteractive(!cvCacheId);
  }, [cvCacheId, setInteractive]);

  useEffect(() => {
    const handleReset = () => {
      setFile(null);
      setCvCacheId(null);
      setCvMetadata(null);
      setIsUploading(false);
      setActiveWorkflow(null);
      setResetKey(prev => prev + 1);
      window.scrollTo(0, 0);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    };
    window.addEventListener("resetApp", handleReset);
    return () => window.removeEventListener("resetApp", handleReset);
  }, []);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    setIsUploading(true);

    try {
      const resp = await uploadCVPdf(selectedFile);
      if (resp.status === "success") {
        setCvCacheId(resp.data.cv_cache_id);
        setCvMetadata(resp.data.cv_metadata);
      }
    } catch (err) {
      console.error(err);
      alert(t("uploadFailed"));
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <motion.div
      key={`main-container-${resetKey}`}
      initial={{ opacity: 0, scale: 0.98, filter: "blur(10px)" }}
      animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
      transition={{ duration: 1.5, ease: "easeOut" }}
      className="flex flex-col items-center justify-center w-full min-h-[80vh] px-4"
    >
      <AnimatePresence mode="wait">
        {!cvCacheId ? (
          <motion.div
            key="upload-view"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.05, filter: "blur(10px)" }}
            transition={{ duration: 0.5 }}
            className="flex flex-col items-center w-full max-w-2xl"
          >
            {/* Central Icon / Logo Aesthetic */}
            <div className="mb-8 relative">
              <div className={cn("absolute inset-0 bg-neon-purple rounded-full blur-[40px] theme-glow", theme === "dark" ? "opacity-40 animate-pulse" : "opacity-0")} />
              <div
                className="relative p-6 rounded-full border shadow-2xl backdrop-blur-md"
                style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
              >
                <Sparkles className="w-12 h-12 drop-shadow-[0_0_15px_rgba(255,255,255,0.7)]" style={{ color: "var(--text-primary)" }} />
              </div>
            </div>

            {/* Hero Text */}
            <div className="text-center mb-12">
              <h1 className={cn("text-5xl md:text-6xl font-bold tracking-tight mb-4", theme === "dark" && "glow-text-purple")} style={{ color: "var(--text-primary)" }}>
                ApplyAI
              </h1>
              <p className="text-lg font-light tracking-wide" style={{ color: "var(--text-secondary)" }}>
                {t("heroSubtitle")}
              </p>
            </div>

            <button
              onClick={handleUploadClick}
              disabled={isUploading}
              className="relative group cursor-pointer w-auto disabled:opacity-50 disabled:cursor-not-allowed mt-2"
            >
              <div className={cn(
                "absolute -inset-1 bg-gradient-to-r from-neon-purple to-neon-pink rounded-full blur-xl theme-glow will-change-transform group-hover:scale-105",
                theme === "dark" ? "opacity-70 group-hover:opacity-100" : "opacity-0"
              )} />
              <div
                className="relative flex items-center gap-3 px-8 py-4 rounded-full border overflow-hidden"
                style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
              >
                <div className="absolute inset-0 bg-gradient-to-tr from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

                {isUploading ? (
                  <div className="w-6 h-6 border-2 border-t-neon-purple rounded-full animate-spin" style={{ borderColor: "var(--border-strong)", borderTopColor: "#9d00ff" }} />
                ) : (
                  <UploadCloud className="w-6 h-6 text-neon-purple transition-transform duration-300 group-hover:-translate-y-1" />
                )}

                <span className="text-lg font-medium tracking-wide" style={{ color: "var(--text-primary)" }}>
                  {isUploading ? t("uploading") : t("uploadButton")}
                </span>
              </div>
            </button>
          </motion.div>
        ) : (
          <motion.div
            key="workflow-view"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="w-full max-w-2xl flex flex-col items-center"
          >
            <div
              className="flex items-center gap-3 mb-8 px-6 py-2 rounded-full border"
              style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)", color: "var(--text-secondary)" }}
            >
              <CheckCircle className="w-4 h-4 text-neon-purple" />
              <span className="text-sm font-medium">{file?.name} {t("cvValidated")}</span>
            </div>

            <div
              className="flex w-full mb-8 relative border rounded-2xl overflow-hidden p-1 shadow-2xl"
              style={{ backgroundColor: "var(--bg)", borderColor: "var(--border)" }}
            >
              <div
                className={cn(
                  "absolute top-1 bottom-1 w-[calc(33.333%-4px)] rounded-xl transition-all duration-300 pointer-events-none",
                  activeWorkflow === "search_cv"
                      ? "left-[calc(66.666%+2px)]"
                      : activeWorkflow === "search"
                      ? "left-[calc(33.333%+2px)]"
                      : "left-1"
                )}
                style={{ backgroundColor: "var(--surface)" }}
              />

              <button
                onClick={() => setActiveWorkflow("match")}
                className={cn(
                  "relative z-10 flex-1 flex flex-col items-center justify-center p-4 sm:p-6 gap-2 transition-colors rounded-xl"
                )}
                style={{ color: activeWorkflow === "match" ? "var(--text-primary)" : "var(--text-muted)" }}
              >
                <Target className="w-6 h-6 mb-2" />
                <span className="font-bold text-base sm:text-lg text-center leading-tight">{t("workflowMatchTitle")}</span>
                <span className="text-[10px] sm:text-xs text-center px-1 sm:px-4 hidden sm:block">{t("workflowMatchDesc")}</span>
              </button>

              <button
                onClick={() => setActiveWorkflow("search")}
                className={cn(
                  "relative z-10 flex-1 flex flex-col items-center justify-center p-4 sm:p-6 gap-2 transition-colors rounded-xl border-l border-r"
                )}
                style={{
                    color: activeWorkflow === "search" ? "var(--text-primary)" : "var(--text-muted)",
                    borderLeftColor: "var(--border-muted)",
                    borderRightColor: "var(--border-muted)"
                }}
              >
                <Search className="w-6 h-6 mb-2" />
                <span className="font-bold text-base sm:text-lg text-center leading-tight">{t("workflowSearchTitle")}</span>
                <span className="text-[10px] sm:text-xs text-center px-1 sm:px-4 hidden sm:block">{t("workflowSearchDesc")}</span>
              </button>

              <button
                onClick={() => setActiveWorkflow("search_cv")}
                className={cn(
                  "relative z-10 flex-1 flex flex-col items-center justify-center p-4 sm:p-6 gap-2 transition-colors rounded-xl"
                )}
                style={{ color: activeWorkflow === "search_cv" ? "var(--text-primary)" : "var(--text-muted)" }}
              >
                <Sparkles className="w-6 h-6 mb-2" />
                <span className="font-bold text-base sm:text-lg text-center leading-tight">{t("workflowSearchCVTitle")}</span>
                <span className="text-[10px] sm:text-xs text-center px-1 sm:px-4 hidden sm:block">{t("workflowSearchCVDesc")}</span>
              </button>
            </div>

            {activeWorkflow === "match" ? (
              <MatchOfferPanel cvCacheId={cvCacheId} />
            ) : activeWorkflow === "search" ? (
              <SearchJobsPanel cvCacheId={cvCacheId} />
            ) : activeWorkflow === "search_cv" ? (
              <SearchByCVPanel cvCacheId={cvCacheId} initialMetadata={cvMetadata || undefined} />
            ) : (
              <div className="text-center mt-12 animate-pulse font-medium" style={{ color: "var(--text-muted)" }}>
                {t("selectWorkflow")}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        className="hidden"
        accept=".pdf,.docx,.txt"
      />
    </motion.div>
  );
}
