import React, { createContext, useCallback, useContext, useEffect, useState } from "react";

import { api, TOKEN_KEY, User } from "@/src/api";
import { queryClient } from "@/src/query-client";
import { storage } from "@/src/utils/storage";

type AuthCtx = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const token = await storage.secureGet(TOKEN_KEY, null);
      if (token) {
        try {
          setUser(await api<User>("/auth/me"));
        } catch {
          await storage.secureRemove(TOKEN_KEY);
        }
      }
      setLoading(false);
    })();
  }, []);

  const finish = async (res: { token: string; user: User }) => {
    await storage.secureSet(TOKEN_KEY, res.token);
    queryClient.clear();
    setUser(res.user);
  };

  const login = useCallback(async (email: string, password: string) => {
    await finish(await api("/auth/login", { method: "POST", body: { email: email.trim(), password } }));
  }, []);

  const register = useCallback(async (name: string, email: string, password: string) => {
    await finish(await api("/auth/register", { method: "POST", body: { name: name.trim(), email: email.trim(), password } }));
  }, []);

  const logout = useCallback(async () => {
    await storage.secureRemove(TOKEN_KEY);
    queryClient.clear();
    setUser(null);
  }, []);

  return <Ctx.Provider value={{ user, loading, login, register, logout }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth outside provider");
  return c;
}
