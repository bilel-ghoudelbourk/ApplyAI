"use client";

import { useLanguage } from "@/components/LanguageContext";

export function Footer() {
    const { t } = useLanguage();

    return (
        <footer
            className="w-full py-6 mt-auto border-t backdrop-blur-md"
            style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-card)" }}
        >
            <div
                className="max-w-5xl mx-auto px-8 flex flex-col md:flex-row items-center justify-between text-sm"
                style={{ color: "var(--text-muted)" }}
            >
                <p>© {new Date().getFullYear()} {t("footerCopy")}</p>
                <div className="flex items-center gap-4 mt-4 md:mt-0">
                    <span
                        className="transition-colors cursor-pointer hover:text-neon-purple"
                        style={{ color: "var(--text-muted)" }}
                    >
                        {t("footerPrivacy")}
                    </span>
                    <span
                        className="transition-colors cursor-pointer hover:text-neon-purple"
                        style={{ color: "var(--text-muted)" }}
                    >
                        {t("footerTerms")}
                    </span>
                </div>
            </div>
        </footer>
    );
}
