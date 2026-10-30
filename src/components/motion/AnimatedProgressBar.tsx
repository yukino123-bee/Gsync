import { useEffect, useState } from 'react';
import { Text, View, type StyleProp, type ViewStyle } from 'react-native';
import Animated, { useAnimatedReaction, useAnimatedStyle, useSharedValue, withSpring, withTiming } from 'react-native-reanimated';
import { scheduleOnRN } from 'react-native-worklets';

import { colors, fonts, radius, spacing } from '@/theme';
import { duration, spring, useMotionEnabled } from '@/theme/motion';

interface Props {
  /** 0-100 */
  value: number;
  showLabel?: boolean;
  height?: number;
  color?: string;
  style?: StyleProp<ViewStyle>;
}

/** Bar fills with a spring and the percentage counts up alongside it. */
export function AnimatedProgressBar({ value, showLabel = true, height = 10, color = colors.primary, style }: Props) {
  const enabled = useMotionEnabled();
  const clamped = Math.max(0, Math.min(100, value));
  const progress = useSharedValue(0);
  const [shown, setShown] = useState(enabled ? 0 : Math.round(clamped));

  useEffect(() => {
    progress.value = enabled ? withSpring(clamped, spring.smooth) : withTiming(clamped, { duration: duration.fast });
  }, [clamped, enabled, progress]);

  // Mirror the animated value into React state only when the rounded number changes
  useAnimatedReaction(
    () => Math.round(Math.max(0, Math.min(100, progress.value))),
    (now, prev) => {
      if (now !== prev) scheduleOnRN(setShown, now);
    },
  );

  const fill = useAnimatedStyle(() => ({ width: `${Math.max(0, Math.min(100, progress.value))}%` }));

  return (
    <View style={[{ flexDirection: 'row', alignItems: 'center', gap: spacing.sm }, style]}>
      <View style={{ flex: 1, height, borderRadius: radius.pill, backgroundColor: colors.primarySoft, overflow: 'hidden' }}>
        <Animated.View style={[{ height: '100%', borderRadius: radius.pill, backgroundColor: color }, fill]} />
      </View>
      {showLabel ? (
        <Text style={{ width: 44, textAlign: 'right', fontSize: fonts.size.sm, fontWeight: fonts.weight.semibold, color: colors.text }}>{shown}%</Text>
      ) : null}
    </View>
  );
}
