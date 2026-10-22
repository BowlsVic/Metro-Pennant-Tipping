import Ionicons from "@react-native-vector-icons/ionicons";
import { useQueryClient } from "@tanstack/react-query";
import * as Haptics from "expo-haptics";
import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import Animated, { FadeInDown } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, MatchItem, Team } from "@/src/api";
import { RoundChips } from "@/src/components/RoundChips";
import { DivisionFilter } from "@/src/components/DivisionFilter";
import { TeamLogo } from "@/src/components/TeamLogo";
import { useToast } from "@/src/components/Toast";
import { Button, EmptyState, ErrorState } from "@/src/components/ui";
import { useNow, useRound, useRounds, useTeams } from "@/src/hooks";
import { usesNativeTabs } from "@/src/navigation";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";
import { formatKickoff, hasStarted, untilLabel } from "@/src/time";

export default function TipsScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const bottomChrome = usesNativeTabs ? insets.bottom : 0;
  const qc = useQueryClient();
  const router = useRouter();
  const toast = useToast();
  const rounds = useRounds();
  const { map: teams } = useTeams();
  const [selected, setSelected] = useState<number | null>(null);
  const round = useRound(selected);
  const [picks, setPicks] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [division, setDivision] = useState<string>("all");

  useEffect(() => {
    if (selected == null && rounds.data?.length) {
      const next = rounds.data.find((r) => !r.complete && !r.locked) ?? rounds.data[rounds.data.length - 1];
      setSelected(next.number);
    }
  }, [rounds.data, selected]);

  useEffect(() => {
    const p: Record<string, string> = {};
    round.data?.matches.forEach((m) => m.my_tip && (p[m.id] = m.my_tip));
    setPicks(p);
  }, [round.data]);

  const now = useNow();
  const isLocked = (m: MatchItem) => m.locked || hasStarted(m.kickoff, now);
  const openMatches = round.data?.matches.filter((m) => !isLocked(m)) ?? [];
  const dirty = openMatches.some((m) => picks[m.id] && picks[m.id] !== m.my_tip);
  const pickedOpen = openMatches.filter((m) => picks[m.id]).length;
  const anyRevealed = round.data?.matches.some(isLocked) ?? false;
  const staleLock = round.data?.matches.some((m) => !m.locked && hasStarted(m.kickoff, now)) ?? false;

  useEffect(() => {
    if (staleLock) round.refetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [staleLock]);

  const submit = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      const tips = openMatches.filter((m) => picks[m.id]).map((m) => ({ match_id: m.id, team_id: picks[m.id] }));
      await api(`/rounds/${selected}/tips`, { method: "POST", body: { tips } });
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
      toast(`Tips saved for ${round.data?.name}`);
      qc.invalidateQueries({ queryKey: ["round", selected] });
      qc.invalidateQueries({ queryKey: ["rounds"] });
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not save tips", "error");
    } finally {
      setSaving(false);
    }
  };

  const refresh = () => {
    rounds.refetch();
    round.refetch();
  };

  const r = round.data;
  const groups = Array.from(new Set((r?.matches ?? []).map((m) => m.group).filter((g): g is string => !!g)));
  const shown = (r?.matches ?? []).filter((m) => division === "all" || m.group === division);

  return (
    <View style={styles.root}>
      <View style={[styles.header, { paddingTop: insets.top + spacing.sm }]}>
        <View style={styles.titleRow}>
          <Text style={styles.title}>BOWLS TIPPING</Text>
          {r && (
            <View testID="round-score-badge" style={styles.scoreBadge}>
              <Text style={styles.scoreNum}>{r.my_points}</Text>
              <Text style={styles.scoreLbl}>PTS</Text>
            </View>
          )}
        </View>
        {rounds.data && <RoundChips rounds={rounds.data} selected={selected} onSelect={setSelected} />}
        {groups.length > 1 && <DivisionFilter options={groups} value={division} onChange={setDivision} />}
      </View>

      {rounds.isError || round.isError ? (
        <ErrorState onRetry={refresh} />
      ) : !r ? (
        <View style={styles.center}><ActivityIndicator color={colors.brandPrimary} /></View>
      ) : (
        <>
          <ScrollView
            contentContainerStyle={styles.list}
            refreshControl={<RefreshControl refreshing={round.isRefetching} onRefresh={refresh} tintColor={colors.brandPrimary} />}
          >
            <View style={styles.roundHead}>
              <View style={{ flex: 1 }}>
                <Text testID="round-name" style={styles.roundName}>{r.name}</Text>
                <Text style={styles.roundMeta}>
                  {r.locked ? "LOCKED" : r.complete ? "COMPLETE" : `${r.matches.length} MATCHES`}
                  {r.my_bonus ? "  ·  +1 PERFECT ROUND BONUS" : ""}
                </Text>
              </View>
              {anyRevealed && (
                <Pressable
                  testID="everyone-tips-button"
                  onPress={() => router.push(`/round-tips/${r.number}`)}
                  style={({ pressed }) => [styles.allBtn, pressed && styles.pressed]}
                >
                  <Ionicons name="people" size={16} color={colors.onBrandTertiary} />
                  <Text style={styles.allBtnText}>Everyone&apos;s tips</Text>
                </Pressable>
              )}
            </View>
            {r.matches.length === 0 ? (
              <EmptyState testID="round-empty" title="Round not configured yet" subtitle="Fixtures for this round will appear here once the admin adds them." />
            ) : (
              shown.map((m, i) => (
                <Animated.View key={m.id} entering={FadeInDown.delay(i * 60)}>
                  {m.group && m.group !== shown[i - 1]?.group && (
                    <Text testID={`group-heading-${i}`} style={[styles.groupHead, i > 0 && styles.groupHeadSpaced]}>{m.group.toUpperCase()}</Text>
                  )}
                  <MatchCard
                    match={m}
                    home={teams[m.home_team_id]}
                    away={teams[m.away_team_id]}
                    pick={picks[m.id]}
                    locked={isLocked(m)}
                    now={now}
                    onPick={(tid) => {
                      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
                      setPicks((p) => ({ ...p, [m.id]: tid }));
                    }}
                  />
                </Animated.View>
              ))
            )}
          </ScrollView>
          {openMatches.length > 0 && !r.locked && (
            <View style={[styles.cta, { paddingBottom: bottomChrome + spacing.md }]}>
              <Text testID="tips-progress" style={styles.ctaMeta}>{pickedOpen}/{openMatches.length} tipped</Text>
              <Button
                testID="submit-tips-button"
                title={dirty ? "Submit tips" : "Tips saved"}
                onPress={submit}
                loading={saving}
                disabled={!dirty}
                style={{ flex: 1 }}
              />
            </View>
          )}
        </>
      )}
    </View>
  );
}

