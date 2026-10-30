import { LinearGradient } from 'expo-linear-gradient';
import { useEffect } from 'react';
import { View, type DimensionValue, type StyleProp, type ViewStyle } from 'react-native';
import Animated, { Easing, useAnimatedStyle, useSharedValue, withRepeat, withTiming } from 'react-native-reanimated';

import { colors, radius } from '@/theme';
import { useMotionEnabled } from '@/theme/motion';

interface Props {
  width?: DimensionValue;
  height?: number;
  borderRadius?: number;
  style?: StyleProp<ViewStyle>;
}

/** Grey placeholder with a light shimmer sweeping across it. Static when Reduce Motion is on. */
export function SkeletonLoader({ width = '100%', height = 16, borderRadius = radius.sm, style }: Props) {
  const enabled = useMotionEnabled();
  const x = useSharedValue(-1);

  useEffect(() => {
    if (!enabled) return;
    x.value = withRepeat(withTiming(1, { duration: 1100, easing: Easing.linear }), -1, false);
  }, [enabled, x]);

  // Translate by a fraction of the band's own width, so it needs no layout measurement
  const band = useAnimatedStyle(() => ({ transform: [{ translateX: `${x.value * 100}%` }] }));

  return (
    <View style={[{ width, height, borderRadius, backgroundColor: '#E5E7EB', overflow: 'hidden' }, style]} accessibilityElementsHidden>
      {enabled ? (
        <Animated.View style={[{ ...absoluteFill }, band]}>
          <LinearGradient
            colors={['rgba(255,255,255,0)', 'rgba(255,255,255,0.65)', 'rgba(255,255,255,0)']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={{ flex: 1 }}
          />
        </Animated.View>
      ) : null}
    </View>
  );
}

const absoluteFill = { position: 'absolute', top: 0, bottom: 0, left: 0, right: 0 } as const;

/** A few stacked card-shaped skeletons, used as a list loading state. */
export function SkeletonCards({ count = 3 }: { count?: number }) {
  return (
    <View style={{ gap: 12 }}>
      {Array.from({ length: count }, (_, i) => (
        <View key={i} style={{ backgroundColor: colors.surface, borderRadius: radius.lg, padding: 16, gap: 10, borderWidth: 1, borderColor: colors.border }}>
          <SkeletonLoader width="55%" height={18} />
          <SkeletonLoader width="90%" />
          <SkeletonLoader width="35%" height={10} />
        </View>
      ))}
    </View>
  );
}
