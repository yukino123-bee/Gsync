import { Children } from 'react';
import type { StyleProp, ViewStyle } from 'react-native';

import { stagger } from '@/theme/motion';
import { FadeInView } from './FadeInView';

/** Wraps each child in a staggered FadeInView. Only the first `maxItems` animate. */
export function StaggerList({ children, style, itemStyle }: {
  children: React.ReactNode; style?: StyleProp<ViewStyle>; itemStyle?: StyleProp<ViewStyle>;
}) {
  const items = Children.toArray(children);
  return (
    <>
      {items.map((child, i) =>
        i < stagger.maxItems ? (
          <FadeInView key={(child as { key?: string }).key ?? i} delay={i * stagger.step} style={[style, itemStyle]}>
            {child}
          </FadeInView>
        ) : (
          child
        ),
      )}
    </>
  );
}
