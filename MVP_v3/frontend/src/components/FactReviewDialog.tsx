import React, { useEffect, useState } from 'react';
import { AlertCircle, Check, Loader2, Plus, X } from 'lucide-react';
import { createContextFact, reviewContextFact } from '../context-v3/api';
import { loadContextWorkspace, type ContextFact, type ContextWorkspaceData } from '../api/contextWorkspace';
import { generateUuid } from '../uuid';
import { formatClock } from '../presentation';

const manualFields = [
  { key: 'transfer.actual.status', label: '실제 이체 여부' },
  { key: 'offender.claimed_organization', label: '상대방이 사칭한 기관' },
  { key: 'offender.incident_claim', label: '상대방이 주장한 사건' },
] as const;

export const manualValue = (key: string, value: string): Record<string, unknown> => {
  if (key === 'transfer.actual.status') return { status: value };
  if (key === 'offender.claimed_organization') return { name: value, claimed: true };
  return { text: value };
};

export const FactReviewDialog: React.FC<{ caseId: string; onDone: () => Promise<void>; onClose: () => void }> = ({ caseId, onDone, onClose }) => {
  const [workspace, setWorkspace] = useState<ContextWorkspaceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [field, setField] = useState<(typeof manualFields)[number]['key']>('transfer.actual.status');
  const [value, setValue] = useState('');
  const [reviewing, setReviewing] = useState<string | null>(null);

  const reload = async () => setWorkspace(await loadContextWorkspace(caseId));
  useEffect(() => {
    let active = true;
    setLoading(true);
    loadContextWorkspace(caseId).then((next) => { if (active) setWorkspace(next); })
      .catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : '확인 사실을 불러오지 못했습니다.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [caseId]);

  const create = async (event: React.FormEvent) => {
    event.preventDefault();
    const selected = manualFields.find((item) => item.key === field);
    if (!selected || !value.trim() || busy) return;
    setBusy(true); setError('');
    try {
      await createContextFact(caseId, {
        client_request_id: generateUuid(), semantic_key: field, display_label: selected.label,
        value: manualValue(field, value.trim()),
        display_value: field === 'transfer.actual.status' ? { TRANSFERRED: '이체함', NOT_TRANSFERRED: '이체하지 않음', UNKNOWN: '확인 필요' }[value] ?? value : value.trim(),
      });
      setValue('');
      await reload();
      await onDone();
    } catch (reason) { setError(reason instanceof Error ? reason.message : '사실 제안을 저장하지 못했습니다.'); }
    finally { setBusy(false); }
  };

  const confirm = async (fact: ContextFact) => {
    if (busy || !workspace?.can_review) return;
    setBusy(true); setError('');
    try {
      await reviewContextFact(caseId, fact.fact_id, fact.version, 'CONFIRM', '담당자 명시적 확인');
      setReviewing(null);
      await reload();
      await onDone();
    } catch (reason) { setError(reason instanceof Error ? reason.message : '확정하지 못했습니다. 최신 상태를 다시 확인해 주세요.'); }
    finally { setBusy(false); }
  };

  return <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) onClose(); }}>
    <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="fact-dialog-title"><header><div><h2 id="fact-dialog-title">담당자 확인 사실</h2><p>제안된 사실의 내용과 출처를 검토한 뒤 직접 확정합니다.</p></div><button className="icon-button" onClick={onClose} aria-label="창 닫기"><X size={18}/></button></header>
      <div className="dialog-body">
        {error && <p className="dialog-error" role="alert"><AlertCircle size={15}/>{error}</p>}
        {loading ? <p className="dialog-loading"><Loader2 className="spin" size={16}/>확인 사실을 불러오는 중입니다.</p> : <>
          <div className="fact-review-list"><h3>확인 필요 · {workspace?.proposed_facts.length ?? 0}건</h3>
            {workspace?.proposed_facts.length ? workspace.proposed_facts.map((fact) => <article key={fact.fact_id} className="fact-review-card"><strong>{fact.display_label}</strong><p>{fact.display_value}</p><small>상태: {fact.status} · 출처: {fact.source_kind}</small>
              {reviewing === fact.fact_id ? <div className="fact-review-actions"><span>담당자가 이 내용을 직접 확인했습니까?</span><button type="button" disabled={busy} onClick={() => setReviewing(null)}>취소</button><button type="button" disabled={busy || !workspace.can_review} onClick={() => void confirm(fact)}><Check size={14}/>확정</button></div> : <button type="button" disabled={busy || !workspace.can_review} onClick={() => setReviewing(fact.fact_id)}>내용 검토</button>}
            </article>) : <p>검토 대기 중인 사실이 없습니다.</p>}
          </div>
          <form className="fact-review-create" onSubmit={(event) => void create(event)}><h3>사실 직접 입력</h3><p>입력만 하면 확인 필요 상태로 저장됩니다. 확정에는 별도의 검토가 필요합니다.</p><label>사실 종류<select value={field} onChange={(event) => { setField(event.target.value as typeof field); setValue(''); }}>{manualFields.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>
            <label>내용{field === 'transfer.actual.status' ? <select value={value} onChange={(event) => setValue(event.target.value)}><option value="">선택</option><option value="TRANSFERRED">이체함</option><option value="NOT_TRANSFERRED">이체하지 않음</option><option value="UNKNOWN">확인 필요</option></select> : <input value={value} onChange={(event) => setValue(event.target.value)} maxLength={3000} placeholder="확인한 내용을 입력하세요"/>}</label>
            <button type="submit" disabled={busy || !workspace?.can_write || !value.trim()}><Plus size={14}/>확인 필요로 저장</button>
          </form>
          {!!workspace?.confirmed_facts.length && <div className="fact-review-list"><h3>담당자 확인 · {workspace.confirmed_facts.length}건</h3>{workspace.confirmed_facts.map((fact) => <article key={fact.fact_id} className="fact-review-card"><strong>{fact.display_label}</strong><p>{fact.display_value}</p><small>상태: {fact.status} · 출처: {fact.source_kind} · 확인자: {fact.confirmed_by || '확인 필요'} · 확인 {fact.confirmed_at ? formatClock(fact.confirmed_at) : '시각 확인 필요'}</small></article>)}</div>}
        </>}
      </div><footer className="dialog-footer"><button type="button" className="secondary-action" onClick={onClose}>닫기</button></footer>
    </section>
  </div>;
};
