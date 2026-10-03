"use client";

import React, { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, getStoredToken } from "@/lib/api-client";
import type { LoginRequest, RegisterRequest, User } from "@/types/api";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (creds: LoginRequest) => Promise<void>;
  register: (creds: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    let isMounted = true;

    async function initAuth() {
      const token = getStoredToken();
      if (!token) {
        if (isMounted) setIsLoading(false);
        return;
      }

      try {
        const currentUser = await api.auth.me();
        if (isMounted) setUser(currentUser);
      } catch {
        // Try token refresh via http-only cookie
        try {
          await api.auth.refresh();
          const refreshedUser = await api.auth.me();
          if (isMounted) setUser(refreshedUser);
        } catch {
          if (isMounted) setUser(null);
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    initAuth();
    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (creds: LoginRequest) => {
    await api.auth.login(creds);
    const currentUser = await api.auth.me();
    setUser(currentUser);
  };

  const register = async (creds: RegisterRequest) => {
    const res = await api.auth.register(creds);
    if (res.user) {
      setUser(res.user);
    } else {
      const currentUser = await api.auth.me();
      setUser(currentUser);
    }
  };

  const logout = async () => {
    try {
      await api.auth.logout();
    } catch {
      // ignore
    } finally {
      setUser(null);
      router.push("/login");
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
