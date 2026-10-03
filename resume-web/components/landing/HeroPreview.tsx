"use client";
import { useState } from "react";
import { cn } from "@/lib/utils";

const ROLES = [
  { id: "api", label: "Backend engineer", score: 91, hit: ["FastAPI", "PostgreSQL", "AWS"], miss: ["Kafka"],
    bullets: ["Cut p95 latency 42% by moving report queries to PostgreSQL materialized views.", "Shipped a FastAPI service on AWS handling 1.2M requests a day."] },
  { id: "ui", label: "Frontend engineer", score: 87, hit: ["React", "TypeScript", "Next.js"], miss: ["Storybook"],
    bullets: ["Rebuilt the dashboard in Next.js and TypeScript, lifting Lighthouse from 61 to 96.", "Introduced a typed API client that removed a class of runtime errors."] },
];

export function HeroPreview() {
  const [i, setI] = useState(0);
  const r = ROLES[i];
  return (
    <div className="rounded-lg border border-zinc-200 bg-white shadow-sm" aria-label="Example of a tailored resume">
      <div role="tablist" aria-label="Example job" className="flex items-center gap-1 border-b border-zinc-200 px-3 py-2">
        {ROLES.map((x, n) => (
          <button key={x.id} role="tab" aria-selected={i === n} onClick={() => setI(n)}
            className={cn("rounded px-2 py-1 text-xs", i === n ? "bg-zinc-900 text-white" : "text-zinc-600 hover:bg-zinc-100")}>{x.label}</button>
        ))}
        <span className="ml-auto text-xs text-zinc-500">ATS match <b className="tabular-nums text-emerald-600">{r.score}%</b></span>
      </div>
      <div className="space-y-3 p-5 text-sm">
        <div><p className="text-lg font-semibold">Ada Rao</p><p className="text-xs text-zinc-500">Pune, India · ada@example.com</p></div>
        <p className="border-b border-zinc-200 pb-0.5 text-xs font-semibold">Experience</p>
        <ul className="list-disc space-y-1.5 pl-5 text-zinc-700">{r.bullets.map((b) => <li key={b}>{b}</li>)}</ul>
        <div className="flex flex-wrap gap-1.5 pt-1">
          {r.hit.map((k) => <span key={k} className="rounded border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs text-emerald-800">{k}</span>)}
          {r.miss.map((k) => <span key={k} className="rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs text-amber-800">{k} · missing</span>)}
        </div>
      </div>
    </div>
  );
}
