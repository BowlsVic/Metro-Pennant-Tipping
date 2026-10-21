import React from "react";
import { ActivityIndicator, Pressable, Text, View, ViewStyle } from "react-native";

import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

export function Button({
  title, onPress, loading, disabled, variant = "primary", testID, style,
}: {
  title: string; onPress: () => void; loading?: boolean; disabled?: boolean;
  variant?: "primary" | "ghost" | "danger"; testID: string; style?: ViewStyle;
}) {
  const styles = useStyles();
  const { colors } = useTheme();
  const off = disabled || loading;
  return (
    <Pressable
      testID={testID}
      onPress={onPress}
      disabled={off}
      style={({ pressed }) => [
        styles.btn,
        variant === "primary" && styles.primary,
        variant === "ghost" && styles.ghost,
        variant === "danger" && styles.danger,
        off && styles.disabled,
        pressed && styles.pressed,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={variant === "primary" ? colors.onBrandPrimary : colors.onSurface} />
      ) : (
        <Text style={[styles.btnText, variant === "primary" ? styles.primaryText : variant === "danger" ? styles.dangerText : styles.ghostText]}>
          {title}
        </Text>
      )}
    </Pressable>
  );
}

export function EmptyState({ title, subtitle, testID }: { title: string; subtitle?: string; testID: string }) {
  const styles = useStyles();
  return (
    <View testID={testID} style={styles.empty}>
      <Text style={styles.emptyTitle}>{title}</Text>
      {subtitle ? <Text style={styles.emptySub}>{subtitle}</Text> : null}
    </View>
  );
}

export function ErrorState({ onRetry, message }: { onRetry: () => void; message?: string }) {
  const styles = useStyles();
  return (
    <View testID="error-state" style={styles.empty}>
      <Text style={styles.emptyTitle}>{message ?? "Couldn't load data"}</Text>
      <Button testID="retry-button" title="Retry" variant="ghost" onPress={onRetry} style={{ marginTop: spacing.lg, paddingHorizontal: spacing.xl }} />
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  btn: { height: 52, borderRadius: radius.md, alignItems: "center", justifyContent: "center", paddingHorizontal: spacing.lg },
  primary: { backgroundColor: c.brandPrimary },
  ghost: { backgroundColor: c.surfaceTertiary, borderWidth: 1, borderColor: c.border },
  danger: { backgroundColor: c.errorTint, borderWidth: 1, borderColor: c.error },
  disabled: { opacity: 0.45 },
  pressed: { transform: [{ scale: 0.98 }], opacity: 0.9 },
  btnText: { fontFamily: fonts.display, fontSize: 20, letterSpacing: 0.5, textTransform: "uppercase" },
  primaryText: { color: c.onBrandPrimary },
  ghostText: { color: c.onSurface },
  dangerText: { color: c.error },
  empty: { alignItems: "center", justifyContent: "center", padding: spacing.xxl },
  emptyTitle: { color: c.onSurface, fontFamily: fonts.display, fontSize: 24, textAlign: "center" },
  emptySub: { color: c.onSurfaceTertiary, fontFamily: fonts.text, fontSize: 14, marginTop: spacing.sm, textAlign: "center" },
}));
