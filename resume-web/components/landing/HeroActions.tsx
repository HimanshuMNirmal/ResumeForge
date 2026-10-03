"use client";

import Link from "next/link";
import { ArrowRight, FileText, Loader2, Sparkles, UserRound, WandSparkles } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export function HeroActions() {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="mt-6 flex h-10 items-center gap-3">
        <div className="h-10 w-36 animate-pulse rounded-md bg-zinc-200" />
        <div className="h-10 w-28 animate-pulse rounded-md bg-zinc-100" />
      </div>
    );
  }

  if (isAuthenticated) {
    return (
      <div className="mt-6 space-y-3">
        <p className="text-xs font-medium text-emerald-700">
          Signed in as <span className="font-semibold">{user?.name || user?.email}</span>
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/builder"
            className="inline-flex items-center gap-2 rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-zinc-800"
          >
            <WandSparkles className="size-4" />
            Open Resume Studio
          </Link>
          <Link
            href="/profile"
            className="inline-flex items-center gap-1.5 rounded-md border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-700 shadow-sm transition hover:bg-zinc-50"
          >
            <UserRound className="size-4" />
            Edit Profile
          </Link>
          <Link
            href="/history"
            className="inline-flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium text-zinc-600 transition hover:text-zinc-900"
          >
            <FileText className="size-4" />
            History
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-6 space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <Link
          href="/register"
          className="inline-flex items-center gap-2 rounded-md bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-zinc-800"
        >
          Get started free
          <ArrowRight className="size-4" />
        </Link>
        <Link
          href="/login"
          className="inline-flex items-center rounded-md border border-zinc-300 bg-white px-5 py-2.5 text-sm font-medium text-zinc-700 shadow-sm transition hover:bg-zinc-50 hover:text-zinc-900"
        >
          Sign in
        </Link>
      </div>
      <p className="text-xs text-zinc-500">
        No API keys or credit card needed · Free truthful tailoring included
      </p>
    </div>
  );
}
