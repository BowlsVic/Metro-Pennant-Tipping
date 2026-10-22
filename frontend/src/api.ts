import { storage } from "@/src/utils/storage";

export const TOKEN_KEY = "auth_token";
const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;

export type Team = {
  id: string; name: string; short: string; color: string; secondary: string; icon: string;
  logo_path?: string | null; logo_v?: number;
};

export const teamLogoUrl = (t: Team) => `${BASE}/api/teams/${t.id}/logo?v=${t.logo_v ?? 0}`;


export type User = { id: string; email: string; name: string; role: "user" | "admin" };
export type RoundSummary = {
  id: string; number: number; name: string; is_final: boolean; locked: boolean;
  match_count: number; decided_count: number; revealed_count: number; tipped_count: number; complete: boolean;
};
export type MatchItem = {
  id: string; round_number: number; order: number; home_team_id: string; away_team_id: string;
  winner_team_id: string | null; kickoff: string | null; started: boolean; group: string | null;
  my_tip: string | null; locked: boolean; correct: boolean | null;
};
export type AllTips = {
  number: number; name: string;
  matches: {
    match_id: string; order: number; home_team_id: string; away_team_id: string; winner_team_id: string | null;
    kickoff: string | null; revealed: boolean; home_count: number; away_count: number;
  }[];
  players: { user_id: string; name: string; tips: Record<string, string>; correct: number }[];
};
export type RoundDetail = RoundSummary & {
  matches: MatchItem[]; my_correct: number; my_bonus: number; my_points: number;
};
export type LadderRow = { user_id: string; name: string; correct: number; bonus: number; points: number; tips: number; rank: number; round_wins: number; streak: number; best_streak: number };
export type RoundWinner = { number: number; name: string; points: number; winners: { user_id: string; name: string }[] };
export type RoundRecap = {
  available: boolean; number: number; name: string; correct: number; total: number; bonus: number; points: number; tipped: number;
  best_pick: { match_id: string; team_id: string; opponent_id: string; share: number; backers: number } | null;
  rank: number | null; prev_rank: number | null; players: number; won_round: boolean; round_top_points: number;
};
export type SyncStatus = {
  last_sync?: string; updated?: number; completed_found?: number; finals_added?: number; kickoffs_updated?: number;
  error?: string | null; last_attempt?: string;
};

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
