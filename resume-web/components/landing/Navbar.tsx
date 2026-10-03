"use client";

import Link from "next/link";
import { Sparkles } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export function LandingNavbar() {
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 md:px-6">
      <Link href="/" className="flex items-center gap-2">
        <div className="flex size-7 items-center justify-center rounded-md bg-zinc-900 text-white shadow-sm">
          <Sparkles className="size-4" />
        </div>
        <span className="text-base font-bold tracking-tight text-zinc-900">ResumeForge</span>
      </Link>

      <nav aria-label="Main" className="flex items-center gap-3 text-sm">
        {isAuthenticated ? (
          <>
            <Link
              href="/profile"
              className="rounded-md px-3 py-1.5 font-medium text-zinc-700 hover:text-zinc-900"
            >
              Dashboard
            </Link>
            <Link
              href="/builder"
              className="rounded-md bg-zinc-900 px-3.5 py-1.5 font-medium text-white shadow-sm hover:bg-zinc-800"
            >
              Open builder
            </Link>
            <button
              onClick={() => logout()}
              className="text-xs font-medium text-zinc-500 hover:text-zinc-900"
            >
              Sign out
            </button>
          </>
        ) : (
          <>
            <Link
              href="/login"
              className="rounded-md px-3 py-1.5 font-medium text-zinc-700 hover:text-zinc-900"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="rounded-md bg-zinc-900 px-3.5 py-1.5 font-medium text-white shadow-sm hover:bg-zinc-800"
            >
              Get started
            </Link>
          </>
        )}
      </nav>
    </header>
  );
}
