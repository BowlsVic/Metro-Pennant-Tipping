import * as Haptics from "expo-haptics";
import { useEffect, useRef } from "react";
import { Pressable, ScrollView, Text } from "react-native";

import { RoundSummary } from "@/src/api";
import { fonts, makeStyles, radius, spacing } from "@/src/theme";

export function chipLabel(r: RoundSummary) {
  return r.is_final ? r.name : `R${r.number}`;
}

export function RoundChips({ rounds, selected, onSelect }: { rounds: RoundSummary[]; selected: number | null; onSelect: (n: number) => void }) {
  const styles = useStyles();
  const ref = useRef<ScrollView>(null);
  const idx = rounds.findIndex((r) => r.number === selected);

  useEffect(() => {
    if (idx > 2) ref.current?.scrollTo({ x: (idx - 2) * 60, animated: true });
  }, [idx]);

  return (
    <ScrollView
      ref={ref}
      horizontal
      showsHorizontalScrollIndicator={false}
      style={styles.row}
      contentContainerStyle={styles.content}
    >
      {rounds.map((r) => {
        const active = r.number === selected;
        return (
          <Pressable
            key={r.number}
            testID={`round-chip-${r.number}`}
            onPress={() => {
              Haptics.selectionAsync().catch(() => {});
              onSelect(r.number);
            }}
            style={[styles.chip, active && styles.chipActive, r.is_final && !active && styles.chipFinal]}
          >
            <Text style={[styles.text, active && styles.textActive]}>{chipLabel(r)}</Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

const useStyles = makeStyles((c) => ({
  row: { height: 56, flexGrow: 0 },
  content: { gap: spacing.sm, paddingHorizontal: spacing.lg, alignItems: "center" },
  chip: {
    height: 36, minWidth: 48, paddingHorizontal: spacing.md, borderRadius: radius.pill, flexShrink: 0,
    backgroundColor: c.surfaceTertiary, borderWidth: 1, borderColor: c.border, alignItems: "center", justifyContent: "center",
  },
  chipActive: { backgroundColor: c.brandPrimary, borderColor: c.brandPrimary },
  chipFinal: { borderColor: c.brandSecondary },
  text: { color: c.onSurfaceSecondary, fontFamily: fonts.displaySemi, fontSize: 16 },
  textActive: { color: c.onBrandPrimary },
}));
