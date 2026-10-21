import Ionicons from "@react-native-vector-icons/ionicons";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";

import { api } from "@/src/api";
import { useToast } from "@/src/components/Toast";
import { EmptyState } from "@/src/components/ui";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

type Player = { id: string; name: string; email: string; created_at: string; tips: number };

export function PlayersAdmin() {
  const styles = useStyles();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const toast = useToast();
  const q = useQuery({ queryKey: ["admin-players"], queryFn: () => api<Player[]>("/admin/players") });
  const [confirming, setConfirming] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const remove = async (p: Player) => {
    setBusy(p.id);
    try {
      await api(`/admin/players/${p.id}`, { method: "DELETE" });
      toast(`${p.name} removed`);
      setConfirming(null);
      qc.invalidateQueries({ queryKey: ["admin-players"] });
      qc.invalidateQueries({ queryKey: ["ladder"] });
      qc.invalidateQueries({ queryKey: ["all-tips"] });
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "error");
    } finally {
      setBusy(null);
    }
  };

  if (q.isLoading) return <ActivityIndicator color={colors.brandPrimary} />;
  const players = q.data ?? [];

  return (
    <>
      <Text testID="players-count" style={styles.note}>
        {players.length} player{players.length === 1 ? "" : "s"}. Removing a player deletes their account and all their tips, and takes them off the ladder.
      </Text>
      {players.length === 0 && <EmptyState testID="players-empty" title="No players yet" subtitle="Players appear here once they sign up." />}
      {players.map((p) => (
        <View key={p.id} testID={`player-row-${p.id}`} style={styles.row}>
          <View style={styles.avatar}><Text style={styles.avatarText}>{p.name[0]?.toUpperCase()}</Text></View>
          <View style={{ flex: 1 }}>
            <Text numberOfLines={1} style={styles.name}>{p.name}</Text>
            <Text numberOfLines={1} style={styles.meta}>{p.email} · {p.tips} tips</Text>
          </View>
          {confirming === p.id ? (
            <View style={styles.confirm}>
              <Pressable testID={`player-cancel-${p.id}`} onPress={() => setConfirming(null)} style={styles.cancelBtn}>
                <Text style={styles.cancelText}>Cancel</Text>
              </Pressable>
              <Pressable testID={`player-confirm-remove-${p.id}`} onPress={() => remove(p)} disabled={busy === p.id} style={styles.removeBtn}>
                {busy === p.id ? <ActivityIndicator color={colors.onError} size="small" /> : <Text style={styles.removeText}>Remove</Text>}
              </Pressable>
            </View>
          ) : (
            <Pressable testID={`player-remove-${p.id}`} hitSlop={8} onPress={() => setConfirming(p.id)} style={styles.trash}>
              <Ionicons name="person-remove-outline" size={20} color={colors.error} />
            </Pressable>
          )}
        </View>
      ))}
    </>
  );
}

const useStyles = makeStyles((c) => ({
  note: { color: c.onSurfaceTertiary, fontFamily: fonts.text, fontSize: 13, marginBottom: spacing.sm },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: c.surfaceSecondary, borderRadius: radius.md, padding: spacing.md, minHeight: 60 },
  avatar: { width: 36, height: 36, borderRadius: 18, backgroundColor: c.surfaceTertiary, alignItems: "center", justifyContent: "center" },
  avatarText: { color: c.onSurface, fontFamily: fonts.display, fontSize: 18 },
  name: { color: c.onSurface, fontFamily: fonts.displaySemi, fontSize: 18 },
  meta: { color: c.onSurfaceTertiary, fontFamily: fonts.text, fontSize: 12 },
  trash: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  confirm: { flexDirection: "row", gap: spacing.xs },
  cancelBtn: { height: 36, paddingHorizontal: spacing.sm, borderRadius: radius.sm, justifyContent: "center", backgroundColor: c.surfaceTertiary },
  cancelText: { color: c.onSurface, fontFamily: fonts.displaySemi, fontSize: 14 },
  removeBtn: { height: 36, minWidth: 72, paddingHorizontal: spacing.sm, borderRadius: radius.sm, alignItems: "center", justifyContent: "center", backgroundColor: c.error },
  removeText: { color: c.onError, fontFamily: fonts.displaySemi, fontSize: 14 },
}));
