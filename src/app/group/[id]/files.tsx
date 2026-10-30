import { Ionicons } from '@expo/vector-icons';
import * as DocumentPicker from 'expo-document-picker';
import { useState } from 'react';
import { Linking, Text, View } from 'react-native';

import { groupsApi } from '@/api/groups';
import { Async } from '@/components/Async';
import {
  Badge, Body, Button, Card, EmptyState, ErrorBanner, Row, Screen, Segmented, TextField,
} from '@/components/ui';
import { colors, spacing } from '@/theme';
import { MAX_UPLOAD_BYTES } from '@/utils/config';
import { openGroupFile } from '@/utils/download';
import { getErrorMessage } from '@/utils/errors';
import { formatBytes, formatDateTime } from '@/utils/format';
import { useGroup } from '@/utils/groupContext';
import { useLoad } from '@/utils/useLoad';
import type { FileItem } from '@/types';

const ACCEPTED = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'image/*',
];

export default function FilesAndNotes() {
  const [tab, setTab] = useState<'files' | 'notes'>('files');
  return (
    <Screen padTop={false}>
      <Segmented value={tab} onChange={setTab} options={[{ value: 'files', label: 'Files' }, { value: 'notes', label: 'Notes & links' }]} />
      {tab === 'files' ? <FilesPanel /> : <NotesPanel />}
    </Screen>
  );
}

function FilesPanel() {
  const { group, readOnly, memberName } = useGroup();
  const load = useLoad(() => groupsApi.files(group.id), [group.id]);
  const [busy, setBusy] = useState<number | 'upload' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<Set<string>>(new Set());

  async function upload() {
    setError(null);
    const result = await DocumentPicker.getDocumentAsync({ type: ACCEPTED, copyToCacheDirectory: true });
    if (result.canceled) return;
    const asset = result.assets[0]!;
    if (asset.size && asset.size > MAX_UPLOAD_BYTES) return setError('That file is larger than 10 MB.');
    setBusy('upload');
    try {
      await groupsApi.uploadFile(group.id, { uri: asset.uri, name: asset.name, mimeType: asset.mimeType });
      load.reload();
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  async function open(item: FileItem) {
    setError(null);
    setBusy(item.id);
    try {
      await openGroupFile(item);
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  function toggleHistory(name: string) {
    setHistory((prev) => {
      const next = new Set(prev);
      if (!next.delete(name)) next.add(name);
      return next;
    });
  }

  return (
    <>
      <ErrorBanner message={error} />
      {!readOnly ? (
        <Button title="Upload file" icon="cloud-upload-outline" onPress={upload} loading={busy === 'upload'} style={{ marginBottom: spacing.sm }} />
      ) : null}
      {!readOnly ? <Body small muted style={{ marginBottom: spacing.md }}>PDF, DOCX or images, up to 10 MB. Uploading a file with the same name adds a new version.</Body> : null}
      <Async load={load}>
        {(files) => {
          if (files.length === 0) {
            return <EmptyState icon="document-outline" title="No files yet" message={readOnly ? 'The group has not uploaded files.' : 'Upload drafts, research and images for your group to share.'} />;
          }
          const names = [...new Set(files.map((f) => f.filename))];
          return (
            <>
              {names.map((name) => {
                const versions = files.filter((f) => f.filename === name); // newest first
                const latest = versions[0]!;
                const expanded = history.has(name);
                return (
                  <Card key={name}>
                    <Row style={{ alignItems: 'flex-start' }}>
                      <Ionicons name={latest.mime_type.startsWith('image/') ? 'image-outline' : 'document-text-outline'} size={28} color={colors.primary} />
                      <View style={{ flex: 1 }}>
                        <Body style={{ fontWeight: '600' }} numberOfLines={2}>{name}</Body>
                        <Body small muted>{formatBytes(latest.size)} · {memberName(latest.uploader_id)} · {formatDateTime(latest.uploaded_at)}</Body>
                      </View>
                      <Badge tone="info" label={`v${latest.version}`} />
                    </Row>
                    <Row style={{ marginTop: spacing.md, justifyContent: 'space-between' }}>
                      <Button small variant="secondary" icon="download-outline" title="Open" onPress={() => open(latest)} loading={busy === latest.id} />
                      {versions.length > 1 ? (
                        <Button small variant="ghost" icon={expanded ? 'chevron-up' : 'time-outline'} title={expanded ? 'Hide history' : `History (${versions.length})`} onPress={() => toggleHistory(name)} />
                      ) : null}
                    </Row>
                    {expanded ? versions.slice(1).map((v) => (
                      <Row key={v.id} style={{ justifyContent: 'space-between', marginTop: spacing.sm }}>
                        <Body small muted style={{ flex: 1 }}>v{v.version} · {memberName(v.uploader_id)} · {formatDateTime(v.uploaded_at)}</Body>
                        <Button small variant="ghost" title="Open" onPress={() => open(v)} loading={busy === v.id} />
                      </Row>
                    )) : null}
                  </Card>
                );
              })}
            </>
          );
        }}
      </Async>
    </>
  );
}

const URL_RE = /(https?:\/\/[^\s]+)/g;

/** Renders note text with tappable links. */
function LinkedText({ text }: { text: string }) {
  const parts = text.split(URL_RE);
  return (
    <Text style={{ fontSize: 16, color: colors.text, lineHeight: 22 }}>
      {parts.map((part, i) =>
        /^https?:\/\//.test(part) ? (
          <Text key={i} style={{ color: colors.primary, textDecorationLine: 'underline' }} onPress={() => Linking.openURL(part).catch(() => {})}>
            {part}
          </Text>
        ) : (
          part
        ),
      )}
    </Text>
  );
}

function NotesPanel() {
  const { group, readOnly } = useGroup();
  const load = useLoad(() => groupsApi.notes(group.id), [group.id]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function add() {
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await groupsApi.addNote(group.id, text.trim());
      setText('');
      load.reload();
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <ErrorBanner message={error} />
      {!readOnly ? (
        <>
          <TextField placeholder="Write a note or paste a link (https://…)" value={text} onChangeText={setText} multiline />
          <Button title="Add note" icon="add" onPress={add} loading={busy} disabled={!text.trim()} style={{ marginBottom: spacing.md }} />
        </>
      ) : null}
      <Async load={load}>
        {(notes) =>
          notes.length === 0 ? (
            <EmptyState icon="reader-outline" title="No notes yet" message="Notes and links your group adds will appear here." />
          ) : (
            <>
              {notes.map((n) => (
                <Card key={n.id}>
                  <LinkedText text={n.content} />
                  <Body small muted style={{ marginTop: spacing.sm }}>{n.author_name} · {formatDateTime(n.created_at)}</Body>
                </Card>
              ))}
            </>
          )
        }
      </Async>
    </>
  );
}
