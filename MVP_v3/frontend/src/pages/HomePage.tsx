import React, { FormEvent, useMemo, useState } from 'react';
import { AlertCircle, ArrowLeftRight, BrainCircuit, CheckCircle2, ChevronRight, FileSearch, MessageSquareText, Play, ShieldAlert, ShieldCheck, Sparkles, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { casesApi } from '../api/cases';
import type { AnalyzeCaseResponse, StoredCase } from '../api/types';
import { riskLabel, riskTone } from '../presentation';

type AnalysisState = 'INPUT' | 'ANALYZING' | 'CREATED' | 'NO_CASE' | 'ERROR';

const splitSentences = (text: string) => text.split(/(?:\r?\n)+|(?<=[.!?。])\s+/u).map((line) => line.trim()).filter(Boolean);

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
  const windows = caseItem.diagnosis.windows ?? [];
  const events = caseItem.diagnosis.evidence ?? [];
  const claims = context.claims ?? [];
  const recommended = context.recommended_next_steps ?? [];
  const unresolved = valueList(caseItem.initial_report, 'unresolved_items');
  const nextChecks = valueList(caseItem.initial_report, 'next_checks');
  return <section className="analysis-result created">
    <div className="analysis-result-heading"><span className={riskTone(caseItem.risk)}><ShieldAlert size={21}/></span><div><p>Shared Case 생성 완료 · {caseItem.case_id}</p><h2>{context.incident_type || '통화 맥락 분석을 완료했습니다.'}</h2><small>{caseItem.initial_brief}</small></div><b className={`analysis-risk ${riskTone(caseItem.risk)}`}>{riskLabel(caseItem.risk)} {Math.round(caseItem.risk_score)}</b></div>
    <div className="analysis-result-grid">
      <section><header><BrainCircuit size={16}/><div><b>ML 문장·구간 위험 분석</b><span>입력 문장을 구간별로 분석한 결과입니다.</span></div></header><div className="analysis-window-list">{windows.length > 0 ? windows.map((window) => <article key={window.segment_id} className={window.label === 'PHISHING' ? 'is-risk' : ''}><span>{window.start_turn === window.end_turn ? `문장 ${window.start_turn}` : `문장 ${window.start_turn}–${window.end_turn}`}</span><p>{window.text}</p><b>{window.label === 'PHISHING' ? '위험 신호' : '정상'} {Math.round(window.final_risk_score)}</b></article>) : events.map((event) => <article key={`${event.turn}-${event.text}`} className="is-risk"><span>문장 {event.turn}</span><p>{event.text}</p><b>{event.event_family}</b></article>)}</div></section>
      <section><header><Sparkles size={16}/><div><b>LLM Case 초기 정리</b><span>전체 통화 맥락을 종합해 Case의 초기 정보를 구성했습니다.</span></div></header><div className="analysis-case-summary"><p>{context.summary || caseItem.initial_brief}</p><div><b>상대방 주장</b><ul>{claims.length ? claims.map((claim) => <li key={claim}>{claim}</li>) : <li>추가 확인이 필요합니다.</li>}</ul></div><div><b>우선 권장 조치</b><ul>{recommended.length ? recommended.map((item) => <li key={item}>{item}</li>) : nextChecks.map((item) => <li key={item}>{item}</li>)}</ul></div>{unresolved.length > 0 && <div><b>아직 확인할 정보</b><ul>{unresolved.map((item) => <li key={item}>{item}</li>)}</ul></div>}</div></section>
    </div>
    <p className="analysis-disclaimer">ML 위험 신호와 LLM 초기 정리는 대응을 돕는 분석 결과입니다. 실제 금융 조치와 사실 확정은 담당자의 확인이 필요합니다.</p>
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
  const sentences = useMemo(() => splitSentences(text), [text]);
  const reset = () => { setText(''); setResult(null); setCaseItem(undefined); setError(''); setState('INPUT'); setOpen(true); };
  const close = () => { setOpen(false); setError(''); };
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!text.trim() || state === 'ANALYZING') return;
    setState('ANALYZING'); setError(''); setResult(null); setCaseItem(undefined);
    try {
      const response = await casesApi.analyze(text.trim());
      setResult(response);
      if (response.disposition === 'CASE_CREATED' && response.case_id) { setCaseItem(await casesApi.get(response.case_id)); setState('CREATED'); }
      else if (response.disposition === 'NO_CASE') setState('NO_CASE');
      else { setState('ERROR'); setError(response.error?.message || '통화 내용을 분석하지 못했습니다.'); }
    } catch (reason) { setState('ERROR'); setError(reason instanceof Error ? reason.message : '통화 내용을 분석하지 못했습니다.'); }
  };
  return <section className={`home-empty ${open ? 'analysis-open' : ''}`}>
    {!open ? <><div className="home-mark"><ShieldCheck size={26}/></div><p className="eyebrow">CONTEXT-FIRST CASE</p><h1>대응할 사건을 선택하세요.</h1><p>통화 맥락, 고객 대화, 기관 확인과 대응 업무를 하나의 Shared Case에서 이어서 확인할 수 있습니다.</p><div className="home-principles"><span><MessageSquareText size={17}/>대화와 업무 기록을 한 흐름으로</span><span><ArrowLeftRight size={17}/>고객 응답과 Case 맥락을 양방향으로</span></div><button className="start-analysis-button" type="button" onClick={() => setOpen(true)}><FileSearch size={17}/>새 통화 분석하기</button></> : <div className="home-analysis-panel">
      <header><div><p className="eyebrow">NEW SHARED CASE</p><h1>새 통화 분석하기</h1><span>문장별 ML 위험 분석과 전체 맥락 LLM 분석으로 Shared Case의 초기 정보를 생성합니다.</span></div><button type="button" onClick={close} aria-label="새 통화 분석 닫기"><X size={19}/></button></header>
      {state === 'INPUT' || state === 'ANALYZING' || state === 'ERROR' ? <form onSubmit={submit}><label htmlFor="call-transcript">통화 내용 텍스트</label><textarea id="call-transcript" value={text} disabled={state === 'ANALYZING'} onChange={(event) => setText(event.target.value)} placeholder={'통화 내용이나 대화 기록을 붙여 넣으세요.\n문장 또는 줄바꿈 단위로 ML이 위험 신호를 분석하고, 전체 맥락은 LLM이 Case 초기 정보로 정리합니다.'}/><div className="analysis-input-meta"><span>문장·줄바꿈 기준 {sentences.length}개 구간 감지</span><span>최대 50,000자</span></div>{sentences.length > 0 && <div className="analysis-sentence-preview">{sentences.slice(0, 5).map((sentence, index) => <span key={`${index}-${sentence}`}>문장 {index + 1} · {sentence}</span>)}{sentences.length > 5 && <span>외 {sentences.length - 5}개 문장</span>}</div>}{error && <p className="analysis-error"><AlertCircle size={15}/>{error}</p>}<footer><button type="button" onClick={close} disabled={state === 'ANALYZING'}>취소</button><button type="submit" className="primary" disabled={!text.trim() || state === 'ANALYZING'}>{state === 'ANALYZING' ? <><span className="spinner"/>문장별 ML·전체 LLM 분석 중</> : <><Play size={16}/>통화 분석하고 Case 만들기</>}</button></footer></form> : result && <AnalysisResult result={result} caseItem={caseItem} onOpenCase={() => result.case_id && navigate(`/cases/${encodeURIComponent(result.case_id)}`)} onRestart={reset}/>}</div>}
  </section>;
};
