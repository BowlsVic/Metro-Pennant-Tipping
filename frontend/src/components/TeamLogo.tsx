import Ionicons from "@react-native-vector-icons/ionicons";
import { StyleSheet, View } from "react-native";

import { Team } from "@/src/api";

// Team colours are data (fixed brand colours of each club), so they are used directly.
export function TeamLogo({ team, size = 44 }: { team?: Team; size?: number }) {
  if (!team) return <View style={{ width: size, height: size }} />;
  return (
    <View
      testID={`team-logo-${team.short}`}
      style={[
        styles.ring,
        { width: size, height: size, borderRadius: size / 2, backgroundColor: team.color, borderColor: team.secondary, borderWidth: Math.max(2, size / 16) },
      ]}
    >
      <Ionicons name={team.icon as never} size={size * 0.48} color={team.secondary} />
    </View>
  );
}

const styles = StyleSheet.create({
  ring: { alignItems: "center", justifyContent: "center" },
});
