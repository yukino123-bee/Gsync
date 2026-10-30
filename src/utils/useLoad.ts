import { useFocusEffect } from 'expo-router';
import { useCallback, useRef, useState } from 'react';

import { getErrorMessage } from './errors';

interface LoadState<T> {
  data: T | undefined;
  error: string | null;
  loading: boolean; // first load, no data yet
  refreshing: boolean; // pull-to-refresh
}

/**
 * Loads data when the screen gains focus (so tabs stay fresh after edits elsewhere).
 * Shows a spinner only for the first load; later reloads happen silently.
 */
export function useLoad<T>(fetcher: () => Promise<T>, deps: readonly unknown[] = []) {
  const [state, setState] = useState<LoadState<T>>({ data: undefined, error: null, loading: true, refreshing: false });
  const latest = useRef(0);

  const run = useCallback(async (manual = false) => {
    const id = ++latest.current;
    if (manual) setState((s) => ({ ...s, refreshing: true }));
    try {
      const data = await fetcher();
      if (id === latest.current) setState({ data, error: null, loading: false, refreshing: false });
    } catch (e) {
      if (id === latest.current) {
        setState((s) => ({ ...s, error: getErrorMessage(e), loading: false, refreshing: false }));
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useFocusEffect(
    useCallback(() => {
      run();
    }, [run]),
  );

  return {
    ...state,
    reload: () => run(),
    refresh: () => run(true),
    setData: (updater: (prev: T | undefined) => T | undefined) =>
      setState((s) => ({ ...s, data: updater(s.data) })),
  };
}
