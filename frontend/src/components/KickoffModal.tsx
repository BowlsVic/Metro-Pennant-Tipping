import Ionicons from "@react-native-vector-icons/ionicons";
import { useEffect, useState } from "react";
import { Modal, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button } from "@/src/components/ui";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";
import { formatKickoff } from "@/src/time";

function defaultKickoff() {
  const d = new Date();
  d.setDate(d.getDate() + ((6 - d.getDay() + 7) % 7 || 7)); // next Saturday
  d.setHours(15, 0, 0, 0);
  return d;
}

export function KickoffModal({
  visible, initial, onSave, onSaveAll, onClear, onClose,
}: {
  visible: boolean; initial: string | null;
  onSave: (iso: string) => void; onSaveAll: (iso: string) => void; onClear: () => void; onClose: () => void;
}) {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const [date, setDate] = useState<Date>(defaultKickoff());

  useEffect(() => {
    if (visible) setDate(initial ? new Date(initial) : defaultKickoff());
  }, [visible, initial]);

  const shift = (mins: number) => setDate((d) => new Date(d.getTime() + mins * 60000));

  const Stepper = ({ label, value, step, id }: { label: string; value: string; step: number; id: string }) => (
    <View style={styles.stepper}>
      <Text style={styles.stepLbl}>{label}</Text>
      <View style={styles.stepRow}>
        <Pressable testID={`kickoff-${id}-minus`} onPress={() => shift(-step)} style={styles.stepBtn}>
          <Ionicons name="remove" size={20} color={colors.onSurface} />
        </Pressable>
        <Text style={styles.stepVal}>{value}</Text>
        <Pressable testID={`kickoff-${id}-plus`} onPress={() => shift(step)} style={styles.stepBtn}>
          <Ionicons name="add" size={20} color={colors.onSurface} />
        </Pressable>
      </View>
    </View>
  );

  const h = date.getHours();
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable testID="kickoff-backdrop" style={styles.backdrop} onPress={onClose} />
      <View style={[styles.sheet, { paddingBottom: insets.bottom + spacing.lg }]}>
        <View style={styles.grabber} />
        <Text style={styles.title}>Kick-off time</Text>
        <Text testID="kickoff-preview" style={styles.preview}>{formatKickoff(date.toISOString())}</Text>
        <Text style={styles.hint}>Tips lock automatically at this time (your local time).</Text>
        <View style={styles.steppers}>
          <Stepper id="day" label="DAY" value={`${date.getDate()}/${date.getMonth() + 1}`} step={1440} />
          <Stepper id="hour" label="HOUR" value={`${h % 12 || 12}${h < 12 ? "am" : "pm"}`} step={60} />
          <Stepper id="min" label="MIN" value={String(date.getMinutes()).padStart(2, "0")} step={5} />
        </View>
        <Button testID="kickoff-save-button" title="Save kick-off" onPress={() => onSave(date.toISOString())} />
        <View style={styles.row}>
          <Button testID="kickoff-save-all-button" title="Apply to all" variant="ghost" onPress={() => onSaveAll(date.toISOString())} style={{ flex: 1 }} />
          <Button testID="kickoff-clear-button" title="Clear" variant="danger" onPress={onClear} style={{ flex: 1 }} />
        </View>
      </View>
    </Modal>
  );
}

const useStyles = makeStyles((c) => ({
  backdrop: { flex: 1, backgroundColor: c.scrim, opacity: 0.6 },
  sheet: { backgroundColor: c.surfaceSecondary, borderTopLeftRadius: radius.lg, borderTopRightRadius: radius.lg, padding: spacing.lg, gap: spacing.md },
  grabber: { alignSelf: "center", width: 40, height: 4, borderRadius: 2, backgroundColor: c.borderStrong },
  title: { color: c.onSurface, fontFamily: fonts.display, fontSize: 24 },
  preview: { color: c.brandPrimary, fontFamily: fonts.display, fontSize: 28 },
  hint: { color: c.onSurfaceTertiary, fontFamily: fonts.text, fontSize: 13, marginTop: -spacing.sm },
  steppers: { flexDirection: "row", gap: spacing.sm },
  stepper: { flex: 1, backgroundColor: c.surfaceTertiary, borderRadius: radius.md, padding: spacing.sm, alignItems: "center", gap: spacing.xs },
  stepLbl: { color: c.muted, fontFamily: fonts.display, fontSize: 12, letterSpacing: 1 },
  stepRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", alignSelf: "stretch" },
  stepBtn: { width: 36, height: 44, alignItems: "center", justifyContent: "center" },
  stepVal: { color: c.onSurface, fontFamily: fonts.display, fontSize: 20 },
  row: { flexDirection: "row", gap: spacing.sm },
}));
