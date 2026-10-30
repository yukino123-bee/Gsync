import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps, ReactNode } from 'react';
import {
  ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleProp, StyleSheet, Text, TextInput,
  TextInputProps, TextStyle, View, ViewStyle,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { colors, fonts, radius, shadow, spacing } from '@/theme';

type IconName = ComponentProps<typeof Ionicons>['name'];

// ---- Text -----------------------------------------------------------------------------

export function Title({ children, style }: { children: ReactNode; style?: StyleProp<TextStyle> }) {
  return <Text style={[s.title, style]}>{children}</Text>;
}

export function Body({
  children, muted, small, style, numberOfLines,
}: { children: ReactNode; muted?: boolean; small?: boolean; style?: StyleProp<TextStyle>; numberOfLines?: number }) {
  return (
    <Text numberOfLines={numberOfLines} style={[s.body, muted && s.muted, small && s.small, style]}>
      {children}
    </Text>
  );
}

export function SectionHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <View style={s.sectionHeader}>
      <Text style={s.sectionTitle}>{title}</Text>
      {action}
    </View>
  );
}

// ---- Layout ---------------------------------------------------------------------------

interface ScreenProps {
  children: ReactNode;
  scroll?: boolean;
  refreshing?: boolean;
  onRefresh?: () => void;
  /** Reserve space for the status bar. Turn off under a native header or tab bar. */
  padTop?: boolean;
  contentStyle?: StyleProp<ViewStyle>;
}

export function Screen({ children, scroll = true, refreshing, onRefresh, padTop = false, contentStyle }: ScreenProps) {
  const insets = useSafeAreaInsets();
  const padding = { paddingTop: padTop ? insets.top + spacing.md : spacing.md };
  if (!scroll) return <View style={[s.screen, s.pad, padding, contentStyle]}>{children}</View>;
  return (
    <ScrollView
      style={s.screen}
      contentContainerStyle={[s.pad, padding, { paddingBottom: spacing.xxl }, contentStyle]}
      keyboardShouldPersistTaps="handled"
      refreshControl={onRefresh ? <RefreshControl refreshing={!!refreshing} onRefresh={onRefresh} tintColor={colors.primary} /> : undefined}
    >
      {children}
    </ScrollView>
  );
}

export function Card({ children, onPress, style }: { children: ReactNode; onPress?: () => void; style?: StyleProp<ViewStyle> }) {
  if (onPress) {
    return (
      <Pressable onPress={onPress} style={({ pressed }) => [s.card, pressed && { opacity: 0.85 }, style]}>
        {children}
      </Pressable>
    );
  }
  return <View style={[s.card, style]}>{children}</View>;
}

export function Row({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[{ flexDirection: 'row', alignItems: 'center', gap: spacing.sm }, style]}>{children}</View>;
}

// ---- Inputs ---------------------------------------------------------------------------

interface FieldProps extends TextInputProps {
  label?: string;
  error?: string | null;
}

export function TextField({ label, error, style, ...rest }: FieldProps) {
  return (
    <View style={{ marginBottom: spacing.md }}>
      {label ? <Text style={s.label}>{label}</Text> : null}
      <TextInput
        placeholderTextColor={colors.textMuted}
        style={[s.input, rest.multiline && { minHeight: 90, textAlignVertical: 'top' }, !!error && { borderColor: colors.danger }, style]}
        {...rest}
      />
      {error ? <Text style={s.fieldError}>{error}</Text> : null}
    </View>
  );
}

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  loading?: boolean;
  disabled?: boolean;
  icon?: IconName;
  small?: boolean;
  style?: StyleProp<ViewStyle>;
}

export function Button({ title, onPress, variant = 'primary', loading, disabled, icon, small, style }: ButtonProps) {
  const off = disabled || loading;
  const fg = variant === 'primary' || variant === 'danger' ? colors.textOnPrimary : variant === 'ghost' ? colors.primary : colors.primary;
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      disabled={off}
      style={({ pressed }) => [
        s.button, small && s.buttonSmall, btnBg[variant], off && { opacity: 0.5 }, pressed && { opacity: 0.8 }, style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={fg} />
      ) : (
        <>
          {icon ? <Ionicons name={icon} size={small ? 16 : 18} color={fg} /> : null}
          <Text style={[s.buttonText, small && { fontSize: fonts.size.sm }, { color: fg }]}>{title}</Text>
        </>
      )}
    </Pressable>
  );
}

const btnBg = StyleSheet.create({
  primary: { backgroundColor: colors.primary },
  secondary: { backgroundColor: colors.primarySoft },
  danger: { backgroundColor: colors.danger },
  ghost: { backgroundColor: 'transparent' },
});

// ---- Feedback -------------------------------------------------------------------------

export function Loading({ label }: { label?: string }) {
  return (
    <View style={s.center}>
      <ActivityIndicator size="large" color={colors.primary} />
      {label ? <Body muted style={{ marginTop: spacing.md }}>{label}</Body> : null}
    </View>
  );
}

export function EmptyState({ icon = 'file-tray-outline', title, message, action }: {
  icon?: IconName; title: string; message?: string; action?: ReactNode;
}) {
  return (
    <View style={s.center}>
      <Ionicons name={icon} size={44} color={colors.textMuted} />
      <Text style={s.emptyTitle}>{title}</Text>
      {message ? <Body muted style={{ textAlign: 'center' }}>{message}</Body> : null}
      {action ? <View style={{ marginTop: spacing.lg }}>{action}</View> : null}
    </View>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <View style={s.center}>
      <Ionicons name="alert-circle-outline" size={44} color={colors.danger} />
      <Text style={s.emptyTitle}>Something went wrong</Text>
      <Body muted style={{ textAlign: 'center' }}>{message}</Body>
      {onRetry ? <View style={{ marginTop: spacing.lg }}><Button title="Try again" onPress={onRetry} variant="secondary" icon="refresh" /></View> : null}
    </View>
  );
}

