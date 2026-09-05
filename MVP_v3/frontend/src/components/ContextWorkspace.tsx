import React, { useEffect, useRef, useState } from 'react';
import { Check, Pencil, Plus, X } from 'lucide-react';
import { loadContextWorkspace, saveContextCommand, type ContextWorkspaceData, type ContextTask } from '../api/contextWorkspace';
import { userText } from '../userText';

type Edit = { key: string; heading: string; path: string; method: string; body: Record<string, unknown>; titleField?: string; textField: string; title: string; text: string; maxText?: number };
const states: Record<string, string> = { OPEN: '확인 필요', AWAITING_CUSTOMER: '고객 답변 대기', AWAITING_INSTITUTION: '기관 회신 대기', STAFF_REVIEW_REQUIRED: '답변 검토 필요', TODO: '진행 예정', IN_PROGRESS: '진행 중', BLOCKED: '보류', COMPLETED: '완료', CANCELLED: '취소', ACCEPTED: '업무로 채택', DISMISSED: '제외', EXPIRED: '기간 만료', SUPERSEDED: '새 기록으로 대체', RESOLVED: '확인됨' };
const time = (value?: string | null) => value ? new Date(value).toLocaleString('ko-KR') : '';
const Empty = () => <p className="context-empty">등록된 항목이 없습니다.</p>;

