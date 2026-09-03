import React, { useState } from 'react';
import { Play } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { caseApi } from '../services/caseApi';

const samples = [
  {
    label: '일반 통화 샘플',
    text: `오늘 퇴근 몇 시쯤 해?
나 지금 장 보고 집 가는 중이야.
저녁은 그냥 집에서 먹을까?
내일 비 온다던데 우산 챙겨.
주말에는 영화 보러 가자.`,
  },
  {
    label: '정상 금융 상담 샘플',
    text: `고객님, 예금 만기일이 다음 주로 예정되어 있습니다.
현재 적용 가능한 재예치 금리를 안내드리겠습니다.
상품 변경 여부는 고객님께서 직접 선택하시면 됩니다.
비밀번호나 인증번호는 전화로 요청하지 않습니다.
추가 상담이 필요하시면 공식 앱이나 영업점을 이용해 주세요.`,
  },
  {
    label: '보이스피싱 샘플',
    text: `서울지검 수사관입니다. 고객님 명의 계좌가 범죄에 연루됐습니다.
현재 자금 추적을 위해 계좌 검증이 필요합니다.
오늘 안에 안내드리는 안전계좌로 자금을 이체하셔야 합니다.
수사 중이므로 가족이나 은행 직원에게는 알리지 마세요.
통화를 끊지 말고 지금 바로 이체 절차를 진행해 주세요.`,
  },
];

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
    <h2 className="mb-4 text-sm font-extrabold">{title}</h2>
    {children}
  </section>
);

const MAX_DIAGNOSIS_CHARS = 6000;
const MAX_DIAGNOSIS_TURNS = 30;
const countDiagnosisTurns = (value: string) => value
  .split(/(?:[.!?]|\n)+/)
  .map((part) => part.trim())
  .filter(Boolean).length;

export const DiagnosisPage: React.FC = () => {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [validationMessage, setValidationMessage] = useState('');
  const [feedbackKind, setFeedbackKind] = useState<'error' | 'info'>('error');
  const navigate = useNavigate();

  const diagnose = async () => {
    if (!text.trim()) {
      setFeedbackKind('error');
      setValidationMessage('내용을 입력하세요.');
      return;
    }
    const turnCount = countDiagnosisTurns(text);
    if (text.length > MAX_DIAGNOSIS_CHARS || turnCount > MAX_DIAGNOSIS_TURNS) {
      setFeedbackKind('error');
      setValidationMessage(`AI 비용 보호를 위해 한 번에 ${MAX_DIAGNOSIS_TURNS}문장·${MAX_DIAGNOSIS_CHARS.toLocaleString()}자까지만 분석합니다. 텍스트를 나누어 실행해 주세요.`);
      return;
    }
    setValidationMessage('');
    setFeedbackKind('error');
    setLoading(true);
    try {
      const result = await caseApi.analyze(text);
      if (result.disposition === 'CASE_CREATED' && result.case_id) {
        navigate(`/cases/${result.case_id}`);
        return;
      }
      if (result.disposition === 'NO_CASE') {
        setFeedbackKind('info');
        setValidationMessage(result.initial_brief || '현재 판정 기준 미만입니다. 안전 확정을 의미하지 않습니다.');
        return;
      }
      setValidationMessage(result.error?.message || '진단을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.');
    } catch (error) {
      setValidationMessage(error instanceof Error ? error.message : '서버 연결을 확인해 주세요.');
    } finally {
      setLoading(false);
    }
  };

  return <AppLayout><div className="mx-auto max-w-6xl py-8 lg:ml-64">
    <div className="mb-8"><p className="mb-2 text-xs font-bold text-blue-600">01 / AI ANALYSIS</p><h1 className="text-3xl font-black tracking-tight">AI 통화 텍스트 진단</h1><p className="mt-2 text-sm text-slate-500">통화 내용을 입력하면 위험 맥락과 다음 확인사항을 분석합니다.</p></div>
    <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
      <Section title="통화 내용 입력">
        <div className="mb-4 flex flex-wrap gap-2">{samples.map((sample) => <button key={sample.label} onClick={() => { setText(sample.text); setValidationMessage(''); }} className="rounded-full border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-600">{sample.label}</button>)}</div>
        <textarea value={text} onChange={(event) => { setText(event.target.value); if (event.target.value.trim()) setValidationMessage(''); }} placeholder="통화 내용을 입력하세요..." className={`min-h-[300px] w-full resize-none rounded-xl border bg-slate-50 p-4 text-sm leading-7 outline-none transition focus:bg-white ${validationMessage && feedbackKind === 'error' ? 'border-rose-400 focus:border-rose-500' : 'border-slate-200 focus:border-blue-500'}`}/>
        {validationMessage && <p className={`mt-2 rounded-lg px-3 py-2 text-sm font-semibold ${feedbackKind === 'info' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-600'}`}>{validationMessage}</p>}
        <div className="mt-4 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end"><Link to="/cases" className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-bold text-slate-700 hover:bg-slate-50">Case 목록</Link><button disabled={loading} onClick={diagnose} className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-blue-200 disabled:cursor-not-allowed disabled:opacity-40">{loading ? '분석 중...' : <><Play size={16}/> 진단하기</>}</button></div>
      </Section>
      <Section title="분석 범위"><div className="space-y-3">{[['전체 맥락 분석', '통화 흐름과 핵심 주장'], ['위험 신호 추출', '사칭·긴급성·송금 요구'], ['초기 Case 생성', '공유 Case와 Brief 저장']].map(([title, description], index) => <div key={title} className="flex gap-3 rounded-xl bg-slate-50 p-3"><div className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-white text-xs font-bold text-blue-600 shadow-sm">0{index + 1}</div><div><p className="text-sm font-bold">{title}</p><p className="mt-0.5 text-xs text-slate-500">{description}</p></div></div>)}</div><div className="mt-5 rounded-xl border border-blue-100 bg-blue-50 p-3 text-xs leading-5 text-blue-800">AI 분석은 최종 금융판단이 아닙니다. 위험 신호를 근거와 함께 정리하고 담당자 확인을 연결합니다.</div></Section>
    </div>
  </div></AppLayout>;
};
