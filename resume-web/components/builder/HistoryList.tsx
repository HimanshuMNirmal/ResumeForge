"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Pencil } from "lucide-react";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/utils";

export function HistoryList() {
  const { data, isLoading, error } = useQuery({ queryKey: ["history"], queryFn: api.resume.history });
  if (isLoading) return <div className="space-y-2">{[0, 1, 2].map((i) => <div key={i} className="h-14 animate-pulse rounded-lg border border-zinc-200 bg-white" />)}</div>;
  if (error) return <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">Couldn't load history: {error.message}</p>;
  if (!data?.length) return (
    <div className="rounded-lg border border-dashed border-zinc-300 p-10 text-center text-sm text-zinc-500">
      No resumes yet. <Link href="/builder" className="font-medium text-zinc-900 underline">Generate your first one</Link>.
    </div>
  );
  const items = [...data].sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? ""));
  return (
    <ul className="divide-y divide-zinc-100 rounded-lg border border-zinc-200 bg-white">
      {items.map((r) => (
        <li key={r.id} className="flex items-center gap-4 px-4 py-3">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{r.job_title || "Untitled role"}{r.company && <span className="font-normal text-zinc-500"> at {r.company}</span>}</p>
            {r.created_at && <p className="text-xs text-zinc-500">{new Date(r.created_at).toLocaleDateString(undefined, { dateStyle: "medium" })}</p>}
          </div>
          <span className={cn("rounded-full px-2 py-0.5 text-xs tabular-nums", r.ats_score >= 75 ? "bg-emerald-50 text-emerald-700" : r.ats_score >= 50 ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-700")}>{r.ats_score}% match</span>
          <Link href={`/builder?resume=${r.id}`} className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2.5 py-1.5 text-xs hover:bg-zinc-50"><Pencil className="size-3.5" />Edit</Link>
        </li>
      ))}
    </ul>
  );
}
