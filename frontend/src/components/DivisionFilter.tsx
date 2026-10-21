import * as Haptics from "expo-haptics";
import { Pressable, ScrollView, Text } from "react-native";

import { fonts, makeStyles, radius, spacing } from "@/src/theme";

export function DivisionFilter({ options, value, onChange }: { options: string[]; value: string; onChange: (v: string) => void }) {
  const styles = useStyles();
  const items = [{ key: "all", label: "All" }, ...options.map((o) => ({ key: o, label: o }))];
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.row} contentContainerStyle={styles.content}>
      {items.map((it) => {
        const active = it.key === value;
        return (
          <Pressable
            key={it.key}
            testID={`division-filter-${it.key === "all" ? "all" : it.key.toLowerCase().replace(/\s+/g, "-")}`}
            onPress={() => {
              Haptics.selectionAsync().catch(() => {});
              onChange(it.key);
            }}
            style={[styles.chip, active && styles.chipActive]}
          >
            <Text style={[styles.text, active && styles.textActive]}>{it.label}</Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

const useStyles = makeStyles((c) => ({
  row: { height: 48, flexGrow: 0 },
  content: { gap: spacing.sm, paddingHorizontal: spacing.lg, alignItems: "center", paddingBottom: spacing.sm },
  chip: {
    height: 32, paddingHorizontal: spacing.md, borderRadius: radius.pill, flexShrink: 0,
    borderWidth: 1, borderColor: c.border, alignItems: "center", justifyContent: "center",
  },
  chipActive: { backgroundColor: c.surfaceTertiary, borderColor: c.onSurface },
  text: { color: c.onSurfaceTertiary, fontFamily: fonts.displaySemi, fontSize: 15 },
  textActive: { color: c.onSurface },
}));
