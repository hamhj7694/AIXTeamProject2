import React from 'react';
import { CheckCircle2, FileText, Landmark, Phone, ShieldAlert, X } from 'lucide-react';
import { mvpChatApi } from '../../../services/mvpChatApi';

interface Props { onClose: () => void; onRequest?: (kind: 'AI_ADVICE' | 'HUMAN_HANDOFF', step: string) => Promise<void> | void; }

/** Customer-facing, deterministic safety guidance. It is shown inside the chat stream. */
export const RecoveryGuideCard: React.FC<Props> = ({ onClose, onRequest }) => {
  const [selected, setSelected] = React.useState<string | null>(null);
  const [requesting, setRequesting] = React.useState(false);
  const [requested, setRequested] = React.useState<string | null>(null);
  const steps = [
    { icon: Phone, title: '즉시 연락', text: '거래 은행에 연락해 지급정지 가능 여부를 문의하세요.', detail: '은행 공식 대표번호나 앱의 사고 신고 메뉴를 이용하고, 상대방이 알려준 번호는 사용하지 마세요.' },
    { icon: FileText, title: '증빙 확보', text: '거래 내역·문자·대화·첨부 자료를 보관하세요.', detail: '송금 시각·금액, 계좌번호, 문자와 메신저 화면을 삭제하지 말고 원본으로 보관하세요.' },
    { icon: ShieldAlert, title: '신고 접수', text: '경찰청 112 또는 금융감독원 1332에 신고하세요.', detail: '긴급 피해는 112, 금융 상담과 피해구제 안내는 1332에 문의할 수 있습니다.' },
    { icon: Landmark, title: '구제 신청', text: '은행의 피해구제 절차와 필요 서류를 안내받으세요.', detail: '은행 담당자에게 지급정지·피해구제 신청 가능 여부와 제출 서류를 확인하세요.' },
  ];
  const request = async (kind: 'AI_ADVICE' | 'HUMAN_HANDOFF') => {
    if (!selected || requesting) return;
    setRequesting(true);
    try {
      if (onRequest) {
        await onRequest(kind, selected);
      } else {
        // The card can be mounted from multiple customer entry points. Persist the
        // request as a customer-visible Case message when no parent callback exists.
        const caseId = window.location.pathname.match(/\/cases\/([^/]+)/)?.[1];
        if (caseId) {
          const label = kind === 'AI_ADVICE' ? 'AI 조언' : '은행 담당자 대행';
          await mvpChatApi.createMessage(caseId, {
            actor_type: 'CUSTOMER', actor_user_id: 'mvp-v2-customer', actor_display_name: '고객', actor_role: 'CUSTOMER',
            content: `${label}을 요청합니다. 피해구제 단계: ${selected}`,
            channel: 'CUSTOMER', audience: 'CUSTOMER', visibility: 'CUSTOMER', message_kind: 'CHAT',
          });
        }
      }
      setRequested(kind);
    } finally { setRequesting(false); }
  };
  const current = steps.find((step) => step.title === selected);
  return <section className="rounded-2xl border border-rose-200 bg-gradient-to-br from-rose-50 to-white p-4 shadow-sm"><div className="flex items-center justify-between gap-3"><div className="flex items-center gap-2 text-rose-700"><ShieldAlert size={19}/><h2 className="text-sm font-black">보이스피싱 피해 구제 안내</h2></div><button type="button" onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-rose-100" aria-label="피해구제 안내 닫기"><X size={16}/></button></div><div className="mt-3 grid gap-2 sm:grid-cols-2">{steps.map(({ icon: Icon, title, text }) => <button type="button" key={title} onClick={() => { setSelected((value) => value === title ? null : title); setRequested(null); }} className={`rounded-xl border p-3 text-left transition ${selected === title ? 'border-rose-400 bg-rose-100' : 'border-rose-100 bg-white hover:border-rose-300'}`}><div className="flex items-center gap-2 text-xs font-black text-slate-800"><Icon size={15} className="text-rose-600"/>{title}</div><p className="mt-1.5 text-[11px] leading-5 text-slate-600">{text}</p></button>)}</div>{current && <div className="mt-3 rounded-xl border border-rose-200 bg-white p-3"><p className="text-xs font-black text-rose-800">{current.title} 절차</p><p className="mt-1 text-xs leading-5 text-slate-700">{current.detail}</p><div className="mt-3 flex flex-wrap gap-2"><button type="button" disabled={requesting} onClick={() => void request('AI_ADVICE')} className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-[11px] font-bold text-blue-800">AI에게 조언 요청</button><button type="button" disabled={requesting} onClick={() => void request('HUMAN_HANDOFF')} className="rounded-lg bg-slate-900 px-3 py-2 text-[11px] font-bold text-white">담당자 대행 요청</button></div>{requested && <p className="mt-2 rounded-lg bg-emerald-50 p-2 text-[11px] font-bold text-emerald-700">{requested === 'AI_ADVICE' ? 'AI 조언 요청이 Case에 기록되었습니다.' : '담당자 대행 요청이 Case에 기록되었습니다.'}</p>}<p className="mt-2 text-[10px] text-slate-400">요청은 Case에 기록되며 외부 기관에 자동 전송되지 않습니다.</p></div>}<p className="mt-3 flex items-center gap-1 rounded-xl bg-rose-100/70 px-3 py-2.5 text-xs font-bold leading-5 text-rose-800"><CheckCircle2 size={14}/> 빠른 신고와 증빙 확보가 피해 구제에 중요합니다.</p></section>;
};
