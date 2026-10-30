import { LinearGradient } from 'expo-linear-gradient';
import { useEffect } from 'react';
import { StyleSheet } from 'react-native';
import Animated, { Easing, useAnimatedStyle, useSharedValue, withDelay, withTiming } from 'react-native-reanimated';
import { scheduleOnRN } from 'react-native-worklets';

import { duration, useMotionEnabled } from '@/theme/motion';
import { AnimatedLogo, LOGO_TIMELINE } from './AnimatedLogo';

// Module-level, so the intro plays once per app session (a reload of the JS bundle resets it)
let played = false;
export const introAlreadyPlayed = () => played;

/** Full-screen brand intro shown over the first screen, then scales slightly and fades away. */
export function IntroSplash({ onDone }: { onDone: () => void }) {
  const enabled = useMotionEnabled();
  const bg = useSharedValue(0);
  const exit = useSharedValue(0);

  useEffect(() => {
    played = true;
    bg.value = withTiming(1, { duration: enabled ? 300 : 0 });
    // Reduce Motion: show the finished logo briefly, then cross-fade out
    const exitAt = enabled ? LOGO_TIMELINE.exit : 700;
    exit.value = withDelay(
      exitAt,
      withTiming(1, { duration: duration.normal, easing: Easing.out(Easing.cubic) }, (finished) => {
        if (finished) scheduleOnRN(onDone);
      }),
    );
  }, [bg, enabled, exit, onDone]);

  const container = useAnimatedStyle(() => ({ opacity: 1 - exit.value }));
  const content = useAnimatedStyle(() => ({ transform: [{ scale: 1 + exit.value * 0.06 }] }));
  const gradient = useAnimatedStyle(() => ({ opacity: bg.value }));

  return (
    <Animated.View style={[StyleSheet.absoluteFill, { backgroundColor: '#3730A3', alignItems: 'center', justifyContent: 'center', zIndex: 100 }, container]}>
      <Animated.View style={[StyleSheet.absoluteFill, gradient]}>
        <LinearGradient colors={['#4F46E5', '#6D5EF0', '#22D3EE']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={{ flex: 1 }} />
      </Animated.View>
      <Animated.View style={content}>
        <AnimatedLogo />
      </Animated.View>
    </Animated.View>
  );
}
