import type { CaseDiagnosis, InitialReport } from './api/types';

export type InitialSummarySectionKey = 'claims' | 'demands' | 'tactics' | 'customer' | 'unresolved';

export interface InitialSummarySection {
  key: InitialSummarySectionKey;
  title: string;
  items: string[];
  hiddenCount: number;
}

export interface InitialSummaryModel {
  headline: string;
  sections: InitialSummarySection[];
}

export type InitialSummaryAdditionalItems = Partial<Record<InitialSummarySectionKey, string[]>>;

const MAX_VISIBLE_ITEMS = 3;
type Context = NonNullable<CaseDiagnosis['context']>;

const normalizeWhitespace = (value: string) => value.replace(/\s+/g, ' ').trim();

const withoutTerminalPunctuation = (value: string) => value.replace(/[.。!?！？]+$/u, '').trim();

/** Remove repeated speaker prefixes while keeping the statement's uncertainty. */
export const compactInitialSummaryLine = (value: string, category?: InitialSummarySectionKey) => {
  let line = withoutTerminalPunctuation(normalizeWhitespace(value));
  line = line.replace(/^(?:보이스피싱 의심 인물(?:로 추정되는(?: 사람| 발화자)?)?|상대방)(?:이|가|은|는|에게)\s*/u, '');
  line = line.replace(/^고객(?:이|가|은|는|에게)\s*/u, '');

  // Keep claims as claims, but shorten repetitive request wording.
  line = line.replace(/(.+?)(?:을|를)\s+하도록 요구(?:함)?$/u, '$1 요구');
  line = line.replace(/(.+?)(?:하라고|하도록)\s+요구(?:함)?$/u, '$1 요구');
  line = line.replace(/(.+?)(?:을|를)\s+요구함$/u, '$1 요구');
  line = line.replace(/(.+?)(?:하라고|하도록)\s+지시(?:함)?$/u, '$1 지시');
  line = line.replace(/정황이\s+(?:확인되었습니다|확인됨)$/u, '정황');
  line = line.replace(/(?:이|가)\s+확인되었습니다$/u, ' 확인됨');
  line = line.replace(/\s{2,}/g, ' ').trim();

  // Customer statements read naturally without a trailing subject marker.
  if (category === 'customer') line = line.replace(/^질문을\s+/u, '질문 ');
  return line;
};

const dedupeKey = (value: string) => withoutTerminalPunctuation(normalizeWhitespace(value)).replace(/[·,，、:：;；]/gu, '').toLocaleLowerCase();

const dedupe = (items: string[], category: InitialSummarySectionKey) => {
  const seen = new Set<string>();
  return items
    .map((item) => compactInitialSummaryLine(item, category))
    .filter(Boolean)
    .filter((item) => {
      const key = dedupeKey(item);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
};

const contentItems = (report: InitialReport | null | undefined, sectionKey: string) => {
  const section = report?.sections?.find((item) => item.section_key === sectionKey);
  const items = section?.content?.items;
  return Array.isArray(items) ? items.filter((item): item is string => typeof item === 'string') : [];
};

const compactUnresolvedLabel = (item: string) => {
  if (/실제.*(?:송금|이체)/u.test(item)) return '실제 송금 여부';
  if (/(?:개인정보.*인증정보|인증정보.*개인정보|인증번호|비밀번호).*노출/u.test(item)) return '개인정보·인증정보 노출 여부';
  if (/(?:상대방|보이스피싱).*주장.*(?:진위|사실)|주장.*진위/u.test(item)) return '상대방 주장 진위';
  return compactInitialSummaryLine(item, 'unresolved');
};

const section = (key: InitialSummarySectionKey, title: string, rawItems: string[]): InitialSummarySection | null => {
  const items = key === 'unresolved'
    ? dedupe(rawItems.map(compactUnresolvedLabel), key)
    : dedupe(rawItems, key);
  if (!items.length) return null;
  return { key, title, items, hiddenCount: Math.max(0, items.length - MAX_VISIBLE_ITEMS) };
};

const compactHeadline = (value: string) => {
  const text = normalizeWhitespace(value);
  if (!text) return '';
  const sentences = text.split(/(?<=[.!?。！？])\s+/u).filter(Boolean).slice(0, 2).join(' ');
  return sentences.length > 220 ? `${sentences.slice(0, 217).trimEnd()}…` : sentences;
};

export const buildInitialSummary = (
  context: Context | undefined,
  initialReport: InitialReport | null | undefined,
  additionalItems: InitialSummaryAdditionalItems = {},
): InitialSummaryModel => {
  const sections = [
    section('claims', '상대방 주장', [...(context?.claims ?? []), ...(additionalItems.claims ?? [])]),
    section('demands', '상대방 요구', [...(context?.demands ?? []), ...(additionalItems.demands ?? [])]),
    section('tactics', '압박·통제 정황', [...(context?.manipulation_tactics ?? []), ...(additionalItems.tactics ?? [])]),
    section('customer', '고객 상태', [...(context?.customer_statements ?? []), ...(additionalItems.customer ?? [])]),
    section('unresolved', '확인 필요', contentItems(initialReport, 'unresolved_items')),
  ].filter((item): item is InitialSummarySection => Boolean(item));

  return { headline: compactHeadline(context?.summary ?? ''), sections };
};

export { MAX_VISIBLE_ITEMS };
