import { createUuid } from '../shared/uuid.ts';

export interface ApiHealth {
  service: 'csr-general-api';
  status: 'ok';
  contract_version: 'v4.health.1';
}

export async function getHealth(signal?: AbortSignal): Promise<ApiHealth> {
  const response = await fetch('/api/v4/health', {
    signal,
    credentials: 'same-origin',
    headers: { 'X-Request-ID': createUuid() },
  });
  if (!response.ok) throw new Error('서버에 연결하지 못했습니다. 잠시 후 다시 확인해 주세요.');
  const body: unknown = await response.json();
  if (typeof body !== 'object' || body === null ||
      !('service' in body) || body.service !== 'csr-general-api' ||
      !('status' in body) || body.status !== 'ok' ||
      !('contract_version' in body) || body.contract_version !== 'v4.health.1') {
    throw new Error('서버 응답을 확인할 수 없습니다.');
  }
  return body as ApiHealth;
}
