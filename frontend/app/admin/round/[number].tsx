import Ionicons from "@react-native-vector-icons/ionicons";
import { useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Switch, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, MatchItem, Team } from "@/src/api";
import { AdminHeader } from "@/src/components/AdminHeader";
import { TeamLogo } from "@/src/components/TeamLogo";
import { TeamPickerModal } from "@/src/components/TeamPickerModal";
import { useToast } from "@/src/components/Toast";
import { Button } from "@/src/components/ui";
import { useRound, useRounds, useTeams } from "@/src/hooks";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

type PickerState = { mode: "add-home" } | { mode: "add-away"; home: Team } | { mode: "edit"; match: MatchItem; side: "home" | "away" } | null;

export default function AdminRound() {
  const { number } = useLocalSearchParams<{ number: string }>();
  const n = Number(number);
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const qc = useQueryClient();
  const toast = useToast();
  const round = useRound(n);
  const rounds = useRounds();
  const teams = useTeams();
  const [picker, setPicker] = useState<PickerState>(null);
  const [busy, setBusy] = useState(false);

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["round", n] });
    qc.invalidateQueries({ queryKey: ["rounds"] });
    qc.invalidateQueries({ queryKey: ["ladder"] });
  };

  const run = async (fn: () => Promise<unknown>, msg: string) => {
    setBusy(true);
    try {
      await fn();
      toast(msg);
      refresh();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "error");
    } finally {
      setBusy(false);
    }
  };

  const setResult = (m: MatchItem, winner: string | null) =>
    run(() => api(`/matches/${m.id}`, { method: "PUT", body: winner ? { winner_team_id: winner } : { clear_result: true } }), winner ? "Result saved" : "Result cleared");

  const onPick = (t: Team) => {
    if (!picker) return;
    if (picker.mode === "add-home") return setPicker({ mode: "add-away", home: t });
    if (picker.mode === "add-away") {
      const home = picker.home;
      setPicker(null);
      return run(() => api(`/rounds/${n}/matches`, { method: "POST", body: { home_team_id: home.id, away_team_id: t.id } }), "Match added");
    }
    const { match, side } = picker;
    setPicker(null);
    run(() => api(`/matches/${match.id}`, { method: "PUT", body: side === "home" ? { home_team_id: t.id } : { away_team_id: t.id } }), "Fixture updated");
  };

  const r = round.data;
  const isLast = rounds.data?.[rounds.data.length - 1]?.number === n;

  return (
    <View style={styles.root}>
      <AdminHeader title={r?.name ?? "Round"} right={busy ? <ActivityIndicator color={colors.brandPrimary} /> : null} />
      {!r ? (
        <View style={styles.center}><ActivityIndicator color={colors.brandPrimary} /></View>
      ) : (
        <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, paddingBottom: insets.bottom + spacing.lg }}>
          <View style={styles.lockRow}>
            <Ionicons name={r.locked ? "lock-closed" : "lock-open"} size={20} color={r.locked ? colors.warning : colors.onSurfaceTertiary} />
            <View style={{ flex: 1 }}>
              <Text style={styles.lockTitle}>Lock tipping</Text>
              <Text style={styles.lockSub}>Stops players changing tips for this round</Text>
            </View>
            <Switch
              testID="round-lock-switch"
              value={r.locked}
              onValueChange={(v) => run(() => api(`/rounds/${n}`, { method: "PUT", body: { locked: v } }), v ? "Round locked" : "Round unlocked")}
              trackColor={{ true: colors.brandPrimary, false: colors.surfaceTertiary }}
              thumbColor={colors.onSurface}
            />
          </View>

          {r.matches.map((m, i) => {
            const home = teams.map[m.home_team_id];
            const away = teams.map[m.away_team_id];
            const opt = (label: string, value: string | null, key: string) => {
              const active = value === null ? !m.winner_team_id : m.winner_team_id === value;
              return (
                <Pressable key={key} testID={`admin-match-${i}-result-${key}`} onPress={() => setResult(m, value)} style={[styles.opt, active && styles.optActive]}>
                  <Text numberOfLines={1} style={[styles.optText, active && styles.optTextActive]}>{label}</Text>
                </Pressable>
              );
            };
            return (
              <View key={m.id} testID={`admin-match-${i}`} style={styles.card}>
                <View style={styles.teamsRow}>
                  <Pressable testID={`admin-match-${i}-edit-home`} onPress={() => setPicker({ mode: "edit", match: m, side: "home" })} style={styles.teamBtn}>
                    <TeamLogo team={home} size={36} />
                    <Text numberOfLines={1} style={styles.teamName}>{home?.name}</Text>
                  </Pressable>
                  <Text style={styles.vs}>VS</Text>
                  <Pressable testID={`admin-match-${i}-edit-away`} onPress={() => setPicker({ mode: "edit", match: m, side: "away" })} style={styles.teamBtn}>
                    <TeamLogo team={away} size={36} />
                    <Text numberOfLines={1} style={styles.teamName}>{away?.name}</Text>
                  </Pressable>
                  <Pressable testID={`admin-match-${i}-delete`} hitSlop={8} onPress={() => run(() => api(`/matches/${m.id}`, { method: "DELETE" }), "Match removed")} style={styles.del}>
                    <Ionicons name="trash-outline" size={20} color={colors.error} />
                  </Pressable>
                </View>
                <Text style={styles.resultLbl}>RESULT</Text>
                <View style={styles.opts}>
                  {opt(home?.short ?? "Home", m.home_team_id, "home")}
                  {opt("Draw", "draw", "draw")}
                  {opt(away?.short ?? "Away", m.away_team_id, "away")}
                  {opt("TBD", null, "clear")}
                </View>
              </View>
            );
          })}

          <Button testID="add-match-button" title="Add match" variant="ghost" onPress={() => setPicker({ mode: "add-home" })} />
          {r.is_final && isLast && (
            <Button
              testID="delete-round-button"
              title="Delete this finals round"
              variant="danger"
              onPress={() =>
                run(async () => {
                  await api(`/rounds/${n}`, { method: "DELETE" });
                  router.back();
                }, "Round deleted")
              }
            />
          )}
        </ScrollView>
      )}
      <TeamPickerModal
        visible={!!picker}
        title={picker?.mode === "add-home" ? "Pick home team" : picker?.mode === "add-away" ? "Pick away team" : "Swap team"}
        teams={teams.data ?? []}
        exclude={picker?.mode === "add-away" ? picker.home.id : picker?.mode === "edit" ? (picker.side === "home" ? picker.match.away_team_id : picker.match.home_team_id) : undefined}
        onPick={onPick}
        onClose={() => setPicker(null)}
      />
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  lockRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: c.surfaceSecondary, borderRadius: radius.md, padding: spacing.md },
  lockTitle: { color: c.onSurface, fontFamily: fonts.displaySemi, fontSize: 18 },
  lockSub: { color: c.onSurfaceTertiary, fontFamily: fonts.text, fontSize: 12 },
  card: { backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, padding: spacing.md, gap: spacing.sm, borderWidth: 1, borderColor: c.border },
  teamsRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  teamBtn: { flex: 1, flexDirection: "row", alignItems: "center", gap: spacing.sm, minHeight: 44 },
  teamName: { flex: 1, color: c.onSurface, fontFamily: fonts.displaySemi, fontSize: 15 },
  vs: { color: c.muted, fontFamily: fonts.display, fontSize: 13 },
  del: { width: 36, height: 44, alignItems: "center", justifyContent: "center" },
  resultLbl: { color: c.muted, fontFamily: fonts.display, fontSize: 12, letterSpacing: 1 },
  opts: { flexDirection: "row", gap: spacing.xs },
  opt: { flex: 1, height: 40, borderRadius: radius.sm, backgroundColor: c.surfaceTertiary, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: c.border },
  optActive: { backgroundColor: c.brandPrimary, borderColor: c.brandPrimary },
  optText: { color: c.onSurfaceSecondary, fontFamily: fonts.displaySemi, fontSize: 15 },
  optTextActive: { color: c.onBrandPrimary },
}));
