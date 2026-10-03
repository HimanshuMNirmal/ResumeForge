"use client";

import { useState } from "react";
import Link from "next/link";
import { FileText, Menu, X, ArrowRight, UserRound, LogOut } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export function LandingNavbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 w-full border-b border-zinc-200/80 bg-white/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3.5 md:px-6">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex size-7 items-center justify-center rounded-md bg-zinc-900 text-white shadow-xs">
            <FileText className="size-4" />
          </div>
          <span className="text-base font-semibold tracking-tight text-zinc-900">ResumeForge</span>
        </Link>

        {/* Desktop Navigation */}
        <nav aria-label="Main" className="hidden items-center gap-2.5 sm:flex">
          {isAuthenticated ? (
            <>
              <Link
                href="/profile"
                className="rounded-md px-3 py-1.5 text-sm font-medium text-zinc-600 transition hover:text-zinc-900 hover:bg-zinc-100"
              >
                Profile
              </Link>
              <Link
                href="/history"
                className="rounded-md px-3 py-1.5 text-sm font-medium text-zinc-600 transition hover:text-zinc-900 hover:bg-zinc-100"
              >
                History
              </Link>
              <Link
                href="/builder"
                className="inline-flex items-center gap-1.5 rounded-md bg-zinc-900 px-3.5 py-1.5 text-sm font-medium text-white shadow-xs transition hover:bg-zinc-800"
              >
                Open Studio
                <ArrowRight className="size-3.5" />
              </Link>
              <button
                onClick={() => logout()}
                className="ml-2 text-xs font-medium text-zinc-500 transition hover:text-zinc-900"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="rounded-md px-3 py-1.5 text-sm font-medium text-zinc-600 transition hover:text-zinc-900 hover:bg-zinc-100"
              >
                Sign in
              </Link>
              <Link
                href="/register"
                className="inline-flex items-center gap-1.5 rounded-md bg-zinc-900 px-3.5 py-1.5 text-sm font-medium text-white shadow-xs transition hover:bg-zinc-800"
              >
                Get started
                <ArrowRight className="size-3.5" />
              </Link>
            </>
          )}
        </nav>

        {/* Mobile Hamburger Toggle */}
        <button
          type="button"
          onClick={() => setMobileOpen(!mobileOpen)}
          className="flex size-9 items-center justify-center rounded-md border border-zinc-200 text-zinc-700 hover:bg-zinc-100 sm:hidden"
          aria-expanded={mobileOpen}
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
        >
          {mobileOpen ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </div>

      {/* Mobile Drawer / Dropdown */}
      {mobileOpen && (
        <div className="border-t border-zinc-200 bg-white px-4 py-4 shadow-lg sm:hidden">
          {isAuthenticated ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 rounded-lg bg-zinc-50 px-3 py-2 text-xs text-zinc-600">
                <UserRound className="size-4 text-zinc-400" />
                <span className="truncate font-medium">{user?.email}</span>
              </div>
              <div className="flex flex-col space-y-1">
                <Link
                  href="/builder"
                  onClick={() => setMobileOpen(false)}
                  className="flex items-center justify-between rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white shadow-xs"
                >
                  Open Studio
                  <ArrowRight className="size-4" />
                </Link>
                <Link
                  href="/profile"
                  onClick={() => setMobileOpen(false)}
                  className="rounded-md px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                >
                  Career Profile
                </Link>
                <Link
                  href="/history"
                  onClick={() => setMobileOpen(false)}
                  className="rounded-md px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                >
                  Resume History
                </Link>
                <Link
                  href="/settings/keys"
                  onClick={() => setMobileOpen(false)}
                  className="rounded-md px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                >
                  API Keys
                </Link>
              </div>
              <div className="border-t border-zinc-100 pt-2">
                <button
                  onClick={() => {
                    setMobileOpen(false);
                    logout();
                  }}
                  className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-medium text-red-600 hover:bg-red-50"
                >
                  <LogOut className="size-4" />
                  Sign out
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <Link
                href="/register"
                onClick={() => setMobileOpen(false)}
                className="flex items-center justify-center gap-1.5 rounded-md bg-zinc-900 px-4 py-2.5 text-center text-sm font-medium text-white shadow-xs"
              >
                Get started free
                <ArrowRight className="size-4" />
              </Link>
              <Link
                href="/login"
                onClick={() => setMobileOpen(false)}
                className="flex items-center justify-center rounded-md border border-zinc-200 bg-white px-4 py-2 text-center text-sm font-medium text-zinc-700 hover:bg-zinc-50"
              >
                Sign in
              </Link>
            </div>
          )}
        </div>
      )}
    </header>
  );
}
