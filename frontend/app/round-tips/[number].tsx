import Ionicons from "@react-native-vector-icons/ionicons";
import { useLocalSearchParams } from "expo-router";
import { ActivityIndicator, RefreshControl, ScrollView, Text, View } from "react-native";
import Animated, { FadeInDown } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useAuth } from "@/src/auth";
import { AdminHeader } from "@/src/components/AdminHeader";
import { TeamLogo } from "@/src/components/TeamLogo";
import { EmptyState, ErrorState } from "@/src/components/ui";
import { useAllTips, useTeams } from "@/src/hooks";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";
import { formatKickoff } from "@/src/time";

export default function RoundTips() {
  const { number } = useLocalSearchParams<{ number: string }>();
  const n = Number(number);
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const { user } = useAuth();
  const q = useAllTips(n);
  const { map: teams } = useTeams();
  const d = q.data;
  const revealed = d?.matches.filter((m) => m.revealed) ?? [];

  return (
    <View style={styles.root}>
      <AdminHeader title={d ? `${d.name.toUpperCase()} TIPS` : "TIPS"} />
      {q.isError ? (
        <ErrorState onRetry={q.refetch} />
      ) : !d ? (
        <View style={styles.center}><ActivityIndicator color={colors.brandPrimary} /></View>
      ) : (
        <ScrollView
          contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, paddingBottom: insets.bottom + spacing.lg }}
          refreshControl={<RefreshControl refreshing={q.isRefetching} onRefresh={q.refetch} tintColor={colors.brandPrimary} />}
        >
          <Text style={styles.note}>Tips are revealed match by match once each game kicks off.</Text>

          <Text style={styles.section}>HOW THE COMP TIPPED</Text>
          {revealed.length === 0 && <EmptyState testID="all-tips-empty" title="Nothing revealed yet" subtitle="Check back after the first kick-off." />}
          {revealed.map((m, i) => {
            const home = teams[m.home_team_id];
            const away = teams[m.away_team_id];
            const total = m.home_count + m.away_count;
            const homePct = total ? Math.round((m.home_count / total) * 100) : 50;
            return (
              <Animated.View key={m.match_id} entering={FadeInDown.delay(i * 60)} testID={`split-card-${m.order}`} style={styles.card}>
                {m.kickoff && <Text style={styles.kick}>{formatKickoff(m.kickoff)}</Text>}
                <View style={styles.splitTeams}>
                  <View style={styles.splitSide}>
                    <TeamLogo team={home} size={32} />
                    <Text numberOfLines={1} style={[styles.splitName, m.winner_team_id === m.home_team_id && styles.winner]}>{home?.short}</Text>
                  </View>
                  <Text testID={`split-count-${m.order}`} style={styles.splitCount}>{m.home_count} – {m.away_count}</Text>
                  <View style={[styles.splitSide, { justifyContent: "flex-end" }]}>
                    <Text numberOfLines={1} style={[styles.splitName, m.winner_team_id === m.away_team_id && styles.winner]}>{away?.short}</Text>
                    <TeamLogo team={away} size={32} />
                  </View>
                </View>
                <View style={styles.bar}>
                  <View style={{ flex: homePct || 0.001, backgroundColor: home?.color }} />
                  <View style={{ flex: 100 - homePct || 0.001, backgroundColor: away?.color }} />
                </View>
              </Animated.View>
            );
          })}

          {revealed.length > 0 && (
            <>
              <Text style={styles.section}>PLAYER BY PLAYER</Text>
              <View style={styles.table}>
                <View style={[styles.tr, styles.thead]}>
                  <Text style={[styles.th, styles.nameCol]}>PLAYER</Text>
                  {revealed.map((m) => (
                    <View key={m.match_id} style={styles.cell}>
                      <Text style={styles.th}>G{m.order + 1}</Text>
                    </View>
                  ))}
                  <Text style={[styles.th, styles.ptsCol]}>✓</Text>
                </View>
                {d.players.map((p) => (
                  <View key={p.user_id} testID={`player-tips-row-${p.user_id}`} style={[styles.tr, p.user_id === user?.id && styles.me]}>
                    <Text numberOfLines={1} style={[styles.td, styles.nameCol]}>{p.name}{p.user_id === user?.id ? " (you)" : ""}</Text>
                    {revealed.map((m) => {
                      const tid = p.tips[m.match_id];
                      const right = m.winner_team_id && tid === m.winner_team_id;
                      const wrong = m.winner_team_id && tid && tid !== m.winner_team_id;
                      return (
                        <View key={m.match_id} style={styles.cell}>
                          {tid ? (
                            <View style={[styles.tipDot, right ? styles.dotRight : wrong ? styles.dotWrong : null]}>
                              <TeamLogo team={teams[tid]} size={24} />
                            </View>
                          ) : (
                            <Ionicons name="remove" size={16} color={colors.muted} />
                          )}
                        </View>
                      );
                    })}
                    <Text style={[styles.td, styles.ptsCol]}>{p.correct}</Text>
                  </View>
                ))}
              </View>
            </>
          )}
        </ScrollView>
      )}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  note: { color: c.onSurfaceTertiary, fontFamily: fonts.text, fontSize: 13 },
  section: { color: c.brandPrimary, fontFamily: fonts.display, fontSize: 14, letterSpacing: 1.2, marginTop: spacing.sm },
  card: { backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, padding: spacing.md, gap: spacing.sm, borderWidth: 1, borderColor: c.border },
  kick: { color: c.onSurfaceTertiary, fontFamily: fonts.displaySemi, fontSize: 12 },
  splitTeams: { flexDirection: "row", alignItems: "center" },
  splitSide: { flex: 1, flexDirection: "row", alignItems: "center", gap: spacing.sm },
  splitName: { color: c.onSurfaceSecondary, fontFamily: fonts.display, fontSize: 18 },
  winner: { color: c.success },
  splitCount: { color: c.onSurface, fontFamily: fonts.display, fontSize: 22 },
  bar: { flexDirection: "row", height: 8, borderRadius: 4, overflow: "hidden", backgroundColor: c.surfaceTertiary },
  table: { backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: c.border, overflow: "hidden" },
  tr: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.md, minHeight: 48, borderTopWidth: 1, borderTopColor: c.divider },
  thead: { borderTopWidth: 0, minHeight: 36, backgroundColor: c.surfaceTertiary },
  me: { backgroundColor: c.brandTertiary },
  th: { color: c.muted, fontFamily: fonts.display, fontSize: 12, letterSpacing: 1 },
  td: { color: c.onSurface, fontFamily: fonts.displaySemi, fontSize: 15 },
  nameCol: { flex: 1, paddingRight: spacing.sm },
  ptsCol: { width: 28, textAlign: "right" },
  cell: { width: 36, alignItems: "center", justifyContent: "center" },
  tipDot: { borderRadius: 16, borderWidth: 2, borderColor: "transparent", padding: 1 },
  dotRight: { borderColor: c.success },
  dotWrong: { borderColor: c.error, opacity: 0.6 },
}));
