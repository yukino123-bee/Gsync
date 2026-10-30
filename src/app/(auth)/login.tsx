import { Link } from 'expo-router';
import { useState } from 'react';
import { Text, View } from 'react-native';

import { AuthShell } from '@/components/AuthForm';
import { Button, ErrorBanner, TextField } from '@/components/ui';
import { useAuth } from '@/store/auth';
import { colors, spacing } from '@/theme';
import { getErrorMessage } from '@/utils/errors';

export default function LoginScreen() {
  const login = useAuth((s) => s.login);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!email.trim() || !password) return setError('Enter your email and password.');
    setError(null);
    setBusy(true);
    try {
      await login(email, password); // the root layout switches to the right tabs
    } catch (e) {
      setError(getErrorMessage(e));
      setBusy(false);
    }
  }

  return (
    <AuthShell title="Welcome back" subtitle="Sign in to your group workspace.">
      <ErrorBanner message={error} />
      <TextField
        label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" autoComplete="email"
        keyboardType="email-address" textContentType="emailAddress" placeholder="you@school.edu"
      />
      <TextField
        label="Password" value={password} onChangeText={setPassword} secureTextEntry autoComplete="password"
        textContentType="password" placeholder="Your password" onSubmitEditing={submit} returnKeyType="go"
      />
      <Button title="Sign in" onPress={submit} loading={busy} />
      <View style={{ flexDirection: 'row', justifyContent: 'center', marginTop: spacing.xl, gap: 4 }}>
        <Text style={{ color: colors.textMuted }}>New here?</Text>
        <Link href="/register" style={{ color: colors.primary, fontWeight: '600' }}>Create an account</Link>
      </View>
    </AuthShell>
  );
}
