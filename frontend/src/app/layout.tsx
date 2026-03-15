import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

import { Navbar } from "@/components/Navbar";
import { BackgroundProvider } from "@/components/BackgroundContext";
import { InteractiveGrid } from "@/components/InteractiveBackground";
import { ThemeProvider } from "@/components/ThemeContext";
import { LanguageProvider } from "@/components/LanguageContext";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "ApplyAI | Intelligent Application Matcher",
  description: "Advanced AI Matching for CVs and Job Descriptions",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="dark">
      <body className={`${inter.variable} font-sans antialiased`} style={{ color: "var(--text-primary)", backgroundColor: "var(--bg)" }}>
        <ThemeProvider>
          <LanguageProvider>
            <BackgroundProvider>
              <main className="relative min-h-screen overflow-hidden flex flex-col items-center justify-center p-4">
                {/* Global Interactive Background */}
                <InteractiveGrid />

                {/* The global intense neon purple floor glow */}
                <div className="neon-floor" />

                <Navbar />

                <div className="relative z-10 w-full max-w-5xl mx-auto flex flex-col items-center justify-center pt-24 pb-12">
                  {children}
                </div>
              </main>
            </BackgroundProvider>
          </LanguageProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
