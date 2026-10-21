import { useQuery } from "@tanstack/react-query";

import { api, LadderRow, RoundDetail, RoundSummary, Team } from "@/src/api";

export function useTeams() {
  const q = useQuery({ queryKey: ["teams"], queryFn: () => api<Team[]>("/teams") });
  const map: Record<string, Team> = {};
  (q.data ?? []).forEach((t) => (map[t.id] = t));
  return { ...q, map };
}

export const useRounds = () => useQuery({ queryKey: ["rounds"], queryFn: () => api<RoundSummary[]>("/rounds") });

export const useRound = (n: number | null) =>
  useQuery({ queryKey: ["round", n], queryFn: () => api<RoundDetail>(`/rounds/${n}`), enabled: n != null });

export const useLadder = () => useQuery({ queryKey: ["ladder"], queryFn: () => api<LadderRow[]>("/leaderboard") });
