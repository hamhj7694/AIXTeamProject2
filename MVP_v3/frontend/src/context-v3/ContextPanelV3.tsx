import React, { Fragment, useCallback, useEffect, useMemo, useState } from 'react';
import { AlertCircle, PanelRightClose, RefreshCw, X } from 'lucide-react';
import type { CaseBundle, CustomerProgressItem, StoredCase, VerificationTask } from '../api/types';
import { casesApi } from '../api/cases';
import { CustomerProgressEditor } from '../components/CustomerProgressEditor';
import { generateUuid } from '../uuid';
import { createContextFact, cancelContextTask, completeContextTask, createContextTask, deleteRejectedContextFact, editContextTask, loadContextPanelV3, loadSummaryDisplayOverride, resetSummaryDisplayOverride, reviewContextFact, reviewContextSuggestion, saveSummaryDisplayOverride, updateContextTask } from './api';
import { ContextQuickNav } from './ContextQuickNav';
import { ContextActionModal, ContextTextArea } from './ContextActionModal';
import { CustomerShareSection, ExposureSection, FactVerificationSection, FraudCircumstanceSection, ImpersonationSection, StaffActionSection, SummarySection, visibleSummaryItems, type WorkflowAction } from './sections';
import type { ContextPanelItemV3, ContextPanelSectionV3, ContextPanelV3 as ContextPanelData } from './types';
import { formatWonInput, parseKoreanWon } from './amount';

interface Props {
  accessRevision: number; caseItem: StoredCase; bundle: CaseBundle; open: boolean; onToggle: () => void;
  onSummaryChange?: (summary: string | null, revision: number) => void;
  onCreateVerification: () => void; onEditVerification: (task: VerificationTask) => void; onProgressSaved: (items: CustomerProgressItem[]) => void;
}

type SectionId = ContextPanelSectionV3['section_id'];
type ContextDialog =
  | { kind: 'confirm'; title: string; description: string; primaryLabel: string; onConfirm: () => void }
  | { kind: 'input'; title: string; description?: string; value: string; primaryLabel: string; onSubmit: (value: string) => void; error?: string };

type FactOption = { key: string; label: string; section: 'EXPOSURE' | 'IMPERSONATION_CONTACT' | 'FRAUD_CIRCUMSTANCES'; kind: 'amount' | 'transfer-status' | 'exposure' | 'occurred' | 'name' | 'role' | 'text' };
const factOptions: FactOption[] = [
  { key: 'transfer.actual.status', label: '실제 이체 여부', section: 'EXPOSURE', kind: 'transfer-status' },
  { key: 'transfer.requested.amount', label: '요구 금액', section: 'EXPOSURE', kind: 'amount' },
  { key: 'transfer.actual.amount', label: '실제 이체 금액', section: 'EXPOSURE', kind: 'amount' },
  { key: 'exposure.personal_information', label: '개인정보 노출', section: 'EXPOSURE', kind: 'exposure' },
  { key: 'exposure.account_information', label: '계좌정보 노출', section: 'EXPOSURE', kind: 'exposure' },
  { key: 'exposure.authentication_information', label: 'OTP·인증정보 노출', section: 'EXPOSURE', kind: 'exposure' },
  { key: 'exposure.identity_or_card', label: '신분증·카드정보 노출', section: 'EXPOSURE', kind: 'exposure' },
  { key: 'device.remote_control_app', label: '원격제어 앱', section: 'EXPOSURE', kind: 'exposure' },
  { key: 'exposure.occurred_at', label: '발생 시점', section: 'EXPOSURE', kind: 'occurred' },
  { key: 'offender.claimed_organization', label: '사칭 기관', section: 'IMPERSONATION_CONTACT', kind: 'name' },
  { key: 'offender.claimed_person_or_role', label: '사칭 인물·직책', section: 'IMPERSONATION_CONTACT', kind: 'role' },
  { key: 'offender.requested_account', label: '제시 계좌', section: 'IMPERSONATION_CONTACT', kind: 'text' },
  { key: 'offender.contact', label: '연락처', section: 'IMPERSONATION_CONTACT', kind: 'text' },
  { key: 'offender.incident_claim', label: '상대방 주장', section: 'FRAUD_CIRCUMSTANCES', kind: 'text' },
  { key: 'circumstance.demand', label: '상대방 요구', section: 'FRAUD_CIRCUMSTANCES', kind: 'text' },
  { key: 'circumstance.tactic', label: '압박·조작 수법', section: 'FRAUD_CIRCUMSTANCES', kind: 'text' },
];
const expectedSections: { id: ContextPanelSectionV3['section_id']; title: string }[] = [
  { id: 'SUMMARY', title: '현재 사건 요약' }, { id: 'EXPOSURE', title: '피해·노출' },
  { id: 'IMPERSONATION_CONTACT', title: '사칭·접촉 정보' }, { id: 'FRAUD_CIRCUMSTANCES', title: '사기 정황' },
  { id: 'FACT_VERIFICATION', title: '사실·확인 현황' }, { id: 'STAFF_ACTIONS', title: '담당자 조치 및 결과' },
  { id: 'CUSTOMER_SHARE', title: '고객 공유 결과' },
];

