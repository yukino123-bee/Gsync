import { Ionicons } from '@expo/vector-icons';
import { createElement } from 'react';
import { Text, View } from 'react-native';

import { colors, fonts, radius, spacing } from '@/theme';
import { Button } from './ui';

interface Props {
  label: string;
  value: Date | null;
  onChange: (d: Date | null) => void;
  minimumDate?: Date;
}

const toInputValue = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

/** Browser build of DateField: the native datetimepicker has no web implementation, so use <input type="date">. */
export function DateField({ label, value, onChange, minimumDate }: Props) {
  return (
    <View style={{ marginBottom: spacing.md }}>
      <Text style={{ fontSize: fonts.size.sm, fontWeight: fonts.weight.medium, color: colors.text, marginBottom: spacing.xs }}>{label}</Text>
      <View style={{ flexDirection: 'row', gap: spacing.sm, alignItems: 'center' }}>
        <View
          style={{
            flex: 1, flexDirection: 'row', alignItems: 'center', gap: spacing.sm, backgroundColor: colors.surface,
            borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, paddingHorizontal: spacing.md, paddingVertical: 8,
          }}
        >
          <Ionicons name="calendar-outline" size={18} color={colors.textMuted} />
          {createElement('input', {
            type: 'date',
            'aria-label': label,
            value: value ? toInputValue(value) : '',
            min: minimumDate ? toInputValue(minimumDate) : undefined,
            onChange: (e: { target: { value: string } }) => {
              const v = e.target.value;
              if (!v) return onChange(null);
              const [y, m, d] = v.split('-').map(Number);
              onChange(new Date(y!, m! - 1, d!));
            },
            style: { flex: 1, border: 'none', outline: 'none', background: 'transparent', fontSize: fonts.size.md, color: colors.text, fontFamily: 'inherit' },
          })}
        </View>
        {value ? <Button title="Clear" variant="secondary" small onPress={() => onChange(null)} /> : null}
      </View>
    </View>
  );
}
