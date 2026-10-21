import Ionicons from "@react-native-vector-icons/ionicons";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Pressable, Text, TextInput, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { AdminHeader } from "@/src/components/AdminHeader";
import { TeamLogo } from "@/src/components/TeamLogo";
import { useToast } from "@/src/components/Toast";
import { Button } from "@/src/components/ui";
import { useRounds, useTeams } from "@/src/hooks";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

export default function AdminHome() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const qc = useQueryClient();
  const toast = useToast();
  const rounds = useRounds();
  const teams = useTeams();
  const [tab, setTab] = useState<"rounds" | "teams">("rounds");
  const [finalName, setFinalName] = useState("");
  const [adding, setAdding] = useState(false);

  const addFinal = async () => {
    const name = finalName.trim() || `Finals Week ${(rounds.data?.filter((r) => r.is_final).length ?? 0) + 1}`;
    setAdding(true);
    try {
      const r = await api<{ number: number }>("/rounds", { method: "POST", body: { name } });
      setFinalName("");
      toast(`${name} added`);
      qc.invalidateQueries({ queryKey: ["rounds"] });
      router.push(`/admin/round/${r.number}`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "error");
    } finally {
      setAdding(false);
    }
  };

  return (
    <View style={styles.root}>
      <AdminHeader title="ADMIN" />
      <View style={styles.segment}>
        {(["rounds", "teams"] as const).map((t) => (
          <Pressable key={t} testID={`admin-tab-${t}`} onPress={() => setTab(t)} style={[styles.segBtn, tab === t && styles.segActive]}>
            <Text style={[styles.segText, tab === t && styles.segTextActive]}>{t === "rounds" ? "Fixtures & Results" : "Manage Teams"}</Text>
          </Pressable>
        ))}
      </View>

      <KeyboardAwareScrollView bottomOffset={24} contentContainerStyle={{ padding: spacing.lg, gap: spacing.sm, paddingBottom: insets.bottom + spacing.lg }}>
        {tab === "rounds" ? (
          <>
            <View style={styles.addBox}>
              <Text style={styles.boxTitle}>Add a finals round</Text>
              <TextInput
                testID="final-round-name-input"
                style={styles.input}
                placeholder="e.g. Qualifying Final, Grand Final"
                placeholderTextColor={colors.muted}
                value={finalName}
                onChangeText={setFinalName}
                maxLength={40}
              />
              <Button testID="add-final-round-button" title="Add finals round" onPress={addFinal} loading={adding} />
            </View>
            {rounds.isLoading && <ActivityIndicator color={colors.brandPrimary} />}
            {rounds.data?.map((r) => (
              <Pressable
                key={r.number}
                testID={`admin-round-${r.number}`}
                onPress={() => router.push(`/admin/round/${r.number}`)}
                style={({ pressed }) => [styles.row, pressed && { opacity: 0.8 }]}
              >
                <View style={{ flex: 1 }}>
                  <Text style={styles.rowTitle}>{r.name}</Text>
                  <Text style={styles.rowMeta}>
                    {r.match_count} matches · {r.decided_count}/{r.match_count} results{r.locked ? " · locked" : ""}
                  </Text>
                </View>
                {r.is_final && <View style={styles.finalTag}><Text style={styles.finalTagText}>FINALS</Text></View>}
                {r.complete && <Ionicons name="checkmark-circle" size={20} color={colors.success} />}
                <Ionicons name="chevron-forward" size={18} color={colors.muted} />
              </Pressable>
            ))}
          </>
        ) : (
          <>
            {(teams.data?.length ?? 0) < 16 && (
              <Button testID="add-team-button" title={`Add team (${teams.data?.length ?? 0}/16)`} variant="ghost" onPress={() => router.push("/admin/team/new")} style={{ marginBottom: spacing.sm }} />
            )}
            {teams.data?.map((t) => (
            <Pressable
              key={t.id}
              testID={`admin-team-${t.short}`}
              onPress={() => router.push(`/admin/team/${t.id}`)}
              style={({ pressed }) => [styles.row, pressed && { opacity: 0.8 }]}
            >
              <TeamLogo team={t} size={40} />
              <View style={{ flex: 1 }}>
                <Text style={styles.rowTitle}>{t.name}</Text>
                <Text style={styles.rowMeta}>{t.short}</Text>
              </View>
              <Ionicons name="create-outline" size={20} color={colors.muted} />
            </Pressable>
            ))}
          </>
        )}
      </KeyboardAwareScrollView>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  segment: { flexDirection: "row", backgroundColor: c.surfaceSecondary, borderRadius: radius.md, padding: spacing.xs, margin: spacing.lg, marginBottom: 0 },
  segBtn: { flex: 1, height: 40, alignItems: "center", justifyContent: "center", borderRadius: radius.sm },
  segActive: { backgroundColor: c.surfaceTertiary },
  segText: { color: c.muted, fontFamily: fonts.text, fontSize: 13, fontWeight: "600" },
  segTextActive: { color: c.onSurface },
  addBox: { backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.md, borderWidth: 1, borderColor: c.brandSecondary, marginBottom: spacing.sm },
  boxTitle: { color: c.onSurface, fontFamily: fonts.displaySemi, fontSize: 20 },
  input: { height: 48, backgroundColor: c.surfaceTertiary, borderRadius: radius.md, borderWidth: 1, borderColor: c.border, paddingHorizontal: spacing.lg, color: c.onSurface, fontFamily: fonts.text, fontSize: 15 },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: c.surfaceSecondary, borderRadius: radius.md, padding: spacing.md, minHeight: 60 },
  rowTitle: { color: c.onSurface, fontFamily: fonts.displaySemi, fontSize: 18 },
  rowMeta: { color: c.onSurfaceTertiary, fontFamily: fonts.text, fontSize: 12 },
  finalTag: { backgroundColor: c.brandTertiary, paddingHorizontal: spacing.sm, paddingVertical: 2, borderRadius: radius.sm },
  finalTagText: { color: c.onBrandTertiary, fontFamily: fonts.display, fontSize: 11, letterSpacing: 1 },
}));
