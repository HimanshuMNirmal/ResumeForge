"use client";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { api, ApiError } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { Experience, Profile, Skills } from "@/types/api";
import { ErrorAlert } from "@/components/ui/ErrorAlert";

const EMPTY: Profile = {
  full_name: "", email: "", phone: "", location: "", linkedin: "", github: "", portfolio: "",
  experience: [], education: [], certifications: [],
  skills: { languages: [], frameworks: [], tools: [], soft: [] },
};
const TABS = ["Personal", "Experience", "Education", "Skills"] as const;
const csv = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
const input = "w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm placeholder:text-zinc-400 focus:border-zinc-900 focus:outline-none";

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1">
      <span className="text-xs font-medium text-zinc-600">{label}</span>
      {children}
      {error && <span role="alert" className="block text-xs text-red-600">{error}</span>}
    </label>
  );
}
function Text({ label, value, onChange, error, ...rest }: { label: string; value: string; onChange: (v: string) => void; error?: string } & Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange" | "value">) {
  return <Field label={label} error={error}><input {...rest} className={cn(input, error && "border-red-400")} value={value} onChange={(e) => onChange(e.target.value)} /></Field>;
}

function normalizeProfile(raw: any): Profile {
  if (!raw) return EMPTY;
  return {
    full_name: raw.full_name || "",
    email: raw.email || "",
    phone: raw.phone || "",
    location: raw.location || "",
    linkedin: raw.linkedin || "",
    github: raw.github || "",
    portfolio: raw.portfolio || "",
    experience: Array.isArray(raw.experience)
      ? raw.experience.map((e: any) => ({
          company: e?.company || "",
          role: e?.role || "",
          start_date: e?.start_date || "",
          end_date: e?.end_date ?? null,
          bullets: Array.isArray(e?.bullets)
            ? e.bullets.map((b: any) => ({
                text: typeof b === "string" ? b : (b?.text || ""),
                skills: Array.isArray(b?.skills) ? b.skills : [],
              }))
            : [],
        }))
      : [],
    education: Array.isArray(raw.education)
      ? raw.education.map((ed: any) => ({
          institution: ed?.institution || "",
          degree: ed?.degree || "",
          field: ed?.field || "",
          start_date: ed?.start_date || "",
          end_date: ed?.end_date ?? null,
        }))
      : [],
    certifications: Array.isArray(raw.certifications) ? raw.certifications : [],
    skills: {
      languages: Array.isArray(raw.skills?.languages) ? raw.skills.languages : [],
      frameworks: Array.isArray(raw.skills?.frameworks) ? raw.skills.frameworks : [],
      tools: Array.isArray(raw.skills?.tools) ? raw.skills.tools : [],
      soft: Array.isArray(raw.skills?.soft) ? raw.skills.soft : [],
    },
  };
}

