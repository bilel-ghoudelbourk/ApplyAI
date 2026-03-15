"use client";

import React, { createContext, useContext, ReactNode, useSyncExternalStore } from "react";
import { translations } from "@/lib/translations";

type Lang = "fr" | "en";

type LanguageContextType = {
    lang: Lang;
    toggleLang: () => void;
    t: (key: keyof typeof translations.fr) => string;
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);
const LANGUAGE_STORAGE_KEY = "applyai-lang";
const languageListeners = new Set<() => void>();

function emitLanguageChange() {
    languageListeners.forEach((listener) => listener());
}

function subscribeLanguage(listener: () => void) {
    languageListeners.add(listener);
    const handleStorage = (event: StorageEvent) => {
        if (event.key === null || event.key === LANGUAGE_STORAGE_KEY) {
            listener();
        }
    };
    window.addEventListener("storage", handleStorage);
    return () => {
        languageListeners.delete(listener);
        window.removeEventListener("storage", handleStorage);
    };
}

function getLanguageSnapshot(): Lang {
    if (typeof window === "undefined") {
        return "fr";
    }
    const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return stored === "fr" || stored === "en" ? stored : "fr";
}

export function LanguageProvider({ children }: { children: ReactNode }) {
    const lang = useSyncExternalStore<Lang>(subscribeLanguage, getLanguageSnapshot, () => "fr");

    const toggleLang = () => {
        const next: Lang = lang === "fr" ? "en" : "fr";
        localStorage.setItem(LANGUAGE_STORAGE_KEY, next);
        emitLanguageChange();
    };

    const t = (key: keyof typeof translations.fr): string => {
        return translations[lang][key] ?? translations.fr[key];
    };

    return (
        <LanguageContext.Provider value={{ lang, toggleLang, t }}>
            {children}
        </LanguageContext.Provider>
    );
}

export function useLanguage() {
    const context = useContext(LanguageContext);
    if (!context) throw new Error("useLanguage must be used within a LanguageProvider");
    return context;
}
