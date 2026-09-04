import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, Bot, CheckCircle2, Loader2, PanelRightOpen, RefreshCw } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { casesApi } from '../api/cases';
import type { CaseBundle, CaseFact, CaseSupportSnapshot, StoredCase, VerificationTask } from '../api/types';
import { ActionDialog, QuestionDialog, VerificationDialog } from '../components/CaseActionDialogs';
import { CaseContextPanel } from '../components/CaseContextPanel';
import { ConversationComposer, type ComposerTarget } from '../components/ConversationComposer';
import { SharedConversation } from '../components/SharedConversation';
import { caseSummary, incidentTitle, riskLabel, riskTone, statusLabel } from '../presentation';

type DialogState = { type: 'questions' } | { type: 'verification'; task?: VerificationTask } | { type: 'action' } | null;

export const CaseRoomPage: React.FC<{ onMutated: () => void }> = ({ onMutated }) => {
  const { caseId = '' } = useParams();
  const [caseItem, setCaseItem] = useState<StoredCase | null>(null);
  const [bundle, setBundle] = useState<CaseBundle | null>(null);
  const [support, setSupport] = useState<CaseSupportSnapshot | null>(null);
  const [facts, setFacts] = useState<CaseFact[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [partialWarnings, setPartialWarnings] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [view, setView] = useState<'conversation' | 'timeline'>('conversation');
  const [dialog, setDialog] = useState<DialogState>(null);
  const [contextOpen, setContextOpen] = useState(false);

  const load = useCallback(async (quiet = false, refreshSupport = !quiet) => {
    if (!caseId) return;
    if (quiet) setRefreshing(true); else setLoading(true);
    const [caseResult, bundleResult, factsResult] = await Promise.allSettled([
      casesApi.get(caseId), casesApi.bundle(caseId), casesApi.facts(caseId),
    ]);
    if (caseResult.status === 'rejected') {
      setError(caseResult.reason instanceof Error ? caseResult.reason.message : 'Case를 불러오지 못했습니다.');
      setLoading(false); setRefreshing(false); return;
    }
    setCaseItem(caseResult.value); if (!quiet) setError('');
    const warnings: string[] = [];
    if (bundleResult.status === 'fulfilled') setBundle(bundleResult.value); else warnings.push('대화와 업무 기록을 갱신하지 못했습니다.');
    if (factsResult.status === 'fulfilled') setFacts(factsResult.value); else warnings.push('확인된 사실을 갱신하지 못했습니다.');
    if (refreshSupport) {
      try { setSupport(await casesApi.support(caseId)); }
      catch { setSupport(null); warnings.push('AI Brief를 갱신하지 못해 최초 Brief를 표시합니다.'); }
    }
    setPartialWarnings(warnings); setLoading(false); setRefreshing(false);
  }, [caseId]);

  useEffect(() => {
    setCaseItem(null); setBundle(null); setSupport(null); setFacts([]); setDialog(null); setContextOpen(false); setError('');
    void load();
    const timer = window.setInterval(() => { void load(true); }, 5000);
    return () => window.clearInterval(timer);
  }, [load]);

  const refreshAfterMutation = async () => { await load(true, true); onMutated(); };
  const send = async (content: string, files: File[], target: ComposerTarget) => {
    setBusy(true);
    try {
      const visibility = target === 'CUSTOMER' ? 'CUSTOMER' : 'BANK_INTERNAL';
      const attachments = [];
      for (const file of files) attachments.push(await casesApi.uploadAttachment(caseId, file, visibility));
      await casesApi.sendMessage(caseId, content, target, attachments.map((item) => item.attachment_id));
      await refreshAfterMutation();
    } finally { setBusy(false); }
  };
  const invokeAi = async () => {
    if (busy) return; setBusy(true); setError('');
    try { await casesApi.invokeAi(caseId); await refreshAfterMutation(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'AI 사건 정리를 요청하지 못했습니다.'); }
    finally { setBusy(false); }
  };

  if (loading && !caseItem) return <section className="room-state"><Loader2 className="spin" size={24}/><strong>Shared Case를 불러오고 있습니다.</strong><span>대화와 현재 맥락을 함께 준비합니다.</span></section>;
  if (error && !caseItem) return <section className="room-state error"><AlertCircle size={24}/><strong>정보를 불러오지 못했습니다.</strong><span>{error}</span><button onClick={() => void load()}>다시 시도</button></section>;
  if (!caseItem || !bundle) return <section className="room-state error"><AlertCircle size={24}/><strong>Case 기록을 열 수 없습니다.</strong><span>General API의 Bundle 응답을 확인해 주세요.</span><button onClick={() => void load()}>다시 시도</button></section>;

  const brief = support?.case_brief?.summary || caseItem.initial_brief || caseSummary(caseItem);
  return <section className="case-room">
    <header className="case-room-header">
      <div className="case-heading"><span className={`risk-dot ${riskTone(caseItem.risk)}`}/><div><div className="case-title-line"><span>{caseItem.case_id}</span><h1>{incidentTitle(caseItem)}</h1></div><p>{statusLabel(caseItem.status, caseItem.mode)} · 담당자 {caseItem.primary_assignee || '미배정'}</p></div></div>
      <div className="room-header-actions"><span className={`risk-pill ${riskTone(caseItem.risk)}`}>{riskLabel(caseItem.risk)} {Math.round(caseItem.risk_score)}</span><Link className="customer-preview-link" to={`/customer/cases/${encodeURIComponent(caseId)}`}>고객 화면 열기</Link><button className="icon-button" onClick={() => void load(true)} aria-label="Case 새로고침"><RefreshCw size={17} className={refreshing ? 'spin' : ''}/></button><button className="context-open" onClick={() => setContextOpen(true)}><PanelRightOpen size={17}/>사건 맥락</button></div>
    </header>
    <div className="case-room-grid">
      <main className="conversation-column">
        <section className="ai-brief"><div className="ai-brief-label"><Bot size={16}/><span>AI BRIEF</span>{support?.available && <small><CheckCircle2 size={12}/>최신 Case 반영</small>}</div><p>{brief}</p></section>
        {partialWarnings.length > 0 && <div className="partial-warning"><AlertCircle size={15}/><span>{partialWarnings.join(' ')}</span></div>}
        {error && <div className="partial-warning danger"><AlertCircle size={15}/><span>{error}</span></div>}
        <div className="conversation-toolbar"><div><button className={view === 'conversation' ? 'active' : ''} onClick={() => setView('conversation')}>대화</button><button className={view === 'timeline' ? 'active' : ''} onClick={() => setView('timeline')}>전체 기록</button></div><span>{refreshing ? '업데이트 확인 중' : '5초마다 안전 갱신'}</span></div>
        <SharedConversation caseItem={caseItem} bundle={bundle} view={view} onEditVerification={(task) => setDialog({ type: 'verification', task })}/>
        <ConversationComposer busy={busy} onSend={send} onOpenQuestions={() => setDialog({ type: 'questions' })} onOpenVerification={() => setDialog({ type: 'verification' })} onOpenAction={() => setDialog({ type: 'action' })} onInvokeAi={() => void invokeAi()}/>
      </main>
      <CaseContextPanel caseItem={caseItem} bundle={bundle} support={support} facts={facts} open={contextOpen} onClose={() => setContextOpen(false)} onEditVerification={(task) => setDialog({ type: 'verification', task })} onCreateAction={() => setDialog({ type: 'action' })}/>
    </div>
    {dialog?.type === 'questions' && <QuestionDialog caseId={caseId} initial={support?.recommended_questions ?? []} onDone={refreshAfterMutation} onClose={() => setDialog(null)}/>} 
    {dialog?.type === 'verification' && <VerificationDialog caseId={caseId} task={dialog.task} onDone={refreshAfterMutation} onClose={() => setDialog(null)}/>} 
    {dialog?.type === 'action' && <ActionDialog caseId={caseId} recovery={caseItem.mode === 'RECOVERY'} onDone={refreshAfterMutation} onClose={() => setDialog(null)}/>} 
  </section>;
};
