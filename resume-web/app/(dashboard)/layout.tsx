"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileText, KeyRound, UserRound, WandSparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/profile", label: "Profile", icon: UserRound },
  { href: "/builder", label: "Builder", icon: WandSparkles },
  { href: "/history", label: "History", icon: FileText },
  { href: "/settings/keys", label: "API keys", icon: KeyRound },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  return (
    <div className="mx-auto flex max-w-7xl gap-8 px-4 py-6 md:px-6">
      <nav aria-label="Main" className="sticky top-6 hidden h-fit w-48 shrink-0 md:block print:hidden">
        <Link href="/" className="mb-6 block px-2 text-sm font-semibold tracking-tight">Tailor</Link>
        <ul className="space-y-0.5">
          {NAV.map(({ href, label, icon: Icon }) => (
            <li key={href}>
              <Link href={href} aria-current={path.startsWith(href) ? "page" : undefined}
                className={cn("flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-zinc-600 transition-colors hover:bg-zinc-100",
                  path.startsWith(href) && "bg-zinc-100 font-medium text-zinc-900")}>
                <Icon className="size-4" />{label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}
