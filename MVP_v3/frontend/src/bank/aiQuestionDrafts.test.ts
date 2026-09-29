import { describe, expect, it } from 'vitest';
import type { CaseMessage, CustomerQuestion, QuestionCandidate, RecommendedChatAction } from '../api/types';
import { questionsFromAiMessage, uniqueRecommendedActions } from './aiQuestionDrafts';

const message = {
  message_id: 'ai-1', message_kind: 'AI_RESPONSE', actor_type: 'BANK_AGENT', channel: 'TEAM',
  content: `네, 다음을 물어보세요.
1. 아직 상대방과 통화·문자·메신저로 연락 중인지, 추가 송금이나 추가 지시를 받고 있는지 확인하세요. 진행 중이면 중단하세요.
2. 원격제어·화면공유 앱을 실제로 설치했는지, 링크를 열었는지 확인하세요. 설치했다면 조치를 검토하세요.
3. 주민등록번호·계좌번호 등 개인정보를 실제로 제공했는지 확인하세요. 이후 송금은 거래 조회로 검토하세요.`,
} as CaseMessage;

const available = [
  { question_id: 'candidate-remote_control_app', target_field: 'remote_control_app', question_text: '원격 제어 또는 화면 공유 앱을 실제로 설치하셨나요?', priority: 'P0' },
  { question_id: 'candidate-personal_information_exposure', target_field: 'personal_information_exposure', question_text: '주민등록번호나 계좌번호 등 개인정보를 제공하셨나요?', priority: 'P0' },
] as QuestionCandidate[];

describe('AI question actions', () => {
  it('shows a single question tool even when several tasks point to it', () => {
    const actions = [
      { action_key: 'CUSTOMER_QUESTION', kind: 'TOOL', target_channel: 'TEAM', target_type: 'TASK', target_id: 'task-1' },
      { action_key: 'CUSTOMER_QUESTION', kind: 'TOOL', target_channel: 'TEAM', target_type: 'TASK', target_id: 'task-2' },
      { action_key: 'OFFICIAL_VERIFICATION', kind: 'TOOL', target_channel: 'TEAM' },
    ] as RecommendedChatAction[];
    expect(uniqueRecommendedActions(actions).map((item) => item.action_key)).toEqual(['CUSTOMER_QUESTION', 'OFFICIAL_VERIFICATION']);
  });

  it('prepares editable customer questions from the AI response without sending them', () => {
    expect(questionsFromAiMessage(message, available, []).map((item) => item.question_text)).toEqual([
      '현재 상대방과 통화·문자·메신저로 연락 중이신가요? 추가 송금이나 다른 지시를 받고 계신가요?',
      available[0].question_text,
      '상대방이 보낸 링크를 열거나 접속하셨나요?',
      available[1].question_text,
    ]);
  });

  it('omits questions that are already queued or answered', () => {
    const existing = [
      { status: 'ANSWERED', target_field: 'remote_control_app', question_text: available[0].question_text },
      { status: 'ASKED', target_field: 'contact_in_progress', question_text: '상대방과 아직 통화 중이신가요?' },
      { status: 'PENDING', target_field: 'link_opened', question_text: '상대방의 링크를 열어 보셨나요?' },
    ] as CustomerQuestion[];
    const drafts = questionsFromAiMessage(message, available, existing);
    expect(drafts.some((item) => item.target_field === 'remote_control_app')).toBe(false);
    expect(drafts.map((item) => item.target_field)).toEqual(['personal_information_exposure']);
  });
});