const normalizeSections = (data: ContextPanelData): ContextPanelSectionV3[] => expectedSections.map(({ id, title }) => data.sections.find((item) => item.section_id === id) ?? { section_id: id, title, items: [], groups: {} });

const typedValue = (option: FactOption, raw: string): Record<string, unknown> => {
  if (option.kind === 'amount') return { amount_krw: parseKoreanWon(raw), currency: 'KRW' };
  if (option.kind === 'transfer-status') return { status: raw };
  if (option.kind === 'exposure') return { status: 'EXPOSED', types: [raw] };
  if (option.kind === 'occurred') return { occurred_at: raw };
  if (option.kind === 'name') return { name: raw };
  if (option.kind === 'role') return { role_or_title: raw };
  if (option.key === 'offender.requested_account') return { account_ref: raw };
  return { text: raw };
};

const formatContextUpdatedAt = (value: string | null | undefined, fallback: string) => {
  const parsed = new Date(value || fallback);
  if (Number.isNaN(parsed.getTime())) return '최종 반영 시각 확인 필요';
  return `${new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
    hour12: false, timeZone: 'Asia/Seoul',
  }).format(parsed)} 최종 반영`;
};

export const ContextPanelV3: React.FC<Props> = (props) => {
  const [data, setData] = useState<ContextPanelData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [summaryEdit, setSummaryEdit] = useState<{ text: string; version: number } | null>(null);
  const [factDraft, setFactDraft] = useState<{ section: FactOption['section']; key: string; value: string } | null>(null);
  const [factFormError, setFactFormError] = useState('');
  const [taskDraft, setTaskDraft] = useState<{ title: string; description: string } | null>(null);
  const [taskEdit, setTaskEdit] = useState<{ item: ContextPanelItemV3; title: string; description: string } | null>(null);
  const [taskFormError, setTaskFormError] = useState('');
  const [openSections, setOpenSections] = useState<Set<SectionId>>(() => new Set());
  const [activeSection, setActiveSection] = useState<SectionId | null>(null);
  const [scrollRequest, setScrollRequest] = useState<{ sectionId: SectionId; requestId: number } | null>(null);
  const [contextDialog, setContextDialog] = useState<ContextDialog | null>(null);

  useEffect(() => {
    setData(null); setError(''); setSummaryEdit(null); setFactDraft(null); setFactFormError(''); setTaskDraft(null); setTaskFormError(''); setOpenSections(new Set()); setActiveSection(null); setScrollRequest(null); setLoading(true);
  }, [props.caseItem.case_id]);

  const setSectionOpen = useCallback((sectionId: SectionId, nextOpen: boolean) => {
    setOpenSections((current) => {
      const next = new Set(current);
      if (nextOpen) next.add(sectionId); else next.delete(sectionId);
      return next;
    });
  }, []);
  const navigateToSection = useCallback((sectionId: SectionId) => {
    setActiveSection(sectionId);
    if (sectionId !== 'SUMMARY') setSectionOpen(sectionId, true);
    setScrollRequest((current) => ({ sectionId, requestId: (current?.requestId ?? 0) + 1 }));
  }, [setSectionOpen]);
  useEffect(() => {
    if (!scrollRequest) return;
    document.getElementById(`context-section-${scrollRequest.sectionId.toLowerCase()}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setScrollRequest((current) => current?.requestId === scrollRequest.requestId ? null : current);
  }, [scrollRequest, openSections]);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    try {
      setError('');
      const panel = await loadContextPanelV3(props.caseItem.case_id, signal);
      const summary = panel.sections.find((section) => section.section_id === 'SUMMARY');
      const summaryItems = summary ? visibleSummaryItems(summary, props.caseItem.risk, props.caseItem.status)
        .filter((item, index, items) => !/^확정 사실 \d+건 · 검토 대기 \d+건$/.test(item.display_value)
          || items.findIndex((candidate) => candidate.display_value === item.display_value) === index) : [];
      props.onSummaryChange?.(summaryItems.map((item) => item.display_value).join('\n') || null, panel.source_revision);
      setData(panel);
    }
    catch (reason) { if (!signal?.aborted) setError(reason instanceof Error ? reason.message : '맥락 패널을 불러오지 못했습니다.'); }
    finally { if (!signal?.aborted) setLoading(false); }
  }, [props.caseItem.case_id, props.onSummaryChange]);
  useEffect(() => { const controller = new AbortController(); void load(controller.signal); return () => controller.abort(); }, [load, props.accessRevision, props.bundle.cursor, props.bundle.case.context_revision]);

  const visibleData = data?.case_id === props.caseItem.case_id ? data : null;
  const normalizedSections = useMemo(() => visibleData ? normalizeSections(visibleData) : [], [visibleData]);
  const getSection = (id: ContextPanelSectionV3['section_id']) => normalizedSections.find((item) => item.section_id === id) ?? { section_id: id, title: id, items: [], groups: {} } as ContextPanelSectionV3;
  const missingSections = useMemo(() => visibleData ? expectedSections.filter(({ id }) => !visibleData.sections.some((item) => item.section_id === id)).map(({ title }) => title) : [], [visibleData]);
  const availableOptions = useMemo(() => factDraft ? factOptions.filter((item) => item.section === factDraft.section) : [], [factDraft]);
  const review = async (item: ContextPanelItemV3, decision: 'CONFIRM' | 'REJECT' | 'RESTORE' | 'UNCONFIRM' | 'INVALIDATE', reasonOverride = '', confirmed = false) => {
    if (decision === 'RESTORE' && !confirmed) { setContextDialog({ kind: 'confirm', title: '정보 복구', description: '이 정보를 다시 확인 필요 상태로 복구할까요?', primaryLabel: '복구', onConfirm: () => { setContextDialog(null); void review(item, decision, reasonOverride, true); } }); return; }
    if (decision === 'UNCONFIRM' && !confirmed) { setContextDialog({ kind: 'confirm', title: '확정 취소', description: '확정을 취소하고 다시 확인 필요 상태로 변경할까요?', primaryLabel: '확정 취소', onConfirm: () => { setContextDialog(null); void review(item, decision, reasonOverride, true); } }); return; }
    if (decision === 'INVALIDATE' && !reasonOverride) {
      setContextDialog({ kind: 'input', title: '확정 정보 제외', description: '제외 사유를 입력하세요.', value: '', primaryLabel: '제외 처리', onSubmit: (value) => { setContextDialog(null); void review(item, decision, value.trim()); } });
      return;
    }
    const invalidationReason = reasonOverride.trim();
    if (decision === 'INVALIDATE' && !invalidationReason) return;
    setBusy(true); setError('');
    try {
      await reviewContextFact(props.caseItem.case_id, item.item_id, item.version, decision, decision === 'CONFIRM' ? '담당자 확인' : decision === 'RESTORE' ? '직원이 제외 항목 복구' : decision === 'UNCONFIRM' ? '직원이 확정 취소' : invalidationReason || '잘못된 정보로 제외');
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : '검토 결과를 저장하지 못했습니다. 최신 상태를 다시 불러와 주세요.'); }
    finally { setBusy(false); }
  };
  const workflow = async (item: ContextPanelItemV3, action: WorkflowAction, confirmed = false, noteOverride = '') => {
    let note = '';
    if (action === 'RESTORE' && !confirmed) { setContextDialog({ kind: 'confirm', title: '업무 복구', description: '이 업무를 대기 상태로 복구할까요?', primaryLabel: '복구', onConfirm: () => { setContextDialog(null); void workflow(item, action, true); } }); return; }
    if (['DISMISS', 'COMPLETE', 'CANCEL'].includes(action) && !noteOverride) { const title = action === 'DISMISS' ? '제안 제외 사유' : action === 'COMPLETE' ? '업무 완료 결과' : '업무 취소 사유'; setContextDialog({ kind: 'input', title, description: '내용을 입력하세요.', value: '', primaryLabel: '저장', onSubmit: (value) => { setContextDialog(null); void workflow(item, action, confirmed, value.trim()); } }); return; }
    if (noteOverride) note = noteOverride.trim();
    if (['DISMISS', 'COMPLETE', 'CANCEL'].includes(action) && !note) return;
    setBusy(true); setError('');
    try {
      if (item.source_kind === 'ACTION_RECORD') {
        const status = action === 'COMPLETE' ? 'COMPLETED' : action === 'CANCEL' ? 'CANCELLED' : action === 'RESTORE' ? 'REQUESTED' : undefined;
        if (status) await casesApi.updateAction(props.caseItem.case_id, item.item_id, { status, note: note || undefined });
      } else if (action === 'ACCEPT' || action === 'DISMISS') await reviewContextSuggestion(props.caseItem.case_id, item.item_id, item.version, action, note);
      else if (action === 'START') await updateContextTask(props.caseItem.case_id, item.item_id, item.version, 'IN_PROGRESS');
      else if (action === 'RESTORE') await updateContextTask(props.caseItem.case_id, item.item_id, item.version, 'TODO');
      else if (action === 'BLOCK') await updateContextTask(props.caseItem.case_id, item.item_id, item.version, 'BLOCKED');
      else if (action === 'COMPLETE') await completeContextTask(props.caseItem.case_id, item.item_id, item.version, note);
      else await cancelContextTask(props.caseItem.case_id, item.item_id, item.version, note);
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : '업무 상태를 저장하지 못했습니다. 최신 상태를 다시 확인해 주세요.'); }
    finally { setBusy(false); }
  };
  const openVerification = (id: string) => {
    const task = props.bundle.verification_tasks.find((item) => item.verification_task_id === id);
    if (!task) return;
    const resumesVerification = ['PENDING', 'ON_HOLD', 'FAILED'].includes(task.status);
    props.onEditVerification(resumesVerification ? { ...task, status: 'IN_PROGRESS' } : task);
  };
  const deleteExcludedFact = (item: ContextPanelItemV3) => {
    setContextDialog({
      kind: 'confirm',
      title: '정보 완전 삭제',
      description: '이 제외 정보를 영구 삭제할까요? 삭제 후에는 복구할 수 없습니다.',
      primaryLabel: '완전 삭제',
      onConfirm: () => {
        setContextDialog(null);
        setBusy(true); setError('');
        void deleteRejectedContextFact(props.caseItem.case_id, item.item_id, item.version)
          .then(() => load())
          .catch((reason) => setError(reason instanceof Error ? reason.message : '제외 정보 삭제에 실패했습니다. 최신 상태를 다시 확인해 주세요.'))
          .finally(() => setBusy(false));
      },
    });
  };
  const correctFactValue = async (item: ContextPanelItemV3, option: FactOption, rawValue: string) => {
    const nextValue = rawValue.trim();
    if (!nextValue || nextValue === item.display_value) return;
    if (option.kind === 'amount' && (!Number.isFinite(Number(nextValue.replace(/,/g, ''))) || Number(nextValue.replace(/,/g, '')) < 0)) { setError('금액은 0 이상의 숫자로 입력해 주세요.'); return; }
    if (option.kind === 'transfer-status' && !['TRANSFERRED', 'NOT_TRANSFERRED', 'UNKNOWN'].includes(nextValue)) { setError('이체 여부는 TRANSFERRED, NOT_TRANSFERRED, UNKNOWN 중 하나로 입력해 주세요.'); return; }
    setBusy(true); setError('');
    try { await createContextFact(props.caseItem.case_id, { client_request_id: generateUuid(), semantic_key: option.key, display_label: option.label, value: typedValue(option, nextValue), display_value: option.kind === 'amount' ? `${Number(nextValue.replace(/,/g, '')).toLocaleString('ko-KR')}원` : nextValue, visibility: item.visibility === 'CUSTOMER_SHARED' ? 'CUSTOMER_SHARED' : 'BANK_INTERNAL', supersedes_fact_id: item.item_id }); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '정정 정보를 저장하지 못했습니다.'); }
    finally { setBusy(false); }
  };
  const correctFact = async (item: ContextPanelItemV3) => {
    const option = factOptions.find((candidate) => candidate.key === item.semantic_key);
    if (!option) { setError('이 정보 종류는 아직 안전한 정정 입력 형식을 지원하지 않습니다. 확정 취소 후 새 정보를 등록해 주세요.'); return; }
    setContextDialog({ kind: 'input', title: `${item.label} 정정`, description: '정정할 값을 입력하세요.', value: item.display_value, primaryLabel: '정정 저장', onSubmit: (value) => { setContextDialog(null); void correctFactValue(item, option, value); } });
  };
  const toggleTaskForm = () => {
    setFactDraft(null); setFactFormError(''); setTaskFormError('');
    const opening = !taskDraft;
    setTaskDraft(opening ? { title: '', description: '' } : null);
    if (opening) setSectionOpen('STAFF_ACTIONS', true);
  };
  const saveTask = async () => {
    if (!taskDraft || busy) return;
    const title = taskDraft.title.trim(); const description = taskDraft.description.trim();
    if (!title || !description) { setTaskFormError('업무 제목과 내용을 모두 입력해 주세요.'); return; }
    setBusy(true); setTaskFormError('');
    try { await createContextTask(props.caseItem.case_id, generateUuid(), title, description); setTaskDraft(null); await load(); }
    catch (reason) { setTaskFormError(reason instanceof Error ? reason.message : '담당자 업무를 추가하지 못했습니다.'); }
    finally { setBusy(false); }
  };
  const openTaskEdit = (item: ContextPanelItemV3) => { setTaskEdit({ item, title: item.label, description: item.display_value }); setTaskFormError(''); setSectionOpen('STAFF_ACTIONS', true); };
  const saveTaskEdit = async () => {
    if (!taskEdit || busy) return;
    const title = taskEdit.title.trim(); const description = taskEdit.description.trim();
    if (!title || !description) { setTaskFormError('업무 제목과 내용을 모두 입력해 주세요.'); return; }
    setBusy(true); setTaskFormError('');
    try { if (taskEdit.item.source_kind === 'ACTION_RECORD') await casesApi.updateAction(props.caseItem.case_id, taskEdit.item.item_id, { note: description }); else await editContextTask(props.caseItem.case_id, taskEdit.item.item_id, taskEdit.item.version, title, description); setTaskEdit(null); await load(); }
    catch (reason) { setTaskFormError(reason instanceof Error ? reason.message : '업무를 수정하지 못했습니다.'); }
    finally { setBusy(false); }
  };
  const startSummaryEdit = async () => {
    try {
      const existing = (await loadSummaryDisplayOverride(props.caseItem.case_id)).find((item) => item.section === 'SUMMARY' && item.semantic_key === 'display');
      const projected = visibleSummaryItems(getSection('SUMMARY'), props.caseItem.risk, props.caseItem.status).map((item) => item.display_value).join('\n');
      setSummaryEdit({ text: existing?.staff_text || projected, version: existing?.item_version ?? 0 });
    } catch (reason) { setError(reason instanceof Error ? reason.message : '표시 요약 편집을 시작하지 못했습니다.'); }
  };
  const saveSummary = async () => {
    if (!summaryEdit?.text.trim()) return; setBusy(true);
    try { await saveSummaryDisplayOverride(props.caseItem.case_id, summaryEdit.version, summaryEdit.text.trim()); setSummaryEdit(null); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '표시용 요약을 저장하지 못했습니다.'); }
    finally { setBusy(false); }
  };
  const resetSummary = async () => {
    setBusy(true); setError('');
    try {
      const existing = (await loadSummaryDisplayOverride(props.caseItem.case_id)).find((item) => item.section === 'SUMMARY' && item.semantic_key === 'display');
      if (existing) await resetSummaryDisplayOverride(props.caseItem.case_id, existing.item_version);
      setSummaryEdit(null); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : '자동 요약으로 복원하지 못했습니다.'); }
    finally { setBusy(false); }
  };
  const toggleFactForm = (target: FactOption['section']) => {
    setTaskDraft(null); setTaskFormError(''); setFactFormError('');
    const opening = factDraft?.section !== target;
    setFactDraft(opening ? { section: target, key: factOptions.find((item) => item.section === target)!.key, value: '' } : null);
    if (opening) setSectionOpen(target, true);
  };
  const saveFact = async () => {
    if (!factDraft || busy) return;
    if (!factDraft.value.trim()) { setFactFormError('내용을 입력해 주세요.'); return; }
    const option = factOptions.find((item) => item.key === factDraft.key); if (!option) return;
    const amount = option.kind === 'amount' ? parseKoreanWon(factDraft.value) : null;
    if (option.kind === 'amount' && amount === null) { setFactFormError('금액을 숫자 또는 한국어 단위로 입력해 주세요. 예: 5천만원, 3백만원'); return; }
    setBusy(true); setFactFormError('');
    try { await createContextFact(props.caseItem.case_id, { client_request_id: generateUuid(), semantic_key: option.key, display_label: option.label, value: typedValue(option, factDraft.value.trim()), display_value: option.kind === 'amount' ? formatWonInput(amount as number) : factDraft.value.trim() }); setFactDraft(null); await load(); }
    catch (reason) { setFactFormError(reason instanceof Error ? reason.message : '정보 제안을 저장하지 못했습니다.'); }
    finally { setBusy(false); }
  };
  const selectedFactOption = factOptions.find((item) => item.key === factDraft?.key);
  const factEditor = factDraft && <form id={`context-create-${factDraft.section.toLowerCase()}`} className="context-fact-form context-inline-create-form" onSubmit={(event) => { event.preventDefault(); void saveFact(); }}><header><strong>직원 정보 제안</strong><button type="button" onClick={() => { setFactDraft(null); setFactFormError(''); }} aria-label="정보 입력 닫기"><X size={14}/></button></header><label>정보 종류<select value={factDraft.key} onChange={(event) => { setFactDraft({ ...factDraft, key: event.target.value, value: '' }); setFactFormError(''); }}>{availableOptions.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>{selectedFactOption?.kind === 'transfer-status' ? <label>실제 이체 여부<select value={factDraft.value} onChange={(event) => { setFactDraft({ ...factDraft, value: event.target.value }); setFactFormError(''); }}><option value="">선택</option><option value="TRANSFERRED">이체함</option><option value="NOT_TRANSFERRED">이체하지 않음</option><option value="UNKNOWN">확인 필요</option></select></label> : <label>내용<input value={factDraft.value} onChange={(event) => { setFactDraft({ ...factDraft, value: event.target.value }); setFactFormError(''); }} placeholder={selectedFactOption?.kind === 'amount' ? '예: 5천만원, 3백만원, 50,000,000원' : '확인한 내용을 입력하세요'}/></label>}{factFormError && <p className="context-inline-form-error" role="alert">{factFormError}</p>}{selectedFactOption?.kind === 'amount' && <p>금액 표현을 입력하면 저장할 때 원 단위 숫자로 변환합니다.</p>}<p>저장 후 ‘확인 필요’ 상태로 등록되며 별도 확정이 필요합니다.</p><footer><button type="button" onClick={() => { setFactDraft(null); setFactFormError(''); }}>취소</button><button type="submit" disabled={busy || !factDraft.value.trim()}>정보 제안 저장</button></footer></form>;
  const taskEditor = taskDraft && <form id="context-create-staff_actions" className="context-fact-form context-inline-create-form context-task-form" onSubmit={(event) => { event.preventDefault(); void saveTask(); }}><header><strong>새 담당자 업무</strong><button type="button" onClick={() => { setTaskDraft(null); setTaskFormError(''); }} aria-label="업무 입력 닫기"><X size={14}/></button></header><label>업무 제목<input value={taskDraft.title} maxLength={300} onChange={(event) => { setTaskDraft({ ...taskDraft, title: event.target.value }); setTaskFormError(''); }} placeholder="수행할 업무 제목을 입력하세요"/></label><label>업무 내용<textarea value={taskDraft.description} maxLength={3000} rows={3} onChange={(event) => { setTaskDraft({ ...taskDraft, description: event.target.value }); setTaskFormError(''); }} placeholder="업무 내용과 확인 기준을 입력하세요"/></label>{taskFormError && <p className="context-inline-form-error" role="alert">{taskFormError}</p>}<footer><button type="button" onClick={() => { setTaskDraft(null); setTaskFormError(''); }}>취소</button><button type="submit" disabled={busy || !taskDraft.title.trim() || !taskDraft.description.trim()}>업무 저장</button></footer></form>;

  const taskEditForm = taskEdit && <form className="context-fact-form context-inline-create-form context-task-form" onSubmit={(event) => { event.preventDefault(); void saveTaskEdit(); }}><header><strong>업무 수정</strong><button type="button" onClick={() => { setTaskEdit(null); setTaskFormError(''); }} aria-label="업무 수정 닫기"><X size={14}/></button></header><label>업무 제목<input value={taskEdit.title} maxLength={300} onChange={(event) => { setTaskEdit({ ...taskEdit, title: event.target.value }); setTaskFormError(''); }}/></label><label>업무 내용<textarea value={taskEdit.description} maxLength={3000} rows={3} onChange={(event) => { setTaskEdit({ ...taskEdit, description: event.target.value }); setTaskFormError(''); }}/></label>{taskFormError && <p className="context-inline-form-error" role="alert">{taskFormError}</p>}<footer><button type="button" onClick={() => { setTaskEdit(null); setTaskFormError(''); }}>취소</button><button type="submit" disabled={busy || !taskEdit.title.trim() || !taskEdit.description.trim()}>수정 저장</button></footer></form>;
  const projectionLabel = visibleData?.projection_status === 'CURRENT' ? '최신' : visibleData?.projection_status === 'UPDATING' ? '갱신 중' : visibleData?.projection_status === 'STALE' ? '오래된 정보' : '확인 필요';
  return <aside className={`context-panel context-panel-v3 ${props.open ? 'is-open' : ''}`} aria-label="사건 맥락 V3">
    <div className="context-header context-v3-sticky-header"><div><p className="eyebrow">사건 정보</p><h2>사건 맥락</h2>{visibleData && <small>{formatContextUpdatedAt(visibleData.updated_at, props.caseItem.updated_at)} · {projectionLabel}</small>}</div><div><button type="button" className="context-open context-header-toggle" onClick={props.onToggle} aria-label="사건 맥락 닫기"><PanelRightClose size={17}/></button></div></div>
    {visibleData && <ContextQuickNav
      sections={normalizedSections} activeSection={activeSection} onNavigate={navigateToSection}
    />}
    <div className="context-scroll" id="case-context-content">
      {loading && !visibleData && <p className="context-v3-state">사건 맥락을 불러오는 중입니다.</p>}
      {error && <div className="context-edit-error context-panel-error"><AlertCircle size={14}/><p>{error}</p><button onClick={() => void load()}><RefreshCw size={13}/>다시 불러오기</button></div>}
      {missingSections.length > 0 && <div className="context-edit-error context-panel-error"><AlertCircle size={14}/><p>서버 응답에서 누락된 영역을 빈 상태로 표시합니다: {missingSections.join(', ')}</p></div>}
      {visibleData && <Fragment key={props.caseItem.case_id}>
        <SummarySection section={getSection('SUMMARY')} caseRisk={props.caseItem.risk} caseStatus={props.caseItem.status} projectionStatus={visibleData.projection_status} editing={Boolean(summaryEdit)} onEdit={() => void startSummaryEdit()} onReset={() => void resetSummary()} editor={<div className="context-v3-summary-edit"><textarea value={summaryEdit?.text ?? ''} onChange={(event) => summaryEdit && setSummaryEdit({ ...summaryEdit, text: event.target.value })}/><div><button disabled={busy} onClick={() => setSummaryEdit(null)}>취소</button><button disabled={busy || !summaryEdit?.text.trim()} onClick={() => void saveSummary()}>표시 요약 저장</button></div></div>}/>
        <ExposureSection section={getSection('EXPOSURE')} busy={busy} onReview={review} onCorrect={correctFact} onDeleteExcluded={deleteExcludedFact} open={openSections.has('EXPOSURE')} onOpenChange={(next) => setSectionOpen('EXPOSURE', next)} onAdd={() => toggleFactForm('EXPOSURE')} addOpen={factDraft?.section === 'EXPOSURE'} createForm={factDraft?.section === 'EXPOSURE' ? factEditor : null}/>
        <ImpersonationSection section={getSection('IMPERSONATION_CONTACT')} busy={busy} onReview={review} onCorrect={correctFact} onDeleteExcluded={deleteExcludedFact} open={openSections.has('IMPERSONATION_CONTACT')} onOpenChange={(next) => setSectionOpen('IMPERSONATION_CONTACT', next)} onAdd={() => toggleFactForm('IMPERSONATION_CONTACT')} addOpen={factDraft?.section === 'IMPERSONATION_CONTACT'} createForm={factDraft?.section === 'IMPERSONATION_CONTACT' ? factEditor : null}/>
        <FraudCircumstanceSection section={getSection('FRAUD_CIRCUMSTANCES')} busy={busy} onReview={review} onCorrect={correctFact} onDeleteExcluded={deleteExcludedFact} open={openSections.has('FRAUD_CIRCUMSTANCES')} onOpenChange={(next) => setSectionOpen('FRAUD_CIRCUMSTANCES', next)} onAdd={() => toggleFactForm('FRAUD_CIRCUMSTANCES')} addOpen={factDraft?.section === 'FRAUD_CIRCUMSTANCES'} createForm={factDraft?.section === 'FRAUD_CIRCUMSTANCES' ? factEditor : null}/>
        <FactVerificationSection section={getSection('FACT_VERIFICATION')} busy={busy} onReview={review} onCorrect={correctFact} open={openSections.has('FACT_VERIFICATION')} onOpenChange={(next) => setSectionOpen('FACT_VERIFICATION', next)} onOpenVerification={openVerification} onCreateVerification={props.onCreateVerification} onDeleteExcluded={deleteExcludedFact}/>
        <StaffActionSection section={getSection('STAFF_ACTIONS')} busy={busy} onWorkflow={workflow} onEditTask={openTaskEdit} open={openSections.has('STAFF_ACTIONS')} onOpenChange={(next) => setSectionOpen('STAFF_ACTIONS', next)} onAddTask={toggleTaskForm} addOpen={Boolean(taskDraft)} createForm={taskEditor} editForm={taskEditForm}/>
        <CustomerShareSection section={getSection('CUSTOMER_SHARE')} open={openSections.has('CUSTOMER_SHARE')} onOpenChange={(next) => setSectionOpen('CUSTOMER_SHARE', next)} progressEditor={<CustomerProgressEditor caseId={props.caseItem.case_id} items={props.bundle.customer_progress ?? []} onSaved={props.onProgressSaved}/>}/>
      </Fragment>}
    </div>
    {contextDialog && <ContextActionModal title={contextDialog.title} description={contextDialog.description} primaryLabel={contextDialog.primaryLabel} onPrimary={() => contextDialog.kind === 'confirm' ? contextDialog.onConfirm() : contextDialog.onSubmit(contextDialog.value)} onClose={() => setContextDialog(null)}>{contextDialog.kind === 'input' ? <ContextTextArea label="내용" value={contextDialog.value} onChange={(event) => setContextDialog({ ...contextDialog, value: event.target.value })} /> : <p>{contextDialog.description}</p>}</ContextActionModal>}
  </aside>;
};
