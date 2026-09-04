const BANK_AI_MENTION = /(^|\s)@ai(?=$|[\s,:;.!?])/iu;
const BANK_AI_MENTION_GLOBAL = /(^|\s)@ai(?=$|[\s,:;.!?])/giu;

/** 이메일 주소와 일반 문장 속 `ai`는 건드리지 않고 독립된 @AI 멘션만 찾는다. */
export const hasBankAiMention = (value: string) => BANK_AI_MENTION.test(value);

/** 저장 메시지는 원문을 유지하고, AI prompt에 보낼 때만 호출용 멘션을 제거한다. */
export const stripBankAiMention = (value: string) => value
  .replace(BANK_AI_MENTION_GLOBAL, '$1')
  .replace(/^\s*[:;,]\s*/, '')
  .replace(/\s{2,}/g, ' ')
  .trim();
