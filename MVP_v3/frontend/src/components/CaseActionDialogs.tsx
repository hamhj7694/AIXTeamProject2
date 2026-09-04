import React, { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, Check, Loader2, Plus, X } from 'lucide-react';
import { casesApi } from '../api/cases';
import type { QuestionCandidate, VerificationTask } from '../api/types';
import { actionLabel } from '../presentation';

const DialogShell: React.FC<{ title: string; description: string; children: React.ReactNode; onClose: () => void }> = ({ title, description, children, onClose }) => {
  const dialogRef = useRef<HTMLElement>(null);
  useEffect(() => {
    dialogRef.current?.focus();
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  return <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) onClose(); }}><section ref={dialogRef} tabIndex={-1} className="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title"><header><div><h2 id="dialog-title">{title}</h2><p>{description}</p></div><button className="icon-button" onClick={onClose} aria-label="창 닫기"><X size={18}/></button></header>{children}</section></div>;
};

const DialogError = ({ message }: { message: string }) => message ? <p className="dialog-error"><AlertCircle size={15}/>{message}</p> : null;

export const QuestionDialog: React.FC<{ caseId: string; initial: QuestionCandidate[]; onDone: () => Promise<void>; onClose: () => void }> = ({ caseId, initial, onDone, onClose }) => {
  const [items, setItems] = useState<QuestionCandidate[]>(initial);
  const [selected, setSelected] = useState<string[]>(initial.filter((item) => item.priority === 'P0').map((item) => item.question_id));
  const [custom, setCustom] = useState('');
  const [loading, setLoading] = useState(initial.length === 0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    if (initial.length) return;
    let active = true;
    casesApi.questionCandidates(caseId).then((next) => { if (active) { setItems(next); setSelected(next.filter((item) => item.priority === 'P0').map((item) => item.question_id)); } }).catch((reason) => active && setError(reason instanceof Error ? reason.message : '질문 후보를 불러오지 못했습니다.')).finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [caseId, initial.length]);
  const addCustom = () => {
    const value = custom.trim(); if (!value) return;
    const id = `staff-${crypto.randomUUID()}`;
    setItems((current) => [...current, { question_id: id, target_field: id, question_text: value, reason: '은행 담당자가 현재 Case 맥락에 따라 직접 추가했습니다.', priority: 'P1', options: [], answer_mode: 'TEXT', allow_free_text: true }]);
    setSelected((current) => [...current, id]); setCustom('');
  };
  const chosen = useMemo(() => items.filter((item) => selected.includes(item.question_id)), [items, selected]);
  const submit = async () => {
    if (!chosen.length || saving) return;
    setSaving(true); setError('');
    try { await casesApi.queueQuestions(caseId, chosen); await onDone(); onClose(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '질문을 고객 대기열에 등록하지 못했습니다.'); }
    finally { setSaving(false); }
  };
  return <DialogShell title="고객에게 확인할 질문" description="AI가 이미 확인한 내용을 제외하고 제안한 질문입니다. 필요한 항목만 선택하세요." onClose={onClose}>
    <div className="dialog-body">
      {loading ? <div className="dialog-loading"><Loader2 className="spin" size={18}/>현재 Case에서 필요한 질문을 정리하고 있습니다.</div> : <div className="question-options">{items.length ? items.map((item) => <label key={item.question_id}><input type="checkbox" checked={selected.includes(item.question_id)} onChange={() => setSelected((current) => current.includes(item.question_id) ? current.filter((id) => id !== item.question_id) : [...current, item.question_id])}/><span><b>{item.question_text}</b><small><em>{item.priority}</em>{item.reason}</small></span></label>) : <p className="dialog-empty">추가로 추천할 질문이 없습니다. 필요한 질문을 직접 추가할 수 있습니다.</p>}</div>}
      <div className="inline-add"><input value={custom} onChange={(event) => setCustom(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); addCustom(); } }} placeholder="직접 질문 추가"/><button type="button" onClick={addCustom} disabled={!custom.trim()}><Plus size={15}/>추가</button></div>
      <DialogError message={error}/>
    </div>
    <footer className="dialog-footer"><button className="secondary-action" onClick={onClose}>취소</button><button className="primary-action" onClick={() => void submit()} disabled={!chosen.length || saving}>{saving ? <Loader2 className="spin" size={15}/> : <Check size={15}/>}선택한 질문 {chosen.length}개 전달</button></footer>
  </DialogShell>;
};

