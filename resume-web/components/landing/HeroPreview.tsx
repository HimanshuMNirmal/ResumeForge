"use client";

import { useState } from "react";
import { Check, CheckCircle2, FileDown, Layers } from "lucide-react";
import { cn } from "@/lib/utils";

const EXAMPLES = [
  {
    id: "backend",
    role: "Senior Backend Engineer",
    company: "Stripe",
    score: 93,
    candidate: {
      name: "Alex Morgan",
      title: "Senior Software Engineer · Distributed Systems",
      contact: "San Francisco, CA · alex.morgan@email.com · github.com/alexm",
    },
    bullets: [
      "Engineered multi-region transaction pipeline in Python and Go, sustaining 14,000 req/sec with p99 latency under 28ms.",
      "Redesigned PostgreSQL materialized views and partitioning strategy, cutting query compute costs by 38%.",
      "Automated CI/CD deployment pipelines on AWS ECS/Fargate, achieving 99.99% service availability.",
    ],
    matched: ["Distributed Systems", "Python", "PostgreSQL", "AWS ECS", "High Concurrency"],
    missing: ["Kafka"],
  },
  {
    id: "fullstack",
    role: "Staff Full-Stack Architect",
    company: "Linear",
    score: 89,
    candidate: {
      name: "Maya Chen",
      title: "Staff Software Engineer · Web Architecture",
      contact: "Seattle, WA · maya.chen@email.com · linkedin.com/in/mayachen",
    },
    bullets: [
      "Architected real-time collaboration engine using Next.js 15, WebSockets, and React 19 server components.",
      "Reduced bundle size by 44% and lifted core web vitals from 68 to 98 across 400k monthly active users.",
      "Established end-to-end typed contract layer across TypeScript, GraphQL, and microservice APIs.",
    ],
    matched: ["Next.js", "TypeScript", "React", "WebSockets", "Performance Optimization"],
    missing: ["Storybook"],
  },
];

export function HeroPreview() {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const current = EXAMPLES[selectedIndex];

  return (
    <div
      className="overflow-hidden rounded-xl border border-zinc-200/90 bg-white shadow-xl shadow-zinc-900/5"
      aria-label="Interactive tailored resume preview"
    >
      {/* Studio Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-200 bg-zinc-50/80 px-3.5 py-2.5 sm:flex-nowrap">
        {/* Role Switcher Tabs */}
        <div role="tablist" aria-label="Target Role Example" className="flex items-center gap-1.5">
          {EXAMPLES.map((item, idx) => {
            const isSelected = selectedIndex === idx;
            return (
              <button
                key={item.id}
                role="tab"
                aria-selected={isSelected}
                onClick={() => setSelectedIndex(idx)}
                className={cn(
                  "rounded-md px-2.5 py-1 text-xs font-medium transition",
                  isSelected
                    ? "bg-zinc-900 text-white shadow-xs"
                    : "text-zinc-600 hover:bg-zinc-200/70 hover:text-zinc-900"
                )}
              >
                {item.role.split(" ")[0]} ({item.company})
              </button>
            );
          })}
        </div>

        {/* ATS Score Indicator */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-800">
            <span className="size-1.5 rounded-full bg-emerald-500" />
            <span className="tabular-nums">{current.score}%</span> ATS Match
          </div>
          <div className="hidden items-center gap-1 text-[11px] font-medium text-zinc-500 sm:flex">
            <FileDown className="size-3 text-zinc-400" />
            <span>DOCX / PDF</span>
          </div>
        </div>
      </div>

      {/* Simulated Document View */}
      <div className="space-y-4 p-5 sm:p-6 text-sm">
        {/* Document Header */}
        <div className="border-b border-zinc-100 pb-3">
          <h3 className="text-xl font-bold tracking-tight text-zinc-900">{current.candidate.name}</h3>
          <p className="text-xs font-medium text-zinc-600">{current.candidate.title}</p>
          <p className="mt-1 text-[11px] text-zinc-400">{current.candidate.contact}</p>
        </div>

        {/* Section: Tailored Experience */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-zinc-800">
              Tailored Experience · {current.company} Target
            </span>
            <span className="text-[11px] text-emerald-700 font-medium flex items-center gap-1">
              <Check className="size-3" /> Keyword aligned
            </span>
          </div>
          <ul className="space-y-2 text-xs leading-relaxed text-zinc-700">
            {current.bullets.map((b, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-1.5 size-1 shrink-0 rounded-full bg-zinc-400" />
                <span>{b}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Real-time ATS Keywords Pill List */}
        <div className="rounded-lg border border-zinc-100 bg-zinc-50/70 p-3">
          <div className="mb-2 flex items-center justify-between text-[11px]">
            <span className="font-semibold text-zinc-700">Target Keyword Match</span>
            <span className="text-zinc-500">{current.matched.length} matched · {current.missing.length} missing</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {current.matched.map((kw) => (
              <span
                key={kw}
                className="inline-flex items-center gap-1 rounded border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-800"
              >
                <CheckCircle2 className="size-2.5" />
                {kw}
              </span>
            ))}
            {current.missing.map((kw) => (
              <span
                key={kw}
                className="inline-flex items-center gap-1 rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-800"
              >
                {kw} · missing
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
