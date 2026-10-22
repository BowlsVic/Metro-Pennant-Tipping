import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";
import { Redirect } from "expo-router";
import { useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useAuth } from "@/src/auth";
import { SocialButtons } from "@/src/components/SocialButtons";
import { Button } from "@/src/components/ui";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const HERO =
  "https://images.unsplash.com/photo-1770658118825-3bc745f79f42?fm=jpg&q=80&w=1200&auto=format&fit=crop";

export default function Login() {
  const { user, login, register, authError } = useAuth();
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  if (user) return <Redirect href="/(tabs)" />;
  const shownErr = err ?? authError;

  const submit = async () => {
    setErr(null);
    if (!email || !password || (mode === "register" && !name)) return setErr("Please fill in all fields");
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(name, email, password);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.root}>
      <KeyboardAwareScrollView bottomOffset={24} contentContainerStyle={{ paddingBottom: insets.bottom + spacing.xl }} keyboardShouldPersistTaps="handled">
        <View style={styles.hero}>
          <Image source={{ uri: HERO }} style={styles.heroImg} contentFit="cover" contentPosition="bottom" />
          <LinearGradient colors={["transparent", colors.scrim, colors.surface]} style={styles.heroScrim} />
          <View style={[styles.heroText, { paddingTop: insets.top }]}>
            <Text style={styles.kicker}>BOWLS TIPPING · METRO PENNANT 2026-27</Text>
            <Text testID="app-title" style={styles.title}>TIP{"\n"}MASTERS</Text>
          </View>
        </View>

        <View style={styles.form}>
          <View style={styles.segment}>
            {(["login", "register"] as const).map((m) => (
              <Pressable
                key={m}
                testID={`auth-mode-${m}`}
                onPress={() => { setMode(m); setErr(null); }}
                style={[styles.segBtn, mode === m && styles.segActive]}
              >
                <Text style={[styles.segText, mode === m && styles.segTextActive]}>{m === "login" ? "Sign in" : "Join comp"}</Text>
              </Pressable>
            ))}
          </View>

          {shownErr && (
            <View testID="auth-error" style={styles.errBox}>
              <Text style={styles.errText}>{shownErr}</Text>
            </View>
          )}

          {mode === "register" && (
            <TextInput
              testID="register-name-input"
              style={styles.input}
              placeholder="Display name"
              placeholderTextColor={colors.muted}
              value={name}
              onChangeText={setName}
              maxLength={40}
            />
          )}
          <TextInput
            testID="auth-email-input"
            style={styles.input}
            placeholder="Email"
            placeholderTextColor={colors.muted}
            autoCapitalize="none"
            keyboardType="email-address"
            value={email}
            onChangeText={setEmail}
          />
          <TextInput
            testID="auth-password-input"
            style={styles.input}
            placeholder="Password (min 6 characters)"
            placeholderTextColor={colors.muted}
            secureTextEntry
            value={password}
            onChangeText={setPassword}
            onSubmitEditing={submit}
          />
          <Button testID="auth-submit-button" title={mode === "login" ? "Sign in" : "Create account"} onPress={submit} loading={busy} />
          <SocialButtons onError={setErr} />
        </View>
      </KeyboardAwareScrollView>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  hero: { height: 340 },
  heroImg: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0 },
  heroScrim: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0 },
  heroText: { flex: 1, justifyContent: "flex-end", paddingHorizontal: spacing.xl, paddingBottom: spacing.lg },
  kicker: { color: c.brandPrimary, fontFamily: fonts.displaySemi, fontSize: 14, letterSpacing: 2 },
  title: { color: c.onSurface, fontFamily: fonts.display, fontSize: 64, lineHeight: 60, marginTop: spacing.xs },
  form: { paddingHorizontal: spacing.xl, gap: spacing.md },
  segment: { flexDirection: "row", backgroundColor: c.surfaceSecondary, borderRadius: radius.md, padding: spacing.xs, marginBottom: spacing.sm },
  segBtn: { flex: 1, height: 44, alignItems: "center", justifyContent: "center", borderRadius: radius.sm },
  segActive: { backgroundColor: c.surfaceTertiary },
  segText: { color: c.muted, fontFamily: fonts.text, fontSize: 14, fontWeight: "600" },
  segTextActive: { color: c.onSurface },
  input: {
    height: 52, backgroundColor: c.surfaceTertiary, borderRadius: radius.md, borderWidth: 1, borderColor: c.border,
    paddingHorizontal: spacing.lg, color: c.onSurface, fontFamily: fonts.text, fontSize: 16,
  },
  errBox: { backgroundColor: c.errorTint, borderColor: c.error, borderWidth: 1, borderRadius: radius.md, padding: spacing.md },
  errText: { color: c.error, fontFamily: fonts.text, fontSize: 14 },
}));