function MatchCard({ match, home, away, pick, locked, now, onPick }: { match: MatchItem; home?: Team; away?: Team; pick?: string; locked: boolean; now: number; onPick: (id: string) => void }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const decided = match.winner_team_id;
  const side = (team: Team | undefined, id: string, testSide: string) => {
    const selected = pick === id;
    const won = decided === id;
    return (
      <Pressable
        testID={`match-${match.order}-pick-${testSide}`}
        disabled={locked}
        onPress={() => onPick(id)}
        style={({ pressed }) => [styles.side, selected && styles.sideSelected, pressed && styles.pressed]}
      >
        <TeamLogo team={team} size={48} />
        <Text numberOfLines={2} style={[styles.teamName, selected && styles.teamNameSel]}>{team?.name ?? "—"}</Text>
        {won && <Text style={styles.winTag}>WINNER</Text>}
      </Pressable>
    );
  };
  return (
    <View testID={`match-card-${match.order}`} style={[styles.card, match.correct === true && styles.cardCorrect, match.correct === false && styles.cardWrong]}>
      <View style={styles.kickRow}>
        <Ionicons name={locked ? "lock-closed" : "time-outline"} size={13} color={locked ? colors.warning : colors.onSurfaceTertiary} />
        <Text testID={`match-${match.order}-kickoff`} style={[styles.kickText, locked && styles.kickLocked]}>
          {match.kickoff ? formatKickoff(match.kickoff) : "Kick-off TBC"}
          {decided ? "  ·  FULL TIME" : locked ? "  ·  TIPS LOCKED" : match.kickoff ? `  ·  ${untilLabel(match.kickoff, now)}` : ""}
        </Text>
      </View>
      <View style={styles.cardRow}>
        {side(home, match.home_team_id, "home")}
        <View style={styles.vs}>
          <Text style={styles.vsText}>{decided === "draw" ? "DRAW" : "VS"}</Text>
          {match.correct === true && <Ionicons name="checkmark-circle" size={22} color={colors.success} />}
          {match.correct === false && <Ionicons name="close-circle" size={22} color={colors.error} />}
          {locked && match.correct === null && !pick && <Ionicons name="lock-closed" size={16} color={colors.muted} />}
        </View>
        {side(away, match.away_team_id, "away")}
      </View>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  header: { backgroundColor: c.surface, borderBottomWidth: 1, borderBottomColor: c.divider },
  titleRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: spacing.lg },
  title: { color: c.onSurface, fontFamily: fonts.display, fontSize: 36, letterSpacing: 0.5 },
  scoreBadge: { flexDirection: "row", alignItems: "baseline", gap: spacing.xs, backgroundColor: c.brandTertiary, paddingHorizontal: spacing.md, paddingVertical: spacing.xs, borderRadius: radius.pill },
  scoreNum: { color: c.onBrandTertiary, fontFamily: fonts.display, fontSize: 22 },
  scoreLbl: { color: c.onBrandTertiary, fontFamily: fonts.displaySemi, fontSize: 12 },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  list: { padding: spacing.lg, gap: spacing.md },
  roundHead: { marginBottom: spacing.xs, flexDirection: "row", alignItems: "center", gap: spacing.sm },
  groupHead: { color: c.onSurfaceTertiary, fontFamily: fonts.display, fontSize: 14, letterSpacing: 1.2, marginBottom: spacing.sm },
  groupHeadSpaced: { marginTop: spacing.md },
  allBtn: { flexDirection: "row", alignItems: "center", gap: spacing.xs, height: 36, paddingHorizontal: spacing.md, borderRadius: radius.pill, backgroundColor: c.brandTertiary },
  allBtnText: { color: c.onBrandTertiary, fontFamily: fonts.displaySemi, fontSize: 15 },
  kickRow: { flexDirection: "row", alignItems: "center", gap: spacing.xs, paddingHorizontal: spacing.sm, paddingTop: spacing.xs },
  kickText: { color: c.onSurfaceTertiary, fontFamily: fonts.displaySemi, fontSize: 13, letterSpacing: 0.3 },
  kickLocked: { color: c.warning },
  roundName: { color: c.onSurface, fontFamily: fonts.display, fontSize: 24 },
  roundMeta: { color: c.brandPrimary, fontFamily: fonts.displaySemi, fontSize: 13, letterSpacing: 1 },
  card: { backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: c.border, padding: spacing.sm },
  cardCorrect: { borderColor: c.success },
  cardWrong: { borderColor: c.error },
  cardRow: { flexDirection: "row", alignItems: "stretch" },
  side: {
    flex: 1, alignItems: "center", paddingVertical: spacing.md, paddingHorizontal: spacing.sm, gap: spacing.sm,
    borderRadius: radius.md, borderWidth: 2, borderColor: "transparent",
  },
  sideSelected: { borderColor: c.brandPrimary, backgroundColor: c.surfaceTertiary },
  pressed: { opacity: 0.8 },
  teamName: { color: c.onSurfaceSecondary, fontFamily: fonts.displaySemi, fontSize: 17, textAlign: "center" },
  teamNameSel: { color: c.onSurface },
  winTag: { color: c.success, fontFamily: fonts.display, fontSize: 12, letterSpacing: 1 },
  vs: { width: 44, alignItems: "center", justifyContent: "center", gap: spacing.xs },
  vsText: { color: c.muted, fontFamily: fonts.display, fontSize: 14 },
  cta: {
    flexDirection: "row", alignItems: "center", gap: spacing.md, paddingHorizontal: spacing.lg, paddingTop: spacing.md,
    backgroundColor: c.surface, borderTopWidth: 1, borderTopColor: c.divider,
  },
  ctaMeta: { color: c.onSurfaceTertiary, fontFamily: fonts.displaySemi, fontSize: 16, minWidth: 80 },
}));
