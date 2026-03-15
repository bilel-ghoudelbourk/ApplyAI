"use client";

import React, { createContext, useContext, useEffect, ReactNode, useSyncExternalStore } from "react";

type Theme = "dark" | "light";

type ThemeContextType = {
    theme: Theme;
    toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);
const THEME_STORAGE_KEY = "applyai-theme";
const themeListeners = new Set<() => void>();

function emitThemeChange() {
    themeListeners.forEach((listener) => listener());
}

function subscribeTheme(listener: () => void) {
    themeListeners.add(listener);
    const handleStorage = (event: StorageEvent) => {
        if (event.key === null || event.key === THEME_STORAGE_KEY) {
            listener();
        }
    };
    window.addEventListener("storage", handleStorage);
    return () => {
        themeListeners.delete(listener);
        window.removeEventListener("storage", handleStorage);
    };
}

function getThemeSnapshot(): Theme {
    if (typeof window === "undefined") {
        return "dark";
    }
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    return stored === "light" || stored === "dark" ? stored : "dark";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
    const theme = useSyncExternalStore<Theme>(subscribeTheme, getThemeSnapshot, () => "dark");

    useEffect(() => {
        document.documentElement.setAttribute("data-theme", theme);
    }, [theme]);

    const toggleTheme = () => {
        const next: Theme = theme === "dark" ? "light" : "dark";
        localStorage.setItem(THEME_STORAGE_KEY, next);
        document.documentElement.setAttribute("data-theme", next);
        emitThemeChange();
    };

    return (
        <ThemeContext.Provider value={{ theme, toggleTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

export function useTheme() {
    const context = useContext(ThemeContext);
    if (!context) throw new Error("useTheme must be used within a ThemeProvider");
    return context;
}