export function ErrorBanner({ message }: { message: string | null | undefined }) {
  if (!message) return null;
  return (
    <View style={s.banner} accessibilityRole="alert">
      <Ionicons name="alert-circle" size={18} color={colors.danger} />
      <Text style={s.bannerText}>{message}</Text>
    </View>
  );
}

// ---- Small widgets --------------------------------------------------------------------

type Tone = 'neutral' | 'success' | 'warning' | 'danger' | 'info';
const tones: Record<Tone, { bg: string; fg: string }> = {
  neutral: { bg: colors.border, fg: colors.textMuted },
  success: { bg: colors.successSoft, fg: colors.success },
  warning: { bg: colors.warningSoft, fg: colors.warning },
  danger: { bg: colors.dangerSoft, fg: colors.danger },
  info: { bg: colors.infoSoft, fg: colors.info },
};

export function Badge({ label, tone = 'neutral', icon }: { label: string; tone?: Tone; icon?: IconName }) {
  const t = tones[tone];
  return (
    <View style={[s.badge, { backgroundColor: t.bg }]}>
      {icon ? <Ionicons name={icon} size={12} color={t.fg} /> : null}
      <Text style={[s.badgeText, { color: t.fg }]}>{label}</Text>
    </View>
  );
}

export function ProgressBar({ percent, height = 8 }: { percent: number; height?: number }) {
  const clamped = Math.max(0, Math.min(100, percent));
  return (
    <View style={[s.progressTrack, { height }]} accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: 100, now: clamped }}>
      <View style={[s.progressFill, { width: `${clamped}%`, height, backgroundColor: clamped === 100 ? colors.success : colors.primary }]} />
    </View>
  );
}

export function Segmented<T extends string | number>({ options, value, onChange }: {
  options: { value: T; label: string }[]; value: T; onChange: (v: T) => void;
}) {
  return (
    <View style={s.segmented}>
      {options.map((o) => {
        const active = o.value === value;
        return (
          <Pressable key={String(o.value)} onPress={() => onChange(o.value)} style={[s.segment, active && s.segmentActive]} accessibilityState={{ selected: active }}>
            <Text style={[s.segmentText, active && { color: colors.textOnPrimary }]} numberOfLines={1}>{o.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export function Avatar({ name, size = 32 }: { name: string; size?: number }) {
  const text = name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]!.toUpperCase()).join('');
  return (
    <View style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' }}>
      <Text style={{ color: colors.primary, fontWeight: fonts.weight.bold, fontSize: size * 0.4 }}>{text}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  pad: { paddingHorizontal: spacing.lg },
  title: { fontSize: fonts.size.xxl, fontWeight: fonts.weight.bold, color: colors.text, marginBottom: spacing.md },
  body: { fontSize: fonts.size.md, color: colors.text, lineHeight: 22 },
  muted: { color: colors.textMuted },
  small: { fontSize: fonts.size.sm, lineHeight: 18 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: spacing.lg, marginBottom: spacing.sm },
  sectionTitle: { fontSize: fonts.size.lg, fontWeight: fonts.weight.semibold, color: colors.text },
  card: { backgroundColor: colors.surface, borderRadius: radius.lg, padding: spacing.lg, marginBottom: spacing.md, borderWidth: StyleSheet.hairlineWidth, borderColor: colors.border, ...shadow },
  label: { fontSize: fonts.size.sm, fontWeight: fonts.weight.medium, color: colors.text, marginBottom: spacing.xs },
  input: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, paddingHorizontal: spacing.md, paddingVertical: 12, fontSize: fonts.size.md, color: colors.text },
  fieldError: { color: colors.danger, fontSize: fonts.size.xs, marginTop: spacing.xs },
  button: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: spacing.sm, paddingVertical: 14, paddingHorizontal: spacing.lg, borderRadius: radius.md, minHeight: 48 },
  buttonSmall: { paddingVertical: 8, minHeight: 36, paddingHorizontal: spacing.md },
  buttonText: { fontSize: fonts.size.md, fontWeight: fonts.weight.semibold },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.xl, gap: spacing.sm, minHeight: 240 },
  emptyTitle: { fontSize: fonts.size.lg, fontWeight: fonts.weight.semibold, color: colors.text, marginTop: spacing.sm },
  banner: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, backgroundColor: colors.dangerSoft, padding: spacing.md, borderRadius: radius.md, marginBottom: spacing.md },
  bannerText: { color: colors.danger, flex: 1, fontSize: fonts.size.sm },
  badge: { flexDirection: 'row', alignItems: 'center', gap: 4, alignSelf: 'flex-start', paddingHorizontal: 8, paddingVertical: 3, borderRadius: radius.pill },
  badgeText: { fontSize: fonts.size.xs, fontWeight: fonts.weight.semibold },
  progressTrack: { backgroundColor: colors.border, borderRadius: radius.pill, overflow: 'hidden' },
  progressFill: { borderRadius: radius.pill },
  segmented: { flexDirection: 'row', backgroundColor: colors.border, borderRadius: radius.md, padding: 3, marginBottom: spacing.md },
  segment: { flex: 1, paddingVertical: 8, alignItems: 'center', borderRadius: radius.md - 2 },
  segmentActive: { backgroundColor: colors.primary },
  segmentText: { fontSize: fonts.size.sm, fontWeight: fonts.weight.medium, color: colors.text },
});
