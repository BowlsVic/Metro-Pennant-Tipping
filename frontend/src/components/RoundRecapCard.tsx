import Ionicons from "@react-native-vector-icons/ionicons";
import { Text, View } from "react-native";
import Animated, { FadeIn } from "react-native-reanimated";

import { Team } from "@/src/api";
import { TeamLogo } from "@/src/components/TeamLogo";
import { useRoundRecap } from "@/src/hooks";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const ordinal = (n: number) => {
  const s = ["th", "st", "nd", "rd"], v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
};

export function RoundRecapCard({ round, teams }: { round: number; teams: Record<string, Team> }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const q = useRoundRecap(round, true);
  const d = q.data;
  if (!d?.available) return null;

  const move = d.rank != null && d.prev_rank != null ? d.prev_rank - d.rank : null;
  const moveIcon = move == null ? "sparkles" : move > 0 ? "arrow-up" : move < 0 ? "arrow-down" : "remove";
  const moveColor = move == null ? colors.brandPrimary : move > 0 ? colors.success : move < 0 ? colors.error : colors.onSurfaceTertiary;
  const moveText = d.rank == null ? "Not on ladder" : move == null ? `Debut at ${ordinal(d.rank)}` : move === 0 ? `Held ${ordinal(d.rank)}` : `${move > 0 ? "Up" : "Down"} ${Math.abs(move)} to ${ordinal(d.rank)}`;
  const best = d.best_pick;
  const bestTeam = best ? teams[best.team_id] : undefined;

  return (
    <Animated.View entering={FadeIn} testID="round-recap-card" style={styles.card}>
      <View style={styles.head}>
        <Text style={styles.kicker}>{d.name.toUpperCase()} RECAP</Text>
        {d.won_round && (
          <View testID="recap-round-winner" style={styles.winPill}>
            <Ionicons name="trophy" size={12} color={colors.onBrandPrimary} />
            <Text style={styles.winText}>ROUND WINNER</Text>
          </View>
        )}
      </View>
      <View style={styles.row}>
        <View style={styles.stat}>
          <Text testID="recap-points" style={styles.big}>{d.points}</Text>
          <Text style={styles.lbl}>{d.correct}/{d.total} correct{d.bonus ? " +1 bonus" : ""}</Text>
        </View>
        <View style={styles.divider} />
        <View style={styles.stat}>
          <View style={styles.moveRow}>
            <Ionicons name={moveIcon} size={22} color={moveColor} />
            <Text testID="recap-rank" style={styles.big}>{d.rank != null ? ordinal(d.rank) : "—"}</Text>
          </View>
          <Text testID="recap-movement" style={[styles.lbl, { color: moveColor }]}>{moveText}</Text>
        </View>
      </View>
      <View testID="recap-best-pick" style={styles.best}>
        {best && bestTeam ? (
          <>
            <TeamLogo team={bestTeam} size={36} />
            <View style={{ flex: 1 }}>
              <Text style={styles.bestTitle}>Best pick: {bestTeam.name}</Text>
              <Text style={styles.bestSub}>
                Beat {teams[best.opponent_id]?.name ?? "their opponent"} · only {best.share}% of players tipped them
              </Text>
            </View>
          </>
        ) : (
          <Text style={styles.bestSub}>{d.tipped ? "No correct picks this round — next week's yours!" : "You didn't tip this round."}</Text>
        )}
      </View>
    </Animated.View>
  );
}

const useStyles = makeStyles((c) => ({
  card: { backgroundColor: c.brandTertiary, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.md, borderWidth: 1, borderColor: c.brandPrimary },
  head: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  kicker: { color: c.onBrandTertiary, fontFamily: fonts.display, fontSize: 14, letterSpacing: 1.2 },
  winPill: { flexDirection: "row", alignItems: "center", gap: spacing.xs, backgroundColor: c.brandPrimary, borderRadius: radius.pill, paddingHorizontal: spacing.sm, paddingVertical: 2 },
  winText: { color: c.onBrandPrimary, fontFamily: fonts.display, fontSize: 12, letterSpacing: 0.8 },
  row: { flexDirection: "row", alignItems: "center" },
  stat: { flex: 1, alignItems: "center", gap: 2 },
  divider: { width: 1, alignSelf: "stretch", backgroundColor: c.border },
  big: { color: c.onSurface, fontFamily: fonts.display, fontSize: 34 },
  lbl: { color: c.onSurfaceTertiary, fontFamily: fonts.displaySemi, fontSize: 14 },
  moveRow: { flexDirection: "row", alignItems: "center", gap: spacing.xs },
  best: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: c.surfaceSecondary, borderRadius: radius.md, padding: spacing.md },
  bestTitle: { color: c.onSurface, fontFamily: fonts.display, fontSize: 17 },
  bestSub: { color: c.onSurfaceTertiary, fontFamily: fonts.text, fontSize: 13 },
}));
