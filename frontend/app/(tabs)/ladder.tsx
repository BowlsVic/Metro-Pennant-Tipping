import Ionicons from "@react-native-vector-icons/ionicons";
import { ActivityIndicator, FlatList, RefreshControl, Text, View } from "react-native";
import Animated, { FadeInDown } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { LadderRow } from "@/src/api";
import { useAuth } from "@/src/auth";
import { EmptyState, ErrorState } from "@/src/components/ui";
import { RoundWinnersStrip, WinsBadge } from "@/src/components/RoundWinners";
import { useLadder, useRoundWinners } from "@/src/hooks";
import { usesNativeTabs } from "@/src/navigation";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

export default function LadderScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const bottomChrome = usesNativeTabs ? insets.bottom : 0;
  const { user } = useAuth();
  const q = useLadder();
  const winners = useRoundWinners();
  const rows = q.data ?? [];
  const top = rows.slice(0, 3);
  const rest = rows.slice(3);

  const Podium = () => (
    <View testID="ladder-podium" style={styles.podium}>
      {top.map((r, i) => (
        <Animated.View key={r.user_id} entering={FadeInDown.delay(i * 80)} style={[styles.podCard, i === 0 && styles.podFirst]}>
          <View style={styles.podRankRow}>
            <Text style={styles.podRank}>#{r.rank}</Text>
            <WinsBadge count={r.round_wins} testID={`ladder-wins-${r.rank}`} />
            <StreakBadge row={r} testID={`ladder-streak-${r.user_id}`} />
          </View>
          <Text numberOfLines={1} style={styles.podName}>{r.name}{r.user_id === user?.id ? " (you)" : ""}</Text>
          <Text testID={`ladder-points-${i + 1}`} style={styles.podPts}>{r.points}</Text>
          <Text style={styles.podMeta}>{r.correct} correct · {r.bonus} bonus{r.round_wins ? ` · ${r.round_wins} round win${r.round_wins === 1 ? "" : "s"}` : ""}{r.best_streak ? ` · best streak ${r.best_streak}` : ""}</Text>
        </Animated.View>
      ))}
    </View>
  );

  const Row = ({ item }: { item: LadderRow }) => (
    <View testID={`ladder-row-${item.rank}`} style={[styles.row, item.user_id === user?.id && styles.rowMe]}>
      <Text style={styles.rank}>{item.rank}</Text>
      <View style={{ flex: 1 }}>
        <View style={styles.nameRow}>
          <Text numberOfLines={1} style={[styles.name, { flexShrink: 1 }]}>{item.name}{item.user_id === user?.id ? " (you)" : ""}</Text>
          <WinsBadge count={item.round_wins} testID={`ladder-row-wins-${item.user_id}`} />
          <StreakBadge row={item} testID={`ladder-streak-${item.user_id}`} />
        </View>
        <Text style={styles.meta}>{item.correct} correct · {item.bonus} bonus{item.best_streak ? ` · best streak ${item.best_streak}` : ""}</Text>
      </View>
      <Text style={styles.pts}>{item.points}</Text>
    </View>
  );

  const refresh = () => {
    q.refetch();
    winners.refetch();
  };

  return (
    <View style={styles.root}>
      <View style={[styles.header, { paddingTop: insets.top + spacing.sm }]}>
        <Text style={styles.title}>LADDER</Text>
        <Text style={styles.sub}>1 pt per correct tip · +1 for a perfect round · <Text style={styles.subAccent}>trophy = round win · flame = current tip streak</Text></Text>
      </View>
      {q.isError ? (
        <ErrorState onRetry={q.refetch} />
      ) : q.isLoading ? (
        <View style={styles.center}><ActivityIndicator color={colors.brandPrimary} /></View>
      ) : (
        <FlatList
          data={rest}
          keyExtractor={(r) => r.user_id}
          renderItem={Row}
          ListHeaderComponent={
            <>
              <RoundWinnersStrip winners={winners.data ?? []} meId={user?.id} />
              {top.length ? <Podium /> : null}
            </>
          }
          ListEmptyComponent={top.length ? null : <EmptyState testID="ladder-empty" title="No players yet" subtitle="Invite friends to join the comp." />}
          contentContainerStyle={{ padding: spacing.lg, gap: spacing.sm, paddingBottom: bottomChrome + spacing.lg }}
          refreshControl={<RefreshControl refreshing={q.isRefetching} onRefresh={refresh} tintColor={colors.brandPrimary} />}
        />
      )}
    </View>
  );
}

// Shows the current run of correct tips (2+ only, so a single tip isn't a "streak").
function StreakBadge({ row, testID }: { row: LadderRow; testID: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  if (row.streak < 2) return null;
  return (
    <View testID={testID} style={styles.streak}>
      <Ionicons name="flame" size={12} color={colors.brandPrimary} />
      <Text style={styles.streakText}>{row.streak}</Text>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  streak: { flexDirection: "row", alignItems: "center", gap: 2, backgroundColor: c.brandTertiary, borderRadius: radius.pill, paddingHorizontal: spacing.sm, paddingVertical: 2 },
  streakText: { color: c.onBrandTertiary, fontFamily: fonts.display, fontSize: 13 },
  root: { flex: 1, backgroundColor: c.surface },
  header: { paddingHorizontal: spacing.lg, paddingBottom: spacing.md, borderBottomWidth: 1, borderBottomColor: c.divider },
  title: { color: c.onSurface, fontFamily: fonts.display, fontSize: 36 },
  sub: { color: c.onSurfaceTertiary, fontFamily: fonts.text, fontSize: 13 },
  subAccent: { color: c.brandPrimary },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  podium: { gap: spacing.sm, marginBottom: spacing.md },
  podCard: { backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: c.border, padding: spacing.lg },
  podFirst: { backgroundColor: c.brandTertiary, borderColor: c.brandPrimary },
  podRankRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  podRank: { color: c.brandPrimary, fontFamily: fonts.display, fontSize: 20 },
  nameRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  podName: { color: c.onSurface, fontFamily: fonts.displaySemi, fontSize: 22 },
  podPts: { position: "absolute", right: spacing.lg, top: spacing.md, color: c.onSurface, fontFamily: fonts.display, fontSize: 44 },
  podMeta: { color: c.onSurfaceTertiary, fontFamily: fonts.text, fontSize: 12, marginTop: spacing.xs },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: c.surfaceSecondary, borderRadius: radius.md, padding: spacing.md },
  rowMe: { borderWidth: 1, borderColor: c.brandPrimary },
  rank: { width: 32, color: c.muted, fontFamily: fonts.display, fontSize: 20, textAlign: "center" },
  name: { color: c.onSurface, fontFamily: fonts.displaySemi, fontSize: 18 },
  meta: { color: c.onSurfaceTertiary, fontFamily: fonts.text, fontSize: 12 },
  pts: { color: c.onSurface, fontFamily: fonts.display, fontSize: 28 },
}));
