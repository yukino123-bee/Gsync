import { Link } from 'expo-router';
import { useState } from 'react';
import { Text, View } from 'react-native';

import { AuthShell } from '@/components/AuthForm';
import { Button, ErrorBanner, Segmented, TextField } from '@/components/ui';
import { useAuth } from '@/store/auth';
import { colors, spacing } from '@/theme';
import { getErrorMessage } from '@/utils/errors';

export default function RegisterScreen() {
  const register = useAuth((s) => s.register);
  const [role, setRole] = useState<'student' | 'teacher'>('student');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!name.trim()) return setError('Enter your name.');
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) return setError('Enter a valid email address.');
    if (password.length < 8) return setError('Password must be at least 8 characters.');
    setError(null);
    setBusy(true);
    try {
      await register(name, email, password, role);
    } catch (e) {
      setError(getErrorMessage(e));
      setBusy(false);
    }
  }

  return (
    <AuthShell title="Create your account" subtitle="Join your class on GroupSync.">
      <ErrorBanner message={error} />
      <Text style={{ fontSize: 14, fontWeight: '500', color: colors.text, marginBottom: 4 }}>I am a</Text>
      <Segmented
        value={role}
        onChange={setRole}
        options={[{ value: 'student', label: 'Student' }, { value: 'teacher', label: 'Teacher' }]}
      />
      <TextField label="Full name" value={name} onChangeText={setName} autoComplete="name" textContentType="name" placeholder="Alex Johnson" />
      <TextField
        label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" autoComplete="email"
        keyboardType="email-address" textContentType="emailAddress" placeholder="you@school.edu"
      />
      <TextField
        label="Password" value={password} onChangeText={setPassword} secureTextEntry autoComplete="new-password"
        textContentType="newPassword" placeholder="At least 8 characters" onSubmitEditing={submit}
      />
      <Button title="Create account" onPress={submit} loading={busy} />
      <View style={{ flexDirection: 'row', justifyContent: 'center', marginTop: spacing.xl, gap: 4 }}>
        <Text style={{ color: colors.textMuted }}>Already have an account?</Text>
        <Link href="/login" style={{ color: colors.primary, fontWeight: '600' }}>Sign in</Link>
      </View>
    </AuthShell>
  );
}
