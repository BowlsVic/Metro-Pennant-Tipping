import { ActivityIndicator, FlatList, Text, View } from "react-native";
import Animated, { FadeInDown } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { TeamLogo } from "@/src/components/TeamLogo";
import { ErrorState } from "@/src/components/ui";
import { useTeams } from "@/src/hooks";
import { usesNativeTabs } from "@/src/navigation";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

export default function TeamsScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const bottomChrome = usesNativeTabs ? insets.bottom : 0;
  const q = useTeams();

  return (
    <View style={styles.root}>
      <View style={[styles.header, { paddingTop: insets.top + spacing.sm }]}>
        <Text style={styles.title}>TEAMS</Text>
        <Text style={styles.sub}>{q.data?.length ?? 0} clubs battling it out</Text>
      </View>
      {q.isError ? (
        <ErrorState onRetry={q.refetch} />
      ) : q.isLoading ? (
        <View style={styles.center}><ActivityIndicator color={colors.brandPrimary} /></View>
      ) : (
        <FlatList
          data={q.data}
          numColumns={2}
          keyExtractor={(t) => t.id}
          columnWrapperStyle={{ gap: spacing.md }}
          contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, paddingBottom: bottomChrome + spacing.lg }}
          renderItem={({ item, index }) => (
            <Animated.View entering={FadeInDown.delay(index * 50)} style={styles.cardWrap}>
              <View testID={`team-card-${item.short}`} style={[styles.card, { borderColor: item.color }]}>
                <View style={[styles.band, { backgroundColor: item.color }]} />
                <TeamLogo team={item} size={64} />
                <Text numberOfLines={2} style={styles.name}>{item.name}</Text>
                <View style={styles.swatches}>
                  <View style={[styles.swatch, { backgroundColor: item.color }]} />
                  <View style={[styles.swatch, { backgroundColor: item.secondary }]} />
                  <Text style={styles.short}>{item.short}</Text>
                </View>
              </View>
            </Animated.View>
          )}
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
  cardWrap: { flex: 1 },
  card: {
    backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, padding: spacing.lg,
    alignItems: "center", gap: spacing.sm, overflow: "hidden",
  },
  band: { position: "absolute", top: 0, left: 0, right: 0, height: 44, opacity: 0.35 },
  name: { color: c.onSurface, fontFamily: fonts.displaySemi, fontSize: 18, textAlign: "center", minHeight: 44 },
  swatches: { flexDirection: "row", alignItems: "center", gap: spacing.xs },
  swatch: { width: 14, height: 14, borderRadius: 7, borderWidth: 1, borderColor: c.borderStrong },
  short: { color: c.muted, fontFamily: fonts.display, fontSize: 13, marginLeft: spacing.xs },
}));
