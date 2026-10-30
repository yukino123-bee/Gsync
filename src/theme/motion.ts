import { Easing, useReducedMotion } from 'react-native-reanimated';

/** Single source of truth for animation timing, so every screen feels the same. */
export const duration = {
  instant: 90,
  fast: 160,
  normal: 250,
  slow: 400,
} as const;

export const easing = {
  out: Easing.out(Easing.cubic),
  inOut: Easing.inOut(Easing.cubic),
  /** Slight overshoot, for things that "pop" in */
  pop: Easing.out(Easing.back(1.4)),
} as const;

export const spring = {
  /** Snappy default: buttons, cards, toggles */
  snappy: { damping: 18, stiffness: 320, mass: 0.7 },
  /** Playful bounce: logo, badges, checkmarks */
  bouncy: { damping: 10, stiffness: 220, mass: 0.8 },
  /** Gentle settle: progress bars, sliders */
  smooth: { damping: 22, stiffness: 140, mass: 1 },
} as const;

export const stagger = {
  step: 60,
  /** Only the first N list items animate; the rest appear instantly so long lists stay fast */
  maxItems: 10,
} as const;

export const pressScale = 0.97;

/** False when the user enabled "Reduce Motion" in system settings; components then skip movement. */
export function useMotionEnabled(): boolean {
  return !useReducedMotion();
}
