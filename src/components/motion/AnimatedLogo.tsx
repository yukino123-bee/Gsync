import { LinearGradient } from 'expo-linear-gradient';
import { useEffect } from 'react';
import { View } from 'react-native';
import Animated, {
  Easing, useAnimatedProps, useAnimatedStyle, useSharedValue, withDelay, withSpring, withTiming,
} from 'react-native-reanimated';
import Svg, { Path } from 'react-native-svg';

import { spring, useMotionEnabled } from '@/theme/motion';

const AnimatedPath = Animated.createAnimatedComponent(Path);

/** Intro timeline in ms (relative to the start of the intro). */
export const LOGO_TIMELINE = {
  draw: 300,
  drawDuration: 700,
  fill: 1000,
  text: 1500,
  textStagger: 40,
  shine: 2200,
  exit: 2500,
} as const;

// Two overlapping speech bubbles that read as a "G": the big bubble is the open curve, the small one is the bar.
const BUBBLE_BACK = 'M28 12 H60 Q76 12 76 28 V48 Q76 64 60 64 H34 L20 78 L22 62 Q12 58 12 48 V28 Q12 12 28 12 Z';
const BUBBLE_FRONT = 'M60 56 H92 Q108 56 108 72 V90 Q108 106 92 106 H84 L70 118 L72 106 H60 Q44 106 44 90 V72 Q44 56 60 56 Z';
const DASH = 320; // a little above the real outline length (~270) so the line fully disappears at 0

const SIZE = 120;

interface Props {
  size?: number;
  /** Show the "GroupSync" wordmark below the logo, animated letter by letter */
  wordmark?: boolean;
  /** Draw color for the back bubble / front bubble */
  colors?: [string, string];
}

function Letter({ char, index, enabled }: { char: string; index: number; enabled: boolean }) {
  const p = useSharedValue(0);
  useEffect(() => {
    p.value = withDelay(
      enabled ? LOGO_TIMELINE.text + index * LOGO_TIMELINE.textStagger : 0,
      withTiming(1, { duration: enabled ? 260 : 120, easing: Easing.out(Easing.cubic) }),
    );
  }, [enabled, index, p]);
  const style = useAnimatedStyle(() => ({ opacity: p.value, transform: [{ translateY: (1 - p.value) * 18 }] }));
  return <Animated.Text style={[{ fontSize: 34, fontWeight: '700', color: '#fff', letterSpacing: 0.5 }, style]}>{char}</Animated.Text>;
}

/** Logo that draws itself on, fills with a bounce, then gets a light shine sweep. */
export function AnimatedLogo({ size = 140, wordmark = true, colors = ['#FFFFFF', '#22D3EE'] }: Props) {
  const enabled = useMotionEnabled();
  const strokeBack = useSharedValue(DASH);
  const strokeFront = useSharedValue(DASH);
  const fill = useSharedValue(0);
  const pop = useSharedValue(enabled ? 0.6 : 1);
  const shine = useSharedValue(-1);

  useEffect(() => {
    if (!enabled) {
      strokeBack.value = 0;
      strokeFront.value = 0;
      fill.value = 1;
      return;
    }
    const draw = { duration: LOGO_TIMELINE.drawDuration, easing: Easing.inOut(Easing.cubic) };
    strokeBack.value = withDelay(LOGO_TIMELINE.draw, withTiming(0, draw));
    strokeFront.value = withDelay(LOGO_TIMELINE.draw + 120, withTiming(0, draw));
    fill.value = withDelay(LOGO_TIMELINE.fill, withTiming(1, { duration: 300 }));
    pop.value = withDelay(LOGO_TIMELINE.fill, withSpring(1, spring.bouncy));
    shine.value = withDelay(LOGO_TIMELINE.shine, withTiming(1.4, { duration: 450, easing: Easing.inOut(Easing.cubic) }));
  }, [enabled, fill, pop, shine, strokeBack, strokeFront]);

  const backProps = useAnimatedProps(() => ({ strokeDashoffset: strokeBack.value, fillOpacity: fill.value * 0.9 }));
  const frontProps = useAnimatedProps(() => ({ strokeDashoffset: strokeFront.value, fillOpacity: fill.value }));
  const logoStyle = useAnimatedStyle(() => ({ transform: [{ scale: pop.value }] }));
  const shineStyle = useAnimatedStyle(() => ({ transform: [{ translateX: shine.value * size }, { skewX: '-20deg' }] }));

  return (
    <View style={{ alignItems: 'center' }}>
      <Animated.View style={[{ width: size, height: size, borderRadius: size * 0.26, overflow: 'hidden' }, logoStyle]}>
        <View style={{ flex: 1, backgroundColor: 'rgba(255,255,255,0.12)', alignItems: 'center', justifyContent: 'center' }}>
          <Svg width={size * 0.8} height={size * 0.8} viewBox={`0 0 ${SIZE} ${SIZE}`}>
            <AnimatedPath
              d={BUBBLE_BACK} stroke={colors[0]} fill={colors[0]} strokeWidth={4} strokeLinejoin="round" strokeLinecap="round"
              strokeDasharray={`${DASH} ${DASH}`} animatedProps={backProps}
            />
            <AnimatedPath
              d={BUBBLE_FRONT} stroke={colors[1]} fill={colors[1]} strokeWidth={4} strokeLinejoin="round" strokeLinecap="round"
              strokeDasharray={`${DASH} ${DASH}`} animatedProps={frontProps}
            />
          </Svg>
        </View>
        <Animated.View pointerEvents="none" style={[{ position: 'absolute', top: 0, bottom: 0, left: -size * 0.5, width: size * 0.35 }, shineStyle]}>
          <LinearGradient
            colors={['rgba(255,255,255,0)', 'rgba(255,255,255,0.55)', 'rgba(255,255,255,0)']}
            start={{ x: 0, y: 0.5 }} end={{ x: 1, y: 0.5 }} style={{ flex: 1 }}
          />
        </Animated.View>
      </Animated.View>

      {wordmark ? (
        <View style={{ flexDirection: 'row', marginTop: 20 }} accessibilityLabel="GroupSync">
          {'GroupSync'.split('').map((c, i) => (
            <Letter key={i} char={c} index={i} enabled={enabled} />
          ))}
        </View>
      ) : null}
    </View>
  );
}

/** Non-animated logo tile, for headers and auth screens (same artwork as the intro). */
export function LogoMark({ size = 64, colors = ['#FFFFFF', '#22D3EE'] }: { size?: number; colors?: [string, string] }) {
  return (
    <View style={{ width: size, height: size, borderRadius: size * 0.26, backgroundColor: 'rgba(255,255,255,0.16)', alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={size * 0.8} height={size * 0.8} viewBox={`0 0 ${SIZE} ${SIZE}`}>
        <Path d={BUBBLE_BACK} fill={colors[0]} fillOpacity={0.9} stroke={colors[0]} strokeWidth={4} strokeLinejoin="round" />
        <Path d={BUBBLE_FRONT} fill={colors[1]} stroke={colors[1]} strokeWidth={4} strokeLinejoin="round" />
      </Svg>
    </View>
  );
}
