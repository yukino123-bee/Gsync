import { LinearGradient } from 'expo-linear-gradient';
import type { ReactNode } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { FadeInView } from '@/components/motion/FadeInView';
import { LogoMark } from '@/components/motion/AnimatedLogo';
import { colors, fonts, gradient, radius, shadow, spacing } from '@/theme';

/** Auth layout: brand gradient (same as the intro) with the form on a white card. */
export function AuthShell({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  const insets = useSafeAreaInsets();
  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <LinearGradient colors={gradient.colors} start={gradient.start} end={gradient.end} style={{ position: 'absolute', top: 0, bottom: 0, left: 0, right: 0 }} />
      <ScrollView
        contentContainerStyle={{ flexGrow: 1, justifyContent: 'center', padding: spacing.xl, paddingTop: insets.top + spacing.xl, paddingBottom: insets.bottom + spacing.xl }}
        keyboardShouldPersistTaps="handled"
      >
        <FadeInView style={{ width: '100%', maxWidth: 440, alignSelf: 'center' }}>
          <View style={{ alignItems: 'center', marginBottom: spacing.xl }}>
            <LogoMark size={72} />
            <Text style={{ fontSize: 32, fontWeight: fonts.weight.bold, color: '#fff', marginTop: spacing.md }}>GroupSync</Text>
            <Text style={{ fontSize: fonts.size.md, color: 'rgba(255,255,255,0.85)', marginTop: 2 }}>Group projects, in sync.</Text>
          </View>
          <View style={[{ backgroundColor: colors.surface, borderRadius: radius.lg, padding: spacing.xl }, shadow]}>
            <Text style={{ fontSize: fonts.size.xl, fontWeight: fonts.weight.semibold, color: colors.text }}>{title}</Text>
            <Text style={{ fontSize: fonts.size.md, color: colors.textMuted, marginTop: spacing.xs, marginBottom: spacing.lg }}>{subtitle}</Text>
            {children}
          </View>
        </FadeInView>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
