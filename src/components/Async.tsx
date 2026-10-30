import type { ReactNode } from 'react';

import { ErrorState, Loading } from './ui';

interface LoadResult<T> {
  data: T | undefined;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

/** Renders a spinner, an error with retry, or the content once data is available. */
export function Async<T>({ load, children }: { load: LoadResult<T>; children: (data: T) => ReactNode }) {
  if (load.data !== undefined) return <>{children(load.data)}</>;
  if (load.error) return <ErrorState message={load.error} onRetry={load.reload} />;
  return <Loading />;
}
