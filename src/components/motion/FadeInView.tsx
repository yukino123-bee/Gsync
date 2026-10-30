import { useEffect } from 'react';
import type { StyleProp, ViewStyle } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withDelay, withTiming } from 'react-native-reanimated';

import { duration, easing, useMotionEnabled } from '@/theme/motion';

interface Props {
  children: React.ReactNode;
  delay?: number;
  /** Starting vertical offset; 0 for a pure fade */
  distance?: number;
  style?: StyleProp<ViewStyle>;
}

/** Fade + slight upward slide on mount (250 ms ease-out). With Reduce Motion it is a plain fade. */
export function FadeInView({ children, delay = 0, distance = 12, style }: Props) {
  const enabled = useMotionEnabled();
  const progress = useSharedValue(0);

  useEffect(() => {
    progress.value = withDelay(delay, withTiming(1, { duration: enabled ? duration.normal : duration.fast, easing: easing.out }));
  }, [delay, enabled, progress]);

  const animated = useAnimatedStyle(() => ({
    opacity: progress.value,
    transform: [{ translateY: enabled ? (1 - progress.value) * distance : 0 }],
  }));

  return <Animated.View style={[style, animated]}>{children}</Animated.View>;
}
