import { useEffect, useRef, useState } from 'react';
import { getBankCaseWorkspace, getCaseDelta, type BankCaseWorkspace } from '../api/cases.ts';
import { mergeCaseDelta, type CaseEntityState } from '../shared/caseDelta.ts';
import { caseFromEntityState, latestRisk, timelineFromEntityState, workspaceEntityState } from '../shared/workspace.ts';

import { CaseList } from './CaseList.tsx';

const POLL_INTERVAL_MS = 5_000;

function displayTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? '-' : new Intl.DateTimeFormat('ko-KR', { dateStyle: 'short', timeStyle: 'short' }).format(date);
}

function riskLabel(score: number | null, classification: string | null): string {
  return score === null ? '분석 대기' : `${score.toFixed(1)} · ${classification ?? '분류 없음'}`;
}

function errorText(error: unknown): string {
  const code = error instanceof Error ? error.message : 'UNKNOWN';
  if (code === 'CASE_NOT_FOUND') return '선택한 사건을 찾을 수 없습니다.';
  if (code === 'CASE_ACCESS_DENIED' || code === 'SERVER_ACTOR_REQUIRED') return '이 사건을 볼 권한이 없습니다.';
  return '사건 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.';
}

export function App() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<BankCaseWorkspace | null>(null);
  const [entityState, setEntityState] = useState<CaseEntityState | null>(null);
  const [workspaceState, setWorkspaceState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);
  const entityStateRef = useRef<CaseEntityState | null>(null);
  const localEditIds = useRef<ReadonlySet<string>>(new Set());

  useEffect(() => {
    if (!selectedId) {
      setWorkspace(null); setEntityState(null); entityStateRef.current = null; setWorkspaceState('idle');
      return undefined;
    }
    let active = true;
    const controller = new AbortController();
    setWorkspaceState('loading'); setError(null);
    getBankCaseWorkspace(selectedId, controller.signal).then((next) => {
      if (!active) return;
      const state = workspaceEntityState(next);
      entityStateRef.current = state; setWorkspace(next); setEntityState(state); setWorkspaceState('ready');
    }).catch((reason: unknown) => {
      if (!active) return;
      setWorkspaceState('error'); setError(errorText(reason));
    });
    return () => { active = false; controller.abort(); };
  }, [selectedId]);

  useEffect(() => {
    if (!selectedId || workspaceState !== 'ready') return undefined;
    let active = true;
    const poll = async () => {
      const current = entityStateRef.current;
      if (!current) return;
      try {
        const delta = await getCaseDelta(selectedId, current.revision, current.fingerprint);
        if (!active || delta.unchanged) return;
        const next = mergeCaseDelta(current, delta, localEditIds.current);
        entityStateRef.current = next;
        setEntityState(next);
      } catch (reason) { if (active) setError(errorText(reason)); }
    };
    const interval = window.setInterval(poll, POLL_INTERVAL_MS);
    return () => { active = false; window.clearInterval(interval); };
  }, [selectedId, workspaceState]);

  const currentCase = entityState ? caseFromEntityState(entityState) : null;
  const timeline = entityState ? timelineFromEntityState(entityState) : [];
  const risk = workspace ? latestRisk(workspace.context_features, timeline) : { score: null, classification: null };

  return <div className="bank-workspace">
    <header className="app-header"><div><strong>CSR</strong><span>Case Share Room</span></div><small>Bank Case Workspace · revision polling</small></header>
    <main className="case-layout">
      <CaseList selectedId={selectedId} onSelect={setSelectedId} />
      <section className="timeline-panel" aria-label="공유 사건 타임라인">
        {!selectedId && <p className="state">왼쪽에서 사건을 선택해 주세요.</p>}
        {selectedId && workspaceState === 'loading' && <p className="state">공유 사건을 불러오는 중입니다.</p>}
        {selectedId && workspaceState === 'error' && <p className="state error">{error}</p>}
        {workspaceState === 'ready' && currentCase && <><div className="case-heading"><div><span className="eyebrow">SHARED CASE</span><h2>{currentCase.id}</h2></div><span className="revision">revision {currentCase.revision}</span></div>
          <ol className="timeline">{timeline.map((event) => <li key={event.id}><time>{displayTime(event.created_at)}</time><div><strong>{event.entity_type}</strong><span>{event.event_type} · {event.visibility}</span>
            {typeof event.payload.risk_score === 'number' && <p>위험 점수 {event.payload.risk_score.toFixed(1)} · {String(event.payload.classification ?? '')}</p>}
          </div></li>)}</ol></>}
      </section>
      <aside className="context-panel" aria-label="사건 컨텍스트"><h2>사건 컨텍스트</h2>
        {!workspace && <p className="state">선택한 사건의 실제 저장 정보를 표시합니다.</p>}
        {workspace && currentCase && <div className="context-content"><dl><dt>위험</dt><dd className="risk-value">{riskLabel(risk.score, risk.classification)}</dd><dt>상태</dt><dd>{currentCase.status} · {currentCase.mode}</dd><dt>버전</dt><dd>{currentCase.version}</dd><dt>최신 이벤트</dt><dd>{timeline.at(-1)?.entity_type ?? '없음'}</dd></dl>
          <section><h3>Context features</h3>{workspace.context_features.length === 0 ? <p>저장된 feature가 없습니다.</p> : <ul>{workspace.context_features.map((item) => <li key={item.id}>{item.source_event_id} · {displayTime(item.received_at)}</li>)}</ul>}</section>
          <section><h3>확정 / 확인 필요</h3>{workspace.facts.length === 0 && workspace.verifications.length === 0 ? <p>기록된 사실 또는 검증 항목이 없습니다.</p> : <ul>{workspace.facts.map((item) => <li key={item.id}>{item.field_key} · {item.status}</li>)}{workspace.verifications.map((item) => <li key={item.id}>{item.claim} · {item.status}</li>)}</ul>}</section>
        </div>}
      </aside>
    </main>
    {error && workspaceState === 'ready' && <div className="poll-error" role="status">{error}</div>}
  </div>;
}
