import { useEffect, useMemo } from 'react';
import { View } from 'react-native';
import Animated, { Easing, useAnimatedStyle, useSharedValue, withDelay, withTiming } from 'react-native-reanimated';

import { useMotionEnabled } from '@/theme/motion';

// Deterministic pseudo-random in [0,1): keeps render pure while still looking scattered
const rand = (n: number) => {
  const x = Math.sin(n * 12.9898) * 43758.5453;
  return x - Math.floor(x);
};

const COLORS = ['#4F46E5', '#22D3EE', '#16A34A', '#F59E0B', '#EC4899'];

interface Props {
  /** Change this number (e.g. increment it) to fire a burst */
  burst: number;
  count?: number;
  radius?: number;
}

function Piece({ burst, angle, distance, spin, color, size, delay }: {
  burst: number; angle: number; distance: number; spin: number; color: string; size: number; delay: number;
}) {
  const t = useSharedValue(0);

  useEffect(() => {
    if (!burst) return;
    t.value = 0;
    t.value = withDelay(delay, withTiming(1, { duration: 750, easing: Easing.out(Easing.quad) }));
  }, [burst, delay, t]);

  const style = useAnimatedStyle(() => ({
    opacity: t.value === 0 ? 0 : 1 - Math.max(0, (t.value - 0.6) / 0.4),
    transform: [
      { translateX: Math.cos(angle) * distance * t.value },
      // gravity: pieces arc up then fall
      { translateY: Math.sin(angle) * distance * t.value + 50 * t.value * t.value },
      { rotate: `${spin * t.value}deg` },
    ],
  }));

  return <Animated.View style={[{ position: 'absolute', width: size, height: size * 0.5, backgroundColor: color, borderRadius: 2 }, style]} />;
}

/** Small confetti burst built from Reanimated views (UI thread, no assets). Does nothing with Reduce Motion. */
export function Confetti({ burst, count = 22, radius = 70 }: Props) {
  const enabled = useMotionEnabled();
  const pieces = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => ({
        angle: (i / count) * Math.PI * 2 + rand(i + 1) * 0.4,
        distance: radius * (0.55 + rand(i + 2) * 0.6),
        spin: (rand(i + 3) - 0.5) * 720,
        color: COLORS[i % COLORS.length]!,
        size: 6 + rand(i + 4) * 6,
        delay: rand(i + 4) * 60,
      })),
    [count, radius],
  );

  if (!enabled) return null;
  return (
    <View pointerEvents="none" style={{ position: 'absolute', top: '50%', left: '50%', width: 0, height: 0 }}>
      {pieces.map((p, i) => (
        <Piece key={i} burst={burst} {...p} />
      ))}
    </View>
  );
}
