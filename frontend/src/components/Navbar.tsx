"use client";

import { motion } from "framer-motion";
import { Sparkles, Globe, Sun, Moon, Home } from "lucide-react";
import { useTheme } from "@/components/ThemeContext";
import { useLanguage } from "@/components/LanguageContext";

export function Navbar() {
    const { theme, toggleTheme } = useTheme();
    const { lang, toggleLang } = useLanguage();

    return (
        <motion.nav
            initial={{ y: -10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 1, delay: 0.5 }}
            className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-5"
        >
            <button
                type="button"
                onClick={() => {
                    window.dispatchEvent(new Event("resetApp"));
                }}
                className="flex items-center gap-3 group"
            >
                <Sparkles className="w-6 h-6 text-neon-purple group-hover:text-neon-pink transition-colors" />
                <span className="font-bold text-xl tracking-wider uppercase" style={{ color: "var(--text-primary)" }}>
                    ApplyAI
                </span>
            </button>

            <div className="flex items-center gap-3">
                {/* Home link */}
                <button
                    type="button"
                    onClick={() => {
                        window.dispatchEvent(new Event("resetApp"));
                    }}
                    className="flex items-center justify-center w-9 h-9 rounded-full border transition-colors duration-300 hover:text-neon-purple hover:border-neon-purple"
                    style={{
                        color: "var(--text-secondary)",
                        borderColor: "var(--border)",
                        backgroundColor: "var(--surface)",
                    }}
                    title={lang === "fr" ? "Accueil" : "Home"}
                >
                    <Home className="w-4 h-4" />
                </button>

                {/* Language toggle */}
                <button
                    onClick={toggleLang}
                    className="flex items-center gap-2 transition-colors duration-300 px-3 py-1.5 rounded-full border"
                    style={{
                        color: "var(--text-secondary)",
                        borderColor: "var(--border)",
                        backgroundColor: "var(--surface)",
                    }}
                    onMouseEnter={e => (e.currentTarget.style.color = "var(--text-primary)")}
                    onMouseLeave={e => (e.currentTarget.style.color = "var(--text-secondary)")}
                    title={lang === "fr" ? "Switch to English" : "Passer en Français"}
                >
                    <Globe className="w-4 h-4" />
                    <span className="text-sm font-bold tracking-wide">{lang.toUpperCase()}</span>
                </button>

                {/* Theme toggle */}
                <button
                    onClick={toggleTheme}
                    className="flex items-center justify-center w-9 h-9 rounded-full border transition-colors duration-300"
                    style={{
                        color: "var(--text-secondary)",
                        borderColor: "var(--border)",
                        backgroundColor: "var(--surface)",
                    }}
                    onMouseEnter={e => (e.currentTarget.style.color = "var(--text-primary)")}
                    onMouseLeave={e => (e.currentTarget.style.color = "var(--text-secondary)")}
                    title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
                >
                    <motion.div
                        key={theme}
                        initial={{ scale: 0, rotate: -90, opacity: 0 }}
                        animate={{ scale: 1, rotate: 0, opacity: 1 }}
                        exit={{ scale: 0, rotate: 90, opacity: 0 }}
                        transition={{ duration: 0.25 }}
                    >
                        {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                    </motion.div>
                </button>
            </div>
        </motion.nav>
    );
}
