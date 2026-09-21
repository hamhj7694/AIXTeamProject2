import { priorityLabel } from '../userText';
import React, { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, Check, ListChecks, Loader2, Pencil, Plus, Sparkles, Trash2, X } from 'lucide-react';
import { casesApi } from '../api/cases';
import type { QuestionCandidate, VerificationTask } from '../api/types';
import { actionLabel } from '../presentation';
import { generateUuid } from '../uuid';

const DialogShell: React.FC<{ title: string; description: string; children: React.ReactNode; onClose: () => void }> = ({ title, description, children, onClose }) => {
  const dialogRef = useRef<HTMLElement>(null);
  const onCloseRef = useRef(onClose);
  useEffect(() => { onCloseRef.current = onClose; }, [onClose]);
  useEffect(() => {
    dialogRef.current?.focus();
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') onCloseRef.current(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
  return <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) onClose(); }}><section ref={dialogRef} tabIndex={-1} className="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title"><header><div><h2 id="dialog-title">{title}</h2><p>{description}</p></div><button className="icon-button" onClick={onClose} aria-label="창 닫기"><X size={18}/></button></header>{children}</section></div>;
};

const DialogError = ({ message }: { message: string }) => message ? <p className="dialog-error"><AlertCircle size={15}/>{message}</p> : null;

type QuestionDraftState = { items: QuestionCandidate[]; selected: string[] };
const questionTargetKey = (value: string) => ({
  PERSONAL_INFO: 'personal_information_exposure', PERSONAL_INFO_SHARED: 'personal_information_exposure', PERSONAL_INFORMATION: 'personal_information_exposure',
  AUTHENTICATION_INFO: 'authentication_information_exposure', AUTH_INFO: 'authentication_information_exposure', AUTH_INFO_SHARED: 'authentication_information_exposure',
  VICTIM_TRANSFER_STATUS: 'transfer_status',
}[value.trim().toUpperCase()] ?? value.trim().toLowerCase());
const questionTextKey = (value: string) => value.trim().replace(/\s+/g, ' ').toLocaleLowerCase();
const isDynamicQuestionDraft = (item: QuestionCandidate) => item.question_id.startsWith('ai-context-')
  || item.question_id.startsWith('qf1:')
  || item.target_field.startsWith('ai-context-')
  || item.target_field.startsWith('qf1:');
const isPersistentQuestionDraft = (item: QuestionCandidate) => item.question_id.startsWith('staff-')
  || isDynamicQuestionDraft(item);

export const reconcileQuestionDraft = (items: QuestionCandidate[], selected: string[], authoritative: QuestionCandidate[]): QuestionDraftState => {
  const validTargets = new Set(authoritative.map((item) => questionTargetKey(item.target_field)));
  const preserved = items.filter((item) => {
    // 이전 기본 문장은 설치 요구를 물었으므로 실제 설치 여부 후보로 교체한다.
    if (item.question_id === 'candidate-remote_control_app' && item.question_text.includes('설치하라는 안내')) return false;
    return isPersistentQuestionDraft(item) || validTargets.has(questionTargetKey(item.target_field));
  });
  const usedTargets = new Set(preserved.map((item) => questionTargetKey(item.target_field)));
  const usedTexts = new Set(preserved.map((item) => questionTextKey(item.question_text)));
  const added = authoritative.filter((item) => !usedTargets.has(questionTargetKey(item.target_field)) && !usedTexts.has(questionTextKey(item.question_text)));
  const nextItems = [...preserved, ...added];
  const authoritativeOrder = new Map(authoritative.map((item, index) => [questionTargetKey(item.target_field), index]));
  nextItems.sort((left, right) =>
    (authoritativeOrder.get(questionTargetKey(left.target_field)) ?? Number.MAX_SAFE_INTEGER)
    - (authoritativeOrder.get(questionTargetKey(right.target_field)) ?? Number.MAX_SAFE_INTEGER));
  const validIds = new Set(nextItems.map((item) => item.question_id));
  return {
    items: nextItems,
    selected: [...new Set([...selected.filter((id) => validIds.has(id)), ...added.filter((item) => item.priority === 'P0').map((item) => item.question_id)])],
  };
};