export const ContextWorkspace: React.FC<{ caseId: string; refreshKey: string; institutions: React.ReactNode; onOpenParticipants: () => void }> = ({ caseId, refreshKey, institutions, onOpenParticipants }) => {
  const [data, setData] = useState<ContextWorkspaceData | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [edit, setEdit] = useState<Edit | null>(null);
  const serial = useRef(0);
  const alive = useRef(true);
  const saving = useRef(false);
  const reload = async () => {
    const id = ++serial.current;
    try { const value = await loadContextWorkspace(caseId); if (alive.current && id === serial.current) { setData(value); setError(''); } }
    catch (e) { if (alive.current && id === serial.current) setError(e instanceof Error ? e.message : '사건 맥락을 불러오지 못했습니다.'); }
  };
  useEffect(() => { alive.current = true; return () => { alive.current = false; ++serial.current; }; }, []);
  useEffect(() => { if (!saving.current) void reload(); }, [caseId, refreshKey]);
  const execute = async (command: Edit) => {
    if (saving.current) return;
    saving.current = true; ++serial.current; setBusy(true); setError('');
    try {
      await saveContextCommand(caseId, command.path, command.method, { ...command.body, ...(command.titleField ? { [command.titleField]: command.title.trim() } : {}), [command.textField]: command.text.trim() });
      if (alive.current) { setEdit(null); await reload(); }
    } catch (e) {
      // Keep the draft and its original expected_version on conflict.
      if (alive.current) { await reload(); setError(e instanceof Error ? e.message : '저장하지 못했습니다.'); }
    } finally { saving.current = false; if (alive.current) setBusy(false); }
  };
  const start = (command: Edit) => { setEdit(command); setError(''); };
  const form = (key: string) => edit?.key === key && <form className="context-command-form" onSubmit={(e) => { e.preventDefault(); void execute(edit); }}>
    <strong>{edit.heading}</strong>
    {edit.titleField && <label>제목<input autoFocus maxLength={300} value={edit.title} disabled={busy} onChange={(e) => setEdit({ ...edit, title: e.target.value })}/></label>}
    <label>{edit.textField === 'reason' ? '처리 사유' : edit.textField === 'result_summary' ? '확인한 처리 결과' : '내용·판단 근거'}<textarea autoFocus={!edit.titleField} rows={3} maxLength={edit.maxText ?? 3000} value={edit.text} disabled={busy} onChange={(e) => setEdit({ ...edit, text: e.target.value })}/></label>
    <div><button type="button" disabled={busy} onClick={() => setEdit(null)}>닫기</button><button type="submit" disabled={busy || !edit.text.trim() || Boolean(edit.titleField && !edit.title.trim())}><Check size={13}/>저장</button></div>
  </form>;
  const noteCommand = (key: string, heading: string, path: string, body: Record<string, unknown>, method = 'PATCH', textField = 'reason', text = ''): Edit => ({ key, heading, path, body, method, textField, text, title: '', maxText: textField === 'reason' ? 1000 : 3000 });
  const titleCommand = (key: string, heading: string, path: string, body: Record<string, unknown>, title = '', text = '', method = 'POST', titleField = 'title', textField = 'description'): Edit => ({ key, heading, path, body, title, text, method, titleField, textField });
  const addTask = () => start(titleCommand('task-new', '담당자 업무 추가', 'tasks', { client_request_id: crypto.randomUUID(), task_type: 'OTHER', priority: 'NORMAL' }));
  const task = (item: ContextTask, archived = false) => <article className="context-resource" key={item.task_id}><header><b>{userText(item.title)}</b><small>{states[item.status] ?? '확인 필요'}</small></header><p>{userText(item.description)}</p>{item.result_summary && <p>처리 결과: {userText(item.result_summary)}</p>}{item.cancellation_reason && <p>취소 사유: {userText(item.cancellation_reason)}</p>}
    {!archived && <div className="context-resource-actions">
      <button disabled={busy || !data?.can_write} onClick={() => start(titleCommand(item.task_id, '업무 수정', `tasks/${item.task_id}`, { expected_version: item.version }, item.title, item.description, 'PATCH'))}><Pencil size={13}/>수정</button>
      <button disabled={busy || !data?.can_write} onClick={() => start(noteCommand(item.task_id, item.status === 'IN_PROGRESS' ? '업무 보류' : '업무 시작', `tasks/${item.task_id}`, { expected_version: item.version, status: item.status === 'IN_PROGRESS' ? 'BLOCKED' : 'IN_PROGRESS' }, 'PATCH', 'description', item.description))}>{item.status === 'IN_PROGRESS' ? '보류' : '시작'}</button>
      <button disabled={busy || !data?.can_review} onClick={() => start(noteCommand(item.task_id, '업무 완료 결과 기록', `tasks/${item.task_id}/complete`, { expected_version: item.version }, 'POST', 'result_summary'))}><Check size={13}/>결과 기록</button>
      <button disabled={busy || !data?.can_review} onClick={() => start(noteCommand(item.task_id, '업무 취소', `tasks/${item.task_id}/cancel`, { expected_version: item.version }, 'POST'))}><X size={13}/>취소</button>
    </div>}{archived && <button disabled={busy || !data?.can_write} onClick={() => start(noteCommand(item.task_id, '업무 다시 진행', `tasks/${item.task_id}`, { expected_version: item.version, status: 'TODO' }, 'PATCH', 'description', item.description))}>다시 진행</button>}{form(item.task_id)}</article>;
  const suggestion = (id: string, title: string, description: string, version: number, legacy = false) => <article className="context-resource ai" key={id}><b>{userText(title)}</b><p>{userText(description)}</p><div className="context-resource-actions">
    <button disabled={busy || !data?.can_review} onClick={() => start(titleCommand(id, '내용 검토 후 업무로 채택', `${legacy ? 'legacy-suggestions' : 'suggestions'}/${id}/review`, { expected_version: version, decision: 'ACCEPT' }, title, description, legacy ? 'POST' : 'PATCH', 'edited_title', 'edited_description'))}><Check size={13}/><Pencil size={13}/>수정·채택</button>
    <button disabled={busy || !data?.can_review} onClick={() => start(noteCommand(id, '제안 제외', `${legacy ? 'legacy-suggestions' : 'suggestions'}/${id}/review`, { expected_version: version, decision: 'DISMISS' }, legacy ? 'POST' : 'PATCH'))}><X size={13}/>제외</button>
    </div>{form(id)}</article>;
  return <>
    {error && <div className="context-edit-error" role="alert">{error} <button type="button" disabled={busy} onClick={() => void reload()}>다시 불러오기</button></div>}
    {!data ? <p className="context-empty">사실·업무 기록을 불러오는 중입니다.</p> : <>
      {!data.can_review && <div className="permission-notice"><strong>검토 권한이 필요합니다</strong><p>사실 확정·제안 채택·업무 완료는 메인 담당자 또는 검토자가 처리할 수 있습니다.</p><button className="secondary-action" type="button" onClick={onOpenParticipants}>참여자 관리에서 내 역할 설정</button></div>}
      <section className="context-section"><h3>사실 현황</h3><h4>확인된 사실</h4>
        {!data.confirmed_facts.length && !data.legacy_facts.some(f => f.status === 'CONFIRMED') && <Empty/>}
        {data.confirmed_facts.map(f => <article className="context-resource" key={f.fact_id}><b>{userText(f.display_label)}</b><p>{userText(f.display_value)}</p><small>담당자 확인 · {time(f.confirmed_at)}</small></article>)}
        {data.legacy_facts.filter(f => f.status === 'CONFIRMED').map(f => <article className="context-resource" key={f.id}><b>{userText(f.title)}</b><p>{userText(f.value || '')}</p><small>기존 확정 기록 {time(f.confirmed_at)}</small></article>)}
        <h4>검토 대기 사실</h4>{!data.proposed_facts.length && !data.legacy_facts.some(f => f.status !== 'CONFIRMED') && <Empty/>}
        {data.proposed_facts.map(f => <article className="context-resource" key={f.fact_id}><b>{userText(f.display_label)}</b><p>{userText(f.display_value)}</p><small>확인 전 정보</small><div className="context-resource-actions"><button disabled={busy || !data.can_review} onClick={() => start(noteCommand(f.fact_id, '사실 확정 근거', `facts/${f.fact_id}/review`, { expected_version: f.version, decision: 'CONFIRM' }))}><Check size={13}/>확정</button><button disabled={busy || !data.can_review} onClick={() => start(noteCommand(f.fact_id, '사실 후보 거절 사유', `facts/${f.fact_id}/review`, { expected_version: f.version, decision: 'REJECT' }))}><X size={13}/>거절</button></div>{form(f.fact_id)}</article>)}
        {data.legacy_facts.filter(f => f.status !== 'CONFIRMED').map(f => <article className="context-resource" key={f.id}><b>{userText(f.title)}</b><p>{userText(f.value || '')}</p><small>기존 고객 진술 · 검토 대기</small></article>)}
<button className="secondary-action" disabled={busy || !data.can_write} onClick={() => start(titleCommand('fact-new', '사실 후보 추가', 'facts', { client_request_id: crypto.randomUUID(), semantic_key: `staff.observation.${crypto.randomUUID().replace(/-/g, '')}`, value: {} }, '', '', 'POST', 'display_label', 'display_value'))}><Plus size={13}/>사실 후보 추가</button>{form('fact-new')}
      </section>
      <section className="context-section"><h3>미확인 핵심 사항</h3><p className="context-section-description">아직 모르는 정보입니다. 답변 접수와 사실 확정을 구분합니다.</p>
        {!data.open_gaps.length && !data.legacy_gaps.length && <Empty/>}
        {data.open_gaps.map(g => <article className="context-resource" key={g.gap_id}><header><b>{userText(g.title)}</b><small>{states[g.status]}</small></header><p>{userText(g.reason)}</p><div className="context-resource-actions">{data.confirmed_facts.filter(f => f.semantic_key === g.semantic_key).map(f => <button key={f.fact_id} disabled={busy || !data.can_write} onClick={() => start(noteCommand(g.gap_id, `확정 사실 연결: ${userText(f.display_value)}`, `gaps/${g.gap_id}`, { expected_version: g.version, status: 'RESOLVED', resolution_fact_id: f.fact_id }))}>확정 사실 연결</button>)}<button disabled={busy || !data.can_write} onClick={() => start(noteCommand(g.gap_id, '확인 항목 제외', `gaps/${g.gap_id}`, { expected_version: g.version, status: 'DISMISSED' }))}><X size={13}/>제외</button></div>{form(g.gap_id)}</article>)}
        {data.legacy_gaps.map(g => <article className="context-resource" key={g.id}><b>{userText(g.title)}</b><small>{states[g.status]}</small></article>)}
        <details className="completed-checklist"><summary>확인·제외 이력 {data.archived_gaps.length}건</summary>{data.archived_gaps.map(g => <p key={g.gap_id}>{userText(g.title)} · {states[g.status]}</p>)}</details>
      </section>
      <section className="context-section"><h3>AI 업무 제안함</h3><p className="context-section-description">검토 후 채택하면 담당자 업무가 생성됩니다. 고객 발송이나 실제 조치 실행은 별도입니다.</p>
        {!data.ai_suggestions.length && !data.legacy_suggestions.length && <Empty/>}
        {data.ai_suggestions.map(s => suggestion(s.suggestion_id, s.title, s.rationale, s.version))}
        {data.legacy_suggestions.map(s => suggestion(s.id, s.title, '기존 AI 확인 항목입니다. 내용을 검토하고 필요한 업무만 채택하세요.', 1, true))}
        {data.legacy_archived_suggestions.length > 0 && <details className="completed-checklist"><summary>기존 완료·제외 항목 {data.legacy_archived_suggestions.length}건</summary>{data.legacy_archived_suggestions.map(s => <article className="context-resource" key={s.id}><b>{userText(s.title)}</b><small>기존 체크 상태 · {states[s.status]}</small></article>)}</details>}
        <details className="completed-checklist"><summary>채택·제외 이력 {data.reviewed_suggestions.length}건</summary>{data.reviewed_suggestions.map(s => <article className="context-resource" key={s.suggestion_id}><b>{userText(s.title)}</b><p>{states[s.status] ?? '검토 완료'}</p>{s.dismissal_reason && <p>{userText(s.dismissal_reason)}</p>}</article>)}</details>
      </section>
      <section className="context-section"><h3>담당자 업무</h3><p className="context-section-description">직원이 수행하기로 정한 업무입니다. 완료 시 처리 결과를 기록하며 고객 진행 상황은 별도로 공개합니다.</p><button className="secondary-action" disabled={busy || !data.can_write} onClick={addTask}><Plus size={13}/>업무 추가</button>{form('task-new')}<h4>진행 중</h4>{data.active_tasks.length ? data.active_tasks.map(t => task(t)) : <Empty/>}<details className="completed-checklist"><summary>완료·취소 {data.archived_tasks.length}건</summary>{data.archived_tasks.map(t => task(t, true))}</details></section>
      {institutions}
      <section className="context-section"><h3>판단·결정 기록</h3><p className="context-section-description">판단한 이유를 남깁니다. 정정할 때도 원래 기록은 보존됩니다.</p><button className="secondary-action" disabled={busy || !data.can_review} onClick={() => start(titleCommand('decision-new', '판단·결정 추가', 'decisions', { client_request_id: crypto.randomUUID(), decision_type: 'OTHER', related_entity_type: 'CASE', related_entity_id: caseId }, '', '', 'POST', 'title', 'rationale'))}><Plus size={13}/>기록 추가</button>{form('decision-new')}
        {data.recent_decisions.length ? data.recent_decisions.map(d => <article className="context-resource" key={d.decision_id}><b>{userText(d.title)}</b><p>{userText(d.rationale)}</p><small>{time(d.created_at)}{d.supersedes_decision_id ? ' · 정정 기록' : ''}</small><button disabled={busy || !data.can_review} onClick={() => start(titleCommand(d.decision_id, '판단 기록 정정', 'decisions', { client_request_id: crypto.randomUUID(), decision_type: 'OTHER', related_entity_type: 'CASE', related_entity_id: caseId, supersedes_decision_id: d.decision_id }, d.title, d.rationale, 'POST', 'title', 'rationale'))}><Pencil size={13}/>정정</button>{form(d.decision_id)}</article>) : <Empty/>}
        {data.legacy_records.length > 0 && <details className="completed-checklist"><summary>기존 판단·조치 기록 {data.legacy_records.length}건</summary><p className="context-note">업무와 판단이 섞여 있던 기록입니다. 새 업무나 결정으로 자동 분류하지 않았습니다.</p>{data.legacy_records.map(r => <article className="context-resource" key={r.id}><p>{userText(r.title)}</p><small>기존 기록 · {states[r.status] ?? '검토 필요'}</small></article>)}</details>}
      </section>
    </>}
  </>;
};
