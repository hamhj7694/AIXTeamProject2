import React, { FormEvent, useState } from 'react';
import { AlertCircle, ArrowLeftRight, BrainCircuit, CheckCircle2, ChevronRight, FileSearch, MessageSquareText, Play, ShieldAlert, ShieldCheck, Sparkles, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { casesApi } from '../api/cases';
import type { AnalyzeCaseResponse, StoredCase } from '../api/types';
import { caseState, caseStateLabel, caseStateTone } from '../presentation';

type AnalysisState = 'INPUT' | 'ANALYZING' | 'CREATED' | 'NO_CASE' | 'ERROR';
type SampleType = 'PHISHING' | 'FINANCE' | 'DAILY';

const CALL_SAMPLES: Record<SampleType, string[]> = {
  PHISHING: [
    ['서울지검 수사관입니다. 고객님 명의 계좌가 범죄에 연루됐습니다.', '현재 자금 추적을 위해 계좌 검증이 필요합니다.', '오늘 안에 안내드리는 안전계좌로 자금을 이체하셔야 합니다.', '수사 중이므로 가족이나 은행 직원에게는 알리지 마세요.', '통화를 끊지 말고 지금 바로 이체 절차를 진행해 주세요.'].join('\n'),
    ['금융감독원 조사팀입니다. 고객님 계좌에서 불법 거래가 발견됐습니다.', '본인 확인을 위해 주민등록번호와 계좌번호를 말씀해 주세요.', '곧 문자로 보내는 링크에서 보안 앱을 설치하셔야 합니다.', '조사가 끝날 때까지 누구에게도 이 내용을 말하면 안 됩니다.', '지금 처리하지 않으면 계좌가 즉시 정지됩니다.'].join('\n'),
    ['카드사 보안센터인데 해외에서 고액 결제가 승인됐습니다.', '취소하려면 문자로 전송된 인증번호를 지금 불러 주세요.', '환불 전용 계좌로 보증금을 보내면 결제가 바로 취소됩니다.', '은행에 문의하면 처리가 지연되니 저희 안내만 따라 주세요.', '통화를 유지한 채 모바일뱅킹을 실행해 주세요.'].join('\n'),
    ['엄마, 휴대폰이 고장 나서 임시 번호로 연락해.', '급하게 결제해야 하는데 내 인증서가 작동하지 않아.', '내가 보내는 계좌로 먼저 300만 원만 이체해 줘.', '지금 회의 중이라 전화는 받을 수 없으니 문자로만 답해 줘.', '오늘 안에 꼭 필요하니까 다른 사람에게 묻지 말고 보내 줘.'].join('\n'),
    ['저금리 대환대출 승인 담당자입니다.', '기존 대출을 먼저 상환해야 신규 대출금이 지급됩니다.', '상환금은 지금 알려드리는 개인 명의 계좌로 보내시면 됩니다.', '신용점수 보호를 위해 원격제어 앱을 설치해 주세요.', '오늘 입금하지 않으면 승인 건이 자동 취소됩니다.'].join('\n'),
  ],
  FINANCE: [
    ['안녕하세요, 정기예금 만기일을 확인하고 싶습니다.', '고객님 본인 확인 후 만기일과 예상 이자를 안내드리겠습니다.', '앱에서 본인 인증을 완료해 주시겠어요?', '인증이 확인되어 만기일은 다음 달 15일입니다.', '재예치 여부는 만기 전에 앱이나 영업점에서 선택하실 수 있습니다.'].join('\n'),
    ['체크카드를 분실해서 사용 정지를 요청하려고 합니다.', '즉시 카드 사용을 정지하고 최근 승인 내역을 확인하겠습니다.', '어제 편의점 결제 이후에는 제가 사용한 내역이 아닙니다.', '해당 거래는 이의 신청으로 접수하고 새 카드를 재발급하겠습니다.', '접수번호는 공식 앱 알림으로 확인하실 수 있습니다.'].join('\n'),
    ['주택담보대출 금리와 준비 서류를 상담받고 싶습니다.', '소득과 담보 조건에 따라 적용 금리가 달라질 수 있습니다.', '필요 서류 목록을 은행 공식 앱 상담함으로 보내드리겠습니다.', '서류 제출 전 예상 한도 조회도 가능합니다.', '검토 후 영업점 방문 일정을 예약해 드리겠습니다.'].join('\n'),
    ['해외 송금 수수료와 처리 시간을 알고 싶습니다.', '송금 국가와 통화, 금액을 확인하면 예상 비용을 안내할 수 있습니다.', '미국으로 2천 달러를 보내려고 합니다.', '영업일 기준 처리 시간과 중계 수수료를 안내드리겠습니다.', '최종 송금 전 앱 화면에서 수취인 정보를 다시 확인해 주세요.'].join('\n'),
    ['자동이체 날짜를 매월 10일에서 25일로 바꾸고 싶습니다.', '등록된 자동이체 항목을 확인한 뒤 변경할 수 있습니다.', '통신비 자동이체 한 건만 변경해 주세요.', '변경 내용은 다음 출금일부터 적용됩니다.', '처리 결과는 은행 앱 알림으로 보내드리겠습니다.'].join('\n'),
  ],
  DAILY: [
    ['오늘 저녁에 같이 식사할래?', '좋아, 퇴근하고 일곱 시쯤 가능해.', '지난번에 갔던 식당 앞에서 만날까?', '응, 내가 먼저 도착하면 자리 잡고 있을게.', '늦어지면 출발 전에 연락할게.'].join('\n'),
    ['주말에 등산 가기로 한 것 기억하지?', '응, 토요일 아침 날씨부터 확인해 보자.', '비가 안 오면 아홉 시에 입구에서 만나자.', '물하고 간단한 간식은 내가 준비할게.', '좋아, 금요일 저녁에 다시 연락하자.'].join('\n'),
    ['택배가 오늘 오후에 도착할 예정이래.', '집에 사람이 없으면 경비실에 맡겨 달라고 해 줘.', '알겠어, 배송 메모를 확인해 볼게.', '상자가 무거우니 저녁에 같이 옮기자.', '도착 알림이 오면 알려 줄게.'].join('\n'),
    ['회의 시간이 오후 두 시로 바뀌었습니다.', '회의실도 변경됐나요?', '네, 3층 소회의실에서 진행합니다.', '자료는 시작 전에 공유 폴더에 올려 주세요.', '확인했습니다. 참석자들에게도 전달하겠습니다.'].join('\n'),
    ['병원 예약을 다음 주로 변경하려고 해.', '어느 요일이 가장 편해?', '수요일 오후면 좋을 것 같아.', '예약실에 확인하고 가능한 시간을 알려 줄게.', '고마워, 확인되면 메시지 남겨 줘.'].join('\n'),
  ],
};

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
  const [lastSample, setLastSample] = useState<Partial<Record<SampleType, number>>>({});
  const applySample = (type: SampleType) => {
    const samples = CALL_SAMPLES[type];
    const previous = lastSample[type];
    let index = Math.floor(Math.random() * samples.length);
    if (samples.length > 1 && index === previous) index = (index + 1 + Math.floor(Math.random() * (samples.length - 1))) % samples.length;
    setLastSample((current) => ({ ...current, [type]: index }));
    setText(samples[index]); setError(''); setState('INPUT');
  };
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
      {state === 'INPUT' || state === 'ANALYZING' || state === 'ERROR' ? <form onSubmit={submit}><label htmlFor="call-transcript">통화 내용 텍스트</label><div className="analysis-sample-row"><span>샘플 입력</span><button type="button" disabled={state === 'ANALYZING'} onClick={() => applySample('PHISHING')}>보이스피싱 사례 샘플</button><button type="button" disabled={state === 'ANALYZING'} onClick={() => applySample('FINANCE')}>정상 금융 상담 샘플</button><button type="button" disabled={state === 'ANALYZING'} onClick={() => applySample('DAILY')}>일상 통화 샘플</button></div><textarea id="call-transcript" value={text} disabled={state === 'ANALYZING'} onChange={(event) => setText(event.target.value)} placeholder={'통화 내용이나 대화 기록을 붙여 넣으세요.\n문장 또는 줄바꿈 단위로 ML이 위험 신호를 추출하고, LLM은 구조화된 핵심 피처만으로 Case 초기 정보를 정리합니다.'}/><div className="analysis-input-meta"><span>최대 50,000자</span></div><p className="analysis-privacy-note">원문은 분석 요청 중에만 사용되며, Shared Case에는 원문 대신 핵심 위험 피처와 집계 결과만 저장됩니다.</p>{error && <p className="analysis-error"><AlertCircle size={15}/>{error}</p>}<footer><button type="button" onClick={close} disabled={state === 'ANALYZING'}>취소</button><button type="submit" className="primary" disabled={!text.trim() || state === 'ANALYZING'}>{state === 'ANALYZING' ? <><span className="spinner"/>문장별 ML·피처 기반 LLM 분석 중</> : <><Play size={16}/>통화 분석하고 Case 만들기</>}</button></footer></form> : result && <AnalysisResult result={result} caseItem={caseItem} onOpenCase={() => result.case_id && navigate(`/cases/${encodeURIComponent(result.case_id)}`)} onRestart={reset}/>}</div>}
  </section>;
};
