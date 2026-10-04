"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import { toast } from "sonner";
import { Check, Copy, Download, FileDown, Info, Loader2, WandSparkles } from "lucide-react";
import { api, getBaseUrl, getStoredToken } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { ResumeResult } from "@/types/api";

const TABS = ["Preview", "ATS match", "Markdown"] as const;
const field = "w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm focus:border-zinc-900 focus:outline-none";

const tone = (v: number) => (v < 34 ? "Keep it concise and direct." : v > 66 ? "Use fuller, more detailed bullets." : "");
const focus = (v: number) => (v < 34 ? "Emphasize technical skills and tools." : v > 66 ? "Emphasize measurable impact and outcomes." : "");

export function ResumeStudio() {
  const [jd, setJd] = useState("");
  const [keyId, setKeyId] = useState("");
  const [model, setModel] = useState("");
  const [extra, setExtra] = useState("");
  const [toneV, setToneV] = useState(50);
  const [focusV, setFocusV] = useState(50);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Preview");
  const [md, setMd] = useState("");
  const [result, setResult] = useState<ResumeResult | null>(null);
  const [copied, setCopied] = useState(false);
  const [downloading, setDownloading] = useState<"docx" | "pdf" | null>(null);
  const preview = useRef<HTMLDivElement>(null);
  const resumeId = useSearchParams().get("resume");
  const saved = useQuery({ queryKey: ["resume", resumeId], enabled: !!resumeId, queryFn: () => api.resume.get(resumeId!) });
  useEffect(() => {
    if (saved.data) {
      setResult(saved.data);
      setMd(saved.data.markdown || "");
      if (saved.data.job_description || saved.data.jd_text) {
        setJd(saved.data.job_description || saved.data.jd_text || "");
      }
    }
  }, [saved.data]);

  const saveMutation = useMutation({
    mutationFn: (updatedMd: string) => {
      if (!result?.id) throw new Error("No resume ID found");
      return api.resume.update(result.id, {
        markdown: updatedMd,
        job_description: jd.trim(),
      });
    },
    onSuccess: (updated) => {
      setResult(updated);
      setMd(updated.markdown);
      toast.success("Resume saved & DOCX/PDF updated!");
    },
    onError: () => {
      toast.error("Failed to save changes");
    },
  });

  const keys = useQuery({ queryKey: ["keys"], queryFn: api.keys.list });
  const models = useQuery({ queryKey: ["models"], queryFn: api.keys.models });
  const activeKeys = keys.data?.filter((k) => k.is_active) ?? [];
  const options = useMemo(() => {
    const k = activeKeys.find((x) => x.id === keyId);
    if (k && models.data?.providers?.[k.provider]) {
      return models.data.providers[k.provider] ?? [];
    }
    if (k && models.data?.strong_models && models.data?.fast_models) {
      return [...models.data.strong_models, ...models.data.fast_models];
    }
    return models.data?.platform_defaults ?? [
      "claude-haiku-4-5-20251001",
      "gpt-4.1-mini",
      "gemini-2.5-flash",
    ];
  }, [keyId, activeKeys, models.data]);
  const chosenModel = options.includes(model) ? model : options[0] ?? "";

  const gen = useMutation({
    mutationFn: api.resume.generate,
    onSuccess: (r) => {
      setResult(r);
      setMd(r.markdown);
      setTab("Preview");
    },
  });
  const hasJd = jd.trim().length > 0;

  const run = () => {
    if (!hasJd) {
      toast.error("Please paste a job description or target role first.");
      return;
    }
    gen.mutate({
      job_description: jd.trim(),
      selected_key_id: keyId || null,
      model: keyId ? chosenModel : "",
      custom_instructions: [tone(toneV), focus(focusV), extra.trim()].filter(Boolean).join(" "),
    });
  };
  const copy = async () => { await navigator.clipboard.writeText(md); setCopied(true); setTimeout(() => setCopied(false), 1500); };
  const downloadFile = async (format: "docx" | "pdf") => {
    if (!result) return;
    setDownloading(format);
    try {
      let currentResult = result;
      // If there are unsaved markdown changes, recompile & save first so the download contains latest edits
      if (result.id && md.trim() !== (result.markdown || "").trim()) {
        toast.info(`Updating ${format.toUpperCase()} with your latest edits…`);
        currentResult = await saveMutation.mutateAsync(md);
      }

      let url = format === "docx" ? currentResult.download_docx_url : currentResult.download_pdf_url;
      if (!url && currentResult.id) {
        const fresh = await api.resume.downloadUrls(currentResult.id);
        url = format === "docx" ? fresh.download_docx_url : fresh.download_pdf_url;
      }
      if (url) {
        let finalUrl = url;
        if (finalUrl.startsWith("/")) {
          const token = getStoredToken();
          const base = getBaseUrl();
          finalUrl = `${base}${finalUrl}${token ? `?token=${encodeURIComponent(token)}` : ""}`;
        }
        const a = document.createElement("a");
        a.href = finalUrl;
        a.download = `${(currentResult.job_title || "resume").toLowerCase().replace(/[^a-z0-9]+/g, "-")}.${format}`;
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
      setDownloading(null);
    }
  };

  if (saved.isLoading) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center gap-3 rounded-lg border border-zinc-200 bg-white p-12 text-zinc-500">
        <Loader2 className="size-6 animate-spin text-zinc-800" />
        <p className="text-sm font-medium">Loading resume...</p>
      </div>
    );
  }

  const score = result?.ats_score ?? 0;
  return (
    <div className="grid min-w-0 max-w-full gap-6 lg:grid-cols-[22rem_1fr]">
      <section className="h-fit min-w-0 max-w-full space-y-4 rounded-lg border border-zinc-200 bg-white p-4">
        <label className="block space-y-1">
          <span className="flex justify-between text-xs font-medium text-zinc-600">Job description <span className="font-normal text-zinc-400">{jd.length} chars</span></span>
          <textarea rows={10} className={field} value={jd} onChange={(e) => setJd(e.target.value)} placeholder="Paste the full job posting" />
          {jd.length > 0 && jd.trim().length < 80 && <span className="text-xs text-amber-600">Tip: 80+ chars recommended for full ATS keyword matching.</span>}
        </label>
        <label className="block space-y-1">
          <span className="text-xs font-medium text-zinc-600">AI Key</span>
          <select className={field} value={keyId} onChange={(e) => setKeyId(e.target.value)}>
            {/* Platform default commented out */}
            {/* <option value={PLATFORM}>Platform default</option> */}
            <option value="">No AI key (Standard Resume)</option>
            {activeKeys.map((k) => <option key={k.id} value={k.id}>{k.label} ({k.provider})</option>)}
          </select>
        </label>
        {keyId ? (
          <label className="block space-y-1">
            <span className="text-xs font-medium text-zinc-600">Model</span>
            <select className={field} value={chosenModel} onChange={(e) => setModel(e.target.value)} disabled={!options.length}>
              {models.isLoading ? <option>Loading models…</option> : options.length ? options.map((m) => <option key={m}>{m}</option>) : <option>No models available</option>}
            </select>
          </label>
        ) : (
          <div className="rounded-md border border-zinc-100 bg-zinc-50 px-3 py-2 text-xs text-zinc-500">
            Generating without AI key — will build directly from your truthful profile.
          </div>
        )}
        {([["Tone", toneV, setToneV, "Concise", "Detailed"], ["Focus", focusV, setFocusV, "Skills", "Impact"]] as const).map(([l, v, set, a, b]) => (
          <label key={l} className="block space-y-1">
            <span className="text-xs font-medium text-zinc-600">{l}</span>
            <input type="range" min={0} max={100} value={v} onChange={(e) => set(+e.target.value)} className="w-full accent-zinc-900" />
            <span className="flex justify-between text-xs text-zinc-500"><span>{a}</span><span>{b}</span></span>
          </label>
        ))}
        <label className="block space-y-1">
          <span className="text-xs font-medium text-zinc-600">Extra instructions (optional)</span>
          <textarea rows={2} className={field} value={extra} onChange={(e) => setExtra(e.target.value)} placeholder="e.g. Keep it to one page" />
        </label>
        <div className="space-y-1.5">
          <button disabled={gen.isPending} onClick={run} className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-zinc-900 px-3 py-2 text-sm text-white hover:bg-zinc-800 disabled:opacity-40">
            {gen.isPending ? <Loader2 className="size-4 animate-spin" /> : <WandSparkles className="size-4" />}{gen.isPending ? "Generating…" : "Generate resume"}
          </button>
          {!hasJd && (
            <p className="text-center text-xs text-zinc-400">
              Paste a job description above to generate
            </p>
          )}
        </div>
      </section>

      <section className="min-w-0 max-w-full min-h-[32rem] rounded-lg border border-zinc-200 bg-white">
        <div role="tablist" className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-200 px-3 py-2">
          <div className="flex items-center gap-1">
            {TABS.map((t) => (
              <button
                key={t}
                role="tab"
                aria-selected={tab === t}
                onClick={() => setTab(t)}
                className={cn(
                  "-mb-2 border-b-2 px-2.5 py-1.5 text-xs sm:text-sm font-medium",
                  tab === t
                    ? "border-zinc-900 text-zinc-900"
                    : "border-transparent text-zinc-500 hover:text-zinc-900"
                )}
              >
                {t}
              </button>
            ))}
          </div>
          {result && (
            <div className="flex flex-wrap items-center gap-1.5">
              <button
                onClick={copy}
                className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs hover:bg-zinc-50"
              >
                {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
                {copied ? "Copied" : "Copy"}
              </button>
              <button
                onClick={() => downloadFile("docx")}
                disabled={downloading === "docx"}
                className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50"
                title="Download Word (.docx)"
              >
                {downloading === "docx" ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <FileDown className="size-3.5 text-blue-600" />
                )}
                <span className="hidden sm:inline">Download </span>DOCX
              </button>
              <button
                onClick={() => downloadFile("pdf")}
                disabled={downloading === "pdf"}
                className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50"
                title="Download PDF document"
              >
                {downloading === "pdf" ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <FileDown className="size-3.5 text-red-600" />
                )}
                <span className="hidden sm:inline">Download </span>PDF
              </button>
            </div>
          )}
        </div>

        <div className="p-4 sm:p-5">
          {gen.isPending && <div className="space-y-3" aria-busy>{[80, 60, 70, 50, 65].map((w, i) => <div key={i} className="h-4 animate-pulse rounded bg-zinc-100" style={{ width: `${w}%` }} />)}</div>}
          {!gen.isPending && !result && <p className="py-24 text-center text-sm text-zinc-500">Paste a job description and generate. Your tailored resume and keyword match appear here.</p>}
          {!gen.isPending && result && tab === "Preview" && (
            <div ref={preview} className="prose-resume min-w-0 max-w-full break-words overflow-x-auto text-sm leading-relaxed [&_h1]:text-2xl [&_h1]:font-semibold [&_h2]:mb-1 [&_h2]:mt-5 [&_h2]:border-b [&_h2]:border-zinc-200 [&_h2]:pb-0.5 [&_h2]:text-sm [&_h2]:font-semibold [&_li]:ml-1 [&_ul]:list-disc [&_ul]:pl-5">
              <ReactMarkdown>{md}</ReactMarkdown>
            </div>
          )}
          {!gen.isPending && result && tab === "ATS match" && (() => {
            const bulletRecs = (result.recommendations ?? []).filter((r) => r.suggested && r.suggested.trim().length > 0);
            const notesList = Array.isArray(result.notes)
              ? result.notes
              : typeof result.notes === "string" && result.notes.trim()
              ? [result.notes]
              : [];

            return (
              <div className="space-y-6">
                <div className="flex items-center gap-4">
                  <p className={cn("text-4xl font-semibold tabular-nums", score >= 75 ? "text-emerald-600" : score >= 50 ? "text-amber-600" : "text-red-600")}>{score}%</p>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-zinc-100" role="meter" aria-valuenow={score} aria-valuemin={0} aria-valuemax={100} aria-label="ATS match score">
                    <div className={cn("h-full", score >= 75 ? "bg-emerald-500" : score >= 50 ? "bg-amber-500" : "bg-red-500")} style={{ width: `${score}%` }} />
                  </div>
                </div>

                {([["Matched keywords", result.matched_keywords ?? [], "border-emerald-200 bg-emerald-50 text-emerald-800"], ["Missing keywords", result.missing_keywords ?? [], "border-amber-200 bg-amber-50 text-amber-800"]] as const).map(([t, list, cls]) => (
                  <div key={t}>
                    <h3 className="mb-2 text-xs font-medium text-zinc-600">{t} ({list.length})</h3>
                    <div className="flex flex-wrap gap-1.5">
                      {list.length ? list.map((k) => <span key={k} className={cn("rounded border px-2 py-0.5 text-xs font-medium", cls)}>{k}</span>) : <span className="text-xs text-zinc-500">None detected</span>}
                    </div>
                  </div>
                ))}

                {bulletRecs.length > 0 && (
                  <div>
                    <h3 className="mb-2 text-xs font-medium text-zinc-600">Suggested bullet changes</h3>
                    <ul className="space-y-2">
                      {bulletRecs.map((r, i) => (
                        <li key={i} className="rounded-md border border-zinc-200 p-3 text-sm">
                          <p className="text-zinc-500 line-through">{r.original}</p>
                          <p className="mt-1 font-medium text-zinc-900">{r.suggested}</p>
                          {r.reason && <p className="mt-1 text-xs text-zinc-500">{r.reason}</p>}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {notesList.length > 0 && (
                  <div className="rounded-lg border border-zinc-200 bg-zinc-50/80 p-4">
                    <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-zinc-700">
                      <Info className="size-3.5 text-zinc-500" />
                      Generation & Validation Insights
                    </h3>
                    <ul className="space-y-1.5 text-xs text-zinc-600">
                      {notesList.map((n, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-zinc-400" />
                          <span>{n}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            );
          })()}
          {!gen.isPending && result && tab === "Markdown" && (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs text-zinc-500">
                  Edit markdown directly. Saving updates both DOCX and PDF downloads.
                </span>
                {result.id && (
                  <button
                    onClick={() => saveMutation.mutate(md)}
                    disabled={saveMutation.isPending || md === result.markdown}
                    className="inline-flex items-center gap-1.5 rounded-md bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-zinc-800 disabled:opacity-40"
                  >
                    {saveMutation.isPending && <Loader2 className="size-3.5 animate-spin" />}
                    {saveMutation.isPending ? "Updating files…" : "Save changes"}
                  </button>
                )}
              </div>
              <textarea
                aria-label="Resume markdown"
                value={md}
                onChange={(e) => setMd(e.target.value)}
                spellCheck={false}
                className="h-[28rem] w-full resize-y rounded-md border border-zinc-300 p-3 font-mono text-xs focus:border-zinc-900 focus:outline-none"
              />
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
