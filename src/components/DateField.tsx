import DateTimePicker from '@react-native-community/datetimepicker';
import { Ionicons } from '@expo/vector-icons';
import { useState } from 'react';
import { Platform, Pressable, Text, View } from 'react-native';

import { colors, fonts, radius, spacing } from '@/theme';
import { formatDate } from '@/utils/format';
import { Button } from './ui';

interface Props {
  label: string;
  value: Date | null;
  onChange: (d: Date | null) => void;
  minimumDate?: Date;
}

/** Calendar-day picker: a dialog on Android, an inline calendar on iOS. */
export function DateField({ label, value, onChange, minimumDate }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <View style={{ marginBottom: spacing.md }}>
      <Text style={{ fontSize: fonts.size.sm, fontWeight: fonts.weight.medium, color: colors.text, marginBottom: spacing.xs }}>{label}</Text>
      <View style={{ flexDirection: 'row', gap: spacing.sm }}>
        <Pressable
          onPress={() => setOpen((o) => !o)}
          accessibilityRole="button"
          style={{
            flex: 1, flexDirection: 'row', alignItems: 'center', gap: spacing.sm, backgroundColor: colors.surface,
            borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, paddingHorizontal: spacing.md, paddingVertical: 12,
          }}
        >
          <Ionicons name="calendar-outline" size={18} color={colors.textMuted} />
          <Text style={{ fontSize: fonts.size.md, color: value ? colors.text : colors.textMuted }}>
            {value ? formatDate(value.toISOString()) : 'Not set'}
          </Text>
        </Pressable>
        {value ? <Button title="Clear" variant="secondary" small onPress={() => onChange(null)} /> : null}
      </View>
      {open ? (
        <>
          <DateTimePicker
            value={value ?? new Date()}
            mode="date"
            display={Platform.OS === 'ios' ? 'inline' : 'default'}
            minimumDate={minimumDate}
            onChange={(event, date) => {
              if (Platform.OS === 'android') setOpen(false);
              if (event.type === 'set' && date) onChange(date);
            }}
          />
          {Platform.OS === 'ios' ? <Button title="Done" small variant="secondary" onPress={() => setOpen(false)} /> : null}
        </>
      ) : null}
    </View>
  );
}
