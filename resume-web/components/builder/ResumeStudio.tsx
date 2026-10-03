"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import { toast } from "sonner";
import { Check, Copy, Download, FileDown, Loader2, WandSparkles } from "lucide-react";
import { api } from "@/lib/api-client";
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
  const preview = useRef<HTMLDivElement>(null);
  const resumeId = useSearchParams().get("resume");
  const saved = useQuery({ queryKey: ["resume", resumeId], enabled: !!resumeId, queryFn: () => api.resume.get(resumeId!) });
  useEffect(() => { if (saved.data) { setResult(saved.data); setMd(saved.data.markdown); } }, [saved.data]);

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
  const canRun = jd.trim().length >= 80 && !gen.isPending;

  const run = () => gen.mutate({
    job_description: jd.trim(),
    selected_key_id: keyId || null,
    model: keyId ? chosenModel : "",
    custom_instructions: [tone(toneV), focus(focusV), extra.trim()].filter(Boolean).join(" "),
  });
  const copy = async () => { await navigator.clipboard.writeText(md); setCopied(true); setTimeout(() => setCopied(false), 1500); };
  const downloadMd = () => {
    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = Object.assign(document.createElement("a"), {
      href: url,
      download: `${(result?.job_title || "resume").toLowerCase().replace(/[^a-z0-9]+/g, "-")}.md`,
    });
    a.click();
    URL.revokeObjectURL(url);
  };
  const exportPdf = () => {
    const w = window.open("", "_blank");
    if (!w || !preview.current) return toast.error("Allow pop-ups to export as PDF.");
    w.document.write(`<title>Resume</title><style>body{font:14px/1.5 system-ui;max-width:760px;margin:32px auto;color:#18181b}h1{font-size:24px;margin:0}h2{font-size:13px;border-bottom:1px solid #d4d4d8;margin:18px 0 6px;padding-bottom:2px}ul{padding-left:18px;margin:4px 0}</style>${preview.current.innerHTML}`);
    w.document.close(); w.focus(); w.print();
  };

  const score = result?.ats_score ?? 0;
  return (
    <div className="grid gap-6 lg:grid-cols-[22rem_1fr]">
      <section className="h-fit space-y-4 rounded-lg border border-zinc-200 bg-white p-4">
        <label className="block space-y-1">
          <span className="flex justify-between text-xs font-medium text-zinc-600">Job description <span className="font-normal text-zinc-400">{jd.length} chars</span></span>
          <textarea rows={10} className={field} value={jd} onChange={(e) => setJd(e.target.value)} placeholder="Paste the full job posting" />
          {jd.length > 0 && jd.trim().length < 80 && <span className="text-xs text-zinc-500">Paste a bit more so keywords can be matched.</span>}
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
        <button disabled={!canRun} onClick={run} className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-zinc-900 px-3 py-2 text-sm text-white hover:bg-zinc-800 disabled:opacity-40">
          {gen.isPending ? <Loader2 className="size-4 animate-spin" /> : <WandSparkles className="size-4" />}{gen.isPending ? "Generating…" : "Generate resume"}
        </button>
      </section>

      <section className="min-h-[32rem] rounded-lg border border-zinc-200 bg-white">
        <div role="tablist" className="flex items-center gap-1 border-b border-zinc-200 px-3 pt-2">
          {TABS.map((t) => (
            <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
              className={cn("-mb-px border-b-2 px-3 py-2 text-sm", tab === t ? "border-zinc-900 font-medium" : "border-transparent text-zinc-500 hover:text-zinc-900")}>{t}</button>
          ))}
          {result && (
            <div className="ml-auto flex gap-1 pb-1">
              <button onClick={copy} className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs hover:bg-zinc-50">{copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}{copied ? "Copied" : "Copy"}</button>
              <button onClick={downloadMd} className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs hover:bg-zinc-50"><Download className="size-3.5" />Download .md</button>
              <button onClick={exportPdf} className="inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-xs hover:bg-zinc-50"><FileDown className="size-3.5" />Export PDF</button>
            </div>
          )}
        </div>

        <div className="p-5">
          {gen.isPending && <div className="space-y-3" aria-busy>{[80, 60, 70, 50, 65].map((w, i) => <div key={i} className="h-4 animate-pulse rounded bg-zinc-100" style={{ width: `${w}%` }} />)}</div>}
          {!gen.isPending && !result && <p className="py-24 text-center text-sm text-zinc-500">Paste a job description and generate. Your tailored resume and keyword match appear here.</p>}
          {!gen.isPending && result && tab === "Preview" && (
            <div ref={preview} className="prose-resume max-w-2xl text-sm leading-relaxed [&_h1]:text-2xl [&_h1]:font-semibold [&_h2]:mb-1 [&_h2]:mt-5 [&_h2]:border-b [&_h2]:border-zinc-200 [&_h2]:pb-0.5 [&_h2]:text-sm [&_h2]:font-semibold [&_li]:ml-1 [&_ul]:list-disc [&_ul]:pl-5">
              <ReactMarkdown>{md}</ReactMarkdown>
            </div>
          )}
          {!gen.isPending && result && tab === "ATS match" && (
            <div className="space-y-6">
              <div className="flex items-center gap-4">
                <p className={cn("text-4xl font-semibold tabular-nums", score >= 75 ? "text-emerald-600" : score >= 50 ? "text-amber-600" : "text-red-600")}>{score}%</p>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-zinc-100" role="meter" aria-valuenow={score} aria-valuemin={0} aria-valuemax={100} aria-label="ATS match score">
                  <div className={cn("h-full", score >= 75 ? "bg-emerald-500" : score >= 50 ? "bg-amber-500" : "bg-red-500")} style={{ width: `${score}%` }} />
                </div>
              </div>
              {([["Matched keywords", result.matched_keywords, "border-emerald-200 bg-emerald-50 text-emerald-800"], ["Missing keywords", result.missing_keywords, "border-amber-200 bg-amber-50 text-amber-800"]] as const).map(([t, list, cls]) => (
                <div key={t}><h3 className="mb-2 text-xs font-medium text-zinc-600">{t} ({list.length})</h3>
                  <div className="flex flex-wrap gap-1.5">{list.length ? list.map((k) => <span key={k} className={cn("rounded border px-2 py-0.5 text-xs", cls)}>{k}</span>) : <span className="text-xs text-zinc-500">None</span>}</div></div>
              ))}
              {result.recommendations.length > 0 && (
                <div><h3 className="mb-2 text-xs font-medium text-zinc-600">Suggested bullet changes</h3>
                  <ul className="space-y-2">{result.recommendations.map((r, i) => (
                    <li key={i} className="rounded-md border border-zinc-200 p-3 text-sm">
                      <p className="text-zinc-500 line-through">{r.original}</p><p className="mt-1">{r.suggested}</p>
                      {r.reason && <p className="mt-1 text-xs text-zinc-500">{r.reason}</p>}
                    </li>))}</ul></div>
              )}
            </div>
          )}
          {!gen.isPending && result && tab === "Markdown" && (
            <textarea aria-label="Resume markdown" value={md} onChange={(e) => setMd(e.target.value)} spellCheck={false} className="h-[28rem] w-full resize-y rounded-md border border-zinc-300 p-3 font-mono text-xs focus:border-zinc-900 focus:outline-none" />
          )}
        </div>
      </section>
    </div>
  );
}
