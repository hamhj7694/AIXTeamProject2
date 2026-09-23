import { priorityLabel } from '../userText';
import React, { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, Check, Loader2, Pencil, Plus, Send, Sparkles, Trash2, X } from 'lucide-react';
import { casesApi } from '../api/cases';
import type { CaseAction, QuestionCandidate, SuggestedResponseAction, VerificationTask } from '../api/types';
import { actionLabel, verificationStatusLabel } from '../presentation';
import { generateUuid } from '../uuid';

const DialogShell: React.FC<{ title: string; description: string; children: React.ReactNode; onClose: () => void; inline?: boolean }> = ({ title, description, children, onClose, inline = false }) => {
  const dialogRef = useRef<HTMLElement>(null);
  const onCloseRef = useRef(onClose);
  useEffect(() => { onCloseRef.current = onClose; }, [onClose]);
  useEffect(() => {
    dialogRef.current?.focus();
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') onCloseRef.current(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
  return <div className={inline ? 'conversation-question-panel' : 'dialog-backdrop'} role={inline ? undefined : 'presentation'} onMouseDown={inline ? undefined : (event) => { if (event.currentTarget === event.target) onClose(); }}><section ref={dialogRef} tabIndex={-1} className={inline ? 'conversation-question-card' : 'dialog'} role="dialog" aria-modal={inline ? undefined : 'true'} aria-labelledby="dialog-title"><header><div><h2 id="dialog-title">{title}</h2><p>{description}</p></div><button className="icon-button" onClick={onClose} aria-label="창 닫기"><X size={18}/></button></header>{children}</section></div>;
};

export const EmptyGuideDialog: React.FC<{ title: string; onClose: () => void }> = ({ title, onClose }) => (
  <DialogShell title={title} description="화면과 기능을 설계 중입니다." onClose={onClose}>
    <div className="dialog-body" style={{ minHeight: 180 }} />
  </DialogShell>
);

const RESPONSE_CATEGORIES = ['금융 보호', '고객 소통', '증빙·기록', '계정·기기 보안', '기관 확인·신고'] as const;
const RESPONSE_PRIORITY: Record<'P0' | 'P1' | 'P2', string> = { P0: '긴급', P1: '높음', P2: '일반' };
const responsePriority = (value: string): 'P0' | 'P1' | 'P2' => value === 'P0' || value === 'P2' ? value : 'P1';
const slugResponse = (value: string) => value.trim().toLocaleLowerCase().replace(/[^a-z0-9가-힣]+/g, '_').replace(/^_|_$/g, '').slice(0, 32) || 'item';
const responseCategory = (action: CaseAction) => {
  const parts = action.action_type.split(':');
  if ((action.action_type.startsWith('RESPONSE_CHECKLIST:') || action.action_type.startsWith('RESPONSE_STEP:')) && parts[2]) return parts[2];
  const text = `${action.action_type} ${action.title ?? ''} ${action.note}`.toLocaleLowerCase();
  if (/증빙|기록|보존|evidence/.test(text)) return '증빙·기록';
  if (/고객|안내|소통|customer/.test(text)) return '고객 소통';
  if (/계정|기기|보안|인증|device|security/.test(text)) return '계정·기기 보안';
  if (/기관|신고|확인|institution|report/.test(text)) return '기관 확인·신고';
  return '금융 보호';
};
const responsePriorityOf = (action: CaseAction) => {
  const match = action.action_type.match(/(?:AI_CHECKLIST|RESPONSE_CHECKLIST):(P[012])(?=:|$)/);
  return responsePriority(match?.[1] ?? 'P1');
};
const responseTitle = (action: CaseAction) => action.title?.trim() || action.note.trim().split(/\r?\n/)[0].slice(0, 120) || actionLabel(action.action_type);
const responseDedupe = (action: CaseAction) => action.action_type.startsWith('RESPONSE_CHECKLIST:') ? action.action_type.split(':').slice(3).join(':') : slugResponse(responseTitle(action));
const responseParentKey = (action: CaseAction) => {
  const parts = action.action_type.split(':');
  if (action.action_type.startsWith('RESPONSE_CHECKLIST:')) return parts.slice(3).join(':');
  if (action.action_type.startsWith('RESPONSE_STEP:')) return parts[3] ?? '';
  return '';
};
const isResponseParent = (action: CaseAction) => action.action_type.startsWith('RESPONSE_CHECKLIST:');
const isResponseStep = (action: CaseAction) => action.action_type.startsWith('RESPONSE_STEP:');
const isStaffResponseAction = (action: CaseAction) => {
  if (action.action_type.startsWith('AI_CHECKLIST:')) return false;
  const text = `${responseTitle(action)} ${action.note}`.toLocaleLowerCase();
  return !/(질문|답변|대답|문의 내용|무엇을 확인할지|사실로 확정할지|고객 답변|고객이 .* 알려)/.test(text);
};
const isStaffSuggestedAction = (item: SuggestedResponseAction) => !/(질문|답변|대답|문의 내용|무엇을 확인할지|사실로 확정할지|고객 답변)/.test(`${item.title} ${item.note}`.toLocaleLowerCase());

type ResponseChecklistItem = { action: CaseAction; category: string; priority: 'P0' | 'P1' | 'P2'; title: string; source: string; parentKey: string; isParent: boolean; steps: CaseAction[] };

export const ResponseActionChecklistDialog: React.FC<{ caseId: string; actions: CaseAction[]; onDone: () => Promise<void>; onClose: () => void }> = ({ caseId, actions, onDone, onClose }) => {
  const [working, setWorking] = useState(actions);
  const [view, setView] = useState<'category' | 'priority'>('category');
  const [busyId, setBusyId] = useState<string | null>(null);
  const [recommending, setRecommending] = useState(false);
  const [adding, setAdding] = useState(false);
  const [draftTitle, setDraftTitle] = useState('');
  const [draftCategory, setDraftCategory] = useState<string>('금융 보호');
  const [draftPriority, setDraftPriority] = useState<'P0' | 'P1' | 'P2'>('P1');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  useEffect(() => setWorking(actions), [actions]);
  const items = useMemo<ResponseChecklistItem[]>(() => {
    const visible = working.filter((item) => !item.action_type.startsWith('CUSTOMER_PROGRESS:') && !isResponseStep(item) && isStaffResponseAction(item));
    return visible.map((action) => ({ action, category: responseCategory(action), priority: responsePriorityOf(action), title: responseTitle(action), source: action.action_type.startsWith('RESPONSE_CHECKLIST:') ? 'AI 추천' : '기존 기록', parentKey: responseParentKey(action), isParent: isResponseParent(action), steps: working.filter((child) => isResponseStep(child) && responseParentKey(child) === responseParentKey(action) && isStaffResponseAction(child)) }));
  }, [working]);
  const sorted = useMemo(() => [...items].sort((a, b) => ({ P0: 0, P1: 1, P2: 2 }[a.priority] - { P0: 0, P1: 1, P2: 2 }[b.priority] || a.category.localeCompare(b.category) || a.title.localeCompare(b.title))), [items]);
  const grouped = useMemo(() => RESPONSE_CATEGORIES.map((category) => ({ category, items: sorted.filter((item) => item.category === category) })).filter((group) => group.items.length), [sorted]);
  const toggle = async (action: CaseAction) => {
    const nextStatus = action.status === 'COMPLETED' ? 'REQUESTED' : 'COMPLETED';
    setBusyId(action.action_id); setError('');
    try {
      const updated = await casesApi.updateAction(caseId, action.action_id, { status: nextStatus });
      setWorking((current) => current.map((action) => action.action_id === updated.action_id ? updated : action));
      await onDone();
    } catch (reason) { setError(reason instanceof Error ? reason.message : '대응 조치 상태를 저장하지 못했습니다.'); }
    finally { setBusyId(null); }
  };
  const recommend = async () => {
    if (recommending) return;
    setRecommending(true); setError(''); setNotice('');
    try {
      const card = await casesApi.generateWorkCard(caseId, 'BANK_ACTION');
      const suggestions: SuggestedResponseAction[] = card.suggested_actions?.length ? card.suggested_actions : (card.suggested_action_note ? [{ dedupe_key: card.suggested_action_type || card.suggested_action_note, category: '금융 보호', priority: 'P1', title: actionLabel(card.suggested_action_type || 'OTHER'), note: card.suggested_action_note, reason_codes: [] }] : []);
      const keys = new Set(working.flatMap((action) => [responseDedupe(action), slugResponse(responseTitle(action))]));
      const additions = suggestions.filter((item) => {
        const key = item.dedupe_key || slugResponse(item.title);
        const titleKey = slugResponse(item.title);
        return item.title.trim() && isStaffSuggestedAction(item) && !keys.has(key) && !keys.has(titleKey);
      }).slice(0, 12);
      let created = 0;
      for (const item of additions) {
        const priority = responsePriority(item.priority);
        const category = RESPONSE_CATEGORIES.includes(item.category as typeof RESPONSE_CATEGORIES[number]) ? item.category : '금융 보호';
        const parentKey = slugResponse(item.dedupe_key || item.title);
        const actionType = `RESPONSE_CHECKLIST:${priority}:${slugResponse(category)}:${parentKey}`;
        const saved = await casesApi.createAction(caseId, actionType, item.note.trim(), item.title.trim());
        setWorking((current) => [...current, saved]); created += 1;
        keys.add(item.dedupe_key || slugResponse(item.title));
        keys.add(slugResponse(item.title));
        for (const [index, step] of (item.steps ?? []).filter((value) => value.title.trim()).slice(0, 8).entries()) {
          const stepKey = slugResponse(step.dedupe_key || step.title) || `step_${index + 1}`;
          const stepType = `RESPONSE_STEP:${priority}:${slugResponse(category)}:${parentKey}:${stepKey}`;
          const child = await casesApi.createAction(caseId, stepType, step.note.trim(), step.title.trim());
          setWorking((current) => [...current, child]);
        }
      }
      await onDone();
      setNotice(created ? `AI 추천 ${created}개 항목을 추가했습니다.` : '새로 추가할 대응 조치가 없습니다.');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'AI 대응 조치 추천에 실패했습니다. 기존 목록은 유지됩니다.'); }
    finally { setRecommending(false); }
  };
  const addManual = async () => {
    const title = draftTitle.trim();
    if (!title || adding) return;
    const titleKey = slugResponse(title);
    if (working.some((action) => responseDedupe(action) === titleKey || slugResponse(responseTitle(action)) === titleKey)) {
      setNotice('같은 제목의 체크리스트 항목이 이미 있습니다.');
      return;
    }
    setAdding(true); setError('');
    try {
      const actionType = `RESPONSE_CHECKLIST:${draftPriority}:${slugResponse(draftCategory)}:${slugResponse(title)}`;
      const saved = await casesApi.createAction(caseId, actionType, title, title);
      setWorking((current) => [...current, saved]);
      setDraftTitle(''); setAdding(false); setNotice('체크리스트 항목을 추가했습니다.');
      await onDone();
    } catch (reason) { setError(reason instanceof Error ? reason.message : '체크리스트 항목을 추가하지 못했습니다.'); setAdding(false); }
  };
  const renderStep = (step: CaseAction, item: ResponseChecklistItem) => <label className={`response-checklist-item response-checklist-step ${step.status === 'COMPLETED' ? 'is-complete' : ''}`} key={step.action_id}><input type="checkbox" checked={step.status === 'COMPLETED'} disabled={busyId === step.action_id} onChange={() => void toggle(step)}/><span className="response-checklist-main"><b>{responseTitle(step)}</b><small>{step.note}</small><em>{item.category}</em></span><span className={`response-checklist-priority is-${item.priority}`}>{item.priority}</span><span className="response-checklist-status">{step.status === 'IN_PROGRESS' ? '수행 중' : step.status === 'COMPLETED' ? '완료' : '요청'}</span></label>;
  const renderItem = (item: ResponseChecklistItem) => {
    const completed = item.steps.filter((step) => step.status === 'COMPLETED').length;
    const hasSteps = item.steps.length > 0;
    if (!hasSteps) return <label className={`response-checklist-item ${item.action.status === 'COMPLETED' ? 'is-complete' : ''}`} key={item.action.action_id}><input type="checkbox" checked={item.action.status === 'COMPLETED'} disabled={busyId === item.action.action_id} onChange={() => void toggle(item.action)}/><span className="response-checklist-main"><b>{item.title}</b><em>{item.category} · {item.source}</em></span><span className={`response-checklist-priority is-${item.priority}`}>{item.priority} {RESPONSE_PRIORITY[item.priority]}</span><span className="response-checklist-status">{item.action.status === 'IN_PROGRESS' ? '수행 중' : item.action.status === 'COMPLETED' ? '완료' : '요청'}</span></label>;
    const parentStatus = hasSteps && completed === item.steps.length ? 'COMPLETED' : hasSteps && item.steps.some((step) => step.status === 'IN_PROGRESS' || step.status === 'COMPLETED') ? 'IN_PROGRESS' : item.action.status;
    return <div className="response-checklist-parent" key={item.action.action_id}><button type="button" className="response-checklist-item response-checklist-parent-row" onClick={() => hasSteps && setExpanded((current) => ({ ...current, [item.action.action_id]: !current[item.action.action_id] }))}><span className="response-checklist-expand">{hasSteps ? (expanded[item.action.action_id] ? '▾' : '▸') : '•'}</span><span className="response-checklist-main"><b>{item.title}</b><em>{item.category} · {item.source}</em></span>{hasSteps && <span className="response-checklist-progress">{completed}/{item.steps.length} 완료 · {Math.round((completed / item.steps.length) * 100)}%</span>}<span className={`response-checklist-priority is-${item.priority}`}>{item.priority} {RESPONSE_PRIORITY[item.priority]}</span><span className="response-checklist-status">{parentStatus === 'IN_PROGRESS' ? '수행 중' : parentStatus === 'COMPLETED' ? '완료' : '요청'}</span></button>{hasSteps && expanded[item.action.action_id] && <div className="response-checklist-steps">{item.steps.map((step) => renderStep(step, item))}</div>}</div>;
  };
  return <DialogShell title="필요 대응 조치 검토" description="Case 맥락에 맞는 대응 조치를 확인하고 진행 상태를 관리합니다." onClose={onClose}><div className="dialog-body response-checklist-body"><div className="response-checklist-toolbar"><div className="response-checklist-toggle"><button type="button" className={view === 'category' ? 'is-active' : ''} onClick={() => setView('category')}>카테고리별</button><button type="button" className={view === 'priority' ? 'is-active' : ''} onClick={() => setView('priority')}>우선순위순</button></div><div className="response-checklist-toolbar-actions"><button type="button" className="response-add-button" onClick={() => setAdding((current) => !current)}><Plus size={14}/>체크리스트 추가하기</button><button type="button" className="ai-dialog-button" onClick={() => void recommend()} disabled={recommending}>{recommending ? <Loader2 className="spin" size={15}/> : <Sparkles size={15}/>}AI에게 추천받기</button></div></div>{adding && <form className="response-checklist-add-form" onSubmit={(event) => { event.preventDefault(); void addManual(); }}><input autoFocus value={draftTitle} onChange={(event) => setDraftTitle(event.target.value)} placeholder="조치 제목을 입력하세요"/><select value={draftCategory} onChange={(event) => setDraftCategory(event.target.value)}>{RESPONSE_CATEGORIES.map((category) => <option key={category}>{category}</option>)}</select><select value={draftPriority} onChange={(event) => setDraftPriority(responsePriority(event.target.value))}><option value="P0">P0 긴급</option><option value="P1">P1 높음</option><option value="P2">P2 일반</option></select><button type="submit" disabled={!draftTitle.trim() || adding}><Check size={13}/>추가</button></form>}{notice && <p className="ai-recommendation-note">{notice}</p>}{error && <DialogError message={error}/>}<div className="response-checklist-list">{view === 'category' ? grouped.map((group) => <section className="response-checklist-group" key={group.category}><h3>{group.category}<small>{group.items.length}개</small></h3>{group.items.map(renderItem)}</section>) : sorted.map(renderItem)}{!items.length && <p className="dialog-empty">등록된 대응 조치가 없습니다. 체크리스트를 직접 추가하거나 AI에게 추천받을 수 있습니다.</p>}</div></div><footer className="dialog-footer"><button type="button" className="secondary-action" onClick={onClose}>닫기</button></footer></DialogShell>;
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

export const QuestionDialog: React.FC<{ caseId: string; initial: QuestionCandidate[]; onDone: () => Promise<void>; onClose: () => void; inline?: boolean }> = ({ caseId, initial, onDone, onClose, inline = false }) => {
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
      const acceptedIds = new Set(next.items.map((item) => item.question_id));
      const accepted = additions.filter((item) => acceptedIds.has(item.question_id)).length;
      setAiNote(accepted > 0 ? `${accepted}개의 질문 초안을 현재 목록에 반영했습니다. 내용을 검토하고 수정·선택해 주세요.` : '현재 Case에서 새로 추천할 질문이 없습니다.');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'AI 질문 추천을 만들지 못했습니다.'); }
    finally { setRecommending(false); }
  };
  const chosen = useMemo(() => items.filter((item) => selected.includes(item.question_id)), [items, selected]);
  const submit = async () => {
    const selectedItems = itemsRef.current.filter((item) => selectedRef.current.includes(item.question_id));
    if (!selectedItems.length || saving) return;
    setSaving(true); setError('');
    try {
      const created = await casesApi.queueQuestions(caseId, selectedItems);
      if (created.length > 0) {
        await casesApi.sendReportCard(caseId, {
          card_type: 'CUSTOMER_QUESTION_DISPATCH',
          title: '고객 확인 질문 발송',
          created_at: new Date().toISOString(),
          external_send: true,
          items: created.map((item) => ({
            question_id: item.question_id,
            question_text: item.question_text,
            sequence: item.sequence,
            status: item.status,
            asked_at: item.asked_at,
          })),
        }, generateUuid(), 'CUSTOMER');
      }
      if (created.length === selectedItems.length) {
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
      if (created.length === 0) setError('새로 발송된 질문이 없습니다. 이미 등록·발송·답변되었거나 확인이 완료된 질문일 수 있습니다.');
      else setAiNote(`${selectedItems.length}개 중 ${created.length}개를 고객 질문으로 발송했습니다. 이미 처리된 질문은 제외되었습니다.`);
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : '질문을 고객에게 발송하지 못했습니다.'); }
    finally { setSaving(false); }
  };
  return <DialogShell title="고객에게 확인 질문" description="AI가 이미 확인한 내용을 제외하고 제안한 질문입니다. 필요한 항목만 선택해 고객에게 바로 발송하세요." onClose={onClose} inline={inline}>
    <div className="dialog-body">
      <div className="ai-dialog-action"><div><Sparkles size={16}/><span><b>AI 질문 추천</b><small>현재 Case의 대화·답변·확인 이력을 읽고 중복되지 않는 질문을 제안합니다.</small></span></div><button type="button" onClick={() => void recommendQuestions()} disabled={recommending || saving}>{recommending ? <Loader2 className="spin" size={15}/> : <Sparkles size={15}/>}AI에게 질문 추천 받기</button></div>
      {aiNote && <p className="ai-recommendation-note">{aiNote}</p>}
      {loading ? <div className="dialog-loading"><Loader2 className="spin" size={18}/>현재 Case에서 필요한 질문을 정리하고 있습니다.</div> : <div className="question-options">{items.length ? items.map((item) => <article className="question-option-card" key={item.question_id}><label><input type="checkbox" checked={selected.includes(item.question_id)} onChange={() => setSelected((current) => current.includes(item.question_id) ? current.filter((id) => id !== item.question_id) : [...current, item.question_id])}/><span>{editingId === item.question_id ? <input className="question-edit-input" value={editingText} autoFocus onChange={(event) => setEditingText(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); saveEditing(item.question_id); } if (event.key === 'Escape') { setEditingId(null); setEditingText(''); } }}/>: <b>{item.question_text}</b>}<small>{isDynamicQuestionDraft(item) && <strong className="ai-dynamic-question">AI 동적 추천</strong>}<em>{priorityLabel(item.priority)}</em>{item.reason}</small></span></label><div className="question-card-actions">{editingId === item.question_id ? <><button type="button" onClick={() => saveEditing(item.question_id)} disabled={!editingText.trim()} aria-label="질문 수정 저장"><Check size={14}/></button><button type="button" onClick={() => { setEditingId(null); setEditingText(''); }} aria-label="질문 수정 취소"><X size={14}/></button></> : <button type="button" onClick={() => startEditing(item)} aria-label="질문 편집"><Pencil size={14}/></button>}<button type="button" onClick={() => removeQuestion(item.question_id)} aria-label="질문 삭제"><Trash2 size={14}/></button></div></article>) : <p className="dialog-empty">추가로 추천할 질문이 없습니다. 필요한 질문을 직접 추가할 수 있습니다.</p>}</div>}
      <div className="inline-add"><input value={custom} onChange={(event) => setCustom(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); addCustom(); } }} placeholder="직접 질문 추가"/><button type="button" onClick={addCustom} disabled={!custom.trim()}><Plus size={15}/>추가</button></div>
      <DialogError message={error}/>
      <p className="dialog-queue-note">선택한 질문은 지금 고객 질문으로 발송됩니다. 고객에게는 한 번에 하나씩 표시되며, 나머지는 답변 대기열에서 순서대로 이어집니다.</p>
    </div>
    <footer className="dialog-footer"><button className="secondary-action" onClick={onClose}>취소</button><button className="primary-action" onClick={() => void submit()} disabled={saving || !chosen.length || loading || Boolean(editingId)}>{saving ? <Loader2 className="spin" size={15}/> : <Send size={15}/>} {saving ? '고객에게 발송 중' : `선택한 질문 ${chosen.length}개 고객에게 발송`}</button></footer>
  </DialogShell>;
};

