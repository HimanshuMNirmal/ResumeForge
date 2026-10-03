import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { Providers } from "./providers";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "https://example.com";

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: { default: "Resume tailoring with your own AI key", template: "%s · Tailor" },
  description: "Paste a job description and get a resume tailored to it, with an ATS keyword score. Bring your own OpenAI, Anthropic or Gemini key.",
  openGraph: { type: "website", siteName: "Tailor", title: "Resume tailoring with your own AI key",
    description: "Tailored resumes with ATS keyword scoring. Your keys stay encrypted.", url: SITE },
  twitter: { card: "summary_large_image", title: "Resume tailoring with your own AI key",
    description: "Tailored resumes with ATS keyword scoring." },
  robots: { index: true, follow: true },
};
export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#fafafa" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-zinc-50 font-sans text-zinc-900 antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
