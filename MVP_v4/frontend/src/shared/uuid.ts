/** The only UUID creation boundary; works on HTTP IP origins as well as HTTPS. */
export function createUuid(): string {
  const provider = globalThis.crypto;
  if (typeof provider?.randomUUID === 'function') {
    return provider.randomUUID();
  }
  if (typeof provider?.getRandomValues !== 'function') {
    throw new Error('이 브라우저에서는 안전한 요청 ID를 생성할 수 없습니다. 브라우저를 업데이트해 주세요.');
  }
  const bytes = provider.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
