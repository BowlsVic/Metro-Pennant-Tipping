import { Modal, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Team } from "@/src/api";
import { TeamLogo } from "@/src/components/TeamLogo";
import { fonts, makeStyles, radius, spacing } from "@/src/theme";

export function TeamPickerModal({
  visible, title, teams, exclude, onPick, onClose,
}: { visible: boolean; title: string; teams: Team[]; exclude?: string; onPick: (t: Team) => void; onClose: () => void }) {
  const styles = useStyles();
  const insets = useSafeAreaInsets();
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable testID="team-picker-backdrop" style={styles.backdrop} onPress={onClose} />
      <View style={[styles.sheet, { paddingBottom: insets.bottom + spacing.lg }]}>
        <View style={styles.grabber} />
        <Text style={styles.title}>{title}</Text>
        <ScrollView contentContainerStyle={{ gap: spacing.sm }}>
          {teams.filter((t) => t.id !== exclude).map((t) => (
            <Pressable key={t.id} testID={`team-picker-option-${t.short}`} onPress={() => onPick(t)} style={({ pressed }) => [styles.row, pressed && { opacity: 0.8 }]}>
              <TeamLogo team={t} size={36} />
              <Text style={styles.name}>{t.name}</Text>
            </Pressable>
          ))}
        </ScrollView>
      </View>
    </Modal>
  );
}

const useStyles = makeStyles((c) => ({
  backdrop: { flex: 1, backgroundColor: c.scrim, opacity: 0.6 },
  sheet: { backgroundColor: c.surfaceSecondary, borderTopLeftRadius: radius.lg, borderTopRightRadius: radius.lg, padding: spacing.lg, maxHeight: "75%" },
  grabber: { alignSelf: "center", width: 40, height: 4, borderRadius: 2, backgroundColor: c.borderStrong, marginBottom: spacing.md },
  title: { color: c.onSurface, fontFamily: fonts.display, fontSize: 24, marginBottom: spacing.md },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: c.surfaceTertiary, borderRadius: radius.md, padding: spacing.md },
  name: { color: c.onSurface, fontFamily: fonts.displaySemi, fontSize: 18 },
}));
