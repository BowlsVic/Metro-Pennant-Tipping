import * as AppleAuthentication from "expo-apple-authentication";
import Ionicons from "@react-native-vector-icons/ionicons";
import { useEffect, useState } from "react";
import { ActivityIndicator, Platform, Pressable, Text, View } from "react-native";

import { useAuth } from "@/src/auth";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

// Google & Apple buttons use their fixed brand colours (identical in every theme).
export function SocialButtons({ onError }: { onError: (msg: string) => void }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const { loginWithGoogle, loginWithApple } = useAuth();
  const [appleAvailable, setAppleAvailable] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (Platform.OS === "ios") AppleAuthentication.isAvailableAsync().then(setAppleAvailable).catch(() => {});
  }, []);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.wrap}>
      <View style={styles.dividerRow}>
        <View style={styles.line} />
        <Text style={styles.or}>or</Text>
        <View style={styles.line} />
      </View>
      <Pressable
        testID="google-signin-button"
        disabled={busy}
        onPress={() => run(loginWithGoogle)}
        style={({ pressed }) => [styles.google, (pressed || busy) && { opacity: 0.85 }]}
      >
        {busy ? (
          <ActivityIndicator color={colors.onSurfaceInverse} />
        ) : (
          <>
            <Ionicons name="logo-google" size={20} color="#4285F4" />
            <Text style={styles.googleText}>Continue with Google</Text>
          </>
        )}
      </Pressable>
      {appleAvailable && (
        <AppleAuthentication.AppleAuthenticationButton
          testID="apple-signin-button"
          buttonType={AppleAuthentication.AppleAuthenticationButtonType.CONTINUE}
          buttonStyle={AppleAuthentication.AppleAuthenticationButtonStyle.WHITE}
          cornerRadius={radius.md}
          style={styles.apple}
          onPress={() => run(loginWithApple)}
        />
      )}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  wrap: { gap: spacing.md, marginTop: spacing.sm },
  dividerRow: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  line: { flex: 1, height: 1, backgroundColor: c.divider },
  or: { color: c.muted, fontFamily: fonts.text, fontSize: 13 },
  google: {
    height: 52, borderRadius: radius.md, backgroundColor: "#FFFFFF", flexDirection: "row",
    alignItems: "center", justifyContent: "center", gap: spacing.sm,
  },
  googleText: { color: "#1F1F1F", fontFamily: fonts.text, fontSize: 16, fontWeight: "600" },
  apple: { height: 52, width: "100%" },
}));
