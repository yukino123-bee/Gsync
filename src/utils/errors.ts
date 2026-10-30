import { isAxiosError } from 'axios';

/** Turn any thrown value into a message that is safe to show the user. */
export function getErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    if (!error.response) {
      return error.code === 'ECONNABORTED'
        ? 'The server took too long to respond. Please try again.'
        : "Can't reach the server. Check your connection and the API address.";
    }
    const detail = error.response.data?.detail;
    if (typeof detail === 'string') return detail;
    if (error.response.status >= 500) return 'Something went wrong on the server. Please try again.';
    return `Request failed (${error.response.status}).`;
  }
  if (error instanceof Error) return error.message;
  return 'Something went wrong.';
}
