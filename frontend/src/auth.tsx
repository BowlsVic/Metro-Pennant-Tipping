import * as AppleAuthentication from "expo-apple-authentication";
import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";
import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { Platform } from "react-native";

import { api, TOKEN_KEY, User } from "@/src/api";
import { queryClient } from "@/src/query-client";
import { storage } from "@/src/utils/storage";

WebBrowser.maybeCompleteAuthSession();

const AUTH_URL = "https://auth.emergentagent.com/?redirect=";
// Emergent returns session_id in the hash fragment (or query); match the raw URL string.
const extractSessionId = (url?: string | null) => url?.match(/[?#&]session_id=([^&#]+)/)?.[1] ?? null;
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function cleanWebUrl() {
  const { pathname, search, hash } = window.location;
  const strip = (s: string, prefix: string) => {
    const p = new URLSearchParams(s.replace(/^[?#]/, ""));
    p.delete("session_id");
    const out = p.toString();
    return out ? prefix + out : "";
  };
  window.history.replaceState(window.history.state, "", pathname + strip(search, "?") + strip(hash, "#"));
}

type AuthResponse = { token: string; user: User };
type AuthCtx = {
  user: User | null;
  loading: boolean;
  authError: string | null;
  clearAuthError: () => void;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  loginWithApple: () => Promise<void>;
  logout: () => Promise<void>;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const sentIds = useRef(new Set<string>());

  const finish = useCallback(async (res: AuthResponse) => {
    await storage.secureSet(TOKEN_KEY, res.token);
    queryClient.clear();
    setAuthError(null);
    setUser(res.user);
  }, []);

  // Exchanges the one-time Google session_id exactly once (several sources can surface the same one).
  const exchange = useCallback(
    async (sid: string) => {
      if (sentIds.current.has(sid)) return;
      sentIds.current.add(sid);
      await finish(await api<AuthResponse>("/auth/session", { method: "POST", body: { session_id: sid } }));
    },
    [finish],
  );

  useEffect(() => {
    const sub =
      Platform.OS === "web"
        ? null
        : Linking.addEventListener("url", ({ url }) => {
            const sid = extractSessionId(url);
            if (sid) exchange(sid).catch((e) => setAuthError(e instanceof Error ? e.message : "Google sign-in failed"));
          });
    (async () => {
      // A session_id on the URL is processed first, before any stored token.
      const sid = extractSessionId(Platform.OS === "web" ? window.location.href : await Linking.getInitialURL());
      if (sid) {
        try {
          await exchange(sid);
          if (Platform.OS === "web") cleanWebUrl();
          setLoading(false);
          return;
        } catch (e) {
          setAuthError(e instanceof Error ? e.message : "Google sign-in failed");
          if (Platform.OS === "web") cleanWebUrl();
        }
      }
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
    return () => sub?.remove();
  }, [exchange]);

  const login = useCallback(async (email: string, password: string) => {
    await finish(await api("/auth/login", { method: "POST", body: { email: email.trim(), password } }));
  }, [finish]);

  const register = useCallback(async (name: string, email: string, password: string) => {
    await finish(await api("/auth/register", { method: "POST", body: { name: name.trim(), email: email.trim(), password } }));
  }, [finish]);

  const loginWithGoogle = useCallback(async () => {
    setAuthError(null);
    if (Platform.OS === "web") {
      window.location.href = AUTH_URL + encodeURIComponent(window.location.origin + "/");
      return;
    }
    const redirect = Linking.createURL("");
    let captured: string | null = null;
    const sub = Linking.addEventListener("url", ({ url }) => (captured = url));
    try {
      const result = await WebBrowser.openAuthSessionAsync(AUTH_URL + encodeURIComponent(redirect), redirect);
      let sid = extractSessionId(result.type === "success" ? result.url : null) ?? extractSessionId(captured);
      if (!sid && result.type !== "success") {
        await sleep(700); // Android Custom Tabs can report "dismiss" just before the deep link lands
        sid = extractSessionId(captured) ?? extractSessionId(await Linking.getInitialURL());
      }
      if (sid) await exchange(sid);
    } finally {
      sub.remove();
    }
  }, [exchange]);

  const loginWithApple = useCallback(async () => {
    setAuthError(null);
    try {
      const cred = await AppleAuthentication.signInAsync({
        requestedScopes: [AppleAuthentication.AppleAuthenticationScope.FULL_NAME, AppleAuthentication.AppleAuthenticationScope.EMAIL],
      });
      const name = [cred.fullName?.givenName, cred.fullName?.familyName].filter(Boolean).join(" ") || null;
      await finish(await api<AuthResponse>("/auth/apple", { method: "POST", body: { identity_token: cred.identityToken, name, email: cred.email } }));
    } catch (e) {
      if ((e as { code?: string }).code === "ERR_REQUEST_CANCELED") return;
      throw e;
    }
  }, [finish]);

  const logout = useCallback(async () => {
    await storage.secureRemove(TOKEN_KEY);
    queryClient.clear();
    setUser(null);
  }, []);

  return (
    <Ctx.Provider
      value={{ user, loading, authError, clearAuthError: () => setAuthError(null), login, register, loginWithGoogle, loginWithApple, logout }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth outside provider");
  return c;
}
