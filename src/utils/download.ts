import { File, Paths } from 'expo-file-system';
import { Platform } from 'react-native';
import * as Sharing from 'expo-sharing';

import { api } from '@/api/client';
import type { FileItem } from '@/types';

/** Downloads a group file (authenticated, so the token is refreshed if needed) and opens the share sheet. */
export async function openGroupFile(item: FileItem): Promise<void> {
  const res = await api.get<ArrayBuffer>(`/files/${item.id}/download`, { responseType: 'arraybuffer', timeout: 60_000 });
  if (Platform.OS === 'web') {
    const url = URL.createObjectURL(new Blob([res.data], { type: item.mime_type }));
    const a = document.createElement('a');
    a.href = url;
    a.download = item.filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 10_000);
    return;
  }
  // Prefix with the id so two versions of the same name never collide in the cache
  const file = new File(Paths.cache, `${item.id}_${item.filename}`);
  if (file.exists) file.delete();
  file.create();
  file.write(new Uint8Array(res.data));

  if (!(await Sharing.isAvailableAsync())) throw new Error('Sharing is not available on this device.');
  await Sharing.shareAsync(file.uri, { mimeType: item.mime_type, dialogTitle: item.filename });
}
