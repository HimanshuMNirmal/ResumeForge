"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Bot, Gem, Loader2, Lock, Plus, Sparkles, Trash2, X } from "lucide-react";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { Provider } from "@/types/api";
import { ErrorAlert } from "@/components/ui/ErrorAlert";

const PROVIDERS: Record<Provider, { name: string; icon: typeof Bot; pattern: RegExp; hint: string }> = {
  openai: { name: "OpenAI", icon: Sparkles, pattern: /^sk-[A-Za-z0-9_-]{20,}$/, hint: "Starts with sk-" },
  anthropic: { name: "Anthropic", icon: Bot, pattern: /^sk-ant-[A-Za-z0-9_-]{20,}$/, hint: "Starts with sk-ant-" },
  gemini: { name: "Google Gemini", icon: Gem, pattern: /^AIza[A-Za-z0-9_-]{30,}$/, hint: "Starts with AIza" },
};
const field = "w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm focus:border-zinc-900 focus:outline-none";

function AddKeyModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [provider, setProvider] = useState<Provider>("openai");
  const [apiKey, setApiKey] = useState("");
  const [label, setLabel] = useState("");
  const [touched, setTouched] = useState(false);
  const cfg = PROVIDERS[provider];
  const valid = cfg.pattern.test(apiKey.trim());

  const add = useMutation({
    mutationFn: api.keys.add,
    meta: { suppressGlobalError: true },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["keys"] });
      qc.invalidateQueries({ queryKey: ["models"] });
      toast.success("Key added");
      onClose();
    },
  });

  return (
    <div role="dialog" aria-modal="true" aria-labelledby="add-key" className="fixed inset-0 z-50 grid place-items-center bg-zinc-900/40 p-4" onClick={onClose}>
      <form onClick={(e) => e.stopPropagation()} onSubmit={(e) => { e.preventDefault(); setTouched(true); if (valid) add.mutate({ provider, api_key: apiKey.trim(), label: label.trim() || cfg.name }); }}
        className="w-full max-w-md space-y-4 rounded-lg border border-zinc-200 bg-white p-5 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 id="add-key" className="font-medium">Add an API key</h2>
          <button type="button" aria-label="Close" onClick={onClose} className="text-zinc-400 hover:text-zinc-900"><X className="size-4" /></button>
        </div>

        {add.isError && <ErrorAlert error={add.error} title="Failed to save API key" />}
        <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Provider">
          {(Object.keys(PROVIDERS) as Provider[]).map((p) => {
            const I = PROVIDERS[p].icon;
            return (
              <button key={p} type="button" role="radio" aria-checked={provider === p} onClick={() => setProvider(p)}
                className={cn("flex flex-col items-center gap-1 rounded-md border px-2 py-3 text-xs", provider === p ? "border-zinc-900 bg-zinc-50 font-medium" : "border-zinc-200 hover:bg-zinc-50")}>
                <I className="size-4" />{PROVIDERS[p].name}
              </button>
            );
          })}
        </div>
        <label className="block space-y-1">
          <span className="text-xs font-medium text-zinc-600">Nickname</span>
          <input className={field} value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Personal key" maxLength={40} />
        </label>
        <label className="block space-y-1">
          <span className="text-xs font-medium text-zinc-600">API key</span>
          <input className={cn(field, "font-mono", touched && !valid && "border-red-400")} type="password" autoComplete="off" spellCheck={false}
            value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder={cfg.hint} />
          {touched && !valid && <span role="alert" className="block text-xs text-red-600">That doesn't look like a {cfg.name} key. {cfg.hint}.</span>}
        </label>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-md border border-zinc-200 px-3 py-1.5 text-sm hover:bg-zinc-50">Cancel</button>
          <button disabled={add.isPending} className="inline-flex items-center gap-1.5 rounded-md bg-zinc-900 px-3 py-1.5 text-sm text-white hover:bg-zinc-800 disabled:opacity-50">
            {add.isPending && <Loader2 className="size-3.5 animate-spin" />}Add key
          </button>
        </div>
      </form>
    </div>
  );
}

export function KeyManager() {
  const qc = useQueryClient();
  const [adding, setAdding] = useState(false);
  const { data: keys, isLoading, error } = useQuery({ queryKey: ["keys"], queryFn: api.keys.list });
  const refresh = () => { qc.invalidateQueries({ queryKey: ["keys"] }); qc.invalidateQueries({ queryKey: ["models"] }); };
  const toggle = useMutation({ mutationFn: api.keys.toggle, onSuccess: refresh });
  const remove = useMutation({
    mutationFn: api.keys.remove,
    onSuccess: () => {
      refresh();
      toast.success("Key deleted");
    },
  });

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
      <section className="rounded-lg border border-zinc-200 bg-white">
        <header className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
          <h2 className="text-sm font-medium">Your keys</h2>
          <button onClick={() => setAdding(true)} className="inline-flex items-center gap-1.5 rounded-md bg-zinc-900 px-2.5 py-1.5 text-xs text-white hover:bg-zinc-800"><Plus className="size-3.5" />Add key</button>
        </header>
        {isLoading && <div className="m-4 h-16 animate-pulse rounded bg-zinc-100" />}
        {error && <p role="alert" className="p-4 text-sm text-zinc-500">Couldn't load keys. Please refresh.</p>}
        {keys?.length === 0 && <p className="p-8 text-center text-sm text-zinc-500">No keys yet. Add one to choose your own model, or skip it and use the platform models.</p>}
        <ul className="divide-y divide-zinc-100">
          {keys?.map((k) => {
            const I = PROVIDERS[k.provider].icon;
            return (
              <li key={k.id} className="flex items-center gap-3 px-4 py-3">
                <span className="grid size-8 place-items-center rounded-md border border-zinc-200 bg-zinc-50"><I className="size-4 text-zinc-600" /></span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{k.label}</p>
                  <p className="font-mono text-xs text-zinc-500">{PROVIDERS[k.provider].name} · {k.key_hint}</p>
                </div>
                <span className={cn("rounded-full px-2 py-0.5 text-xs", k.is_active ? "bg-emerald-50 text-emerald-700" : "bg-zinc-100 text-zinc-500")}>{k.is_active ? "Active" : "Paused"}</span>
                <button role="switch" aria-checked={k.is_active} aria-label={`${k.is_active ? "Pause" : "Activate"} ${k.label}`} onClick={() => toggle.mutate(k.id)}
                  className={cn("relative h-5 w-9 rounded-full transition-colors", k.is_active ? "bg-zinc-900" : "bg-zinc-300")}>
                  <span className={cn("absolute top-0.5 size-4 rounded-full bg-white transition-all", k.is_active ? "left-[18px]" : "left-0.5")} />
                </button>
                <button aria-label={`Delete ${k.label}`} onClick={() => confirm(`Delete "${k.label}"? This can't be undone.`) && remove.mutate(k.id)} className="text-zinc-400 hover:text-red-600"><Trash2 className="size-4" /></button>
              </li>
            );
          })}
        </ul>
      </section>

      <aside className="h-fit space-y-2 rounded-lg border border-zinc-200 bg-white p-4 text-sm">
        <p className="flex items-center gap-2 font-medium"><Lock className="size-4" />How your keys are handled</p>
        <p className="text-zinc-600">Keys are encrypted before they're stored, and only a short hint is shown here. Delete a key at any time to remove it.</p>
        <p className="text-zinc-600">With no active key, resumes are generated with the platform's default models.</p>
      </aside>
      {adding && <AddKeyModal onClose={() => setAdding(false)} />}
    </div>
  );
}
