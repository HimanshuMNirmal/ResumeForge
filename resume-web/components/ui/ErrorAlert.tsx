"use client";

import { useState } from "react";
import { AlertCircle, ChevronDown } from "lucide-react";
import { ApiError } from "@/lib/api-client";

interface ErrorAlertProps {
  error: unknown;
  className?: string;
  title?: string;
}

export function ErrorAlert({ error, className = "", title }: ErrorAlertProps) {
  const [open, setOpen] = useState(true);
  if (!error) return null;

  let message = "";
  let errors: string[] = [];

  if (error instanceof ApiError) {
    message = error.message;
    errors = error.errors || [];
  } else if (error instanceof Error) {
    message = error.message;
  } else if (typeof error === "string") {
    message = error;
  } else {
    message = "An unexpected error occurred.";
  }

  // Filter out any errors that are identical to the whole message
  const detailedErrors = errors.filter((e) => e && e !== message);

  return (
    <div
      role="alert"
      className={`rounded-lg border border-red-200 bg-red-50/90 p-3.5 text-red-900 shadow-sm transition-all ${className}`}
    >
      <div className="flex items-start gap-2.5">
        <AlertCircle className="mt-0.5 size-4 shrink-0 text-red-600" />
        <div className="min-w-0 flex-1">
          {title && (
            <p className="text-xs font-semibold uppercase tracking-wider text-red-700">
              {title}
            </p>
          )}
          <p className="text-sm font-medium leading-snug break-words">{message}</p>

          {detailedErrors.length > 0 && (
            <div className="mt-2.5 border-t border-red-200/80 pt-2">
              <button
                type="button"
                onClick={() => setOpen(!open)}
                className="flex items-center gap-1 text-xs font-medium text-red-700 hover:text-red-900"
              >
                <span>
                  {detailedErrors.length} validation issue{detailedErrors.length > 1 ? "s" : ""}
                </span>
                <ChevronDown
                  className={`size-3.5 transition-transform duration-150 ${open ? "rotate-180" : ""}`}
                />
              </button>
              {open && (
                <ul className="mt-1.5 space-y-1 pl-1 text-xs font-mono text-red-800">
                  {detailedErrors.map((err, i) => (
                    <li key={i} className="flex items-start gap-1.5">
                      <span className="font-bold text-red-500">•</span>
                      <span className="break-words">{err}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