export function ProfileForm() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<(typeof TABS)[number]>("Personal");
  const [draft, setDraft] = useState<Profile>(EMPTY);

  const { data, isLoading, error } = useQuery({
    queryKey: ["profile"],
    refetchOnWindowFocus: false,
    queryFn: () => api.profile.get().catch((e) => { if (e instanceof ApiError && e.status === 404) return EMPTY; throw e; }),
  });
  useEffect(() => { if (data) setDraft(normalizeProfile(data)); }, [data]);

  const dirty = useMemo(() => !!data && JSON.stringify(normalizeProfile(data)) !== JSON.stringify(draft), [data, draft]);
  useEffect(() => {
    if (!dirty) return;
    const h = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", h);
    return () => window.removeEventListener("beforeunload", h);
  }, [dirty]);

  const emailError = draft.email && !/^\S+@\S+\.\S+$/.test(draft.email) ? "Enter a valid email address" : undefined;
  const nameError = dirty && !(draft.full_name || "").trim() ? "Name is required" : undefined;
  const invalid = !!emailError || !(draft.full_name || "").trim();

  const save = useMutation({
    mutationFn: api.profile.update,
    onSuccess: (p) => { qc.setQueryData(["profile"], p); toast.success("Profile saved"); },
    onError: (e) => toast.error(e.message),
  });

  const update = (fn: (p: Profile) => void) => setDraft((p) => { const n = structuredClone(p); fn(n); return n; });
  const setExp = (i: number, fn: (e: Experience) => void) => update((p) => fn(p.experience[i]));

  if (isLoading) return <div className="h-64 animate-pulse rounded-lg border border-zinc-200 bg-white" aria-label="Loading profile" />;
  if (error) return <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">Couldn't load your profile: {error.message}</p>;

  return (
    <section className="rounded-lg border border-zinc-200 bg-white">
      <div role="tablist" className="flex gap-1 border-b border-zinc-200 px-3 pt-2">
        {TABS.map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
            className={cn("-mb-px border-b-2 px-3 py-2 text-sm", tab === t ? "border-zinc-900 font-medium" : "border-transparent text-zinc-500 hover:text-zinc-900")}>{t}</button>
        ))}
      </div>

      {save.isError && (
        <div className="p-4 pb-0">
          <ErrorAlert error={save.error} title="Validation error saving profile" />
        </div>
      )}

      <div className="space-y-4 p-4">
        {tab === "Personal" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Text label="Full name" value={draft.full_name} error={nameError} onChange={(v) => update((p) => { p.full_name = v; })} autoComplete="name" />
            <Text label="Email" type="email" value={draft.email} error={emailError} onChange={(v) => update((p) => { p.email = v; })} autoComplete="email" />
            <Text label="Phone" value={draft.phone} onChange={(v) => update((p) => { p.phone = v; })} autoComplete="tel" />
            <Text label="Location" value={draft.location} onChange={(v) => update((p) => { p.location = v; })} placeholder="City, Country" />
            <Text label="LinkedIn" value={draft.linkedin} onChange={(v) => update((p) => { p.linkedin = v; })} placeholder="linkedin.com/in/you" />
            <Text label="GitHub" value={draft.github} onChange={(v) => update((p) => { p.github = v; })} placeholder="github.com/you" />
            <div className="sm:col-span-2"><Text label="Portfolio" value={draft.portfolio} onChange={(v) => update((p) => { p.portfolio = v; })} /></div>
          </div>
        )}

        {tab === "Experience" && (
          <>
            {draft.experience.length === 0 && <p className="rounded-md border border-dashed border-zinc-300 p-6 text-center text-sm text-zinc-500">No roles yet. Add one, or import a JSON profile above.</p>}
            {draft.experience.map((x, i) => (
              <fieldset key={i} className="space-y-3 rounded-md border border-zinc-200 p-3">
                <div className="flex items-center justify-between">
                  <legend className="text-sm font-medium">{x.role || "New role"}{x.company && ` at ${x.company}`}</legend>
                  <button aria-label="Remove role" onClick={() => update((p) => { p.experience.splice(i, 1); })} className="text-zinc-400 hover:text-red-600"><Trash2 className="size-4" /></button>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Text label="Company" value={x.company} onChange={(v) => setExp(i, (e) => { e.company = v; })} />
                  <Text label="Role" value={x.role} onChange={(v) => setExp(i, (e) => { e.role = v; })} />
                  <Text label="Start" type="month" value={x.start_date} onChange={(v) => setExp(i, (e) => { e.start_date = v; })} />
                  <Text label="End (blank if current)" type="month" value={x.end_date ?? ""} onChange={(v) => setExp(i, (e) => { e.end_date = v || null; })} />
                </div>
                {x.bullets.map((b, j) => (
                  <div key={j} className="space-y-1.5 rounded-md bg-zinc-50 p-2">
                    <textarea aria-label={`Bullet ${j + 1}`} rows={2} className={input} placeholder="What you did and what changed because of it" value={b.text}
                      onChange={(e) => setExp(i, (ex) => { ex.bullets[j].text = e.target.value; })} />
                    <div className="flex gap-2">
                      <input aria-label="Skills for this bullet" className={cn(input, "py-1.5 text-xs")} placeholder="Skills, comma separated" value={b.skills.join(", ")}
                        onChange={(e) => setExp(i, (ex) => { ex.bullets[j].skills = csv(e.target.value); })} />
                      <button aria-label="Remove bullet" onClick={() => setExp(i, (ex) => { ex.bullets.splice(j, 1); })} className="text-zinc-400 hover:text-red-600"><Trash2 className="size-4" /></button>
                    </div>
                  </div>
                ))}
                <button onClick={() => setExp(i, (e) => { e.bullets.push({ text: "", skills: [] }); })} className="inline-flex items-center gap-1 text-xs text-zinc-600 hover:text-zinc-900"><Plus className="size-3.5" />Add bullet</button>
              </fieldset>
            ))}
            <button onClick={() => update((p) => { p.experience.push({ company: "", role: "", start_date: "", end_date: null, bullets: [{ text: "", skills: [] }] }); })}
              className="inline-flex items-center gap-1.5 rounded-md border border-zinc-200 px-3 py-1.5 text-sm hover:bg-zinc-50"><Plus className="size-4" />Add role</button>
          </>
        )}

        {tab === "Education" && (
          <>
            {draft.education.map((ed, i) => (
              <div key={i} className="grid gap-3 rounded-md border border-zinc-200 p-3 sm:grid-cols-2">
                <Text label="Institution" value={ed.institution} onChange={(v) => update((p) => { p.education[i].institution = v; })} />
                <Text label="Degree" value={ed.degree} onChange={(v) => update((p) => { p.education[i].degree = v; })} />
                <Text label="Field" value={ed.field} onChange={(v) => update((p) => { p.education[i].field = v; })} />
                <div className="flex items-end gap-2">
                  <Text label="Start" type="month" value={ed.start_date} onChange={(v) => update((p) => { p.education[i].start_date = v; })} />
                  <Text label="End" type="month" value={ed.end_date ?? ""} onChange={(v) => update((p) => { p.education[i].end_date = v || null; })} />
                  <button aria-label="Remove education" onClick={() => update((p) => { p.education.splice(i, 1); })} className="pb-2 text-zinc-400 hover:text-red-600"><Trash2 className="size-4" /></button>
                </div>
              </div>
            ))}
            <button onClick={() => update((p) => { p.education.push({ institution: "", degree: "", field: "", start_date: "", end_date: null }); })}
              className="inline-flex items-center gap-1.5 rounded-md border border-zinc-200 px-3 py-1.5 text-sm hover:bg-zinc-50"><Plus className="size-4" />Add education</button>
            <Field label="Certifications (comma separated)">
              <input className={input} value={draft.certifications.join(", ")} onChange={(e) => update((p) => { p.certifications = csv(e.target.value); })} />
            </Field>
          </>
        )}

        {tab === "Skills" && (
          <div className="grid gap-4 sm:grid-cols-2">
            {([["languages", "Languages"], ["frameworks", "Frameworks"], ["tools", "Tools"], ["soft", "Soft skills"]] as [keyof Skills, string][]).map(([k, label]) => (
              <Field key={k} label={`${label} (comma separated)`}>
                <input className={input} value={draft.skills[k].join(", ")} onChange={(e) => update((p) => { p.skills[k] = csv(e.target.value); })} />
                <span className="mt-1.5 flex flex-wrap gap-1">{draft.skills[k].map((s) => <span key={s} className="rounded border border-zinc-200 bg-zinc-50 px-1.5 py-0.5 text-xs text-zinc-700">{s}</span>)}</span>
              </Field>
            ))}
          </div>
        )}
      </div>

      <footer className="flex items-center justify-between border-t border-zinc-200 px-4 py-3">
        <span className="text-xs text-zinc-500" aria-live="polite">{dirty ? "Unsaved changes" : "All changes saved"}</span>
        <div className="flex gap-2">
          <button disabled={!dirty} onClick={() => data && setDraft(data)} className="rounded-md border border-zinc-200 px-3 py-1.5 text-sm hover:bg-zinc-50 disabled:opacity-40">Discard</button>
          <button disabled={!dirty || invalid || save.isPending} onClick={() => save.mutate(draft)}
            className="inline-flex items-center gap-1.5 rounded-md bg-zinc-900 px-3 py-1.5 text-sm text-white hover:bg-zinc-800 disabled:opacity-40">
            {save.isPending && <Loader2 className="size-3.5 animate-spin" />}Save changes
          </button>
        </div>
      </footer>
    </section>
  );
}
