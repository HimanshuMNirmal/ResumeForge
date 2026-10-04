"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  FileDown,
  Loader2,
  Pencil,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { api, getBaseUrl, getStoredToken } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { HistoryItem } from "@/types/api";

const PAGE_SIZE = 10;

export function HistoryList() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<"newest" | "oldest" | "score_desc" | "score_asc">("newest");
  const [page, setPage] = useState(1);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const offset = (page - 1) * PAGE_SIZE;

  const { data, isLoading, isPlaceholderData, error } = useQuery({
    queryKey: ["history", { page, search, sortBy }],
    queryFn: () =>
      api.resume.history({
        limit: PAGE_SIZE,
        offset,
        q: search.trim() || undefined,
        sort_by: sortBy,
      }),
    placeholderData: (prev) => prev,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.resume.delete(id),
    onSuccess: () => {
      toast.success("Resume deleted from history");
      queryClient.invalidateQueries({ queryKey: ["history"] });
    },
    onError: () => {
      toast.error("Failed to delete resume");
    },
  });

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
        let finalUrl = url;
        if (finalUrl.startsWith("/")) {
          const token = getStoredToken();
          const base = getBaseUrl();
          finalUrl = `${base}${finalUrl}${token ? `?token=${encodeURIComponent(token)}` : ""}`;
        }
        const role = item.job_title || item.jd_title || "resume";
        const a = document.createElement("a");
        a.href = finalUrl;
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

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const items = data?.items ?? [];

  const handleSearchChange = (val: string) => {
    setSearch(val);
    setPage(1);
  };

  return (
    <div className="space-y-4">
      {/* Controls: Search, Sort, Stats */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-400" />
          <input
            type="text"
            placeholder="Search by role or company…"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="w-full rounded-md border border-zinc-300 bg-white py-2 pl-9 pr-8 text-xs sm:text-sm focus:border-zinc-900 focus:outline-none"
          />
          {search && (
            <button
              onClick={() => handleSearchChange("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
              title="Clear search"
            >
              <X className="size-3.5" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <div className="relative inline-flex items-center">
            <ArrowUpDown className="pointer-events-none absolute left-2.5 size-3.5 text-zinc-400" />
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value as any);
                setPage(1);
              }}
              className="rounded-md border border-zinc-300 bg-white py-1.5 pl-8 pr-7 text-xs font-medium text-zinc-700 hover:border-zinc-400 focus:border-zinc-900 focus:outline-none"
            >
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
              <option value="score_desc">Highest match</option>
              <option value="score_asc">Lowest match</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg border border-zinc-200 bg-white" />
          ))}
        </div>
      ) : error ? (
        <div className="rounded-lg border border-dashed border-zinc-200 p-8 text-center text-sm text-zinc-500">
          Couldn&apos;t load resume history. Please refresh the page.
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-lg border border-dashed border-zinc-300 p-10 text-center text-sm text-zinc-500">
          {search ? (
            <div>
              <p>No resumes matching &ldquo;{search}&rdquo;.</p>
              <button
                onClick={() => handleSearchChange("")}
                className="mt-2 text-xs font-medium text-zinc-900 underline"
              >
                Clear filter
              </button>
            </div>
          ) : (
            <div>
              No resumes yet.{" "}
              <Link href="/builder" className="font-medium text-zinc-900 underline">
                Generate your first one
              </Link>
              .
            </div>
          )}
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-sm">
          <ul className="divide-y divide-zinc-100">
            {items.map((r) => {
              const title = r.job_title || r.jd_title || "Untitled role";
              const company = r.company || r.jd_company;
              const score = r.ats_score ?? 0;
              const isDeleting = deleteMutation.isPending && deleteMutation.variables === r.id;

              return (
                <li
                  key={r.id}
                  className={cn(
                    "flex flex-col gap-3 p-4 transition-colors sm:flex-row sm:items-center sm:justify-between hover:bg-zinc-50/50",
                    isDeleting && "opacity-40 pointer-events-none"
                  )}
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-zinc-900">
                      {title}
                      {company && <span className="font-normal text-zinc-500"> · {company}</span>}
                    </p>
                    <div className="mt-1 flex items-center gap-2 text-xs text-zinc-500">
                      {r.created_at && (
                        <span>
                          {new Date(r.created_at).toLocaleDateString(undefined, {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                          })}
                        </span>
                      )}
                      {r.model_used && (
                        <>
                          <span>•</span>
                          <span className="truncate max-w-[140px] text-zinc-400 font-mono text-[11px]">
                            {r.model_used}
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 sm:flex-nowrap">
                    <span
                      className={cn(
                        "rounded-full px-2.5 py-0.5 text-xs font-medium tabular-nums",
                        score >= 75
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : score >= 50
                          ? "bg-amber-50 text-amber-700 border border-amber-200"
                          : "bg-red-50 text-red-700 border border-red-200"
                      )}
                    >
                      {score}% match
                    </span>

                    {/* On-demand DOCX download */}
                    <button
                      onClick={() => downloadFile(r, "docx")}
                      disabled={downloadingId === `${r.id}-docx`}
                      className="inline-flex items-center gap-1.5 rounded-md border border-zinc-200 bg-white px-2.5 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50"
                      title="Generate & download DOCX"
                    >
                      {downloadingId === `${r.id}-docx` ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : (
                        <FileDown className="size-3.5 text-blue-600" />
                      )}
                      <span>DOCX</span>
                    </button>

                    {/* On-demand PDF download */}
                    <button
                      onClick={() => downloadFile(r, "pdf")}
                      disabled={downloadingId === `${r.id}-pdf`}
                      className="inline-flex items-center gap-1.5 rounded-md border border-zinc-200 bg-white px-2.5 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50"
                      title="Generate & download PDF"
                    >
                      {downloadingId === `${r.id}-pdf` ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : (
                        <FileDown className="size-3.5 text-red-600" />
                      )}
                      <span>PDF</span>
                    </button>

                    {/* Edit in ResumeStudio */}
                    <Link
                      href={`/builder?resume=${r.id}`}
                      className="inline-flex items-center gap-1 rounded-md border border-zinc-200 bg-white px-2.5 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50"
                      title="Edit resume in builder"
                    >
                      <Pencil className="size-3.5 text-zinc-500" />
                      <span>Edit</span>
                    </Link>

                    {/* Delete */}
                    <button
                      onClick={() => {
                        if (confirm("Delete this resume from history?")) {
                          deleteMutation.mutate(r.id);
                        }
                      }}
                      className="inline-flex items-center justify-center rounded-md border border-transparent p-1.5 text-zinc-400 hover:border-zinc-200 hover:text-red-600"
                      title="Delete resume"
                    >
                      <Trash2 className="size-3.5" />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>

          {/* Pagination Footer */}
          <div className="flex items-center justify-between border-t border-zinc-100 bg-zinc-50/50 px-4 py-3 text-xs text-zinc-500">
            <div>
              Showing <span className="font-medium text-zinc-800">{Math.min(offset + 1, total)}</span> to{" "}
              <span className="font-medium text-zinc-800">{Math.min(offset + items.length, total)}</span> of{" "}
              <span className="font-medium text-zinc-800">{total}</span> resumes
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1 || isPlaceholderData}
                className="inline-flex items-center gap-1 rounded border border-zinc-200 bg-white px-2 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-40"
              >
                <ChevronLeft className="size-3.5" />
                Previous
              </button>

              <span className="px-1 text-zinc-600 font-medium">
                {page} / {totalPages}
              </span>

              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages || isPlaceholderData}
                className="inline-flex items-center gap-1 rounded border border-zinc-200 bg-white px-2 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-40"
              >
                Next
                <ChevronRight className="size-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
