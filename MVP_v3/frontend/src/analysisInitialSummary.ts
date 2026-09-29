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
  for (let pass = 0; pass < 4; pass += 1) {
    const previous = line;
    line = line.replace(/(일회용\s*인증번호)\s*\(\s*일회용\s*인증번호\s*\(/giu, '$1(');
    if (line === previous) break;
  }
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

const semanticDedupeKey = (value: string, category: InitialSummarySectionKey) => {
  const text = value.toLocaleLowerCase();
  if (category === 'claims') {
    if (/(?:승인되지|무단|허용되지).{0,12}결제|결제.{0,12}(?:승인되지|무단|허용되지)/u.test(text)) return 'claim:unauthorized-payment';
    if (/(?:돌려주|반환|환급|환불).{0,12}(?:약속|주장)|(?:약속|주장).{0,12}(?:돌려주|반환|환급|환불)/u.test(text)) return 'claim:refund-promise';
    if (/(?:소속|사칭|담당자).{0,12}(?:주장|것처럼|인 것처럼)|(?:주장|것처럼|인 것처럼).{0,12}(?:소속|사칭|담당자)/u.test(text)) {
      const organization = text.match(/카드사|보안센터|은행|금융감독원|검찰|경찰|수사관/u)?.[0];
      if (organization) return `claim:impersonation:${organization}`;
    }
  }
  if (category === 'demands') {
    if (/(?:otp|일회용\s*인증번호|인증번호|인증정보|인증 정보)/iu.test(text)) return 'demand:authentication-information';
    if (/(?:송금|이체|자금 이동)/u.test(text)) return 'demand:transfer';
    if (/(?:은행|외부|공식).{0,16}(?:연락|확인).{0,12}(?:말|금지|제한)|(?:연락|확인).{0,12}(?:하지 말|금지|제한)/u.test(text)) return 'demand:block-official-contact';
    if (/(?:원격제어|원격 제어).{0,8}앱|앱.{0,8}(?:설치|실행)/u.test(text)) return 'demand:remote-app';
  }
  if (category === 'tactics') {
    if (/(?:즉시|긴급|바로|시간 제한|기한)/u.test(text)) return 'tactic:urgency';
    if (/(?:불안|공포|처벌|피해)/u.test(text)) return 'tactic:fear';
    if (/(?:돌려주|반환|환급|환불)/u.test(text)) return 'tactic:refund-promise';
    if (/(?:은행|가족|직원|외부|공식).{0,14}(?:연락|확인).{0,10}(?:말|차단|제한)|(?:연락하지 말|확인을 막|외부 확인)/u.test(text)) return 'tactic:isolation';
  }
  if (category === 'customer') {
    if (/(?:인증번호|otp).{0,16}(?:질문|물어|문의)/iu.test(text)) return 'customer:authentication-question';
    if (/(?:송금|이체|개인정보|인증번호).{0,20}(?:완료되지|완료 여부|제공 여부).{0,14}(?:확인되지|진술은 없음|확인 필요)/u.test(text)) return 'customer:action-completion-unknown';
  }
  return dedupeKey(text);
};

const representativeScore = (value: string) =>
  (/(?:확인되지|미확인|확인 필요|여부는 알 수 없)/u.test(value) ? 1000 : 0) - value.length;

const dedupe = (items: string[], category: InitialSummarySectionKey) => {
  const result: string[] = [];
  const positions = new Map<string, number>();
  for (const rawItem of items) {
    const item = compactInitialSummaryLine(rawItem, category);
    if (!item) continue;
    const key = semanticDedupeKey(item, category);
    const position = positions.get(key);
    if (position === undefined) {
      positions.set(key, result.length);
      result.push(item);
    } else if (representativeScore(item) > representativeScore(result[position])) {
      result[position] = item;
    }
  }
  return result;
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
  initialReport: InitialReport | null | undefined = undefined,
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