export const visibleQuestionCandidates = (items: QuestionCandidate[], showAdditional: boolean) =>
  showAdditional ? items : items.slice(0, 5);

const questionDraftKey = (caseId: string) => `csr:question-drafts:${caseId}`;
const readQuestionDraft = (caseId: string): QuestionDraftState | null => {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(questionDraftKey(caseId)) || 'null') as QuestionDraftState | null;
    return parsed && Array.isArray(parsed.items) && Array.isArray(parsed.selected) ? parsed : null;
  } catch { return null; }
};
const writeQuestionDraft = (caseId: string, value: QuestionDraftState) => {
  window.localStorage.setItem(questionDraftKey(caseId), JSON.stringify(value));
};
const clearQuestionDraft = (caseId: string) => window.localStorage.removeItem(questionDraftKey(caseId));

export const QuestionDialog: React.FC<{ caseId: string; initial: QuestionCandidate[]; onDone: () => Promise<void>; onClose: () => void }> = ({ caseId, initial, onDone, onClose }) => {
  const savedDraft = useMemo(() => readQuestionDraft(caseId), [caseId]);
  const [items, setItems] = useState<QuestionCandidate[]>(savedDraft?.items ?? initial);
  const [selected, setSelected] = useState<string[]>(savedDraft?.selected ?? initial.filter((item) => item.priority === 'P0').map((item) => item.question_id));
  const [custom, setCustom] = useState('');
  const [loading, setLoading] = useState(true);
  const [recommending, setRecommending] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [aiNote, setAiNote] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState('');
  const [showAdditional, setShowAdditional] = useState(false);
  const [reviewItems, setReviewItems] = useState<QuestionCandidate[] | null>(null);
  const itemsRef = useRef(items);
  const selectedRef = useRef(selected);
  itemsRef.current = items;
  selectedRef.current = selected;
  const applyAuthoritativeCandidates = (authoritative: QuestionCandidate[], baseItems = itemsRef.current, baseSelected = selectedRef.current) => {
    const next = reconcileQuestionDraft(baseItems, baseSelected, authoritative);
    setItems(next.items); setSelected(next.selected);
  };
  useEffect(() => {
    let active = true;
    setLoading(true);
    casesApi.questionCandidates(caseId).then((next) => { if (active) applyAuthoritativeCandidates(next); }).catch((reason) => active && setError(reason instanceof Error ? reason.message : '질문 후보를 불러오지 못했습니다.')).finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [caseId]);
  useEffect(() => {
    if (!loading) writeQuestionDraft(caseId, { items, selected });
  }, [caseId, items, loading, selected]);
  useEffect(() => {
    // 선택된 질문은 접힌 영역에 숨겨진 채로 전송되지 않게 한다.
    if (!showAdditional && items.slice(5).some((item) => selected.includes(item.question_id))) {
      setShowAdditional(true);
    }
  }, [items, selected, showAdditional]);
  const removeQuestion = (questionId: string) => {
    setItems((current) => current.filter((item) => item.question_id !== questionId));
    setSelected((current) => current.filter((id) => id !== questionId));
    if (editingId === questionId) { setEditingId(null); setEditingText(''); }
  };
  const startEditing = (item: QuestionCandidate) => { setEditingId(item.question_id); setEditingText(item.question_text); };
  const saveEditing = (questionId: string) => {
    const value = editingText.trim();
    if (!value) return;
    setItems((current) => current.map((item) => item.question_id === questionId ? { ...item, question_text: value } : item));
    setEditingId(null); setEditingText('');
  };
  const addCustom = () => {
    const value = custom.trim(); if (!value) return;
    const id = `staff-${generateUuid()}`;
    setItems((current) => [...current, { question_id: id, target_field: id, question_text: value, reason: '은행 담당자가 현재 Case 맥락에 따라 직접 추가했습니다.', priority: 'P1', options: [], answer_mode: 'TEXT', allow_free_text: true }]);
    if (itemsRef.current.length >= 5) setShowAdditional(true);
    setSelected((current) => [...current, id]); setCustom('');
  };
  const recommendQuestions = async () => {
    if (recommending) return;
    setRecommending(true); setError(''); setAiNote('');
    try {
      const card = await casesApi.generateWorkCard(caseId, 'QUESTION_PLAN', itemsRef.current);
      const recommended = card.questions ?? [];
      const targets = new Set(itemsRef.current.map((item) => questionTargetKey(item.target_field)));
      const texts = new Set(itemsRef.current.map((item) => questionTextKey(item.question_text)));
      const additions = recommended.filter((item) => !targets.has(questionTargetKey(item.target_field)) && !texts.has(questionTextKey(item.question_text)));
      const combined = [...itemsRef.current, ...additions];
      const latest = await casesApi.questionCandidates(caseId);
      const next = reconcileQuestionDraft(combined, [...selectedRef.current, ...additions.map((item) => item.question_id)], latest);
      setItems(next.items); setSelected(next.selected);
      if (additions.length > 0 && next.items.length > 5) setShowAdditional(true);
      const acceptedIds = new Set(next.items.map((item) => item.question_id));
      const accepted = additions.filter((item) => acceptedIds.has(item.question_id)).length;
      setAiNote(accepted > 0 ? `${accepted}개의 질문 초안을 현재 목록에 반영했습니다. 내용을 검토하고 수정·선택해 주세요.` : '현재 Case에서 새로 추천할 질문이 없습니다.');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'AI 질문 추천을 만들지 못했습니다.'); }
    finally { setRecommending(false); }
  };
  const chosen = useMemo(() => items.filter((item) => selected.includes(item.question_id)), [items, selected]);
  const visibleItems = visibleQuestionCandidates(items, showAdditional);
  const additionalCount = Math.max(0, items.length - 5);
  const submit = async () => {
    if (!reviewItems?.length || saving) return;
    setSaving(true); setError('');
    try {
      const created = await casesApi.queueQuestions(caseId, reviewItems);
      if (created.length === reviewItems.length) {
        clearQuestionDraft(caseId); await onDone(); onClose(); return;
      }
      if (created.length > 0) await onDone();
      const createdTargets = new Set(created.map((item) => questionTargetKey(item.target_field)));
      const createdTexts = new Set(created.map((item) => questionTextKey(item.question_text)));
      const remaining = created.length > 0
        ? itemsRef.current.filter((item) => !createdTargets.has(questionTargetKey(item.target_field)) && !createdTexts.has(questionTextKey(item.question_text)))
        : itemsRef.current;
      const remainingIds = new Set(remaining.map((item) => item.question_id));
      try {
        const latest = await casesApi.questionCandidates(caseId);
        applyAuthoritativeCandidates(latest, remaining, selectedRef.current.filter((id) => remainingIds.has(id)));
      } catch {
        setItems(remaining); setSelected((current) => current.filter((id) => remainingIds.has(id)));
      }
      if (created.length === 0) setError('새로 등록된 질문이 없습니다. 이미 등록·발송·답변되었거나 확인이 완료된 질문일 수 있습니다.');
      else setAiNote(`${reviewItems.length}개 중 ${created.length}개를 등록했습니다. 나머지는 이미 처리된 질문이라 제외되었습니다.`);
      setReviewItems(null);
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : '질문을 고객 대기열에 등록하지 못했습니다.'); }
    finally { setSaving(false); }
  };
  return <DialogShell title="고객에게 확인 질문" description={reviewItems ? '고객 대기열에 등록할 질문을 전송 전에 확인하세요.' : 'AI가 이미 확인한 내용을 제외하고 제안한 질문입니다. 필요한 항목만 선택하세요.'} onClose={onClose}>
    <div className="dialog-body">
      {reviewItems ? <section className="question-send-review" aria-label="보낼 질문 묶음"><h3>보낼 질문 묶음 · {reviewItems.length}개</h3><ol>{reviewItems.map((item) => <li key={item.question_id}>{item.question_text}</li>)}</ol><p className="dialog-queue-note">등록 후 첫 질문만 고객에게 표시됩니다. 나머지는 답변 대기열에서 순서대로 진행됩니다.</p></section> : <>
      <div className="ai-dialog-action"><div><Sparkles size={16}/><span><b>AI 질문 추천</b><small>현재 Case의 대화·답변·확인 이력을 읽고 중복되지 않는 질문을 제안합니다.</small></span></div><button type="button" onClick={() => void recommendQuestions()} disabled={recommending || saving}>{recommending ? <Loader2 className="spin" size={15}/> : <Sparkles size={15}/>}AI에게 질문 추천 받기</button></div>
      {aiNote && <p className="ai-recommendation-note">{aiNote}</p>}
      {loading ? <div className="dialog-loading"><Loader2 className="spin" size={18}/>현재 Case에서 필요한 질문을 정리하고 있습니다.</div> : <div className="question-options">{items.length ? visibleItems.map((item) => <article className="question-option-card" key={item.question_id}><label><input type="checkbox" checked={selected.includes(item.question_id)} onChange={() => setSelected((current) => current.includes(item.question_id) ? current.filter((id) => id !== item.question_id) : [...current, item.question_id])}/><span>{editingId === item.question_id ? <input className="question-edit-input" value={editingText} autoFocus onChange={(event) => setEditingText(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); saveEditing(item.question_id); } if (event.key === 'Escape') { setEditingId(null); setEditingText(''); } }}/>: <b>{item.question_text}</b>}<small>{isDynamicQuestionDraft(item) && <strong className="ai-dynamic-question">AI 동적 추천</strong>}<em>{priorityLabel(item.priority)}</em>{item.reason}</small></span></label><div className="question-card-actions">{editingId === item.question_id ? <><button type="button" onClick={() => saveEditing(item.question_id)} disabled={!editingText.trim()} aria-label="질문 수정 저장"><Check size={14}/></button><button type="button" onClick={() => { setEditingId(null); setEditingText(''); }} aria-label="질문 수정 취소"><X size={14}/></button></> : <button type="button" onClick={() => startEditing(item)} aria-label="질문 편집"><Pencil size={14}/></button>}<button type="button" onClick={() => removeQuestion(item.question_id)} aria-label="질문 삭제"><Trash2 size={14}/></button></div></article>) : <p className="dialog-empty">추가로 추천할 질문이 없습니다. 필요한 질문을 직접 추가할 수 있습니다.</p>}</div>}
      {!loading && additionalCount > 0 && <button type="button" className="secondary-action" onClick={() => setShowAdditional((current) => !current)}>{showAdditional ? '추가 후보 접기' : `추가 후보 ${additionalCount}개 보기`}</button>}
      <div className="inline-add"><input value={custom} onChange={(event) => setCustom(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); addCustom(); } }} placeholder="직접 질문 추가"/><button type="button" onClick={addCustom} disabled={!custom.trim()}><Plus size={15}/>추가</button></div>
      </>}
      <DialogError message={error}/>
      {!reviewItems && <p className="dialog-queue-note">여러 질문을 등록해도 고객에게는 한 번에 하나씩 표시되며, 나머지는 답변 대기열에 저장됩니다.</p>}
    </div>
    <footer className="dialog-footer"><button className="secondary-action" onClick={reviewItems ? () => setReviewItems(null) : onClose}>{reviewItems ? '질문 수정' : '취소'}</button><button className="primary-action" onClick={reviewItems ? () => void submit() : () => setReviewItems([...chosen])} disabled={reviewItems ? saving : !chosen.length || loading || Boolean(editingId)}>{saving ? <Loader2 className="spin" size={15}/> : <Check size={15}/>} {reviewItems ? `질문 ${reviewItems.length}개 등록` : `선택한 질문 ${chosen.length}개 검토`}</button></footer>
  </DialogShell>;
};

