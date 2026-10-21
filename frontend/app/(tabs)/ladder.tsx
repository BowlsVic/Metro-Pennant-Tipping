import { ActivityIndicator, FlatList, RefreshControl, Text, View } from "react-native";
import Animated, { FadeInDown } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { LadderRow } from "@/src/api";
import { useAuth } from "@/src/auth";
import { EmptyState, ErrorState } from "@/src/components/ui";
import { useLadder } from "@/src/hooks";
import { usesNativeTabs } from "@/src/navigation";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

export default function LadderScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const bottomChrome = usesNativeTabs ? insets.bottom : 0;
  const { user } = useAuth();
  const q = useLadder();
  const rows = q.data ?? [];
  const top = rows.slice(0, 3);
  const rest = rows.slice(3);

  const Podium = () => (
    <View testID="ladder-podium" style={styles.podium}>
      {top.map((r, i) => (
        <Animated.View key={r.user_id} entering={FadeInDown.delay(i * 80)} style={[styles.podCard, i === 0 && styles.podFirst]}>
          <Text style={styles.podRank}>#{r.rank}</Text>
          <Text numberOfLines={1} style={styles.podName}>{r.name}{r.user_id === user?.id ? " (you)" : ""}</Text>
          <Text testID={`ladder-points-${i + 1}`} style={styles.podPts}>{r.points}</Text>
          <Text style={styles.podMeta}>{r.correct} correct · {r.bonus} bonus</Text>
        </Animated.View>
      ))}
    </View>
  );

  const Row = ({ item }: { item: LadderRow }) => (
    <View testID={`ladder-row-${item.rank}`} style={[styles.row, item.user_id === user?.id && styles.rowMe]}>
      <Text style={styles.rank}>{item.rank}</Text>
      <View style={{ flex: 1 }}>
        <Text numberOfLines={1} style={styles.name}>{item.name}{item.user_id === user?.id ? " (you)" : ""}</Text>
        <Text style={styles.meta}>{item.correct} correct · {item.bonus} bonus</Text>
      </View>
      <Text style={styles.pts}>{item.points}</Text>
    </View>
  );

  return (
    <View style={styles.root}>
      <View style={[styles.header, { paddingTop: insets.top + spacing.sm }]}>
        <Text style={styles.title}>LADDER</Text>
        <Text style={styles.sub}>1 pt per correct tip · +1 for a perfect round</Text>
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
          ListHeaderComponent={top.length ? <Podium /> : null}
          ListEmptyComponent={top.length ? null : <EmptyState testID="ladder-empty" title="No players yet" subtitle="Invite friends to join the comp." />}
          contentContainerStyle={{ padding: spacing.lg, gap: spacing.sm, paddingBottom: bottomChrome + spacing.lg }}
          refreshControl={<RefreshControl refreshing={q.isRefetching} onRefresh={q.refetch} tintColor={colors.brandPrimary} />}
        />
      )}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  header: { paddingHorizontal: spacing.lg, paddingBottom: spacing.md, borderBottomWidth: 1, borderBottomColor: c.divider },
  title: { color: c.onSurface, fontFamily: fonts.display, fontSize: 36 },
  sub: { color: c.onSurfaceTertiary, fontFamily: fonts.text, fontSize: 13 },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  podium: { gap: spacing.sm, marginBottom: spacing.md },
  podCard: { backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: c.border, padding: spacing.lg },
  podFirst: { backgroundColor: c.brandTertiary, borderColor: c.brandPrimary },
  podRank: { color: c.brandPrimary, fontFamily: fonts.display, fontSize: 20 },
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
