import { useRef, useState } from 'react';
import { readJson, type CaseTask, type TaskSuggestion, type WorkspaceCase } from '../api/cases.ts';
import { createUuid } from '../shared/uuid.ts';

const statusLabels = { TODO: '진행 전', IN_PROGRESS: '진행 중', BLOCKED: '확인 대기', COMPLETED: '완료', CANCELLED: '취소' };
type Editor = { task: CaseTask | null; suggestion: TaskSuggestion | null; caseVersion: number };
export function TaskWorkspace({ currentCase, tasks, suggestions, onChanged }: {
  currentCase: WorkspaceCase; tasks: CaseTask[]; suggestions: TaskSuggestion[]; onChanged: () => Promise<void>;
}) {
  const [editor, setEditor] = useState<Editor | null>(null);
  const [title, setTitle] = useState('');
  const [status, setStatus] = useState<CaseTask['status']>('TODO');
  const [result, setResult] = useState('');
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const requestId = useRef('');
  const open = (task: CaseTask | null = null, suggestion: TaskSuggestion | null = null) => {
    requestId.current = createUuid(); setError(''); setEditor({ task, suggestion, caseVersion: currentCase.version });
    setTitle(task?.title ?? (typeof suggestion?.proposal.title === 'string' ? suggestion.proposal.title : ''));
    setStatus(task?.status ?? 'TODO'); setResult(task?.result ?? ''); setReason(task?.cancel_reason ?? '');
  };
  const send = async (path: string, body: unknown) => {
    setBusy(true); setError('');
    try { await readJson(path, undefined, body); await onChanged(); setEditor(null); }
    catch (failure) { setError(failure instanceof Error && ['CASE_VERSION_CONFLICT', 'SUGGESTION_STALE'].includes(failure.message) ? '사건이나 제안이 변경되었습니다. 초안을 확인하고 최신 내용을 다시 열어 주세요.' : '업무 기록을 저장하지 못했습니다. 입력 내용은 유지됩니다.'); }
    finally { setBusy(false); }
  };
  const submit = (event: React.FormEvent) => {
    event.preventDefault(); if (!editor || busy) return;
    const common = { client_request_id: requestId.current, expected_case_version: editor.caseVersion };
    if (editor.suggestion) void send(`/api/v4/cases/${currentCase.id}/suggestions/${editor.suggestion.id}/decision`, {
      ...common, expected_version: editor.suggestion.version, decision: title === editor.suggestion.proposal.title ? 'ACCEPT' : 'EDIT',
      ...(title === editor.suggestion.proposal.title ? {} : { title }),
    });
    else void send(`/api/v4/cases/${currentCase.id}/tasks${editor.task ? `/${editor.task.id}` : ''}`, {
      ...common, title, ...(editor.task ? { expected_version: editor.task.version, status, result: result || null, cancel_reason: reason || null } : {}),
    });
  };
  return <section className="task-workspace" aria-label="대응 업무">
    <div className="panel-heading"><h3>대응 업무</h3><button disabled={busy} onClick={() => open()}>업무 추가</button></div>
    <p className="composer-hint">업무 기록입니다. 실제 금융 조치나 고객 진행 상태가 자동으로 변경되지는 않습니다.</p>
    {!tasks.length && <p className="state">등록된 업무가 없습니다.</p>}
    {tasks.map(task => <article className="task-block" key={task.id} data-task-id={task.id}>
      <strong>{task.title}</strong><span>{statusLabels[task.status]}</span>
      {task.result && <p>결과: {task.result}</p>}{task.cancel_reason && <p>취소 사유: {task.cancel_reason}</p>}
      <button disabled={busy} onClick={() => open(task)}>업무 수정</button>
    </article>)}
    {suggestions.map(suggestion => <article className="task-block" key={suggestion.id}>
      <h3>대응 제안</h3><p>{typeof suggestion.proposal.title === 'string' ? suggestion.proposal.title : '제안 내용을 확인해 주세요.'}</p>
      {suggestion.status === 'PENDING' ? <>
        {suggestion.source_revision !== currentCase.revision && <p>사건이 변경되어 최신 검토가 필요합니다.</p>}
        <button disabled={busy || suggestion.source_revision !== currentCase.revision} onClick={() => open(null, suggestion)}>검토 및 채택</button>
        <button disabled={busy} onClick={() => void send(`/api/v4/cases/${currentCase.id}/suggestions/${suggestion.id}/decision`, {
          client_request_id: createUuid(), expected_case_version: currentCase.version, expected_version: suggestion.version, decision: 'REJECT',
        })}>거절</button>
      </> : <p>{suggestion.status === 'REJECTED' ? '거절한 제안입니다.' : suggestion.status === 'STALE' ? '최신 검토가 필요한 제안입니다.' : '업무에 반영한 제안입니다.'}</p>}
    </article>)}
    <button disabled title="AI 제안 생성 연결 준비 중">AI에게 업무 추천 받기</button>
    {error && <p role="alert" className="error">{error}</p>}
    {editor && <div className="modal-backdrop"><form className="utility-dialog" role="dialog" aria-modal="true" aria-label={editor.suggestion ? '제안 검토' : '업무 기록'} onSubmit={submit}>
      <h2>{editor.suggestion ? '제안 검토 후 업무로 저장' : '업무 기록'}</h2>
      <label>업무 제목<input autoFocus aria-label="업무 제목" required maxLength={300} value={title} onChange={e => setTitle(e.target.value)} /></label>
      {editor.task && <>
        <label>업무 상태<select aria-label="업무 상태" value={status} onChange={e => setStatus(e.target.value as CaseTask['status'])}>{Object.entries(statusLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        <label>처리 결과<textarea aria-label="처리 결과" required={status === 'COMPLETED'} maxLength={4000} value={result} onChange={e => setResult(e.target.value)} /></label>
        <label>취소 사유<textarea aria-label="취소 사유" required={status === 'CANCELLED'} maxLength={4000} value={reason} onChange={e => setReason(e.target.value)} /></label>
      </>}
      {error && <p role="alert" className="error">{error}</p>}
      <div className="dialog-actions"><button type="button" disabled={busy} onClick={() => setEditor(null)}>닫기</button><button disabled={busy}>저장</button></div>
    </form></div>}
  </section>;
}
