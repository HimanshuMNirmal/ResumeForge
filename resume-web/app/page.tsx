import type { Metadata } from "next";
import { CheckCircle2, FileDown, FileJson, FileText, KeyRound, ScanSearch, ShieldCheck, Target } from "lucide-react";
import { HeroPreview } from "@/components/landing/HeroPreview";
import { LandingNavbar } from "@/components/landing/Navbar";
import { HeroActions } from "@/components/landing/HeroActions";

export const metadata: Metadata = {
  title: "ResumeForge — Targeted resume tailoring with ATS scoring",
  description: "Tailor your resume to any job description with real-time ATS keyword matching, clean single-column formatting, and direct DOCX and PDF downloads.",
  alternates: { canonical: "/" },
};

const FEATURES = [
  {
    icon: ScanSearch,
    badge: "Keyword Analysis",
    title: "Real-time ATS Keyword Matching",
    body: "Identify precisely which hard skills and competencies the target job description requires, with clear visibility into matched and missing keywords.",
  },
  {
    icon: FileText,
    badge: "ATS Standards",
    title: "Verified Single-Column Hierarchy",
    body: "Built specifically to parse without text scramble in Workday, Greenhouse, Taleo, and Lever. Clean typographic hierarchy with zero multi-column bugs.",
  },
  {
    icon: FileDown,
    badge: "Direct Storage",
    title: "Direct S3 DOCX & PDF Downloads",
    body: "Download your finished resume instantly in editable Word (.docx) or vector PDF directly from secure cloud storage—no browser print popups.",
  },
  {
    icon: KeyRound,
    badge: "BYOK Keys",
    title: "Optional AI Provider Integration",
    body: "Optionally connect your personal OpenAI, Anthropic, or Gemini key for targeted bullet rephrasing. Stored securely with AES-256-GCM encryption.",
  },
  {
    icon: FileJson,
    badge: "Data Ownership",
    title: "Structured JSON Profile Portability",
    body: "Export your complete career profile to standard JSON anytime or import an existing profile. Your professional data remains 100% yours.",
  },
  {
    icon: ShieldCheck,
    badge: "Privacy First",
    title: "Secure & Account Isolated",
    body: "Your profile history, tailored resumes, and credentials remain private to your account. Never used for public training datasets.",
  },
];

const STEPS = [
  {
    step: "01",
    title: "Build or import career profile",
    body: "Add your career history, projects, and verified technical skills once, or import your structured JSON profile in seconds.",
  },
  {
    step: "02",
    title: "Paste any target job description",
    body: "Paste the job description from LinkedIn, Greenhouse, or any company careers page into the studio.",
  },
  {
    step: "03",
    title: "Inspect ATS match & export",
    body: "Review keyword coverage, check bullet suggestions, and download your tailored DOCX or PDF file directly.",
  },
];

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "ResumeForge",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  description: "Tailor your resume to any job description with real-time ATS keyword matching, clean formatting, and direct DOCX/PDF export.",
  offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
};

export default function Landing() {
  return (
    <div className="min-h-screen bg-zinc-50/50">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <LandingNavbar />

      <main className="space-y-16 pb-20 sm:space-y-24">
        {/* Hero Section */}
        <section className="mx-auto grid max-w-6xl items-center gap-10 px-4 pt-8 md:px-6 lg:grid-cols-2 lg:pt-16">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs font-medium text-zinc-700 shadow-xs">
              <span className="flex size-2 rounded-full bg-emerald-500" />
              <span>Verified Profiles · Direct S3 DOCX & PDF Exports</span>
            </div>

            <h1 className="text-3xl font-bold tracking-tight text-zinc-900 sm:text-5xl sm:leading-tight">
              Targeted resumes engineered for modern hiring systems
            </h1>

            <p className="max-w-lg text-base leading-relaxed text-zinc-600 sm:text-lg">
              Align your verified achievements with any job posting. Inspect real-time keyword coverage, eliminate formatting parse errors, and download interview-ready resumes directly.
            </p>

            <HeroActions />

            <div className="flex flex-wrap items-center gap-4 pt-2 text-xs text-zinc-500">
              <span className="flex items-center gap-1">
                <CheckCircle2 className="size-3.5 text-emerald-600" /> Direct DOCX & PDF downloads
              </span>
              <span className="flex items-center gap-1">
                <CheckCircle2 className="size-3.5 text-emerald-600" /> Single-column ATS format
              </span>
              <span className="flex items-center gap-1">
                <CheckCircle2 className="size-3.5 text-emerald-600" /> 100% portable JSON
              </span>
            </div>
          </div>

          <div className="relative w-full">
            <HeroPreview />
          </div>
        </section>

        {/* How It Works Section */}
        <section className="mx-auto max-w-6xl px-4 md:px-6">
          <div className="border-t border-zinc-200 pt-12 sm:pt-14">
            <div className="mb-10 text-center">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                How It Works
              </h2>
              <p className="mt-2 text-2xl font-bold tracking-tight text-zinc-900 sm:text-3xl">
                From job posting to tailored resume in 3 steps
              </p>
            </div>

            <div className="grid gap-5 md:grid-cols-3">
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
          <div className="border-t border-zinc-200 pt-12 sm:pt-14">
            <div className="mb-10">
              <h2 id="features" className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                Core Architecture
              </h2>
              <p className="mt-2 text-2xl font-bold tracking-tight text-zinc-900 sm:text-3xl">
                Built for reliability, privacy, and applicant tracking compliance
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
          <p>© 2026 ResumeForge. Precision resume tailoring for engineers and professionals.</p>
        </footer>
      </main>
    </div>
  );
}
