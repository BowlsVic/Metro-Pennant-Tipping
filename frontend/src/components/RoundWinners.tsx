import Ionicons from "@react-native-vector-icons/ionicons";
import { ScrollView, Text, View } from "react-native";
import Animated, { FadeInRight } from "react-native-reanimated";

import { RoundWinner } from "@/src/api";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

export function RoundWinnersStrip({ winners, meId }: { winners: RoundWinner[]; meId?: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  if (!winners.length) return null;
  return (
    <View testID="round-winners-strip" style={styles.wrap}>
      <Text style={styles.section}>ROUND WINNERS</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.content}>
        {winners.map((w, i) => {
          const latest = i === 0;
          return (
            <Animated.View
              key={w.number}
              entering={FadeInRight.delay(i * 60)}
              testID={`round-winner-card-${w.number}`}
              style={[styles.card, latest && styles.cardLatest]}
            >
              <View style={styles.top}>
                <Text numberOfLines={1} style={[styles.round, latest && styles.roundLatest]}>{latest ? `LATEST · ${w.name.toUpperCase()}` : w.name.toUpperCase()}</Text>
                <Ionicons name="trophy" size={16} color={latest ? colors.brandPrimary : colors.warning} />
              </View>
              <Text numberOfLines={2} style={styles.names}>
                {w.winners.map((p) => (p.user_id === meId ? `${p.name} (you)` : p.name)).join(", ")}
              </Text>
              <Text style={styles.pts}>{w.points} pts{w.winners.length > 1 ? " · shared" : ""}</Text>
            </Animated.View>
          );
        })}
      </ScrollView>
    </View>
  );
}

export function WinsBadge({ count, testID }: { count: number; testID: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  if (!count) return null;
  return (
    <View testID={testID} style={styles.badge}>
      <Ionicons name="trophy" size={12} color={colors.onBrandTertiary} />
      <Text style={styles.badgeText}>{count}</Text>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  wrap: { marginBottom: spacing.md, marginHorizontal: -spacing.lg },
  section: { color: c.brandPrimary, fontFamily: fonts.display, fontSize: 14, letterSpacing: 1.2, marginBottom: spacing.sm, paddingHorizontal: spacing.lg },
  content: { gap: spacing.sm, paddingHorizontal: spacing.lg },
  card: { width: 180, backgroundColor: c.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: c.border, padding: spacing.md, gap: spacing.xs },
  cardLatest: { borderColor: c.brandPrimary, backgroundColor: c.brandTertiary },
  top: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: spacing.sm },
  round: { flex: 1, color: c.muted, fontFamily: fonts.display, fontSize: 12, letterSpacing: 1 },
  roundLatest: { color: c.onBrandTertiary },
  names: { color: c.onSurface, fontFamily: fonts.displaySemi, fontSize: 18, minHeight: 22 },
  pts: { color: c.onSurfaceTertiary, fontFamily: fonts.text, fontSize: 12 },
  badge: { flexDirection: "row", alignItems: "center", gap: 3, backgroundColor: c.brandTertiary, borderRadius: radius.pill, paddingHorizontal: spacing.sm, height: 22 },
  badgeText: { color: c.onBrandTertiary, fontFamily: fonts.display, fontSize: 13 },
}));
