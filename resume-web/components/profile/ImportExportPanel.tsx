"use client";
import { useRef, useState, type DragEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CheckCircle2, ChevronDown, Download, FileJson, Loader2, TriangleAlert, Upload } from "lucide-react";
import { api, ImportValidationError } from "@/lib/api-client";
import { cn } from "@/lib/utils";

type DropState = "idle" | "dragging" | "validating" | "success" | "error";

export function ImportExportPanel() {
  const qc = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<DropState>("idle");
  const [message, setMessage] = useState("");
  const [errors, setErrors] = useState<string[]>([]);
  const [open, setOpen] = useState(true);

  const importer = useMutation({
    mutationFn: api.profile.import,
    onMutate: () => { setState("validating"); setErrors([]); },
    onSuccess: (r) => {
      qc.setQueryData(["profile"], r.profile);
      qc.invalidateQueries({ queryKey: ["profile"] });
      setState("success"); setMessage(r.message);
      toast.success("Profile imported");
    },
    onError: (e) => {
      setState("error");
      if (e instanceof ImportValidationError) { setErrors(e.errors); setMessage(e.message); setOpen(true); }
      else setMessage(e.message);
    },
  });

  const handleFile = (file?: File) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".json")) {
      setState("error"); setErrors([]); setMessage("Only .json files are supported."); return;
    }
    importer.mutate(file);
  };
  const onDrop = (e: DragEvent) => { e.preventDefault(); handleFile(e.dataTransfer.files[0]); };
  const run = (fn: () => Promise<void>) => fn().catch((e) => toast.error(e.message));

  const copy = {
    idle: ["Drop a profile JSON here", "or click to browse"],
    dragging: ["Release to import", ""],
    validating: ["Checking your file…", ""],
    success: ["Profile imported", message],
    error: [errors.length ? `${errors.length} field${errors.length > 1 ? "s" : ""} need fixing` : "Import failed", message],
  }[state];
  const Icon = { idle: Upload, dragging: FileJson, validating: Loader2, success: CheckCircle2, error: TriangleAlert }[state];

  return (
    <section aria-labelledby="ie-title" className="rounded-lg border border-zinc-200 bg-white p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 id="ie-title" className="text-sm font-medium">Import or export</h2>
        <div className="flex gap-2">
          <button onClick={() => run(api.profile.sample)} className="btn-ghost inline-flex items-center gap-1.5 rounded-md border border-zinc-200 px-2.5 py-1.5 text-xs hover:bg-zinc-50">
            <Download className="size-3.5" /> Download sample JSON
          </button>
          <button onClick={() => run(api.profile.export)} className="inline-flex items-center gap-1.5 rounded-md bg-zinc-900 px-2.5 py-1.5 text-xs text-white hover:bg-zinc-800">
            <Download className="size-3.5" /> Export my profile
          </button>
        </div>
      </div>

      <div role="button" tabIndex={0} aria-busy={state === "validating"}
        onClick={() => input.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setState("dragging"); }}
        onDragLeave={() => setState("idle")}
        onDrop={onDrop}
        className={cn("flex cursor-pointer flex-col items-center gap-1 rounded-md border border-dashed px-4 py-8 text-center transition-colors",
          state === "idle" && "border-zinc-300 hover:border-zinc-400 hover:bg-zinc-50",
          state === "dragging" && "border-zinc-900 bg-zinc-100",
          state === "validating" && "border-zinc-300 bg-zinc-50",
          state === "success" && "border-emerald-300 bg-emerald-50",
          state === "error" && "border-red-300 bg-red-50")}>
        <Icon className={cn("size-5 text-zinc-500", state === "validating" && "animate-spin", state === "success" && "text-emerald-600", state === "error" && "text-red-600")} />
        <p className="text-sm font-medium">{copy[0]}</p>
        {copy[1] && <p className="text-xs text-zinc-500">{copy[1]}</p>}
        <input ref={input} type="file" accept="application/json,.json" hidden
          onChange={(e) => { handleFile(e.target.files?.[0]); e.target.value = ""; }} />
      </div>

      {errors.length > 0 && (
        <div className="mt-3 rounded-md border border-red-200">
          <button onClick={() => setOpen(!open)} aria-expanded={open}
            className="flex w-full items-center justify-between px-3 py-2 text-left text-xs font-medium text-red-700">
            Validation errors ({errors.length})
            <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} />
          </button>
          {open && (
            <ul className="max-h-56 space-y-1 overflow-auto border-t border-red-100 bg-red-50/50 px-3 py-2 font-mono text-xs text-red-800">
              {errors.map((er, i) => <li key={i} className="break-words">• {er}</li>)}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
