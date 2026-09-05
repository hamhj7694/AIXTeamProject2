import React, { useState } from 'react';
import { casesApi, CURRENT_BANK_USER } from '../api/cases';
import type { CustomerProgressItem, ProgressStatus, UpdateCustomerProgress } from '../api/types';

const statuses: Record<ProgressStatus, string> = {
  UNKNOWN: '확인되지 않음', IN_PROGRESS: '담당자 확인·처리 중',
  SUBMITTED: '제출 확인 · 접수 결과 대기', COMPLETED: '담당자 완료 확인', NOT_APPLICABLE: '해당 없음',
};

export const CustomerProgressEditor: React.FC<{
  caseId: string; items: CustomerProgressItem[];
  onSaved: (items: CustomerProgressItem[]) => void;
}> = ({ caseId, items, onSaved }) => {
  const [editing, setEditing] = useState<CustomerProgressItem | null>(null);
  const [draft, setDraft] = useState<UpdateCustomerProgress | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const edit = (item: CustomerProgressItem) => {
    setEditing(item); setError('');
    setDraft({ expected_revision: item.revision, status: item.status,
      summary: item.revision ? item.summary : '', next_action: item.next_action, reference: item.reference,
      confirmed_at: item.confirmed_at, updated_by: CURRENT_BANK_USER.display_name });
  };
  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!editing || !draft || busy) return;
    setBusy(true); setError('');
    try {
      const updated = await casesApi.updateCustomerProgress(caseId, editing.step, draft);
      onSaved(updated); setEditing(null); setDraft(null);
    } catch (reason) { setError(reason instanceof Error ? reason.message : '처리 결과를 저장하지 못했습니다.'); }
    finally { setBusy(false); }
  };
  return <section className="context-section public-progress-editor">
    <h3>고객에게 공유할 처리 결과</h3>
    <p className="context-section-description">실제 확인한 결과와 고객이 할 일을 기록하세요. 저장하면 고객 화면과 AI 상담에 반영됩니다.</p>
    <div className="public-progress-list">{items.map((item) => <article key={item.step}>
      <header><strong>{item.label}</strong><button type="button" disabled={busy} onClick={() => edit(item)}>결과 기록</button></header>
      <b>{item.status_label}</b><p>{item.summary}</p>
      {item.confirmation_requested && <p className="progress-next">고객 확인 요청 · 회신이 필요합니다.</p>}
    </article>)}</div>
    {editing && draft && <form className="form-grid progress-edit-form" onSubmit={(event) => void save(event)}>
      <h4>{editing.label} 결과 기록</h4>
      <label>진행 상태<select value={draft.status} disabled={busy} onChange={(e) => setDraft({ ...draft, status: e.target.value as ProgressStatus })}>{Object.entries(statuses).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label>고객에게 공개할 결과<textarea required maxLength={1000} disabled={busy} value={draft.summary} onChange={(e) => setDraft({ ...draft, summary: e.target.value })}/></label>
      <label>고객이 지금 할 일<textarea maxLength={500} disabled={busy} value={draft.next_action} onChange={(e) => setDraft({ ...draft, next_action: e.target.value })}/></label>
      <label>확인 근거 또는 접수번호<input maxLength={300} required={['SUBMITTED', 'COMPLETED'].includes(draft.status)} disabled={busy} value={draft.reference} onChange={(e) => setDraft({ ...draft, reference: e.target.value })}/></label>
      <label>확인 시각<input type="datetime-local" required={['SUBMITTED', 'COMPLETED'].includes(draft.status)} disabled={busy}
        value={draft.confirmed_at ? new Date(new Date(draft.confirmed_at).getTime() - new Date(draft.confirmed_at).getTimezoneOffset() * 60000).toISOString().slice(0, 16) : ''}
        onChange={(e) => setDraft({ ...draft, confirmed_at: e.target.value ? new Date(e.target.value).toISOString() : null })}/></label>
      <p>입력한 내용은 고객에게 공개됩니다. 접수 확인은 환급 완료를 뜻하지 않습니다.</p>
      {error && <p role="alert" className="progress-error">{error}</p>}
      <div><button type="button" className="secondary-action" disabled={busy} onClick={() => { setEditing(null); setDraft(null); }}>취소</button> <button className="primary-action" disabled={busy}>{busy ? '저장 중…' : '결과 저장·고객 공유'}</button></div>
    </form>}
  </section>;
};
