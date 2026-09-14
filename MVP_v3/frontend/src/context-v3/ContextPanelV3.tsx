import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, PanelRightClose, PanelRightOpen, RefreshCw, Trash2, Users } from 'lucide-react';
import type { CaseAction, CaseBundle, CaseFact, CaseSupportSnapshot, CustomerProgressItem, StoredCase, VerificationTask } from '../api/types';
import { AdminCaseDialog } from '../components/AdminCaseDialog';
import { CustomerProgressEditor } from '../components/CustomerProgressEditor';
import { cancelContextTask, completeContextTask, createContextTask, loadContextPanelV3, loadSummaryDisplayOverride, reviewContextFact, reviewContextSuggestion, saveSummaryDisplayOverride, updateContextTask } from './api';
import { ContextV3Section } from './sections';
import type { ContextPanelItemV3, ContextPanelV3 as ContextPanelData } from './types';
import { generateUuid } from '../uuid';

interface Props {
  accessRevision: number; onOpenParticipants: () => void; caseItem: StoredCase; bundle: CaseBundle;
  facts: CaseFact[]; support: CaseSupportSnapshot | null; open: boolean; onToggle: () => void;
  onEditVerification: (task: VerificationTask) => void; onCreateJudgment: (note: string) => Promise<boolean>;
  onUpdateChecklist: (action: CaseAction, values: { status?: 'REQUESTED' | 'COMPLETED' | 'CANCELLED'; note?: string }) => Promise<boolean>;
  checklistBusy: boolean; onProgressSaved: (items: CustomerProgressItem[]) => void;
  onFinalize: (password: string, note: string) => Promise<void>; onReopen: (password: string) => Promise<void>; onTrash: (password: string) => Promise<void>;
}

