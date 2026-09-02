import React, { useEffect, useState } from 'react';
import { AlertTriangle, ArrowLeft, Check, Clock3, Phone, Send } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import type { QuestionKey } from '../features/consultation/components/CompactSafetyChat';
import { caseApi } from '../services/caseApi';
import type { CaseDetail } from '../services/caseApi';
import { caseWorkflowApi, WorkflowMessage } from '../services/caseWorkflowApi';
import { VoiceCallPopup } from '../components/voice/VoiceCallPopup';
import { clearVoiceCallSnapshot, getVoiceCallSnapshot, updateVoiceCallSnapshot } from '../components/voice/voiceCallPersistence';
import { useCaseEventRefresh } from '../features/case-state/useCaseEventRefresh';

type LiveStatus = {
  transfer: string;
  personal: string;
  verification: string;
  bank: string;
  bankAction: string;
  human: string;
};

const statusStyle = (value: string) => {
  if (value.includes('않음') || value.includes('완료')) return 'text-emerald-600';
  if (value.includes('필요') || value.includes('중')) return 'text-amber-600';
  return 'text-slate-600';
};

const StatusRow: React.FC<{ label: string; value: string }> = ({ label, value }) => {
  const isPositive = value.includes('않음') || value.includes('완료');
  return (
    <div className="flex items-center justify-between border-b border-slate-100 pb-3 text-sm last:border-0 last:pb-0">
      <span className="text-slate-700">{label}</span>
      <span className={`inline-flex items-center gap-1 font-bold ${statusStyle(value)}`}>
        {isPositive && <Check size={14} />}
        {value}
      </span>
    </div>
  );
};