type VerificationDraft = { id: string; claim: string; target: string };

const emptyVerificationDraft = (): VerificationDraft => ({ id: generateUuid(), claim: '', target: '' });

export const VerificationDialog: React.FC<{ caseId: string; task?: VerificationTask | null; onDone: () => Promise<void>; onClose: () => void }> = ({ caseId, task, onDone, onClose }) => {
  const [drafts, setDrafts] = useState<VerificationDraft[]>(() => task ? [] : [emptyVerificationDraft()]);
  const [status, setStatus] = useState(task?.status ?? 'PENDING');
  const [result, setResult] = useState(task?.result_summary ?? '');
  const [evidence, setEvidence] = useState(task?.evidence_url ?? '');
  const [source, setSource] = useState(task?.rag_source ?? '');
  const [customerVisible, setCustomerVisible] = useState(task?.customer_visible ?? false);
  const [recommending, setRecommending] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [aiNote, setAiNote] = useState('');
  const completeDrafts = drafts.filter((item) => item.claim.trim() && item.target.trim());

  const updateDraft = (id: string, field: 'claim' | 'target', value: string) => {
    setDrafts((current) => current.map((item) => item.id === id ? { ...item, [field]: value } : item));
  };
  const recommendVerification = async () => {
    if (recommending) return;
    setRecommending(true); setError(''); setAiNote('');
    try {
      const card = await casesApi.generateWorkCard(caseId, 'VERIFICATION_REQUEST');
      const proposed = { claim: card.suggested_claim?.trim() ?? '', target: card.suggested_target?.trim() ?? '' };
      if (!proposed.claim || !proposed.target) {
        setAiNote('현재 Case에서 구체적인 기관 확인 초안을 만들지 못했습니다. 항목을 직접 입력해 주세요.');
      } else {
        setDrafts((current) => {
          const duplicate = current.some((item) => item.claim.trim() === proposed.claim && item.target.trim() === proposed.target);
          if (duplicate) return current;
          const blankIndex = current.findIndex((item) => !item.claim.trim() && !item.target.trim());
          if (blankIndex < 0) return [...current, { id: generateUuid(), ...proposed }];
          return current.map((item, index) => index === blankIndex ? { ...item, ...proposed } : item);
        });
        setAiNote('AI가 사칭 주장과 공식 확인 대상을 초안으로 작성했습니다. 기관 공식 대표번호나 담당자 연락처를 확인해 수정할 수 있습니다.');
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'AI 기관 확인 추천을 만들지 못했습니다.'); }
    finally { setRecommending(false); }
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault(); if (saving) return; setSaving(true); setError('');
    try {
      if (task) {
        await casesApi.updateVerification(caseId, task, { status, result_summary: result || null, evidence_url: evidence || null, rag_source: source || null, verified_by: '은행 담당자', customer_visible: customerVisible });
      } else {
        for (const draft of completeDrafts) await casesApi.createVerification(caseId, draft.claim.trim(), draft.target.trim());
      }
      await onDone(); onClose();
    } catch (reason) { setError(reason instanceof Error ? reason.message : '기관 확인 업무를 저장하지 못했습니다.'); }
    finally { setSaving(false); }
  };
  return <DialogShell title={task ? '기관 확인 결과' : '기관 확인 리스트'} description={task ? '공식 채널에서 확인한 결과를 기록하고 고객 공개 여부를 결정합니다.' : '외부 기관으로 즉시 전송되지 않습니다. 확인할 주장과 공식 확인 대상을 목록으로 검토한 뒤 Shared Case에 등록합니다.'} onClose={onClose}>
    <form onSubmit={submit}><div className="dialog-body form-grid">
      {!task && <>
        <div className="ai-dialog-action"><div><Sparkles size={16}/><span><b>AI 기관 확인 추천</b><small>현재 Case 전체 맥락에서 사칭 기관·주장·확인 대상을 찾아 초안을 작성합니다.</small></span></div><button type="button" onClick={() => void recommendVerification()} disabled={recommending || saving}>{recommending ? <Loader2 className="spin" size={15}/> : <Sparkles size={15}/>}AI에게 추천 받기</button></div>
        {aiNote && <p className="ai-recommendation-note">{aiNote}</p>}
        <div className="verification-draft-list"><div className="verification-list-title"><span><ListChecks size={15}/><b>확인 예정 항목</b></span><small>{completeDrafts.length}개 등록 가능</small></div>{drafts.map((draft, index) => <section key={draft.id} className="verification-draft-item"><header><b>기관 확인 {index + 1}</b><button type="button" onClick={() => setDrafts((current) => current.length === 1 ? [emptyVerificationDraft()] : current.filter((item) => item.id !== draft.id))} aria-label={`기관 확인 ${index + 1} 삭제`}><Trash2 size={14}/></button></header><label>확인할 주장<textarea value={draft.claim} onChange={(event) => updateDraft(draft.id, 'claim', event.target.value)} rows={3} placeholder="예: 상대방이 서울중앙지검 수사관이라고 주장하며 안전계좌 이체를 요구했다"/></label><label>확인 기관·공식 연락처<input value={draft.target} onChange={(event) => updateDraft(draft.id, 'target', event.target.value)} placeholder="예: 서울중앙지검 공식 대표번호·담당 부서·사건번호"/></label></section>)}</div>
        <button type="button" className="add-verification-draft" onClick={() => setDrafts((current) => [...current, emptyVerificationDraft()])}><Plus size={15}/>확인 항목 추가</button>
      </>}
      {task && <><div className="read-only-summary"><span>확인 대상</span><b>{task.target}</b><p>{task.claim}</p></div><label>확인 상태<select value={status} onChange={(event) => setStatus(event.target.value)}><option value="PENDING">확인 대기</option><option value="IN_PROGRESS">확인 중</option><option value="COMPLETED">확인 완료</option><option value="ON_HOLD">보류</option><option value="FAILED">확인 불가</option></select></label><label>확인 결과<textarea value={result} onChange={(event) => setResult(event.target.value)} rows={3} placeholder="공식 채널에서 확인한 결과를 적어주세요."/></label><label>근거 URL<input value={evidence} onChange={(event) => setEvidence(event.target.value)} placeholder="https://..."/></label><label>공식 자료 출처<input value={source} onChange={(event) => setSource(event.target.value)} placeholder="기관 공식 홈페이지 또는 문서명"/></label><label className="check-row"><input type="checkbox" checked={customerVisible} onChange={(event) => setCustomerVisible(event.target.checked)}/>완료 결과를 고객에게 공개할 수 있음</label></>}
      <DialogError message={error}/>
    </div><footer className="dialog-footer"><button type="button" className="secondary-action" onClick={onClose}>취소</button><button className="primary-action" disabled={saving || (!task && completeDrafts.length === 0)}>{saving ? <Loader2 className="spin" size={15}/> : <Check size={15}/>} {task ? '결과 저장' : `확인 항목 ${completeDrafts.length}개 등록`}</button></footer></form>
  </DialogShell>;
};

