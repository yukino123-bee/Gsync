import { Alert } from '@/utils/alert';
import { LinearGradient } from 'expo-linear-gradient';
import { useState } from 'react';
import { Text, View } from 'react-native';

import { Avatar, Body, Button, Card, Row, Screen } from '@/components/ui';
import { useAuth } from '@/store/auth';
import { API_URL } from '@/utils/config';
import { fonts, gradient, radius, spacing } from '@/theme';

export function ProfileView() {
  const user = useAuth((s) => s.user);
  const logout = useAuth((s) => s.logout);
  const [busy, setBusy] = useState(false);
  if (!user) return null;

  function confirmLogout() {
    Alert.alert('Sign out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign out', style: 'destructive',
        onPress: async () => {
          setBusy(true);
          await logout();
        },
      },
    ]);
  }

  return (
    <Screen>
      <LinearGradient colors={gradient.colors} start={gradient.start} end={gradient.end} style={{ borderRadius: radius.lg, padding: spacing.xl, marginBottom: spacing.md }}>
        <Row style={{ gap: spacing.lg }}>
          <Avatar name={user.name} size={64} />
          <View style={{ flex: 1, gap: 2 }}>
            <Text style={{ fontSize: fonts.size.xl, fontWeight: fonts.weight.bold, color: '#fff' }}>{user.name}</Text>
            <Text style={{ fontSize: fonts.size.sm, color: 'rgba(255,255,255,0.85)', marginBottom: spacing.xs }}>{user.email}</Text>
            <View style={{ alignSelf: 'flex-start', backgroundColor: 'rgba(255,255,255,0.22)', borderRadius: radius.pill, paddingHorizontal: 10, paddingVertical: 3 }}>
              <Text style={{ color: '#fff', fontSize: fonts.size.xs, fontWeight: fonts.weight.semibold, textTransform: 'capitalize' }}>{user.role}</Text>
            </View>
          </View>
        </Row>
      </LinearGradient>
      <Card>
        <Body muted small>Server</Body>
        <Body small>{API_URL}</Body>
      </Card>
      <Button title="Sign out" variant="danger" icon="log-out-outline" onPress={confirmLogout} loading={busy} />
    </Screen>
  );
}
