import type { components } from '../generated/generalApiSchema';
import { notifyApiMutation } from './caseSync';

export type GeneralApiSchemas = components['schemas'];
export type GeneralApiSchema<Name extends keyof GeneralApiSchemas> = GeneralApiSchemas[Name];

export const generalApiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export const generalApiUrl = (path: string): string => `${generalApiBaseUrl}${path}`;

export const generalApiErrorMessage = (payload: unknown, status: number): string => {
  const body = payload && typeof payload === 'object' ? payload as {
    error?: { message?: unknown };
    detail?: string | { message?: unknown };
  } : null;
  const errorMessage = typeof body?.error?.message === 'string' ? body.error.message : null;
  const detail = typeof body?.detail === 'string'
    ? body.detail
    : typeof body?.detail?.message === 'string' ? body.detail.message : null;
  if (errorMessage || detail) return errorMessage || detail || '';
  if (status === 404) return '요청한 기능을 서버에서 찾을 수 없습니다. API 서버가 최신 버전인지 확인해 주세요.';
  return `요청을 처리하지 못했습니다. (${status})`;
};

export const generalApiRequest = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(generalApiUrl(path), {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new Error(generalApiErrorMessage(payload, response.status));
  notifyApiMutation(path, init, payload);
  return payload as T;
};
