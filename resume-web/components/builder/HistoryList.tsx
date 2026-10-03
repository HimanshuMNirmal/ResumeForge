"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { FileDown, Loader2, Pencil } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { HistoryItem } from "@/types/api";

export function HistoryList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["history"],
    queryFn: api.resume.history,
  });
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const downloadFile = async (item: HistoryItem, format: "docx" | "pdf") => {
    const key = `${item.id}-${format}`;
    setDownloadingId(key);
    try {
      let url = format === "docx" ? item.download_docx_url : item.download_pdf_url;
      if (!url) {
        const fresh = await api.resume.downloadUrls(item.id);
        url = format === "docx" ? fresh.download_docx_url : fresh.download_pdf_url;
      }
      if (url) {
        const role = item.job_title || item.jd_title || "resume";
        const a = document.createElement("a");
        a.href = url;
        a.download = `${role.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.${format}`;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      } else {
        toast.error(`${format.toUpperCase()} file is not available for this resume.`);
      }
    } catch {
      toast.error(`Failed to download ${format.toUpperCase()}.`);
    } finally {
      setDownloadingId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-14 animate-pulse rounded-lg border border-zinc-200 bg-white" />
        ))}
      </div>
    );
  }
  if (error) {
    return (
      <div className="rounded-lg border border-dashed border-zinc-200 p-8 text-center text-sm text-zinc-500">
        Couldn&apos;t load resume history. Please refresh the page.
      </div>
    );
  }
  if (!data?.length) {
    return (
      <div className="rounded-lg border border-dashed border-zinc-300 p-10 text-center text-sm text-zinc-500">
        No resumes yet.{" "}
        <Link href="/builder" className="font-medium text-zinc-900 underline">
          Generate your first one
        </Link>
        .
      </div>
    );
  }
  const items = [...data].sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? ""));
  return (
    <ul className="divide-y divide-zinc-100 rounded-lg border border-zinc-200 bg-white">
      {items.map((r) => {
        const title = r.job_title || r.jd_title || "Untitled role";
        const company = r.company || r.jd_company;
        const score = r.ats_score ?? 0;
        return (
          <li key={r.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 sm:flex-nowrap">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">
                {title}
                {company && <span className="font-normal text-zinc-500"> at {company}</span>}
              </p>
              {r.created_at && (
                <p className="text-xs text-zinc-500">
                  {new Date(r.created_at).toLocaleDateString(undefined, { dateStyle: "medium" })}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-xs tabular-nums font-medium",
                  score >= 75
                    ? "bg-emerald-50 text-emerald-700"
                    : score >= 50
                    ? "bg-amber-50 text-amber-700"
                    : "bg-red-50 text-red-700"
                )}
              >
                {score}% match
              </span>
              <button
                onClick={() => downloadFile(r, "docx")}
                disabled={downloadingId === `${r.id}-docx`}
                className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2.5 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50"
                title="Download DOCX"
              >
                {downloadingId === `${r.id}-docx` ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <FileDown className="size-3.5 text-blue-600" />
                )}
                DOCX
              </button>
              <button
                onClick={() => downloadFile(r, "pdf")}
                disabled={downloadingId === `${r.id}-pdf`}
                className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2.5 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50"
                title="Download PDF"
              >
                {downloadingId === `${r.id}-pdf` ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <FileDown className="size-3.5 text-red-600" />
                )}
                PDF
              </button>
              <Link
                href={`/builder?resume=${r.id}`}
                className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2.5 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50"
              >
                <Pencil className="size-3.5 text-zinc-500" />
                Edit
              </Link>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
