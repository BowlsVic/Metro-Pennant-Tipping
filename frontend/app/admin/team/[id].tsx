import Ionicons from "@react-native-vector-icons/ionicons";
import { useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, Team } from "@/src/api";
import { AdminHeader } from "@/src/components/AdminHeader";
import { LogoUploader } from "@/src/components/LogoUploader";
import { TeamLogo } from "@/src/components/TeamLogo";
import { useToast } from "@/src/components/Toast";
import { Button } from "@/src/components/ui";
import { useTeams } from "@/src/hooks";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

// Team kit palette: data values that represent club colours, identical in any theme.
const PALETTE = ["#C8102E", "#E35205", "#F2A900", "#FFD100", "#00843D", "#1B5E20", "#0072CE", "#002B5C", "#6A1B9A", "#5B6770", "#1A1A1A", "#FFFFFF"];
const ICONS = ["paw", "fish", "shield", "flash", "moon", "rocket", "diamond", "trophy", "flame", "star", "football", "skull", "leaf", "planet", "snow", "sunny"];

export default function EditTeam() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const qc = useQueryClient();
  const toast = useToast();
  const { map } = useTeams();
  const isNew = id === "new";
  const team = map[id];
  const [draft, setDraft] = useState<Team | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (draft) return;
    if (isNew) setDraft({ id: "", name: "", short: "", color: "#0072CE", secondary: "#FFFFFF", icon: "shield" });
    else if (team) setDraft(team);
  }, [team, draft, isNew]);

  if (!draft) return <View style={styles.root}><AdminHeader title="Team" /></View>;

  const body = () => ({ name: draft.name.trim(), short: draft.short.trim().toUpperCase(), color: draft.color, secondary: draft.secondary, icon: draft.icon });

  const save = async () => {
    if (!draft.name.trim() || !draft.short.trim()) return toast("Name and short code are required", "error");
    setSaving(true);
    try {
      if (isNew) await api("/teams", { method: "POST", body: body() });
      else await api(`/teams/${id}`, { method: "PUT", body: body() });
      qc.invalidateQueries({ queryKey: ["teams"] });
      toast(isNew ? "Team added" : "Team updated");
      router.back();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "error");
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    setSaving(true);
    try {
      await api(`/teams/${id}`, { method: "DELETE" });
      qc.invalidateQueries({ queryKey: ["teams"] });
      toast("Team deleted");
      router.back();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "error");
    } finally {
      setSaving(false);
    }
  };

  const Swatches = ({ field }: { field: "color" | "secondary" }) => (
    <View style={styles.grid}>
      {PALETTE.map((p) => (
        <Pressable key={p} testID={`team-${field}-${p.slice(1)}`} onPress={() => setDraft({ ...draft, [field]: p })} style={[styles.swatch, { backgroundColor: p }, draft[field] === p && styles.swatchSel]}>
          {draft[field] === p && <Ionicons name="checkmark" size={18} color={p === "#FFFFFF" || p === "#FFD100" ? "#000000" : "#FFFFFF"} />}
        </Pressable>
      ))}
    </View>
  );

  return (
    <View style={styles.root}>
      <AdminHeader title={isNew ? "NEW TEAM" : "EDIT TEAM"} />
      <KeyboardAwareScrollView bottomOffset={24} contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, paddingBottom: insets.bottom + spacing.lg }}>
        <View style={styles.preview}>
          <TeamLogo team={draft} size={88} />
          <Text style={styles.previewName}>{draft.name || "Team name"}</Text>
        </View>
        <Text style={styles.label}>CLUB LOGO</Text>
        {isNew ? (
          <Text style={styles.hint}>Add the team first, then open it again to upload its logo.</Text>
        ) : (
          <LogoUploader
            team={draft}
            onChange={(t) => {
              setDraft({ ...draft, logo_path: t.logo_path, logo_v: t.logo_v });
              qc.invalidateQueries({ queryKey: ["teams"] });
            }}
          />
        )}
        <Text style={styles.label}>NAME</Text>
        <TextInput testID="team-name-input" style={styles.input} value={draft.name} onChangeText={(v) => setDraft({ ...draft, name: v })} maxLength={30} placeholderTextColor={colors.muted} />
        <Text style={styles.label}>SHORT CODE</Text>
        <TextInput testID="team-short-input" style={styles.input} value={draft.short} autoCapitalize="characters" onChangeText={(v) => setDraft({ ...draft, short: v })} maxLength={4} placeholderTextColor={colors.muted} />
        <Text style={styles.label}>PRIMARY COLOUR</Text>
        <Swatches field="color" />
        <Text style={styles.label}>SECONDARY COLOUR</Text>
        <Swatches field="secondary" />
        <Text style={styles.label}>{draft.logo_path ? "FALLBACK ICON" : "LOGO ICON"}</Text>
        <View style={styles.grid}>
          {ICONS.map((ic) => (
            <Pressable key={ic} testID={`team-icon-${ic}`} onPress={() => setDraft({ ...draft, icon: ic })} style={[styles.iconBtn, draft.icon === ic && styles.iconSel]}>
              <Ionicons name={ic as never} size={22} color={draft.icon === ic ? colors.onBrandPrimary : colors.onSurfaceSecondary} />
            </Pressable>
          ))}
        </View>
        <Button testID="save-team-button" title={isNew ? "Add team" : "Save team"} onPress={save} loading={saving} style={{ marginTop: spacing.sm }} />
        {!isNew && <Button testID="delete-team-button" title="Delete team" variant="danger" onPress={remove} disabled={saving} />}
      </KeyboardAwareScrollView>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  preview: { alignItems: "center", gap: spacing.sm, paddingVertical: spacing.md },
  previewName: { color: c.onSurface, fontFamily: fonts.display, fontSize: 26 },
  label: { color: c.muted, fontFamily: fonts.display, fontSize: 13, letterSpacing: 1, marginTop: spacing.sm },
  hint: { color: c.onSurfaceTertiary, fontFamily: fonts.text, fontSize: 13 },
  input: { height: 48, backgroundColor: c.surfaceTertiary, borderRadius: radius.md, borderWidth: 1, borderColor: c.border, paddingHorizontal: spacing.lg, color: c.onSurface, fontFamily: fonts.text, fontSize: 15 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  swatch: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center", borderWidth: 2, borderColor: c.border },
  swatchSel: { borderColor: c.brandPrimary, borderWidth: 3 },
  iconBtn: { width: 48, height: 48, borderRadius: radius.md, backgroundColor: c.surfaceTertiary, alignItems: "center", justifyContent: "center" },
  iconSel: { backgroundColor: c.brandPrimary },
}));
