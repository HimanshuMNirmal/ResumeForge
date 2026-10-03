"use client";

import { useState, type ReactNode } from "react";
import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster, toast } from "sonner";
import { AuthProvider } from "@/lib/auth-context";
import { ApiError } from "@/lib/api-client";

export function Providers({ children }: { children: ReactNode }) {
  const [qc] = useState(
    () =>
      new QueryClient({
        queryCache: new QueryCache({
          onError: (error: any, query) => {
            // Ignore 401 or session expired errors (handled globally by central interceptor)
            if (error?.status === 401 || error?.isSessionExpired) return;

            // Allow queries to opt out of global toasts
            if (query.meta?.suppressGlobalError) return;

            const msg = error instanceof Error ? error.message : "Failed to load data";
            toast.error(msg);
          },
        }),
        mutationCache: new MutationCache({
          onError: (error: any, _variables, _context, mutation) => {
            // Ignore 401 or session expired errors
            if (error?.status === 401 || error?.isSessionExpired) return;

            // Allow mutations to opt out of global toasts
            if (mutation.meta?.suppressGlobalError) return;

            if (error instanceof ApiError && error.details.length > 1) {
              const bullets = error.details
                .map((d) => (d.field ? `• ${d.field}: ${d.message}` : `• ${d.message}`))
                .join("\n");
              toast.error(error.message, {
                description: bullets,
                duration: 6000,
              });
            } else {
              const msg = error instanceof Error ? error.message : "Action failed";
              toast.error(msg);
            }
          },
        }),
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: (failureCount, error: any) => {
              if (error?.status === 401 || error?.status === 403 || error?.status === 404) return false;
              return failureCount < 1;
            },
          },
        },
      })
  );

  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>
        {children}
        <Toaster position="bottom-right" toastOptions={{ className: "text-sm" }} />
      </AuthProvider>
    </QueryClientProvider>
  );
}