export const VerificationDialog: React.FC<{ caseId: string; task?: VerificationTask | null; onDone: () => Promise<void>; onClose: () => void }> = ({ caseId, task, onDone, onClose }) => {
  const [claim, setClaim] = useState(task?.claim ?? '');
  const [target, setTarget] = useState(task?.target ?? '');
  const [status, setStatus] = useState(task?.status ?? 'PENDING');
  const [result, setResult] = useState(task?.result_summary ?? '');
  const [evidence, setEvidence] = useState(task?.evidence_url ?? '');
  const [source, setSource] = useState(task?.rag_source ?? '');
  const [customerVisible, setCustomerVisible] = useState(task?.customer_visible ?? false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const submit = async (event: FormEvent) => {
    event.preventDefault(); if (saving) return; setSaving(true); setError('');
    try {
      if (task) await casesApi.updateVerification(caseId, task, { status, result_summary: result || null, evidence_url: evidence || null, rag_source: source || null, verified_by: '은행 담당자', customer_visible: customerVisible });
      else await casesApi.createVerification(caseId, claim.trim(), target.trim());
      await onDone(); onClose();
    } catch (reason) { setError(reason instanceof Error ? reason.message : '기관 확인 업무를 저장하지 못했습니다.'); }
    finally { setSaving(false); }
  };
  return <DialogShell title={task ? '기관 확인 결과' : '기관 확인 요청'} description="외부 기관에 자동 전송되지 않습니다. 공식 채널로 확인할 업무와 결과를 Shared Case에 기록합니다." onClose={onClose}>
    <form onSubmit={submit}><div className="dialog-body form-grid">
      {!task && <><label>확인할 주장<textarea value={claim} onChange={(event) => setClaim(event.target.value)} rows={3} placeholder="예: 검찰이 안전계좌 이체를 요구했다" required/></label><label>확인 대상<input value={target} onChange={(event) => setTarget(event.target.value)} placeholder="기관명, 전화번호, 계좌번호 등" required/></label></>}
      {task && <><div className="read-only-summary"><span>확인 대상</span><b>{task.target}</b><p>{task.claim}</p></div><label>확인 상태<select value={status} onChange={(event) => setStatus(event.target.value)}><option value="PENDING">확인 대기</option><option value="IN_PROGRESS">확인 중</option><option value="COMPLETED">확인 완료</option><option value="ON_HOLD">보류</option><option value="FAILED">확인 불가</option></select></label><label>확인 결과<textarea value={result} onChange={(event) => setResult(event.target.value)} rows={3} placeholder="공식 채널에서 확인한 결과를 적어주세요."/></label><label>근거 URL<input value={evidence} onChange={(event) => setEvidence(event.target.value)} placeholder="https://..."/></label><label>공식 자료 출처<input value={source} onChange={(event) => setSource(event.target.value)} placeholder="기관 공식 홈페이지 또는 문서명"/></label><label className="check-row"><input type="checkbox" checked={customerVisible} onChange={(event) => setCustomerVisible(event.target.checked)}/>완료 결과를 고객에게 공개할 수 있음</label></>}
      <DialogError message={error}/>
    </div><footer className="dialog-footer"><button type="button" className="secondary-action" onClick={onClose}>취소</button><button className="primary-action" disabled={saving || (!task && (!claim.trim() || !target.trim()))}>{saving ? <Loader2 className="spin" size={15}/> : <Check size={15}/>}저장</button></footer></form>
  </DialogShell>;
};

const actionTypes = ['PAYMENT_HOLD_REVIEW', 'ACCOUNT_REPORT_GUIDANCE', 'EVIDENCE_PRESERVATION', 'DEVICE_SECURITY_GUIDANCE', 'CUSTOMER_CALLBACK', 'OTHER'];

export const ActionDialog: React.FC<{ caseId: string; recovery: boolean; onDone: () => Promise<void>; onClose: () => void }> = ({ caseId, recovery, onDone, onClose }) => {
  const [type, setType] = useState(recovery ? 'PAYMENT_HOLD_REVIEW' : 'CUSTOMER_CALLBACK');
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const submit = async (event: FormEvent) => {
    event.preventDefault(); if (!note.trim() || saving) return; setSaving(true); setError('');
    try { await casesApi.createAction(caseId, type, note.trim()); await onDone(); onClose(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : '대응 업무를 기록하지 못했습니다.'); }
    finally { setSaving(false); }
  };
  return <DialogShell title="대응 업무 기록" description="권장 조치를 검토한 뒤 담당자가 수행하거나 확인할 업무를 기록합니다." onClose={onClose}>
    <form onSubmit={submit}><div className="dialog-body form-grid"><label>업무 유형<select value={type} onChange={(event) => setType(event.target.value)}>{actionTypes.map((value) => <option key={value} value={value}>{actionLabel(value)}</option>)}</select></label><label>업무 내용<textarea value={note} onChange={(event) => setNote(event.target.value)} rows={4} placeholder="확인 대상, 수행할 조치, 인수인계할 내용을 구체적으로 적어주세요." required/></label><p className="safety-notice">이 기록은 실제 지급정지나 신고를 자동 실행하지 않습니다. 은행 권한과 공식 승인 절차를 별도로 진행해야 합니다.</p><DialogError message={error}/></div><footer className="dialog-footer"><button type="button" className="secondary-action" onClick={onClose}>취소</button><button className="primary-action" disabled={saving || !note.trim()}>{saving ? <Loader2 className="spin" size={15}/> : <Check size={15}/>}업무 기록</button></footer></form>
  </DialogShell>;
};
