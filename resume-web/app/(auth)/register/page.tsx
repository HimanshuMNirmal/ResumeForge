"use client";

import { useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth-context";
import { ErrorAlert } from "@/components/ui/ErrorAlert";

function RegisterForm() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<any>(null);

  const { register } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect") || "/profile";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setLoading(true);

    try {
      await register({ name, email, password });
      toast.success("Account created successfully!");
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
        <h2 className="text-xl font-semibold tracking-tight text-zinc-900">Create your account</h2>
        <p className="mt-1 text-sm text-zinc-500">
          Get started with truthful, ATS-optimized resume tailoring.
        </p>
      </div>

      {error && <ErrorAlert error={error} title="Registration failed" />}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="name" className="block text-xs font-medium text-zinc-700">
            Full name
          </label>
          <input
            id="name"
            type="text"
            required
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1.5 block w-full rounded-md border border-zinc-300 px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 shadow-sm focus:border-zinc-900 focus:outline-none focus:ring-1 focus:ring-zinc-900"
            placeholder="Jane Doe"
          />
        </div>

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
          <label htmlFor="password" className="block text-xs font-medium text-zinc-700">
            Password (min 8 characters)
          </label>
          <input
            id="password"
            type="password"
            required
            autoComplete="new-password"
            minLength={8}
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
              Creating account...
            </>
          ) : (
            "Create account"
          )}
        </button>
      </form>

      <div className="text-center text-xs text-zinc-500">
        Already have an account?{" "}
        <Link href={`/login${redirectUrl !== "/profile" ? `?redirect=${encodeURIComponent(redirectUrl)}` : ""}`} className="font-semibold text-zinc-900 hover:underline">
          Sign in instead
        </Link>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-sm text-zinc-400">Loading...</div>}>
      <RegisterForm />
    </Suspense>
  );
}