type InstitutionMessageDraft = { id: string; institution: string; target: string; claim: string; message: string; reason_codes: string[]; selected: boolean };

const newInstitutionDraft = (): InstitutionMessageDraft => ({ id: generateUuid(), institution: '', target: '', claim: '', message: '', reason_codes: [], selected: true });
export const InstitutionVerificationBoardDialog: React.FC<{ caseId: string; verificationTasks?: VerificationTask[]; onDone: () => Promise<void>; onClose: () => void }> = ({ caseId, verificationTasks = [], onDone, onClose }) => {   const [rows, setRows] = useState<InstitutionMessageDraft[]>([newInstitutionDraft()]);   const [busy, setBusy] = useState(false);   const [recommendBusy, setRecommendBusy] = useState(false);   const [error, setError] = useState('');   const [notice, setNotice] = useState('');   const [historyOpen, setHistoryOpen] = useState(false);   const [historyTask, setHistoryTask] = useState<VerificationTask | null>(null);   const setRow = (id: string, key: keyof Pick<InstitutionMessageDraft, 'institution' | 'target' | 'claim' | 'message'>, value: string) => setRows((current) => current.map((row) => row.id === id ? { ...row, [key]: value } : row));   const selected = rows.filter((row) => row.selected && row.institution.trim() && row.target.trim() && row.claim.trim() && row.message.trim());   const recommendAll = async () => {     if (recommendBusy || busy) return;     setRecommendBusy(true); setError(''); setNotice('');     try {       const card = await casesApi.generateWorkCard(caseId, 'VERIFICATION_REQUEST');       const proposals = (card.verification_messages ?? []).map((item) => ({ id: generateUuid(), institution: item.institution?.trim() ?? '', target: item.target?.trim() ?? '', claim: item.claim?.trim() ?? '', message: item.message?.trim() ?? '', reason_codes: item.reason_codes ?? [], selected: true })).filter((item) => item.institution && item.target && item.claim && item.message).slice(0, 10);       if (!proposals.length) { setNotice('구조화된 분석에서 확인할 기관을 찾지 못했습니다. 행을 직접 추가해 주세요.'); return; }       setRows((current) => {         const keys = new Set(current.map((row) => `${row.institution.toLowerCase()}|${row.target.toLowerCase()}`));         const additions = proposals.filter((row) => !keys.has(`${row.institution.toLowerCase()}|${row.target.toLowerCase()}`));         const blank = current.findIndex((row) => !row.institution.trim() && !row.target.trim());         if (blank >= 0 && additions.length) { const [first, ...rest] = additions; return current.map((row, index) => index === blank ? first : row).concat(rest).slice(0, 10); }         return [...current, ...additions].slice(0, 10);       });       setNotice(`AI가 ${proposals.length}개 기관의 확인 메시지 초안을 채웠습니다. 직원이 검토·수정한 뒤 선택해 주세요.`);     } catch (reason) { setError(reason instanceof Error ? reason.message : 'AI 추천을 불러오지 못했습니다. 직접 입력할 수 있습니다.'); }     finally { setRecommendBusy(false); }   };   const submitBoard = async (event: FormEvent) => {     event.preventDefault(); if (busy) return; if (!selected.length) { setError('선택된 행을 완성해 주세요.'); return; }     setBusy(true); setError('');     let created = 0;     try {       for (const row of selected) { await casesApi.createVerification(caseId, row.claim.trim(), row.target.trim()); created += 1; }       await casesApi.sendReportCard(caseId, { card_type: 'VERIFICATION_DISPATCH', title: '기관 확인 요청 발송 시뮬레이션', created_at: new Date().toISOString(), external_send: false, items: selected.map((row) => ({ institution: row.institution.trim(), target: row.target.trim(), claim: row.claim.trim(), message: row.message.trim(), status: 'SIMULATED_SENT' })) });       await onDone(); onClose();     } catch (reason) { setError(`${created}개 행은 저장되었습니다. ${reason instanceof Error ? reason.message : '나머지 저장에 실패했습니다.'}`); }     finally { setBusy(false); }   };   return <DialogShell title="기관 확인 요청" description="게시판에서 기관별 확인 대상을 관리하고, 선택한 행을 발송 시뮬레이션으로 기록합니다." onClose={onClose}>     <form onSubmit={submitBoard}><div className={`dialog-body verification-board-body ${historyOpen ? 'is-history-mode' : ''}`}>       <div className="verification-board-toolbar"><div><b>기관 확인 리스트</b><small>총 {rows.length}개 · 선택 {selected.length}개</small></div><button type="button" className="verification-ai-button" onClick={() => void recommendAll()} disabled={recommendBusy || busy}>{recommendBusy ? <Loader2 className="spin" size={15}/> : <Sparkles size={15}/>}AI에게 추천받기</button></div>       <button type="button" className="verification-history-button verification-history-float" onClick={() => setHistoryOpen((value) => !value)}>{historyOpen ? '목록 닫기' : '기관 확인 내역'} <span>{verificationTasks.length}</span></button>       {historyOpen && <section className="verification-history-panel"><div className="verification-history-table-wrap"><table className="verification-history-table"><thead><tr><th>기관/대상</th><th>상태</th><th>최근 회신</th><th>일시</th></tr></thead><tbody>{verificationTasks.length ? verificationTasks.map((task) => <tr key={task.verification_task_id} className={historyTask?.verification_task_id === task.verification_task_id ? 'is-selected' : ''} onClick={() => setHistoryTask((current) => current?.verification_task_id === task.verification_task_id ? null : task)}><td><b>{task.target}</b><small>{task.claim}</small></td><td>{verificationStatusLabel(task.status)}</td><td>{task.result_summary || '회신 대기'}</td><td>{new Date(task.updated_at || task.created_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</td></tr>) : <tr><td colSpan={4}>등록된 기관 확인 내역이 없습니다.</td></tr>}</tbody></table></div>{historyTask && <div className="verification-history-detail"><b>상세 확인 정보</b><div className="verification-history-columns"><section className="verification-history-column"><dl><dt>발송 대상</dt><dd>{historyTask.target}</dd><dt>발송 내용</dt><dd>{historyTask.claim}</dd></dl></section><section className="verification-history-column"><dl><dt>근거·출처</dt><dd>{historyTask.evidence_url || historyTask.rag_source || '등록된 근거 없음'}</dd><dt>회신 내용</dt><dd>{historyTask.result_summary || '회신 없음'}</dd></dl></section></div></div>}</section>}       {notice && <p className="verification-board-notice">{notice}</p>}       <div className="verification-board-scroll"><table className="verification-board-table"><thead><tr><th scope="col">선택</th><th scope="col">기관명 · 확인 대상</th><th scope="col">확인 요청 메시지</th><th scope="col" aria-label="삭제"/></tr></thead><tbody>{rows.map((row, index) => <tr key={row.id}><td><input type="checkbox" checked={row.selected} onChange={(event) => setRows((current) => current.map((item) => item.id === row.id ? { ...item, selected: event.target.checked } : item))}/></td><td><div className="verification-board-stack"><input value={row.institution} onChange={(event) => setRow(row.id, 'institution', event.target.value)} placeholder={`기관 ${index + 1}`}/><input value={row.target} onChange={(event) => setRow(row.id, 'target', event.target.value)} placeholder="부서·직책·채널"/></div></td><td><textarea rows={3} value={row.message || row.claim} onChange={(event) => setRows((current) => current.map((item) => item.id === row.id ? { ...item, message: event.target.value, claim: event.target.value } : item))} placeholder="확인이 필요한 내용과 기관에 보낼 요청 문장을 작성해 주세요."/></td><td><button type="button" className="verification-board-delete" onClick={() => setRows((current) => current.length === 1 ? [newInstitutionDraft()] : current.filter((item) => item.id !== row.id))} aria-label={`기관 ${index + 1} 삭제`}><Trash2 size={15}/></button></td></tr>)}</tbody></table></div>       <DialogError message={error}/>     </div><footer className="dialog-footer"><button type="button" className="verification-board-add" onClick={() => setRows((current) => current.length >= 10 ? current : [...current, newInstitutionDraft()])}><Plus size={15}/>기관 행 추가</button><span className="dialog-footer-spacer"/><button type="button" className="secondary-action" onClick={onClose}>취소</button><button className="primary-action" disabled={busy || !selected.length}>{busy ? <Loader2 className="spin" size={15}/> : <Check size={15}/>}발송 시뮬레이션</button></footer></form>   </DialogShell>; };

/** Institution-by-institution verification request composer. No external send occurs. */
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
