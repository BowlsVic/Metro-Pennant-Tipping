import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { AllTips, api, LadderRow, RoundDetail, RoundRecap, RoundSummary, RoundWinner, Team } from "@/src/api";

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

// Keyed under "ladder" so every ladder invalidation refreshes round winners too.
export const useRoundWinners = () =>
  useQuery({ queryKey: ["ladder", "round-winners"], queryFn: () => api<RoundWinner[]>("/round-winners") });

export const useAllTips = (n: number) =>
  useQuery({ queryKey: ["all-tips", n], queryFn: () => api<AllTips>(`/rounds/${n}/all-tips`) });

export const useRoundRecap = (n: number, enabled: boolean) =>
  useQuery({ queryKey: ["ladder", "recap", n], queryFn: () => api<RoundRecap>(`/rounds/${n}/recap`), enabled });

// Ticks every 30s so kick-off locks update on screen without a refetch.
export function useNow(intervalMs = 30000) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(t);
  }, [intervalMs]);
  return now;
}
