import Ionicons from "@react-native-vector-icons/ionicons";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Text, View } from "react-native";

import { api, SyncStatus } from "@/src/api";
import { useToast } from "@/src/components/Toast";
import { Button } from "@/src/components/ui";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";
import { formatKickoff } from "@/src/time";

export function BowlslinkCard() {
  const styles = useStyles();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const toast = useToast();
  const status = useQuery({ queryKey: ["sync-status"], queryFn: () => api<SyncStatus>("/admin/sync-status") });
  const [busy, setBusy] = useState<"sync" | "logos" | null>(null);

  const syncNow = async () => {
    setBusy("sync");
    try {
      const s = await api<SyncStatus>("/admin/sync-results", { method: "POST" });
      toast(s.updated ? `${s.updated} result${s.updated === 1 ? "" : "s"} updated` : "Results are up to date");
      ["sync-status", "rounds", "round", "ladder", "all-tips"].forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
    } catch (e) {
      toast(e instanceof Error ? e.message : "Sync failed", "error");
    } finally {
      setBusy(null);
    }
  };

  const importLogos = async () => {
    setBusy("logos");
    try {
      const r = await api<{ imported: number; failed: string[] }>("/admin/import-logos", { method: "POST" });
      toast(r.failed.length ? `${r.imported} logos imported, failed: ${r.failed.join(", ")}` : `${r.imported} club logos imported`, r.failed.length ? "error" : "success");
      qc.invalidateQueries({ queryKey: ["teams"] });
    } catch (e) {
      toast(e instanceof Error ? e.message : "Import failed", "error");
    } finally {
      setBusy(null);
    }
  };

  const s = status.data;
  return (
    <View testID="bowlslink-card" style={styles.box}>
      <View style={styles.titleRow}>
        <Ionicons name="sync" size={18} color={colors.brandPrimary} />
        <Text style={styles.title}>Bowlslink auto-sync</Text>
      </View>
      <Text testID="sync-status-text" style={styles.meta}>
        Results are pulled automatically every 15 minutes.
        {s?.last_sync ? `\nLast synced ${formatKickoff(s.last_sync)} · ${s.completed_found ?? 0} completed matches found` : ""}
      </Text>
      {s?.error ? <Text testID="sync-error-text" style={styles.error}>Last attempt failed: {s.error}</Text> : null}
      <View style={styles.row}>
        <Button testID="sync-results-button" title="Sync now" onPress={syncNow} loading={busy === "sync"} disabled={!!busy} style={{ flex: 1 }} />
        <Button testID="import-logos-button" title="Import logos" variant="ghost" onPress={importLogos} loading={busy === "logos"} disabled={!!busy} style={{ flex: 1 }} />
      </View>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  box: { backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.md, borderWidth: 1, borderColor: c.border, marginBottom: spacing.sm },
  titleRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  title: { color: c.onSurface, fontFamily: fonts.displaySemi, fontSize: 20 },
  meta: { color: c.onSurfaceTertiary, fontFamily: fonts.text, fontSize: 13, lineHeight: 19 },
  error: { color: c.error, fontFamily: fonts.text, fontSize: 13 },
  row: { flexDirection: "row", gap: spacing.sm },
}));