export const CustomerPage: React.FC = () => {
  const { caseId = 'VP-014' } = useParams();
  const [currentCase, setCurrentCase] = useState<CaseDetail | null>(null);
  const [loadError, setLoadError] = useState('');
  const [liveStatus, setLiveStatus] = useState<LiveStatus>({
    transfer: '확인 필요',
    personal: '확인 필요',
    verification: '진행 중',
    bank: '추가 확인 중',
    bankAction: '조치 검토 중',
    human: '참여 대기 중',
  });
  const [answeredQuestions, setAnsweredQuestions] = useState<QuestionKey[]>([]);
  const [messages, setMessages] = useState<WorkflowMessage[]>([]);
  const [messageInput, setMessageInput] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  const [eventCursor, setEventCursor] = useState<string | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [recoveryMode, setRecoveryMode] = useState(false);
  const [humanTakeover] = useState(false);
  const [customerCallOpen, setCustomerCallOpen] = useState(() => getVoiceCallSnapshot('customer').open);
  const [customerVoiceSessionId, setCustomerVoiceSessionId] = useState<string | null>(null);
  const openCustomerCall = () => { updateVoiceCallSnapshot('customer', { open: true }); setCustomerCallOpen(true); };
  const closeCustomerCall = () => { clearVoiceCallSnapshot('customer'); setCustomerCallOpen(false); };
  const handleCustomerCallStarted = async () => {
    const session = await caseWorkflowApi.createVoiceSession(caseId, ['CUSTOMER', 'BANK_STAFF']);
    setCustomerVoiceSessionId(session.session_id);
    await caseWorkflowApi.updateVoiceSession(caseId, session.session_id, 'ACTIVE');
  };
  const handleCustomerCallEnded = () => {
    if (customerVoiceSessionId) void caseWorkflowApi.updateVoiceSession(caseId, customerVoiceSessionId, 'ENDED');
  };
  useEffect(() => {
    let active = true;
    setCurrentCase(null); setLoadError('');
    Promise.all([caseApi.get(caseId), caseWorkflowApi.getBundle(caseId, 'customer')])
      .then(([value, bundle]) => {
        if (!active) return;
        setCurrentCase(value);
        setMessages(bundle.recent_messages);
        setEventCursor(bundle.cursor);
        setCustomerVoiceSessionId(bundle.voice_session?.session_id ?? null);
      })
      .catch((reason) => { if (active) setLoadError(reason instanceof Error ? reason.message : 'Case를 불러오지 못했습니다.'); });
    return () => { active = false; };
  }, [caseId, refreshNonce]);

  useCaseEventRefresh({
    caseId,
    cursor: eventCursor,
    onEvents: (events) => {
      setEventCursor(String(events[events.length - 1].event_id));
      setRefreshNonce((current) => current + 1);
    },
  });

  const sendCustomerMessage = async () => {
    const content = messageInput.trim();
    if (!content || sendingMessage) return;
    setSendingMessage(true);
    try {
      const message = await caseWorkflowApi.createMessage(caseId, content, 'CUSTOMER');
      setMessages((current) => [...current, message]);
      setMessageInput('');
    } catch (reason) {
      setLoadError(reason instanceof Error ? reason.message : '메시지를 저장하지 못했습니다.');
    } finally {
      setSendingMessage(false);
    }
  };

  const toggleRecoveryMode = async () => {
    if (recoveryMode) {
      setRecoveryMode(false);
      return;
    }
    const version = Number((currentCase as CaseDetail & { version?: number } | null)?.version ?? 1);
    try {
      const updated = await caseWorkflowApi.patchCase(caseId, version, { mode: 'RECOVERY', status: 'IN_PROGRESS' });
      setCurrentCase((current) => current ? { ...current, status: updated.status as CaseDetail['status'] } : current);
      setRecoveryMode(true);
    } catch (reason) {
      setLoadError(reason instanceof Error ? reason.message : '구제 모드로 전환하지 못했습니다.');
    }
  };

  const handleResponse = async (question: QuestionKey, answer: string) => {
    try {
      await caseWorkflowApi.createMessage(caseId, `${question}: ${answer}`);
    } catch (reason) {
      setLoadError(reason instanceof Error ? reason.message : '응답을 저장하지 못했습니다.');
      return;
    }
    setAnsweredQuestions((current) => current.includes(question) ? current : [...current, question]);
    setLiveStatus((current) => {
      if (question === 'transfer') {
        if (answer.startsWith('아니요')) return { ...current, transfer: '송금하지 않음' };
        if (answer.includes('보냈') || answer.includes('일부')) return { ...current, transfer: '송금 확인됨' };
      }
      if (question === 'personal') {
        if (answer.startsWith('제공하지')) return { ...current, personal: '노출되지 않음' };
        if (answer.includes('이름만')) return { ...current, personal: '이름·연락처 노출' };
        if (answer.includes('제공')) return { ...current, personal: '노출 범위 확인 중' };
      }
      if (question === 'personalDegree') {
        if (answer.includes('주민') || answer.includes('인증') || answer.includes('비밀번호')) return { ...current, personal: '중요정보 노출' };
        if (answer.includes('이름')) return { ...current, personal: '이름·연락처 노출' };
        return { ...current, personal: '노출 범위 확인 중' };
      }
      if (question === 'link' || question === 'impersonation') return { ...current, verification: '추가 확인 중' };
      if (question === 'call') return { ...current, bank: '응답 반영 중', bankAction: '조치 검토 중' };
      return current;
    });
  };

  const progressTotal = 6;
  const progressCount = Math.min(answeredQuestions.length, progressTotal);
  const progressPercent = `${(progressCount / progressTotal) * 100}%`;

  if (loadError) return <AppLayout><div className="mx-auto max-w-6xl py-8 lg:ml-64"><div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm font-bold text-rose-700">{loadError}</div></div></AppLayout>;
  if (!currentCase) return <AppLayout><div className="mx-auto max-w-6xl py-8 lg:ml-64"><div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm font-bold text-slate-500">Case 데이터를 불러오는 중입니다.</div></div></AppLayout>;

  return (
    <AppLayout>
      <div className="mx-auto max-w-6xl py-8 lg:ml-64">
        <div className="mb-5 flex items-center justify-between">
          <Link to={`/cases/${caseId}`} className="inline-flex items-center gap-1 text-sm font-bold text-slate-500">
            <ArrowLeft size={16} /> Case로 돌아가기
          </Link>
          <div className="flex flex-col items-end gap-2"><span className="text-xs font-bold text-slate-400">CUSTOMER SAFETY ROOM</span><button type="button" onClick={openCustomerCall} className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-emerald-700"><Phone size={14} /> 음성 통화 요청</button></div>
        </div>

        <div className="mb-5 flex items-center justify-between rounded-2xl border border-rose-200 bg-rose-50 p-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="text-rose-600" />
            <div>
              <p className="text-sm font-black text-rose-800">HIGH RISK · PREVENT</p>
              <p className="text-xs text-rose-700">은행 확인 중 · #{currentCase.id}</p>
            </div>
          </div>
          <div className="flex items-center gap-2"><span className={`rounded-full px-2.5 py-1 text-[11px] font-extrabold ${recoveryMode ? 'bg-rose-100 text-rose-700' : 'bg-blue-50 text-blue-700'}`}>{recoveryMode ? '구제모드' : currentCase.status}</span><span className="rounded-full bg-white/70 px-2.5 py-1 text-[11px] font-bold text-slate-500">{recoveryMode ? '피해 대응 진행 중' : '상황 확인 및 상담'}</span></div>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1.35fr_1fr]">
          <div className="space-y-4">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-4 text-sm font-extrabold">AI Brief</h2>
              <p className="text-sm leading-7 text-slate-700">{currentCase.summary} <b>확인 전까지 송금하지 마세요.</b></p>
            </section>
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-sm font-extrabold">상담 기록</h2>
                <span className="text-xs font-bold text-blue-600">Case에 자동 기록</span>
              </div>
              <div className="max-h-72 space-y-2 overflow-y-auto rounded-xl bg-slate-50 p-3">
                {messages.length === 0 ? (
                  <p className="py-5 text-center text-sm text-slate-500">아직 기록된 상담 내용이 없습니다.</p>
                ) : messages.map((message) => (
                  <div key={message.message_id} className={`rounded-xl px-3 py-2 text-sm ${message.actor_type === 'CUSTOMER' ? 'ml-8 bg-blue-600 text-white' : 'mr-8 bg-white text-slate-700 shadow-sm'}`}>
                    <p className="mb-1 text-[11px] font-bold opacity-75">{message.actor_type === 'CUSTOMER' ? '고객' : message.actor_type}</p>
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  </div>
                ))}
              </div>
              <div className="mt-3 flex gap-2">
                <textarea value={messageInput} onChange={(event) => setMessageInput(event.target.value)} rows={2} placeholder="현재 상황이나 요청받은 내용을 입력하세요." className="min-h-[52px] flex-1 resize-none rounded-xl border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                <button type="button" onClick={sendCustomerMessage} disabled={!messageInput.trim() || sendingMessage} aria-label="상담 내용 저장" className="grid h-11 w-11 place-items-center self-end rounded-xl bg-blue-600 text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"><Send size={16} /></button>
              </div>
            </section>
            <button onClick={toggleRecoveryMode} className={`w-full rounded-xl border py-3 text-sm font-bold transition ${recoveryMode ? 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50' : 'border-rose-200 bg-white text-rose-600 hover:bg-rose-50'}`}>{recoveryMode ? '상담으로 돌아가기' : '이미 피해를 입었어요 → 구제모드 시작'}</button>
          </div>

          <div className="space-y-4">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-sm font-extrabold">Case Status</h2>
                <span className="text-sm font-bold text-blue-600">실시간 반영</span>
              </div>
              <div className="mb-4 flex items-center justify-between rounded-xl bg-blue-50 p-3">
                <span className="text-sm font-bold text-blue-700">현재 진행 상태</span>
                <span className="text-sm font-extrabold text-blue-700">{currentCase.status}</span>
              </div>
              <div className="space-y-3">
                <StatusRow label="송금 여부" value={liveStatus.transfer} />
                <StatusRow label="개인정보 노출" value={liveStatus.personal} />
                <StatusRow label="공식기관 검증" value={liveStatus.verification} />
                <StatusRow label="은행 확인 및 조치 상태" value={`${liveStatus.bank} · ${liveStatus.bankAction}`} />
                <StatusRow label="담당자 참여" value={humanTakeover ? '담당자 참여 중' : liveStatus.human} />
              </div>
              <p className="mt-4 inline-flex items-center gap-1 text-sm text-slate-400"><Clock3 size={14} /> 챗봇 답변을 선택하면 바로 갱신됩니다.</p>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-extrabold">검증 진행률</h2>
              <div className="mb-2 mt-4 flex justify-between text-xs font-bold"><span>P0 긴급 문진</span><span>{progressCount} / {progressTotal} 완료</span></div>
              <div className="h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-blue-600 transition-all duration-500" style={{ width: progressPercent }} /></div>
              <p className="mt-3 text-xs leading-5 text-slate-500">왼쪽 챗봇 질문에 답변하면 확인 상태와 진행률이 자동으로 반영됩니다.</p>
            </section>
            {recoveryMode && <section className="rounded-2xl border border-rose-200 bg-rose-50 p-5 shadow-sm"><h2 className="text-sm font-extrabold text-rose-800">피해 발생 후 안내</h2><div className="mt-3 space-y-2 text-sm leading-6 text-rose-900"><p>• 추가 송금과 상대방의 연락을 중단하세요.</p><p>• 거래 내역과 대화·문자·첨부 파일을 보관하세요.</p><p>• 은행에 지급정지 및 피해구제 절차를 문의하세요.</p><p>• 필요한 신고와 증빙 제출 상태를 이 Case에서 확인하세요.</p></div><p className="mt-3 rounded-xl bg-white/70 p-3 text-xs font-semibold text-rose-700">실제 금융 조치는 금융기관 담당자의 확인 후 진행됩니다.</p></section>}
          </div>
        </div>
      </div>
      <VoiceCallPopup open={customerCallOpen} role="customer" onClose={closeCustomerCall} onCallStarted={handleCustomerCallStarted} onCallEnded={handleCustomerCallEnded} />
    </AppLayout>
  );
};
