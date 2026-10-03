"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { FileText, KeyRound, LogOut, Loader2, Sparkles, UserRound, WandSparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";

const NAV = [
  { href: "/profile", label: "Profile", icon: UserRound },
  { href: "/builder", label: "Builder", icon: WandSparkles },
  { href: "/history", label: "History", icon: FileText },
  { href: "/settings/keys", label: "API keys", icon: KeyRound },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const { user, isLoading, isAuthenticated, logout } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-zinc-500">
          <Loader2 className="size-6 animate-spin text-zinc-900" />
          <p className="text-sm font-medium">Loading session...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Will redirect in useEffect
  }

  return (
    <div className="mx-auto flex max-w-7xl gap-8 px-4 py-6 md:px-6">
      <nav aria-label="Main" className="sticky top-6 hidden h-[calc(100vh-3rem)] w-56 shrink-0 flex-col justify-between md:flex print:hidden">
        <div>
          <Link href="/" className="mb-6 flex items-center gap-2 px-2 text-base font-bold tracking-tight text-zinc-900">
            <div className="flex size-7 items-center justify-center rounded-md bg-zinc-900 text-white shadow-sm">
              <Sparkles className="size-4" />
            </div>
            ResumeForge
          </Link>
          <ul className="space-y-1">
            {NAV.map(({ href, label, icon: Icon }) => (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={path.startsWith(href) ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm text-zinc-600 transition-colors hover:bg-zinc-100 hover:text-zinc-900",
                    path.startsWith(href) && "bg-zinc-100 font-semibold text-zinc-900"
                  )}
                >
                  <Icon className="size-4" />
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        {/* User Card & Logout */}
        <div className="border-t border-zinc-200/80 pt-4">
          <div className="mb-3 px-2">
            <p className="truncate text-xs font-semibold text-zinc-900">{user?.name || "User"}</p>
            <p className="truncate text-[11px] text-zinc-500">{user?.email}</p>
          </div>
          <button
            onClick={() => logout()}
            className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs font-medium text-zinc-600 hover:bg-red-50 hover:text-red-700"
          >
            <LogOut className="size-3.5" />
            Sign out
          </button>
        </div>
      </nav>

      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}
