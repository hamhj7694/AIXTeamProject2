import React, { useState } from 'react';
import { Send } from 'lucide-react';
import { mvpChatApi } from '../../../services/mvpChatApi';
import { WorkCardFrame } from './WorkCardFrame';
import type { WorkCardStage } from './types';

const templates = [
  { label: '추가 행동 중단', text: '추가 송금이나 개인정보 전달을 중단하고, 확인 전까지 상대방의 안내를 따르지 마세요.' },
  { label: '기관 확인 중', text: '현재 기관 정보의 진위 여부를 확인하고 있습니다. 확인 결과가 나오기 전까지 기다려 주세요.' },
  { label: '피해 증빙 보존', text: '피해가 발생했다면 거래내역과 대화 화면을 보존하고 즉시 은행 담당자에게 알려 주세요.' },
];

interface Props { caseId: string; requestedBy: string; initialContent?: string; onCompleted: () => Promise<void> | void; onClose: () => void; }

export const CustomerNoticeCard: React.FC<Props> = ({ caseId, requestedBy, initialContent = '', onCompleted, onClose }) => {
  const [content, setContent] = useState(initialContent);
  const [stage, setStage] = useState<WorkCardStage>('DRAFT');
  const [error, setError] = useState('');
  const [noticeWarning, setNoticeWarning] = useState('');
  const submit = async () => {
    if (!content.trim() || stage === 'SUBMITTING') return;
    setStage('SUBMITTING'); setError('');
    try {
      await mvpChatApi.createMessage(caseId, { actor_type: 'BANK_STAFF', actor_user_id: 'mvp-v2-current-user', actor_display_name: requestedBy, actor_role: 'CHAT_OPERATOR', content: content.trim(), channel: 'CUSTOMER', audience: 'CUSTOMER', visibility: 'CUSTOMER', message_kind: 'CHAT' });
      setStage('DELIVERED');
      try { await mvpChatApi.createMessage(caseId, { actor_type: 'SYSTEM', actor_user_id: 'case-system', actor_display_name: '시스템', actor_role: null, content: '은행 담당자가 고객 안전 안내를 전송했습니다.', channel: 'TEAM', audience: 'BANK_INTERNAL', visibility: 'BANK_INTERNAL', message_kind: 'SYSTEM_EVENT' }); }
      catch { setNoticeWarning('고객 안내는 전송됐지만 은행 협업 알림을 동기화하지 못했습니다. 다시 전송하지 말고 새로고침해 주세요.'); }
      try { await onCompleted(); } catch { setNoticeWarning('고객 안내는 전송됐지만 최신 화면을 불러오지 못했습니다. 다시 전송하지 말고 새로고침해 주세요.'); }
      onClose();
    } catch (reason) { setError(reason instanceof Error ? reason.message : '고객 안내를 전송하지 못했습니다.'); setStage('FAILED'); }
  };
  return <WorkCardFrame eyebrow="AI 개인 작업 · 고객 안내" title="고객 공개 안내 작성" description="고객 화면에 그대로 전달됩니다. 내부 판단·위험 점수·검증 근거가 포함되지 않았는지 확인하세요." stage={stage} onClose={onClose}>
    <div className="mt-4 flex flex-wrap gap-2">{templates.map((template) => <button key={template.label} type="button" disabled={stage === 'DELIVERED'} onClick={() => { setContent(template.text); setStage('READY'); }} className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5 text-left text-[11px] font-bold text-slate-300 hover:border-violet-400">{template.label}</button>)}</div>
    <label className="mt-3 block text-xs font-bold text-slate-300">고객에게 보낼 내용<textarea value={content} disabled={stage === 'DELIVERED'} onChange={(event) => { setContent(event.target.value); setStage(event.target.value.trim() ? 'READY' : 'DRAFT'); }} rows={4} className="mt-1.5 w-full resize-none rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none focus:border-violet-400"/></label>
    {stage === 'DELIVERED' && <p className="mt-3 rounded-xl border border-emerald-500/30 bg-emerald-950/40 p-3 text-xs font-bold text-emerald-200">고객 채널에 전달되었고 은행 협업 채널에도 업무 알림이 기록되었습니다.</p>}
    {error && <p className="mt-3 rounded-xl bg-rose-950/60 p-3 text-xs text-rose-200">{error}</p>}
    {noticeWarning && <p className="mt-3 rounded-xl bg-amber-950/60 p-3 text-xs text-amber-200">{noticeWarning}</p>}
    <div className="mt-4 flex justify-end gap-2"><button type="button" onClick={onClose} className="rounded-xl border border-slate-700 px-3 py-2 text-xs font-bold text-slate-300">닫기</button>{stage !== 'DELIVERED' && <button type="button" disabled={!content.trim() || stage === 'SUBMITTING'} onClick={() => void submit()} className="inline-flex items-center gap-1 rounded-xl bg-violet-500 px-3 py-2 text-xs font-black text-white disabled:opacity-50"><Send size={14}/>검토 후 고객에게 전송</button>}</div>
  </WorkCardFrame>;
};