export const ContextPanelV3: React.FC<Props> = (props) => {
  const [data, setData] = useState<ContextPanelData | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [adminAction, setAdminAction] = useState<'finalize' | 'reopen' | 'trash' | null>(null);
  const [summaryEdit, setSummaryEdit] = useState<{ text: string; version: number } | null>(null);
  const load = useCallback(async (signal?: AbortSignal) => {
    try { setError(''); setData(await loadContextPanelV3(props.caseItem.case_id, signal)); }
    catch (reason) { if (!signal?.aborted) setError(reason instanceof Error ? reason.message : '맥락 패널을 불러오지 못했습니다.'); }
  }, [props.caseItem.case_id]);
  useEffect(() => { const controller = new AbortController(); void load(controller.signal); return () => controller.abort(); }, [load, props.accessRevision, props.bundle.cursor, props.bundle.case.context_revision]);
  const review = async (item: ContextPanelItemV3, decision: 'CONFIRM' | 'REJECT') => {
    setBusy(true); setError('');
    try {
      const scalarKeys = new Set(['transfer.actual.status', 'transfer.requested.amount', 'transfer.actual.amount', 'exposure.personal_information', 'exposure.account_information', 'exposure.authentication_information', 'exposure.identity_or_card', 'exposure.occurred_at', 'device.remote_control_app']);
      const confirmed = scalarKeys.has(item.semantic_key) ? data?.sections.flatMap((section) => [
        ...section.items, ...Object.values(section.groups).flat(),
      ]).find((candidate) => candidate.semantic_key === item.semantic_key && candidate.status === 'CONFIRMED') : undefined;
      await reviewContextFact(props.caseItem.case_id, item.item_id, item.version, decision, decision === 'CONFIRM' ? '담당자 확인' : '담당자 검토 결과 불일치', decision === 'CONFIRM' ? confirmed?.item_id : undefined);
      await load();
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : '검토 결과를 저장하지 못했습니다. 최신 상태를 다시 불러와 주세요.'); }
    finally { setBusy(false); }
  };
  const workflow = async (item: ContextPanelItemV3, action: 'ACCEPT' | 'DISMISS' | 'START' | 'COMPLETE' | 'CANCEL') => {
    let note = '';
    if (action === 'DISMISS') note = window.prompt('제안 제외 사유를 입력하세요.')?.trim() ?? '';
    if (action === 'COMPLETE') note = window.prompt('확인한 처리 결과를 입력하세요.')?.trim() ?? '';
    if (action === 'CANCEL') note = window.prompt('업무 취소 사유를 입력하세요.')?.trim() ?? '';
    if (['DISMISS', 'COMPLETE', 'CANCEL'].includes(action) && !note) return;
    setBusy(true); setError('');
    try {
      if (action === 'ACCEPT' || action === 'DISMISS') await reviewContextSuggestion(props.caseItem.case_id, item.item_id, item.version, action, note);
      else if (action === 'START') await updateContextTask(props.caseItem.case_id, item.item_id, item.version, 'IN_PROGRESS');
      else if (action === 'COMPLETE') await completeContextTask(props.caseItem.case_id, item.item_id, item.version, note);
      else await cancelContextTask(props.caseItem.case_id, item.item_id, item.version, note);
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : '업무 상태를 저장하지 못했습니다. 최신 상태를 다시 확인해 주세요.'); }
    finally { setBusy(false); }
  };
  const openVerification = (id: string) => { const task = props.bundle.verification_tasks.find((item) => item.verification_task_id === id); if (task) props.onEditVerification(task); };
  const addTask = async () => {
    const title = window.prompt('추가할 담당자 업무 제목을 입력하세요.')?.trim() ?? '';
    if (!title) return;
    const description = window.prompt('업무 내용과 확인 기준을 입력하세요.')?.trim() ?? '';
    if (!description) return;
    setBusy(true); setError('');
    try { await createContextTask(props.caseItem.case_id, generateUuid(), title, description); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '담당자 업무를 추가하지 못했습니다.'); }
    finally { setBusy(false); }
  };
  const startSummaryEdit = async () => {
    const existing = (await loadSummaryDisplayOverride(props.caseItem.case_id)).find((item) => item.section === 'SUMMARY' && item.semantic_key === 'display');
    const projected = data?.sections.find((section) => section.section_id === 'SUMMARY')?.items.map((item) => item.display_value).join('\n') ?? '';
    setSummaryEdit({ text: existing?.staff_text || projected, version: existing?.item_version ?? 0 });
  };
  const saveSummary = async () => {
    if (!summaryEdit?.text.trim()) return;
    setBusy(true);
    try { await saveSummaryDisplayOverride(props.caseItem.case_id, summaryEdit.version, summaryEdit.text.trim()); setSummaryEdit(null); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '표시용 요약을 저장하지 못했습니다.'); }
    finally { setBusy(false); }
  };
  const closed = props.caseItem.status === 'CLOSED' || props.caseItem.mode === 'CLOSED';

  return <><aside className={`context-panel ${props.open ? 'is-open' : ''}`} aria-label="사건 맥락 V3">
    <div className="context-header"><div><p className="eyebrow">CASE CONTEXT V3</p><h2>사건 맥락</h2>{data && <small>Revision {data.source_revision} · {data.projection_status}</small>}</div><button type="button" className="context-open context-header-toggle" onClick={props.onToggle}>{props.open ? <PanelRightClose size={17}/> : <PanelRightOpen size={17}/>}</button></div>
    <div className="context-scroll" id="case-context-content">
      <button type="button" className="secondary-action context-v3-participants" onClick={props.onOpenParticipants}><Users size={14}/>참여자 관리</button>
      {data && <button type="button" className="secondary-action" disabled={busy} onClick={() => void addTask()}>담당자 업무 추가</button>}
      {!data && !error && <p className="context-v3-state">맥락을 불러오는 중입니다.</p>}
      {error && <div className="context-edit-error"><p>{error}</p><button onClick={() => void load()}><RefreshCw size={13}/>다시 불러오기</button></div>}
      {data?.sections.map((section) => <React.Fragment key={section.section_id}><ContextV3Section section={section} busy={busy} onReview={review} onWorkflow={workflow} onOpenVerification={openVerification}/>{section.section_id === 'SUMMARY' && <div className="context-v3-summary-edit">{summaryEdit ? <><textarea value={summaryEdit.text} onChange={(event) => setSummaryEdit({ ...summaryEdit, text: event.target.value })}/><div><button disabled={busy} onClick={() => setSummaryEdit(null)}>취소</button><button disabled={busy || !summaryEdit.text.trim()} onClick={() => void saveSummary()}>표시용 요약 저장</button></div></> : <button className="secondary-action" onClick={() => void startSummaryEdit()}>표시용 요약 편집</button>}</div>}</React.Fragment>)}
      <section className="context-section"><h3>고객 진행 상태 편집</h3><CustomerProgressEditor caseId={props.caseItem.case_id} items={props.bundle.customer_progress ?? []} onSaved={props.onProgressSaved}/></section>
      <section className="case-management-section" aria-label="사건 관리"><h3>사건 관리</h3><button type="button" className={`case-finalize-button ${closed ? 'is-closed' : ''}`} onClick={() => setAdminAction(closed ? 'reopen' : 'finalize')}><CheckCircle2 size={15}/>{closed ? '사건 다시 진행하기' : '해결 및 종료 처리'}</button><button type="button" className="case-trash-button" onClick={() => setAdminAction('trash')}><Trash2 size={15}/>휴지통으로 보내기</button></section>
    </div>
  </aside>
  {adminAction === 'finalize' && <AdminCaseDialog title="해결 및 종료 처리" description="사건을 해결 상태로 종료합니다." confirmLabel="해결 및 종료" noteLabel="종료 메모 (선택)" onConfirm={props.onFinalize} onClose={() => setAdminAction(null)}/>}
  {adminAction === 'reopen' && <AdminCaseDialog title="사건 다시 진행하기" description="종료 직전 상태로 복구합니다." confirmLabel="진행 상태로 복구" onConfirm={(password) => props.onReopen(password)} onClose={() => setAdminAction(null)}/>}
  {adminAction === 'trash' && <AdminCaseDialog title="휴지통으로 보내기" description="사건을 휴지통으로 이동합니다." confirmLabel="휴지통으로 보내기" onConfirm={(password) => props.onTrash(password)} onClose={() => setAdminAction(null)}/>}
  </>;
};
