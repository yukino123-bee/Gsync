import { LinearGradient } from 'expo-linear-gradient';

import { gradient } from '@/theme';

/** Header background for navigators, matching the intro splash. */
export function GradientHeader() {
  return <LinearGradient colors={gradient.colors} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={{ flex: 1 }} />;
}

export const gradientHeaderOptions = {
  headerBackground: () => <GradientHeader />,
  headerTintColor: '#FFFFFF',
  headerTitleStyle: { color: '#FFFFFF' },
  headerShadowVisible: false,
} as const;
