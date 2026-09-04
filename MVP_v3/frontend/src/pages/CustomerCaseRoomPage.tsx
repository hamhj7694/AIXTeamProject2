import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, AlertTriangle, ArrowLeft, Bookmark, CheckCircle2, Loader2, RefreshCw, ShieldCheck, Wifi, X } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { casesApi } from '../api/cases';
import type { CaseBundle, CustomerQuestion } from '../api/types';
import { readCustomerBookmarks, writeCustomerBookmarks, type CustomerBookmark } from '../customer/bookmarks';
import { CustomerBookmarks } from '../customer/CustomerBookmarks';
import { CustomerComposer } from '../customer/CustomerComposer';
import { CustomerConversation } from '../customer/CustomerConversation';
import { CustomerProgressPanel, CustomerSafetyGuide } from '../customer/CustomerProgressPanel';
import { RecoveryNavigator } from '../customer/RecoveryCards';
import { RECOVERY_MESSAGE_PREFIX, recoveryStepFromMessage, type RecoveryStep, type RecoveryStepId } from '../customer/recovery';

export const CustomerCaseRoomPage: React.FC = () => {
  const { caseId = '' } = useParams();
  const [bundle, setBundle] = useState<CaseBundle | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [confirmRecovery, setConfirmRecovery] = useState(false);
  const [bookmarkOpen, setBookmarkOpen] = useState(false);
  const [bookmarks, setBookmarks] = useState<CustomerBookmark[]>([]);
  const ensuredQuestions = useRef(false);

  const load = useCallback(async (quiet = false) => {
    if (!caseId) return;
    if (quiet) setRefreshing(true); else setLoading(true);
    try { setBundle(await casesApi.customerBundle(caseId)); setError(''); }
    catch (reason) { if (!quiet) setError(reason instanceof Error ? reason.message : '안전 상담 정보를 불러오지 못했습니다.'); }
    finally { setLoading(false); setRefreshing(false); }
  }, [caseId]);

  useEffect(() => {
    setBundle(null); setError(''); setNotice(''); setLoading(true); setConfirmRecovery(false);
    ensuredQuestions.current = false;
    setBookmarks(readCustomerBookmarks(caseId));
    void load();
    const timer = window.setInterval(() => void load(true), 4000);
    return () => window.clearInterval(timer);
  }, [caseId]);

  useEffect(() => {
    if (!bundle || ensuredQuestions.current || String(bundle.case.status ?? '') === 'CLOSED') return;
    if (bundle.questions.length > 0) return;
    ensuredQuestions.current = true;
    casesApi.ensureCustomerQuestions(caseId).then(() => load(true)).catch((reason) => {
      setNotice(reason instanceof Error ? `안전 확인 질문을 준비하지 못했습니다. ${reason.message}` : '안전 확인 질문을 준비하지 못했습니다.');
    });
  }, [bundle, caseId, load]);

  const refresh = async () => { await load(true); };
  const recovery = String(bundle?.case.mode ?? '') === 'RECOVERY' || String(bundle?.case.victim_transfer_status ?? '') === 'YES';
  const selectedStep = useMemo<RecoveryStepId | null>(() => {
    if (!bundle) return null;
    const messages = [...bundle.recent_messages].reverse();
    return recoveryStepFromMessage(messages.find((message) => recoveryStepFromMessage(message.content))?.content ?? '')?.id ?? null;
  }, [bundle]);
  const closed = String(bundle?.case.status ?? '') === 'CLOSED' || String(bundle?.case.mode ?? '') === 'CLOSED';

  const send = async (content: string, files: File[], requestAi: boolean) => {
    setBusy(true); setError(''); setNotice('');
    try {
      const attachments = [];
      for (const file of files) attachments.push(await casesApi.uploadCustomerAttachment(caseId, file));
      const message = await casesApi.sendCustomerMessage(caseId, content, attachments.map((item) => item.attachment_id));
      if (requestAi && content) {
        try { await casesApi.invokeCustomerAi(caseId, content, message.message_id); }
        catch (reason) { setNotice(`메시지는 전달됐지만 AI 안내를 만들지 못했습니다. ${reason instanceof Error ? reason.message : '잠시 후 다시 요청해 주세요.'}`); }
      }
      await refresh();
    } finally { setBusy(false); }
  };

  const answer = async (question: CustomerQuestion, rawAnswer: string) => {
    setBusy(true); setError(''); setNotice('');
    try {
      await casesApi.answerCustomerQuestion(caseId, question.question_id, rawAnswer);
      try { await refresh(); } catch { setNotice('답변은 접수됐지만 최신 화면을 갱신하지 못했습니다. 다시 요청하지 말고 새로고침해 주세요.'); }
    } finally { setBusy(false); }
  };

  const startRecovery = async () => {
    if (recovery || busy) return;
    setBusy(true); setError(''); setNotice('');
    try { await casesApi.startCustomerEmergency(caseId); setConfirmRecovery(false); await refresh(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '피해구제 요청을 접수하지 못했습니다.'); }
    finally { setBusy(false); }
  };

  const selectRecoveryStep = async (step: RecoveryStep) => {
    const existing = bundle?.recent_messages.find((message) => message.content === `${RECOVERY_MESSAGE_PREFIX} ${step.title}`);
    if (existing) { document.getElementById(`recovery-${existing.message_id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }); return; }
    setBusy(true); setError('');
    try {
      const message = await casesApi.sendCustomerMessage(caseId, `${RECOVERY_MESSAGE_PREFIX} ${step.title}`);
      await refresh();
      window.setTimeout(() => document.getElementById(`recovery-${message.message_id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 60);
    } catch (reason) { setError(reason instanceof Error ? reason.message : '피해구제 절차를 열지 못했습니다.'); }
    finally { setBusy(false); }
  };

  const requestRecoveryHelp = async (kind: 'AI_ADVICE' | 'HUMAN_HANDOFF', step: RecoveryStep) => {
    setBusy(true); setError(''); setNotice('');
    try {
      const label = kind === 'AI_ADVICE' ? '내 상황에 맞는 AI 조언' : '은행 담당자 지원';
      const message = await casesApi.sendCustomerMessage(caseId, `${step.title} 단계에 대해 ${label}을 요청합니다.`);
      if (kind === 'AI_ADVICE') {
        try { await casesApi.invokeCustomerAi(caseId, `${step.title} 피해구제 단계에서 제가 지금 해야 할 일을 쉬운 순서로 알려주세요.`, message.message_id); }
        catch (reason) { setNotice(`지원 요청은 접수됐지만 AI 안내를 만들지 못했습니다. ${reason instanceof Error ? reason.message : ''}`); }
      }
      await refresh();
    } finally { setBusy(false); }
  };

  const toggleBookmark = (bookmark: CustomerBookmark) => {
    const next = bookmarks.some((item) => item.entryId === bookmark.entryId) ? bookmarks.filter((item) => item.entryId !== bookmark.entryId) : [...bookmarks, bookmark];
    setBookmarks(next); writeCustomerBookmarks(caseId, next);
  };

  if (loading && !bundle) return <div className="customer-page"><section className="customer-room-state"><Loader2 className="spin" size={26}/><strong>안전 상담 정보를 불러오고 있습니다.</strong><span>현재 Case의 공개 정보를 준비합니다.</span></section></div>;
  if (!bundle) return <div className="customer-page"><section className="customer-room-state error"><AlertCircle size={25}/><strong>안전 상담을 열지 못했습니다.</strong><span>{error || '잠시 후 다시 시도해 주세요.'}</span><button onClick={() => void load()}>다시 시도</button></section></div>;

  return <div className={`customer-page ${recovery ? 'is-recovery' : ''}`}>
    <header className="customer-header"><Link to="/" aria-label="서비스 홈으로"><ArrowLeft size={17}/>서비스 홈</Link><div><span><ShieldCheck size={18}/></span><b>CONTEXT-FIRST CASE</b><small>{caseId} · 고객 안전 상담</small></div><div className="customer-header-actions"><span><Wifi size={13}/>안전하게 연결됨</span><button type="button" onClick={() => setBookmarkOpen(true)}><Bookmark size={16}/>북마크{bookmarks.length > 0 && <b>{bookmarks.length}</b>}</button><button type="button" onClick={() => void load(true)} aria-label="상담 내용 새로고침"><RefreshCw size={16} className={refreshing ? 'spin' : ''}/></button></div></header>
    <main className="customer-main">
      <section className={`customer-safety-banner ${closed ? 'closed' : recovery ? 'recovery' : ''}`}><div>{closed ? <CheckCircle2 size={20}/> : <AlertTriangle size={20}/>}<span><strong>{closed ? '상담이 마무리되었습니다.' : recovery ? '피해구제 절차를 함께 진행하고 있습니다.' : '지금은 송금·인증정보 제공을 멈춰주세요.'}</strong><small>{closed ? '추가 피해가 의심되면 공식 은행 고객센터로 다시 상담을 요청해 주세요.' : recovery ? '추가 송금과 상대방 접촉을 중단하고 아래 절차를 확인하세요.' : '상대방이 알려준 연락처가 아닌 공식 채널로만 확인해 주세요.'}</small></span></div>{!closed && <button type="button" disabled={recovery || busy} onClick={() => setConfirmRecovery(true)}>{recovery ? '피해구제 안내 진행 중' : '이미 사기 당했어요'}</button>}</section>
      {error && <div className="customer-global-message danger"><AlertCircle size={16}/><span>{error}</span><button type="button" onClick={() => setError('')} aria-label="오류 닫기"><X size={15}/></button></div>}
      {notice && <div className="customer-global-message"><AlertCircle size={16}/><span>{notice}</span><button type="button" onClick={() => setNotice('')} aria-label="안내 닫기"><X size={15}/></button></div>}
      <div className="customer-room-grid">
        <section className="customer-chat-panel"><header><div><h1>보이스피싱 대응 AI 상담</h1><p>필요한 내용을 한 가지씩 확인하고 은행 담당자와 연결합니다.</p></div><span>고객 공개 채널</span></header><CustomerConversation bundle={bundle} busy={busy} bookmarkedIds={new Set(bookmarks.map((item) => item.entryId))} onAnswer={answer} onRecoveryRequest={requestRecoveryHelp} onToggleBookmark={toggleBookmark}/><CustomerComposer busy={busy} disabled={closed} onSend={send}/></section>
        <aside className="customer-side-panel"><CustomerProgressPanel bundle={bundle} recovery={recovery} selectedStep={selectedStep}/>{recovery ? <RecoveryNavigator selected={selectedStep} busy={busy} onSelect={selectRecoveryStep}/> : <CustomerSafetyGuide/>}</aside>
      </div>
    </main>
    <CustomerBookmarks open={bookmarkOpen} items={bookmarks} onClose={() => setBookmarkOpen(false)}/>
    {confirmRecovery && <div className="dialog-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setConfirmRecovery(false); }}><section className="customer-confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="recovery-confirm-title"><header><AlertTriangle size={21}/><div><h2 id="recovery-confirm-title">이미 사기 피해가 발생했나요?</h2><p>송금 또는 개인정보·인증정보 제공 피해가 있다면 피해구제 모드로 전환합니다.</p></div></header><p>전환 후에는 추가 송금 중단, 증빙 확보, 신고, 피해구제 신청 순서를 안내하며 은행 담당자에게 긴급 신호가 전달됩니다.</p><footer><button type="button" onClick={() => setConfirmRecovery(false)}>취소</button><button type="button" className="danger" disabled={busy} onClick={() => void startRecovery()}>{busy ? '접수 중' : '피해구제 시작'}</button></footer></section></div>}
  </div>;
};
