import React, { createContext, useCallback, useContext, useRef, useState } from "react";
import { Text } from "react-native";
import Animated, { FadeInUp, FadeOutUp } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { fonts, makeStyles, radius, spacing } from "@/src/theme";

type Kind = "success" | "error";
const Ctx = createContext<(msg: string, kind?: Kind) => void>(() => {});

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toast, setToast] = useState<{ msg: string; kind: Kind; key: number } | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const insets = useSafeAreaInsets();
  const styles = useStyles();

  const show = useCallback((msg: string, kind: Kind = "success") => {
    if (timer.current) clearTimeout(timer.current);
    setToast({ msg, kind, key: Date.now() });
    timer.current = setTimeout(() => setToast(null), 2600);
  }, []);

  return (
    <Ctx.Provider value={show}>
      {children}
      {toast && (
        <Animated.View
          key={toast.key}
          entering={FadeInUp}
          exiting={FadeOutUp}
          style={[styles.toast, { pointerEvents: "none" }, { top: insets.top + spacing.sm }, toast.kind === "error" ? styles.error : styles.success]}
        >
          <Text testID="toast-message" style={toast.kind === "error" ? styles.errorText : styles.successText}>
            {toast.msg}
          </Text>
        </Animated.View>
      )}
    </Ctx.Provider>
  );
}

export const useToast = () => useContext(Ctx);

const useStyles = makeStyles((c) => ({
  toast: {
    position: "absolute",
    left: spacing.lg,
    right: spacing.lg,
    padding: spacing.md,
    borderRadius: radius.md,
  },
  success: { backgroundColor: c.success },
  error: { backgroundColor: c.error },
  successText: { color: c.onSuccess, fontFamily: fonts.text, fontSize: 14, fontWeight: "600" },
  errorText: { color: c.onError, fontFamily: fonts.text, fontSize: 14, fontWeight: "600" },
}));
