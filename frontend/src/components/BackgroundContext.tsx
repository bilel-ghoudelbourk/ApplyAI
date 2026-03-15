"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";

type BackgroundContextType = {
    isInteractive: boolean;
    setInteractive: (value: boolean) => void;
};

const BackgroundContext = createContext<BackgroundContextType | undefined>(undefined);

export function BackgroundProvider({ children }: { children: ReactNode }) {
    const [isInteractive, setInteractive] = useState(true);

    return (
        <BackgroundContext.Provider value={{ isInteractive, setInteractive }}>
            {children}
        </BackgroundContext.Provider>
    );
}

export function useBackground() {
    const context = useContext(BackgroundContext);
    if (!context) {
        throw new Error("useBackground must be used within a BackgroundProvider");
    }
    return context;
}
