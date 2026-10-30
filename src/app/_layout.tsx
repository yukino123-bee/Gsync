import { Stack, SplashScreen } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useCallback, useEffect, useState } from 'react';
import { Platform, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { gradientHeaderOptions } from '@/components/GradientHeader';
import { IntroSplash, introAlreadyPlayed } from '@/components/motion/IntroSplash';
import { usePushNotifications } from '@/utils/push';
import { colors } from '@/theme';
import { useAuth } from '@/store/auth';

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const bootstrap = useAuth((s) => s.bootstrap);
  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  // Brand intro plays once per session, after the native splash has gone
  const ready = useAuth((s) => s.status) !== 'loading';
  const [showIntro, setShowIntro] = useState(!introAlreadyPlayed());
  const endIntro = useCallback(() => setShowIntro(false), []);

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      {/* On wide screens (web/tablet) keep the app in a centred, phone-like column instead of stretching it */}
      <View style={frame.outer}>
        <View style={frame.inner}>
          <RootNavigator />
        </View>
        {ready && showIntro ? <IntroSplash onDone={endIntro} /> : null}
      </View>
    </SafeAreaProvider>
  );
}

const frame = {
  outer: { flex: 1, backgroundColor: Platform.OS === 'web' ? '#E9EBF3' : colors.background },
  inner: {
    flex: 1, width: '100%', maxWidth: Platform.OS === 'web' ? 720 : undefined, alignSelf: 'center',
    backgroundColor: colors.background, overflow: 'hidden',
    ...(Platform.OS === 'web' ? { borderLeftWidth: 1, borderRightWidth: 1, borderColor: colors.border } : null),
  },
} as const;

function RootNavigator() {
  const status = useAuth((s) => s.status);
  const role = useAuth((s) => s.user?.role);
  const signedIn = status === 'signedIn';
  usePushNotifications(signedIn);

  useEffect(() => {
    if (status !== 'loading') SplashScreen.hide();
  }, [status]);

  if (status === 'loading') return null; // splash screen is still visible

  const header = {
    ...gradientHeaderOptions,
    contentStyle: { backgroundColor: colors.background },
  } as const;

  return (
    <Stack screenOptions={{ headerShown: false, ...header }}>
      <Stack.Protected guard={!signedIn}>
        <Stack.Screen name="(auth)" />
      </Stack.Protected>

      <Stack.Protected guard={role === 'student'}>
        <Stack.Screen name="(student)" />
      </Stack.Protected>
      <Stack.Protected guard={role === 'teacher'}>
        <Stack.Screen name="(teacher)" />
      </Stack.Protected>
      <Stack.Protected guard={role === 'admin'}>
        <Stack.Screen name="admin" />
      </Stack.Protected>

      {/* Shared by both roles; each screen adapts (teachers get a read-only workspace) */}
      <Stack.Protected guard={signedIn && role !== 'admin'}>
        <Stack.Screen name="group/[id]" options={{ headerShown: true, title: 'Group' }} />
        <Stack.Screen name="project/new" options={{ headerShown: true, title: 'New project', presentation: 'modal' }} />
        <Stack.Screen name="project/[id]" options={{ headerShown: true, title: 'Project' }} />
        <Stack.Screen name="manage-groups/[id]" options={{ headerShown: true, title: 'Manage groups' }} />
        <Stack.Screen name="evaluation/[id]" options={{ headerShown: true, title: 'Peer evaluations' }} />
      </Stack.Protected>
    </Stack>
  );
}
