"use client";

import { useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth-context";
import { ErrorAlert } from "@/components/ui/ErrorAlert";

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<any>(null);

  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect") || "/profile";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login({ email, password });
      toast.success("Welcome back!");
      router.push(redirectUrl);
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-zinc-900">Sign in to your account</h2>
        <p className="mt-1 text-sm text-zinc-500">
          Enter your credentials to manage profiles and generate resumes.
        </p>
      </div>

      {error && <ErrorAlert error={error} title="Sign in failed" />}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="email" className="block text-xs font-medium text-zinc-700">
            Email address
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1.5 block w-full rounded-md border border-zinc-300 px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 shadow-sm focus:border-zinc-900 focus:outline-none focus:ring-1 focus:ring-zinc-900"
            placeholder="you@example.com"
          />
        </div>

        <div>
          <div className="flex items-center justify-between">
            <label htmlFor="password" className="block text-xs font-medium text-zinc-700">
              Password
            </label>
          </div>
          <input
            id="password"
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1.5 block w-full rounded-md border border-zinc-300 px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 shadow-sm focus:border-zinc-900 focus:outline-none focus:ring-1 focus:ring-zinc-900"
            placeholder="••••••••"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="flex w-full items-center justify-center gap-2 rounded-md bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white shadow hover:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-900 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Signing in...
            </>
          ) : (
            "Sign in"
          )}
        </button>
      </form>

      <div className="text-center text-xs text-zinc-500">
        Don&apos;t have an account?{" "}
        <Link href={`/register${redirectUrl !== "/profile" ? `?redirect=${encodeURIComponent(redirectUrl)}` : ""}`} className="font-semibold text-zinc-900 hover:underline">
          Create one now
        </Link>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-sm text-zinc-400">Loading...</div>}>
      <LoginForm />
    </Suspense>
  );
}
