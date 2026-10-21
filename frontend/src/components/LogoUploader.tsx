import * as ImagePicker from "expo-image-picker";
import { useState } from "react";
import { Linking, Text, View } from "react-native";

import { api, Team, TOKEN_KEY } from "@/src/api";
import { useToast } from "@/src/components/Toast";
import { Button } from "@/src/components/ui";
import { fonts, makeStyles, spacing } from "@/src/theme";
import { uploadForm } from "@/src/utils/upload";
import { storage } from "@/src/utils/storage";

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;

export function LogoUploader({ team, onChange }: { team: Team; onChange: (t: Team) => void }) {
  const styles = useStyles();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [blocked, setBlocked] = useState(false);

  const pick = async () => {
    let perm = await ImagePicker.getMediaLibraryPermissionsAsync();
    if (!perm.granted && perm.canAskAgain) perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      setBlocked(!perm.canAskAgain);
      toast("Photo access is needed to choose a logo", "error");
      return;
    }
    setBlocked(false);
    const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], allowsEditing: true, aspect: [1, 1], quality: 0.8 });
    if (res.canceled || !res.assets?.[0]) return;
    const asset = res.assets[0];
    setBusy(true);
    try {
      const token = await storage.secureGet(TOKEN_KEY, null);
      const r = await uploadForm(`${BASE}/api/teams/${team.id}/logo`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        files: { file: { uri: asset.uri, name: asset.fileName ?? "logo.jpg", mimeType: asset.mimeType ?? "image/jpeg" } },
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Upload failed");
      onChange(data as Team);
      toast("Logo uploaded");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Upload failed", "error");
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    try {
      onChange(await api<Team>(`/teams/${team.id}/logo`, { method: "DELETE" }));
      toast("Logo removed, using icon");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.wrap}>
      <Text style={styles.hint}>Upload the club&apos;s real logo (square PNG/JPG, under 3 MB). We&apos;ll ask for photo access so you can pick it.</Text>
      <View style={styles.row}>
        <Button testID="upload-logo-button" title={team.logo_path ? "Replace logo" : "Upload logo"} variant="ghost" onPress={pick} loading={busy} style={{ flex: 1 }} />
        {team.logo_path && <Button testID="remove-logo-button" title="Use icon" variant="danger" onPress={remove} disabled={busy} style={{ flex: 1 }} />}
      </View>
      {blocked && <Button testID="open-settings-button" title="Open Settings" variant="ghost" onPress={() => Linking.openSettings()} />}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  wrap: { gap: spacing.sm },
  hint: { color: c.onSurfaceTertiary, fontFamily: fonts.text, fontSize: 13 },
  row: { flexDirection: "row", gap: spacing.sm },
}));
