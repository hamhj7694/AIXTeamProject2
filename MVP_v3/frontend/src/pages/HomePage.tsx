import React, { FormEvent, useState } from 'react';
import { AlertCircle, ArrowLeftRight, BrainCircuit, CheckCircle2, ChevronRight, FileSearch, MessageSquareText, Play, ShieldAlert, ShieldCheck, Sparkles, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { casesApi } from '../api/cases';
import type { AnalyzeCaseResponse, StoredCase } from '../api/types';
import { caseState, caseStateLabel, caseStateTone } from '../presentation';

type AnalysisState = 'INPUT' | 'ANALYZING' | 'CREATED' | 'NO_CASE' | 'ERROR';

const valueList = (report: StoredCase['initial_report'], key: string) => {
  const content = report?.sections?.find((item) => item.section_key === key)?.content;
  return Array.isArray(content?.items) ? content.items.filter((item): item is string => typeof item === 'string') : [];
};

const AnalysisResult: React.FC<{ result: AnalyzeCaseResponse; caseItem?: StoredCase; onOpenCase: () => void; onRestart: () => void }> = ({ result, caseItem, onOpenCase, onRestart }) => {
  if (result.disposition === 'NO_CASE') return <section className="analysis-result no-case">
    <div className="analysis-result-heading"><span><CheckCircle2 size={21}/></span><div><p>분석 완료</p><h2>현재는 보이스피싱 Case 생성 기준에 해당하지 않습니다.</h2></div></div>
    <p className="analysis-brief">{result.initial_brief}</p>
    <div className="analysis-result-actions"><button type="button" onClick={onRestart}>다른 통화 분석하기</button></div>
  </section>;
  if (!caseItem) return <section className="analysis-result error"><AlertCircle size={20}/><div><h2>Case는 생성됐지만 분석 결과를 불러오지 못했습니다.</h2><p>사건 목록에서 새 Case를 열어 확인해 주세요.</p></div><button type="button" onClick={onOpenCase}>Case 열기</button></section>;
  const context = caseItem.diagnosis.context ?? {};
  const events = caseItem.diagnosis.evidence ?? [];
  const signalLabels = Array.from(new Set(events.map((event) => event.text).filter(Boolean)));
  const claims = context.claims ?? [];
  const recommended = context.recommended_next_steps ?? [];
  const unresolved = valueList(caseItem.initial_report, 'unresolved_items');
  const nextChecks = valueList(caseItem.initial_report, 'next_checks');
  return <section className="analysis-result created">
    <div className="analysis-result-heading"><span className={caseStateTone(caseState(caseItem))}><ShieldAlert size={21}/></span><div><p>Shared Case 생성 완료 · {caseItem.case_id}</p><h2>{context.incident_type || '통화 맥락 분석을 완료했습니다.'}</h2><small>{caseItem.initial_brief}</small></div><b className={`analysis-risk ${caseStateTone(caseState(caseItem))}`}>{caseStateLabel(caseState(caseItem))}</b></div>
    <div className="analysis-result-grid">
      <section><header><BrainCircuit size={16}/><div><b>탐지된 핵심 신호</b><span>원문과 ML 점수는 화면에 표시하거나 Case에 저장하지 않습니다.</span></div></header><div className="analysis-window-list">{signalLabels.length > 0 ? <div className="analysis-signal-list"><b>Case 생성에 반영된 신호</b><ul>{signalLabels.map((label) => <li key={label}>{label}</li>)}</ul></div> : <p className="analysis-empty-signal">추가 확인이 필요한 신호를 정리 중입니다.</p>}</div></section>
      <section><header><Sparkles size={16}/><div><b>LLM Case 초기 정리</b><span>전체 통화 맥락을 종합해 Case의 초기 정보를 구성했습니다.</span></div></header><div className="analysis-case-summary"><p>{context.summary || caseItem.initial_brief}</p><div><b>상대방 주장</b><ul>{claims.length ? claims.map((claim) => <li key={claim}>{claim}</li>) : <li>추가 확인이 필요합니다.</li>}</ul></div><div><b>우선 권장 조치</b><ul>{recommended.length ? recommended.map((item) => <li key={item}>{item}</li>) : nextChecks.map((item) => <li key={item}>{item}</li>)}</ul></div>{unresolved.length > 0 && <div><b>아직 확인할 정보</b><ul>{unresolved.map((item) => <li key={item}>{item}</li>)}</ul></div>}</div></section>
    </div>
    <p className="analysis-disclaimer">AI가 정리한 핵심 신호와 초기 Case 정보는 대응을 돕기 위한 참고입니다. 실제 금융 조치와 사실 확정은 담당자의 확인이 필요합니다.</p>
    <div className="analysis-result-actions"><button type="button" onClick={onRestart}>새 통화 분석하기</button><button type="button" className="primary" onClick={onOpenCase}>생성된 Case 열기<ChevronRight size={16}/></button></div>
  </section>;
};

export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [state, setState] = useState<AnalysisState>('INPUT');
  const [result, setResult] = useState<AnalyzeCaseResponse | null>(null);
  const [caseItem, setCaseItem] = useState<StoredCase | undefined>();
  const [error, setError] = useState('');
  const reset = () => { setText(''); setResult(null); setCaseItem(undefined); setError(''); setState('INPUT'); setOpen(true); };
  const close = () => { setOpen(false); setError(''); };
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!text.trim() || state === 'ANALYZING') return;
    setState('ANALYZING'); setError(''); setResult(null); setCaseItem(undefined);
    try {
      const response = await casesApi.analyze(text.trim());
      // The source transcript is intentionally transient in this screen too.
      setText('');
      setResult(response);
      if (response.disposition === 'CASE_CREATED' && response.case_id) { setCaseItem(await casesApi.get(response.case_id)); setState('CREATED'); }
      else if (response.disposition === 'NO_CASE') setState('NO_CASE');
      else { setState('ERROR'); setError(response.error?.message || '통화 내용을 분석하지 못했습니다.'); }
    } catch (reason) { setState('ERROR'); setError(reason instanceof Error ? reason.message : '통화 내용을 분석하지 못했습니다.'); }
  };
  return <section className={`home-empty ${open ? 'analysis-open' : ''}`}>
    {!open ? <><div className="home-mark"><ShieldCheck size={26}/></div><p className="eyebrow">CSR | Case Share Room</p><h1>대응할 사건을 선택하세요.</h1><p>통화 맥락, 고객 대화, 기관 확인과 대응 업무를 하나의 Shared Case에서 이어서 확인할 수 있습니다.</p><div className="home-principles"><span><MessageSquareText size={17}/>대화와 업무 기록을 한 흐름으로</span><span><ArrowLeftRight size={17}/>고객 응답과 Case 맥락을 양방향으로</span></div><button className="start-analysis-button" type="button" onClick={() => setOpen(true)}><FileSearch size={17}/>새 통화 분석하기</button></> : <div className="home-analysis-panel">
      <header><div><p className="eyebrow">NEW SHARED CASE</p><h1>새 통화 분석하기</h1><span>ML이 문장 단위로 신호를 추출한 뒤, LLM은 구조화된 핵심 피처만으로 Case 초기 정보를 정리합니다.</span></div><button type="button" onClick={close} aria-label="새 통화 분석 닫기"><X size={19}/></button></header>
      {state === 'INPUT' || state === 'ANALYZING' || state === 'ERROR' ? <form onSubmit={submit}><label htmlFor="call-transcript">통화 내용 텍스트</label><textarea id="call-transcript" value={text} disabled={state === 'ANALYZING'} onChange={(event) => setText(event.target.value)} placeholder={'통화 내용이나 대화 기록을 붙여 넣으세요.\n문장 또는 줄바꿈 단위로 ML이 위험 신호를 추출하고, LLM은 구조화된 핵심 피처만으로 Case 초기 정보를 정리합니다.'}/><div className="analysis-input-meta"><span>최대 50,000자</span></div><p className="analysis-privacy-note">원문은 분석 요청 중에만 사용되며, Shared Case에는 원문 대신 핵심 위험 피처와 집계 결과만 저장됩니다.</p>{error && <p className="analysis-error"><AlertCircle size={15}/>{error}</p>}<footer><button type="button" onClick={close} disabled={state === 'ANALYZING'}>취소</button><button type="submit" className="primary" disabled={!text.trim() || state === 'ANALYZING'}>{state === 'ANALYZING' ? <><span className="spinner"/>문장별 ML·피처 기반 LLM 분석 중</> : <><Play size={16}/>통화 분석하고 Case 만들기</>}</button></footer></form> : result && <AnalysisResult result={result} caseItem={caseItem} onOpenCase={() => result.case_id && navigate(`/cases/${encodeURIComponent(result.case_id)}`)} onRestart={reset}/>}</div>}
  </section>;
};
