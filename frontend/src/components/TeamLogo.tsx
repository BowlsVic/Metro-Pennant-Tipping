import Ionicons from "@react-native-vector-icons/ionicons";
import { Image } from "expo-image";
import { StyleSheet, View } from "react-native";

import { Team, teamLogoUrl } from "@/src/api";

// Team colours are data (fixed brand colours of each club), so they are used directly.
// Uploaded club logos sit on a white badge so any logo artwork stays readable in every theme.
export function TeamLogo({ team, size = 44 }: { team?: Team; size?: number }) {
  if (!team) return <View style={{ width: size, height: size }} />;
  const ring = { width: size, height: size, borderRadius: size / 2, borderWidth: Math.max(2, size / 16) };
  if (team.logo_path) {
    return (
      <View testID={`team-logo-${team.short}`} style={[styles.ring, ring, styles.logoBadge, { borderColor: team.color }]}>
        <Image source={{ uri: teamLogoUrl(team) }} style={{ width: size * 0.74, height: size * 0.74 }} contentFit="contain" transition={150} cachePolicy="memory-disk" />
      </View>
    );
  }
  return (
    <View testID={`team-logo-${team.short}`} style={[styles.ring, ring, { backgroundColor: team.color, borderColor: team.secondary }]}>
      <Ionicons name={team.icon as never} size={size * 0.48} color={team.secondary} />
    </View>
  );
}

const styles = StyleSheet.create({
  ring: { alignItems: "center", justifyContent: "center", overflow: "hidden" },
  logoBadge: { backgroundColor: "#FFFFFF" },
});