const actionTypes = ['PAYMENT_HOLD_REVIEW', 'ACCOUNT_REPORT_GUIDANCE', 'EVIDENCE_PRESERVATION', 'DEVICE_SECURITY_GUIDANCE', 'CUSTOMER_CALLBACK', 'OTHER'];

type ActionRecommendation = { type: string; note: string };

const normalizeRecommendedActionType = (value?: string | null) =>
  value && actionTypes.includes(value) ? value : 'OTHER';

export const ActionDialog: React.FC<{ caseId: string; recovery: boolean; onDone: () => Promise<void>; onClose: () => void }> = ({ caseId, recovery, onDone, onClose }) => {
  const [type, setType] = useState(recovery ? 'PAYMENT_HOLD_REVIEW' : 'CUSTOMER_CALLBACK');
  const [title, setTitle] = useState('');
  const [note, setNote] = useState('');
  const [recommendation, setRecommendation] = useState<ActionRecommendation | null>(null);
  const [recommending, setRecommending] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [aiError, setAiError] = useState('');
  const [aiNote, setAiNote] = useState('');
  const draftTouched = useRef(false);
  const recommendationRequest = useRef(0);
  const activeCaseId = useRef(caseId);
  activeCaseId.current = caseId;
  useEffect(() => () => { recommendationRequest.current += 1; }, []);
  useEffect(() => {
    recommendationRequest.current += 1;
    draftTouched.current = false;
    setType(recovery ? 'PAYMENT_HOLD_REVIEW' : 'CUSTOMER_CALLBACK');
    setTitle(''); setNote(''); setRecommendation(null); setRecommending(false); setAiError(''); setAiNote('');
  }, [caseId, recovery]);

  const recommendAction = async () => {
    if (recommending || saving) return;
    const currentRequest = ++recommendationRequest.current;
    const targetCaseId = caseId;
    setRecommending(true); setAiError(''); setAiNote('');
    try {
      const card = await casesApi.generateWorkCard(targetCaseId, 'BANK_ACTION');
      if (currentRequest !== recommendationRequest.current || activeCaseId.current !== targetCaseId) return;
      const proposed = {
        type: normalizeRecommendedActionType(card.suggested_action_type),
        note: card.suggested_action_note?.trim().slice(0, 3000) ?? '',
      };
      if (!proposed.note) {
        setAiNote('현재 사건에서 구체적인 대응 업무 초안을 만들지 못했습니다. 직접 입력하거나 다시 추천받아 주세요.');
      } else if (!draftTouched.current && !note.trim()) {
        setType(proposed.type); setNote(proposed.note); setRecommendation(null);
        draftTouched.current = true;
        setAiNote('AI 추천을 업무 유형과 내용에 반영했습니다. 검토 후 업무 기록을 눌러 주세요.');
      } else {
        setRecommendation(proposed);
        setAiNote('작성 중인 내용을 보호하기 위해 추천을 미리보기로 표시했습니다.');
      }
    } catch (reason) {
      if (currentRequest === recommendationRequest.current && activeCaseId.current === targetCaseId) {
        setAiError(reason instanceof Error ? reason.message : 'AI 대응 업무 추천을 만들지 못했습니다. 다시 시도해 주세요.');
      }
    } finally {
      if (currentRequest === recommendationRequest.current && activeCaseId.current === targetCaseId) setRecommending(false);
    }
  };
  const applyRecommendation = () => {
    if (!recommendation) return;
    setType(recommendation.type); setNote(recommendation.note); setRecommendation(null);
    draftTouched.current = true;
    setAiNote('AI 추천을 반영했습니다. 검토 후 업무 기록을 눌러 주세요.');
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault(); if (!note.trim() || saving || recommending) return; setSaving(true); setError('');
    try {
      await casesApi.createAction(caseId, type, note.trim(), title.trim() || null);
      await onDone(); onClose();
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : '대응 업무를 기록하지 못했습니다.'); }
    finally { setSaving(false); }
  };
  return <DialogShell title="대응 업무 기록" description="권장 조치를 검토한 뒤 담당자가 수행하거나 확인할 업무를 기록합니다." onClose={onClose}>
    <form onSubmit={submit}><div className="dialog-body form-grid">
      <div className="ai-dialog-action"><div><Sparkles size={16}/><span><b>AI 대응 업무 추천</b><small>현재 Case의 맥락과 기존 대응 이력을 바탕으로 업무 유형과 내용을 제안합니다.</small></span></div><button type="button" onClick={() => void recommendAction()} disabled={recommending || saving}>{recommending ? <Loader2 className="spin" size={15}/> : <Sparkles size={15}/>}AI에게 추천 받기</button></div>
      {aiNote && <p className="ai-recommendation-note">{aiNote}</p>}
      {recommendation && <section className="action-recommendation-preview"><div><span>추천 업무 유형</span><b>{actionLabel(recommendation.type)}</b><p>{recommendation.note}</p></div><button type="button" onClick={applyRecommendation} disabled={saving}>추천 적용</button></section>}
      <DialogError message={aiError}/>
      <label>Action title<input value={title} onChange={(event) => { draftTouched.current = true; setTitle(event.target.value); }} maxLength={300} placeholder={`${actionLabel(type)} (optional)`}/></label>
      <label>업무 유형<select value={type} onChange={(event) => { draftTouched.current = true; setType(event.target.value); }}>{actionTypes.map((value) => <option key={value} value={value}>{actionLabel(value)}</option>)}</select></label>
      <label>업무 내용<textarea value={note} onChange={(event) => { draftTouched.current = true; setNote(event.target.value); }} rows={4} maxLength={3000} placeholder="확인 대상, 수행할 조치, 인수인계할 내용을 구체적으로 적어주세요." required/></label>
      <p className="safety-notice">이 기록은 실제 지급정지나 신고를 자동 실행하지 않습니다. 은행 권한과 공식 승인 절차를 별도로 진행해야 합니다.</p><DialogError message={error}/>
    </div><footer className="dialog-footer"><button type="button" className="secondary-action" onClick={onClose}>취소</button><button className="primary-action" disabled={saving || recommending || !note.trim()}>{saving ? <Loader2 className="spin" size={15}/> : <Check size={15}/>}업무 기록</button></footer></form>
  </DialogShell>;
};
