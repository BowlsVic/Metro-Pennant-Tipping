import { storage } from "@/src/utils/storage";

export const TOKEN_KEY = "auth_token";
const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;

export type Team = { id: string; name: string; short: string; color: string; secondary: string; icon: string };
export type User = { id: string; email: string; name: string; role: "user" | "admin" };
export type RoundSummary = {
  id: string; number: number; name: string; is_final: boolean; locked: boolean;
  match_count: number; decided_count: number; tipped_count: number; complete: boolean;
};
export type MatchItem = {
  id: string; round_number: number; order: number; home_team_id: string; away_team_id: string;
  winner_team_id: string | null; my_tip: string | null; locked: boolean; correct: boolean | null;
};
export type RoundDetail = RoundSummary & {
  matches: MatchItem[]; my_correct: number; my_bonus: number; my_points: number;
};
export type LadderRow = { user_id: string; name: string; correct: number; bonus: number; points: number; tips: number; rank: number };

export async function api<T>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const token = await storage.secureGet(TOKEN_KEY, null);
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${BASE}/api${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (data as { detail?: unknown }).detail;
    const msg = typeof detail === "string" ? detail : Array.isArray(detail) ? "Please check your details" : "Something went wrong";
    throw new Error(msg);
  }
  return data as T;
}
