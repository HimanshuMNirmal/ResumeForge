import type { Metadata } from "next";
import Link from "next/link";
import { FileJson, Lock, ScanSearch } from "lucide-react";
import { HeroPreview } from "@/components/landing/HeroPreview";

export const metadata: Metadata = {
  title: "Resume tailoring with your own AI key",
  alternates: { canonical: "/" },
};

const FEATURES = [
  { icon: ScanSearch, title: "ATS keyword scoring", body: "See which keywords from the job post your resume already covers and which are missing, with suggested bullet rewrites." },
  { icon: Lock, title: "Your key, your cost", body: "Use your own OpenAI, Anthropic or Gemini key. Keys are encrypted at rest, and you can pause or delete them any time." },
  { icon: FileJson, title: "JSON in, JSON out", body: "Import your profile from a JSON file and export it whenever you like. Your data is never locked in." },
];

const jsonLd = {
  "@context": "https://schema.org", "@type": "SoftwareApplication", name: "Tailor",
  applicationCategory: "BusinessApplication", operatingSystem: "Web",
  description: "Tailor your resume to any job description with ATS keyword scoring, using your own AI provider key.",
  offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
};

export default function Landing() {
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 md:px-6">
        <span className="text-sm font-semibold tracking-tight">Tailor</span>
        <nav aria-label="Main" className="flex gap-4 text-sm text-zinc-600">
          <Link href="/profile" className="hover:text-zinc-900">Profile</Link>
          <Link href="/builder" className="rounded-md bg-zinc-900 px-3 py-1.5 text-white hover:bg-zinc-800">Open builder</Link>
        </nav>
      </header>
      <main>
        <section className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-14 md:px-6 lg:grid-cols-2">
          <div>
            <h1 className="max-w-md text-4xl font-semibold leading-tight tracking-tight">A resume that fits the job you're applying to</h1>
            <p className="mt-4 max-w-md text-zinc-600">Paste a job description. Tailor rewrites your resume from your saved profile and shows how well it matches the keywords the employer's tracking system looks for.</p>
            <div className="mt-6 flex gap-3">
              <Link href="/profile" className="rounded-md bg-zinc-900 px-4 py-2 text-sm text-white hover:bg-zinc-800">Create your profile</Link>
              <Link href="/settings/keys" className="rounded-md border border-zinc-300 px-4 py-2 text-sm hover:bg-white">Add an API key</Link>
            </div>
          </div>
          <HeroPreview />
        </section>
        <section aria-labelledby="features" className="mx-auto max-w-6xl px-4 pb-20 md:px-6">
          <h2 id="features" className="sr-only">Features</h2>
          <div className="grid gap-4 md:grid-cols-3">
            {FEATURES.map(({ icon: I, title, body }) => (
              <article key={title} className="rounded-lg border border-zinc-200 bg-white p-5">
                <I className="size-5 text-zinc-700" />
                <h3 className="mt-3 text-sm font-medium">{title}</h3>
                <p className="mt-1 text-sm text-zinc-600">{body}</p>
              </article>
            ))}
          </div>
        </section>
      </main>
    </>
  );
}
