import { afterEach, describe, expect, it, vi } from 'vitest';
import { transcribeAudioFile } from './audioTranscription';

describe('transcribeAudioFile', () => {
  afterEach(() => { vi.unstubAllGlobals(); });

  it('returns Korean transcript segments without speaker labels and filters English-only noise', async () => {
    const events = [
      { type: 'transcript.text.segment', speaker: 'A', text: '안녕하세요.' },
      { type: 'transcript.text.segment', speaker: 'B', text: '네, 말씀하세요.' },
      { type: 'transcript.text.segment', speaker: 'C', text: 'Yeah, you can eat that engine.' },
      { type: 'transcript.text.segment', speaker: 'A', text: '거래를 확인하고 싶습니다.' },
    ].map((data) => `event: transcript.text.segment\ndata: ${JSON.stringify(data)}\n\n`).join('');
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(events));
        controller.close();
      },
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 200 })));
    const file = new Blob(['audio']) as File;
    Object.defineProperty(file, 'name', { value: 'call.wav' });
    const segments: Array<{ text: string }> = [];

    await transcribeAudioFile(file, new AbortController().signal, (segment) => segments.push(segment));

    expect(segments).toEqual([
      { text: '안녕하세요.' },
      { text: '네, 말씀하세요.' },
      { text: '거래를 확인하고 싶습니다.' },
    ]);
  });

  it('streams completed phrases and keeps spoken number-only content', async () => {
    const events = [
      { type: 'transcript.text.delta', delta: '고객 전화번호는 공삼사팔입니다. ' },
      { type: 'transcript.text.delta', delta: '사건번호는 2026-1234입니다. ' },
      { type: 'transcript.text.delta', delta: '0348' },
      { type: 'transcript.text.done', text: '고객 전화번호는 공삼사팔입니다. 사건번호는 2026-1234입니다.' },
    ].map((data) => `event: ${data.type}\ndata: ${JSON.stringify(data)}\n\n`).join('');
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(events));
        controller.close();
      },
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 200 })));
    const file = new Blob(['audio']) as File;
    Object.defineProperty(file, 'name', { value: 'call.wav' });
    const segments: Array<{ text: string }> = [];

    await transcribeAudioFile(file, new AbortController().signal, (segment) => segments.push(segment));

    expect(segments).toEqual([
      { text: '고객 전화번호는 공삼사팔입니다.' },
      { text: '사건번호는 2026-1234입니다.' },
      { text: '0348' },
    ]);
  });
});
