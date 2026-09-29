import type { CaseMessage, CustomerQuestion, QuestionCandidate, RecommendedChatAction } from '../api/types';

// A recommendation tray opens a tool once, even when several tasks point at it.
export const uniqueRecommendedActions = (actions: RecommendedChatAction[]) => actions
  .filter((action) => action.action_key !== 'TRANSACTION_LOOKUP')
  .filter((action) => action.action_key !== 'DRAFT_REPLY' || Boolean(action.draft_text?.trim()))
  .filter((action, index, all) => all.findIndex((candidate) => candidate.action_key === action.action_key) === index)
  .sort((left, right) => {
    const preference: Partial<Record<RecommendedChatAction['action_key'], number>> = {
      CUSTOMER_QUESTION: 0, OFFICIAL_VERIFICATION: 1, RESPONSE_ACTION: 2, DRAFT_REPLY: 3,
    };
    return (preference[left.action_key] ?? 99) - (preference[right.action_key] ?? 99);
  })
  .slice(0, 3);

const normalize = (text: string) => text.trim().replace(/\s+/g, ' ').toLocaleLowerCase();
const contextualQuestion = (text: string, stableKey?: string): QuestionCandidate => {
  // A stable key lets the existing draft/queue deduplication survive reopening.
  let hash = 2166136261;
  for (const char of text) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619);
  const key = stableKey ?? `ai-context-${(hash >>> 0).toString(16)}`;
  return {
    question_id: key, target_field: key, question_text: text,
    reason: 'AI 답변에서 제안한 확인 항목입니다. 발송 전에 내용을 검토해 주세요.',
    priority: 'P1', options: [], answer_mode: 'TEXT', allow_free_text: true,
  };
};

const numberedItems = (content: string): string[] => {
  const items: string[] = [];
  for (const line of content.split(/\r?\n/)) {
    const match = line.match(/^\s*(?:\d{1,2}[.)]|[-*])\s+(.+)/);
    if (match) items.push(match[1].trim());
    else if (items.length && line.trim()) items[items.length - 1] += ` ${line.trim()}`;
  }
  return items;
};

export const questionsFromAiMessage = (
  message: CaseMessage,
  available: QuestionCandidate[],
  existing: CustomerQuestion[],
): QuestionCandidate[] => {
  if (message.message_kind !== 'AI_RESPONSE' || message.actor_type !== 'BANK_AGENT' || message.channel !== 'TEAM') return [];
  const availableByField = new Map(available.map((item) => [item.target_field, item]));
  const handledFields = new Set(existing.filter((item) => item.status !== 'SKIPPED').map((item) => item.target_field));
  const handledTexts = new Set(existing.filter((item) => item.status !== 'SKIPPED').map((item) => normalize(item.question_text)));
  const handledQuestions = existing.filter((item) => item.status !== 'SKIPPED').map((item) => item.question_text);
  const drafts: QuestionCandidate[] = [];
  const add = (item?: QuestionCandidate) => {
    if (!item || handledFields.has(item.target_field) || handledTexts.has(normalize(item.question_text))) return;
    if (drafts.some((current) => current.target_field === item.target_field || normalize(current.question_text) === normalize(item.question_text))) return;
    drafts.push(item);
  };
  for (const item of numberedItems(message.content)) {
    const check = item.split(/확인하세요|물어보세요|질문하세요|확인해 주세요/)[0];
    if (!/(확인|질문|물어|\?)/.test(item)) continue;
    const countBeforeItem = drafts.length;
    if (/연락|통화|문자|메신저/.test(check) && /중인지|받고 있는지|연락/.test(check)) {
      if (!handledQuestions.some((text) => /연락|통화|문자|메신저/.test(text) && /중|지시|받고/.test(text))) {
        add(contextualQuestion('현재 상대방과 통화·문자·메신저로 연락 중이신가요? 추가 송금이나 다른 지시를 받고 계신가요?', 'ai-context-contact-status'));
      }
    }
    if (/원격\s*제어|화면\s*공유|원격\s*앱/.test(check)) add(availableByField.get('remote_control_app'));
    if (/링크/.test(check) && /열었|접속|눌렀/.test(check)
      && !handledQuestions.some((text) => /링크/.test(text) && /열|접속|누르/.test(text))) {
      add(contextualQuestion('상대방이 보낸 링크를 열거나 접속하셨나요?', 'ai-context-link-opened'));
    }
    if (/개인정보|주민등록번호|계좌번호/.test(check) && /제공|전달|노출/.test(check)) add(availableByField.get('personal_information_exposure'));
    if (/인증번호|비밀번호|OTP/.test(check) && /제공|전달|노출/.test(check)) add(availableByField.get('authentication_information_exposure'));
    if (/송금|이체/.test(check) && /했는지|했나요|여부/.test(check)) {
      add(availableByField.get('victim_transfer_status') ?? availableByField.get('transfer_status'));
    }
    if (drafts.length === countBeforeItem && check.trim().endsWith('?')) add(contextualQuestion(check.trim()));
  }
  return drafts;
};
