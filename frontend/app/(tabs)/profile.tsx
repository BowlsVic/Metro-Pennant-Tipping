import Ionicons from "@react-native-vector-icons/ionicons";
import { useRouter } from "expo-router";
import { Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useAuth } from "@/src/auth";
import { Button } from "@/src/components/ui";
import { useLadder, useRounds } from "@/src/hooks";
import { usesNativeTabs } from "@/src/navigation";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

export default function ProfileScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const bottomChrome = usesNativeTabs ? insets.bottom : 0;
  const router = useRouter();
  const { user, logout } = useAuth();
  const ladder = useLadder();
  const rounds = useRounds();
  const me = ladder.data?.find((r) => r.user_id === user?.id);
  const isAdmin = user?.role === "admin";

  const stats = [
    { label: "Rank", value: me ? `#${me.rank}` : "—" },
    { label: "Points", value: me?.points ?? 0 },
    { label: "Correct", value: me?.correct ?? 0 },
    { label: "Bonus", value: me?.bonus ?? 0 },
  ];

  return (
    <View style={styles.root}>
      <ScrollView contentContainerStyle={{ paddingTop: insets.top + spacing.sm, padding: spacing.lg, paddingBottom: bottomChrome + spacing.lg, gap: spacing.lg }}>
        <Text style={styles.title}>PROFILE</Text>
        <View style={styles.card}>
          <View style={styles.avatar}><Text style={styles.avatarText}>{user?.name?.[0]?.toUpperCase()}</Text></View>
          <View style={{ flex: 1 }}>
            <Text testID="profile-name" style={styles.name}>{user?.name}</Text>
            <Text testID="profile-email" style={styles.email}>{user?.email}</Text>
          </View>
          {isAdmin && <View style={styles.badge}><Text style={styles.badgeText}>ADMIN</Text></View>}
        </View>

        {!isAdmin && (
          <View style={styles.stats}>
            {stats.map((s) => (
              <View key={s.label} style={styles.stat}>
                <Text testID={`profile-stat-${s.label.toLowerCase()}`} style={styles.statVal}>{s.value}</Text>
                <Text style={styles.statLbl}>{s.label}</Text>
              </View>
            ))}
          </View>
        )}

        <View style={styles.card}>
          <Ionicons name="calendar" size={20} color={colors.brandPrimary} />
          <Text style={styles.email}>
            {rounds.data ? `${rounds.data.filter((r) => !r.is_final).length} regular rounds · ${rounds.data.filter((r) => r.is_final).length} finals rounds` : "Loading season…"}
          </Text>
        </View>

        {isAdmin && (
          <Pressable testID="open-admin-button" onPress={() => router.push("/admin")} style={({ pressed }) => [styles.adminCard, pressed && { opacity: 0.85 }]}>
            <Ionicons name="construct" size={22} color={colors.onBrandTertiary} />
            <View style={{ flex: 1 }}>
              <Text style={styles.adminTitle}>Admin dashboard</Text>
              <Text style={styles.adminSub}>Enter results, edit fixtures, add finals, edit teams</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.onBrandTertiary} />
          </Pressable>
        )}

        <Button testID="logout-button" title="Log out" variant="ghost" onPress={logout} />
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  title: { color: c.onSurface, fontFamily: fonts.display, fontSize: 36 },
  card: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, padding: spacing.lg, borderWidth: 1, borderColor: c.border },
  avatar: { width: 52, height: 52, borderRadius: 26, backgroundColor: c.brandPrimary, alignItems: "center", justifyContent: "center" },
  avatarText: { color: c.onBrandPrimary, fontFamily: fonts.display, fontSize: 26 },
  name: { color: c.onSurface, fontFamily: fonts.displaySemi, fontSize: 22 },
  email: { color: c.onSurfaceTertiary, fontFamily: fonts.text, fontSize: 14, flexShrink: 1 },
  badge: { backgroundColor: c.brandTertiary, paddingHorizontal: spacing.sm, paddingVertical: spacing.xs, borderRadius: radius.sm },
  badgeText: { color: c.onBrandTertiary, fontFamily: fonts.display, fontSize: 12, letterSpacing: 1 },
  stats: { flexDirection: "row", gap: spacing.sm },
  stat: { flex: 1, backgroundColor: c.surfaceSecondary, borderRadius: radius.md, paddingVertical: spacing.md, alignItems: "center", borderWidth: 1, borderColor: c.border },
  statVal: { color: c.onSurface, fontFamily: fonts.display, fontSize: 28 },
  statLbl: { color: c.muted, fontFamily: fonts.text, fontSize: 12 },
  adminCard: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: c.brandTertiary, borderRadius: radius.lg, padding: spacing.lg, borderWidth: 1, borderColor: c.brandSecondary },
  adminTitle: { color: c.onBrandTertiary, fontFamily: fonts.displaySemi, fontSize: 20 },
  adminSub: { color: c.onBrandTertiary, fontFamily: fonts.text, fontSize: 13, opacity: 0.85 },
}));
