import type { Metadata } from "next";
import { CheckCircle2, Download, FileJson, KeyRound, Lock, ScanSearch, ShieldCheck, Sparkles, WandSparkles } from "lucide-react";
import { HeroPreview } from "@/components/landing/HeroPreview";
import { LandingNavbar } from "@/components/landing/Navbar";
import { HeroActions } from "@/components/landing/HeroActions";

export const metadata: Metadata = {
  title: "ResumeForge — Truthful resume tailoring with ATS scoring",
  description: "Tailor your resume to any job posting with ATS keyword scoring. Generate free with standard profile matching or bring your own AI key for intelligent rewrites.",
  alternates: { canonical: "/" },
};

const FEATURES = [
  {
    icon: Sparkles,
    badge: "Free forever",
    title: "Truthful Tailoring (0 AI Keys)",
    body: "Generate tailored resumes immediately using deterministic keyword matching and verified facts directly from your profile—zero hallucination risk and no AI keys needed.",
  },
  {
    icon: ScanSearch,
    badge: "ATS analysis",
    title: "Real-time ATS Scoring",
    body: "See exactly which job description keywords your resume matches and which ones are missing, complete with readability and formatting compliance checks.",
  },
  {
    icon: KeyRound,
    badge: "Bring-your-own-key",
    title: "Optional AI Provider Keys",
    body: "Optionally connect your personal OpenAI, Anthropic, or Gemini key for AI bullet rephrasing. Stored keys are encrypted with AES-256-GCM.",
  },
  {
    icon: Download,
    badge: "Instant exports",
    title: "PDF & Markdown Downloads",
    body: "Export ATS-compliant single-column resumes directly to PDF or raw Markdown with one click, ready to apply immediately.",
  },
  {
    icon: FileJson,
    badge: "Portability",
    title: "JSON In, JSON Out",
    body: "Export your entire career profile to portable JSON or import an existing profile anytime. Your career data is 100% yours and never vendor locked.",
  },
  {
    icon: ShieldCheck,
    badge: "Privacy first",
    title: "Private & Secure",
    body: "All data and credentials are kept securely under your account. Session tokens and keys are never shared across users or third parties.",
  },
];

const STEPS = [
  {
    step: "01",
    title: "Build or import your profile",
    body: "Fill out your career history, skills, and projects, or upload your structured profile JSON in seconds.",
  },
  {
    step: "02",
    title: "Paste any target job posting",
    body: "Paste the job description from LinkedIn, Indeed, or company sites into Resume Studio.",
  },
  {
    step: "03",
    title: "Get your tailored resume & ATS score",
    body: "Inspect matched keywords, export as PDF or Markdown, and apply with confidence.",
  },
];

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "ResumeForge",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  description: "Tailor your resume to any job description with ATS keyword scoring, using standard truthful matching or your own AI key.",
  offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
};

export default function Landing() {
  return (
    <div className="min-h-screen bg-zinc-50/50">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <LandingNavbar />

      <main className="space-y-20 pb-20">
        {/* Hero Section */}
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 pt-10 md:px-6 lg:grid-cols-2 lg:pt-16">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs font-medium text-zinc-700 shadow-xs">
              <span className="flex size-2 rounded-full bg-emerald-500" />
              <span>Free Truthful Matching · Optional AI Keys</span>
            </div>

            <h1 className="text-4xl font-bold tracking-tight text-zinc-900 sm:text-5xl sm:leading-tight">
              A resume tailored to the exact job you want
            </h1>

            <p className="max-w-lg text-base leading-relaxed text-zinc-600 sm:text-lg">
              Paste any job description. ResumeForge instantly aligns your verified skills, scores your ATS keyword coverage, and generates ready-to-send resumes.
            </p>

            <HeroActions />

            <div className="pt-2 flex flex-wrap items-center gap-4 text-xs text-zinc-500">
              <span className="flex items-center gap-1">
                <CheckCircle2 className="size-3.5 text-emerald-600" /> No AI key required
              </span>
              <span className="flex items-center gap-1">
                <CheckCircle2 className="size-3.5 text-emerald-600" /> Single-column ATS format
              </span>
              <span className="flex items-center gap-1">
                <CheckCircle2 className="size-3.5 text-emerald-600" /> Instant PDF download
              </span>
            </div>
          </div>

          <div className="relative">
            <div className="absolute -inset-1 rounded-xl bg-linear-to-r from-zinc-200 to-zinc-100 opacity-60 blur-xs" />
            <div className="relative">
              <HeroPreview />
            </div>
          </div>
        </section>

        {/* How It Works Section */}
        <section className="mx-auto max-w-6xl px-4 md:px-6">
          <div className="border-t border-zinc-200 pt-14">
            <div className="mb-10 text-center">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                How It Works
              </h2>
              <p className="mt-2 text-2xl font-bold tracking-tight text-zinc-900 sm:text-3xl">
                From job posting to interview-ready resume in 3 steps
              </p>
            </div>

            <div className="grid gap-6 md:grid-cols-3">
              {STEPS.map((s) => (
                <div
                  key={s.step}
                  className="relative rounded-xl border border-zinc-200 bg-white p-6 shadow-xs"
                >
                  <span className="text-3xl font-extrabold tracking-tight text-zinc-200">
                    {s.step}
                  </span>
                  <h3 className="mt-3 text-base font-semibold text-zinc-900">{s.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-zinc-600">{s.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section aria-labelledby="features" className="mx-auto max-w-6xl px-4 md:px-6">
          <div className="border-t border-zinc-200 pt-14">
            <div className="mb-10">
              <h2 id="features" className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                Capabilities
              </h2>
              <p className="mt-2 text-2xl font-bold tracking-tight text-zinc-900 sm:text-3xl">
                Engineered for speed, privacy, and applicant tracking systems
              </p>
            </div>

            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map(({ icon: Icon, badge, title, body }) => (
                <article
                  key={title}
                  className="flex flex-col justify-between rounded-xl border border-zinc-200 bg-white p-6 shadow-xs transition hover:border-zinc-300"
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <div className="flex size-9 items-center justify-center rounded-lg bg-zinc-100 text-zinc-800">
                        <Icon className="size-5" />
                      </div>
                      <span className="rounded-full bg-zinc-100 px-2.5 py-0.5 text-[11px] font-medium text-zinc-600">
                        {badge}
                      </span>
                    </div>
                    <h3 className="mt-4 text-base font-semibold text-zinc-900">{title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-zinc-600">{body}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="mx-auto max-w-6xl border-t border-zinc-200 px-4 pt-8 text-center text-xs text-zinc-500 md:px-6">
          <p>© {new Date().getFullYear()} ResumeForge. Built with truthful tailoring and open standards.</p>
        </footer>
      </main>
    </div>
  );
}
