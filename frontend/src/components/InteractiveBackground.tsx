"use client";

import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { useEffect, useRef } from "react";
import { useBackground } from "./BackgroundContext";
import { useTheme } from "./ThemeContext";

export function InteractiveGrid() {
    const { isInteractive } = useBackground();
    const { theme } = useTheme();
    const containerRef = useRef<HTMLDivElement>(null);

    // Initial position far away to avoid initial glitch
    const mouseX = useMotionValue(-1000);
    const mouseY = useMotionValue(-1000);

    const smoothX = useSpring(mouseX, { stiffness: 100, damping: 25 });
    const smoothY = useSpring(mouseY, { stiffness: 100, damping: 25 });
    const glowX = useTransform(smoothX, (x) => x - 192);
    const glowY = useTransform(smoothY, (y) => y - 192);

    useEffect(() => {

        const handleMouseMove = (e: MouseEvent) => {
            if (!isInteractive) {
                mouseX.set(-1000);
                mouseY.set(-1000);
                return;
            }
            mouseX.set(e.clientX);
            mouseY.set(e.clientY);
        };

        window.addEventListener("mousemove", handleMouseMove);

        return () => {
            window.removeEventListener("mousemove", handleMouseMove);
        };
    }, [mouseX, mouseY, isInteractive]);

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1.5 }}
            ref={containerRef}
            className="fixed inset-0 z-0 pointer-events-none overflow-hidden will-change-opacity"
        >
            {/* The Animated Mesh Gradient Background (Fully unmounted in Dark Mode for 0% CPU usage) */}
            {theme === "light" && (
                <div className="absolute inset-0 will-change-transform">
                    <div className="absolute inset-0 bg-[#f8f8fb]" />
                    <motion.div
                        animate={{ x: [0, 50, -50, 0], y: [0, -50, 50, 0] }}
                        transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
                        className="absolute top-0 left-0 w-[80vw] h-[80vh] bg-blue-400/10 rounded-full blur-[100px] will-change-transform"
                    />
                    <motion.div
                        animate={{ x: [0, -60, 60, 0], y: [0, 60, -60, 0] }}
                        transition={{ duration: 25, repeat: Infinity, ease: "easeInOut", delay: 2 }}
                        className="absolute top-[20%] right-[-10%] w-[70vw] h-[70vh] bg-purple-400/10 rounded-full blur-[100px] will-change-transform"
                    />
                    <motion.div
                        animate={{ x: [0, 40, -40, 0], y: [0, 70, -70, 0] }}
                        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut", delay: 4 }}
                        className="absolute bottom-[-10%] left-[20%] w-[90vw] h-[60vh] bg-pink-400/10 rounded-full blur-[100px] will-change-transform"
                    />
                    <motion.div
                        animate={{ x: [0, -30, 30, 0], y: [0, -40, 40, 0] }}
                        transition={{ duration: 18, repeat: Infinity, ease: "easeInOut", delay: 1 }}
                        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60vw] h-[60vh] bg-indigo-400/10 rounded-full blur-[100px] will-change-transform"
                    />
                </div>
            )}

            {/* The Static Grid Layer - Architect Grid (Ultra fast CSS) */}
            <div
                className="absolute inset-0 opacity-40 pointer-events-none will-change-transform"
                style={{
                    backgroundImage: `linear-gradient(to right, ${theme === "dark" ? "rgba(255,255,255,0.04)" : "rgba(17,17,24,0.03)"} 1px, transparent 1px),
                                      linear-gradient(to bottom, ${theme === "dark" ? "rgba(255,255,255,0.04)" : "rgba(17,17,24,0.03)"} 1px, transparent 1px)`,
                    backgroundSize: "40px 40px"
                }}
            />

            {isInteractive && (
                <motion.div
                    className="absolute w-96 h-96 rounded-full blur-[100px] pointer-events-none will-change-transform"
                    style={{
                        x: glowX,
                        y: glowY,
                        backgroundColor: theme === "light" ? "rgba(157, 0, 255, 0.12)" : "rgba(157, 0, 255, 0.22)",
                    }}
                />
            )}
        </motion.div>
    );
}
