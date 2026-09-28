import { apiUrl, errorMessage } from './client';

export type TranscriptSegment = { text: string };

const readEvent = (block: string): { event: string; data: string } => {
  let event = '';
  const data: string[] = [];
  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
  }
  return { event, data: data.join('\n') };
};

export const transcribeAudioFile = async (
  file: File,
  signal: AbortSignal,
  onSegment: (segment: TranscriptSegment) => void,
) => {
  const response = await fetch(apiUrl('/api/audio/transcriptions'), {
    method: 'POST',
    headers: {
      'Content-Type': file.type || 'application/octet-stream',
      'X-Audio-Filename': encodeURIComponent(file.name),
    },
    body: file,
    signal,
  });
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    throw new Error(errorMessage(payload, response.status));
  }
  if (!response.body) throw new Error('음성 전사 스트림을 시작할 수 없습니다.');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let pending = '';
  let unflushedTranscript = '';
  let receivedDelta = false;
  const emitCompletedText = (final = false) => {
    // Split completed sentences, but keep decimal numbers and digit groups intact.
    const parts = unflushedTranscript.split(/(?<=[!?。？！])\s+|(?<!\d)(?<=\.)\s+|\n+/u);
    unflushedTranscript = final ? '' : (parts.pop() ?? '');
    for (const part of parts) {
      const text = part.trim();
      // Preserve numeric-only utterances; suppress English-only fragments/noise.
      if (!text || !/[가-힣0-9]/.test(text)) continue;
      onSegment({ text });
    }
    if (final && unflushedTranscript.trim()) {
      const text = unflushedTranscript.trim();
      if (/[가-힣0-9]/.test(text)) onSegment({ text });
    }
  };
  const processBlock = (block: string) => {
    if (!block.trim()) return;
    const { event, data } = readEvent(block);
    if (!data || data === '[DONE]') return;
    let payload: Record<string, unknown>;
    try { payload = JSON.parse(data) as Record<string, unknown>; }
    catch { return; }
    const type = String(payload.type ?? event);
    if (type === 'error') throw new Error(typeof payload.message === 'string' ? payload.message : '음성 전사 중 오류가 발생했습니다.');
    if (type === 'transcript.text.segment') {
      const text = typeof payload.text === 'string' ? payload.text.trim() : '';
      if (text) {
        // Backwards compatibility for a diarized provider configuration.
        unflushedTranscript += `${unflushedTranscript ? ' ' : ''}${text}`;
        emitCompletedText(true);
      }
      return;
    }
    if (type === 'transcript.text.delta') {
      const delta = typeof payload.delta === 'string' ? payload.delta : '';
      if (!delta) return;
      receivedDelta = true;
      unflushedTranscript += delta;
      emitCompletedText();
      return;
    }
    if (type === 'transcript.text.done' && !receivedDelta) {
      const text = typeof payload.text === 'string' ? payload.text.trim() : '';
      if (text) {
        unflushedTranscript += text;
        emitCompletedText(true);
      }
    }
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      pending += decoder.decode(value, { stream: !done });
      const blocks = pending.split(/\r?\n\r?\n/);
      pending = blocks.pop() ?? '';
      for (const block of blocks) processBlock(block);
      if (done) break;
    }
    if (pending.trim()) processBlock(pending);
    emitCompletedText(true);
  } finally {
    reader.releaseLock();
  }
};
