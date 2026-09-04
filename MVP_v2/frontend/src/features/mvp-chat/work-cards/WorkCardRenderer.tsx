import React from 'react';
import { AlertTriangle, ArrowRight, CheckCircle2, Layers3, Sparkles } from 'lucide-react';
import { QuestionRecommendationCard } from '../cards/QuestionRecommendationCard';
import { UnconfirmedFactsCard } from '../cards/UnconfirmedFactsCard';
import { VerificationRequestCard } from '../cards/VerificationRequestCard';
import { BankActionCard } from './BankActionCard';
import { CaseTransitionCard } from './CaseTransitionCard';
import { CustomerNoticeCard } from './CustomerNoticeCard';
import type { WorkCardDescriptor, WorkCardRenderContext } from './types';
import type { AiWorkCardProposal } from '../../../services/mvpChatApi';

const ProposalOverview: React.FC<{ proposal: AiWorkCardProposal }> = ({ proposal }) => {
  const fallback = proposal.model_mode.startsWith('RULE_BASED');
  return <section className="overflow-hidden rounded-2xl border border-violet-400/40 bg-gradient-to-br from-slate-950 via-slate-950 to-violet-950/70 text-slate-100 shadow-xl">
    <div className="border-b border-white/10 bg-white/[0.03] px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-violet-400/15 px-2.5 py-1 text-[10px] font-black tracking-wide text-violet-200"><Sparkles size={12}/>SHARED CASE 업무 제안</span>
        <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${fallback ? 'bg-amber-400/15 text-amber-200' : 'bg-emerald-400/15 text-emerald-200'}`}>{fallback ? 'Case 데이터 기반 안전 초안' : 'AI 맞춤 분석'}</span>
      </div>
      <h2 className="mt-3 text-base font-black tracking-tight text-white">{proposal.title}</h2>
      <p className="mt-1 text-xs leading-5 text-slate-300">{proposal.summary}</p>
      {proposal.context_sources.length > 0 && <div className="mt-3 flex flex-wrap items-center gap-1.5"><span className="inline-flex items-center gap-1 text-[10px] font-bold text-slate-500"><Layers3 size={12}/>참고 맥락</span>{proposal.context_sources.map((source) => <span key={source} className="rounded-full border border-slate-700 bg-slate-900/80 px-2 py-1 text-[10px] font-bold text-slate-300">{source}</span>)}</div>}
    </div>
    <div className="grid gap-3 p-4 md:grid-cols-[minmax(0,1fr)_minmax(220px,0.8fr)]">
      <div className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
        <p className="flex items-center gap-1.5 text-[11px] font-black text-slate-200"><CheckCircle2 size={14} className="text-emerald-300"/>판단 근거</p>
        <ul className="mt-2 space-y-2 text-[11px] leading-5 text-slate-400">{proposal.rationale.map((item) => <li key={item} className="flex gap-2"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-violet-300"/><span>{item}</span></li>)}</ul>
      </div>
      <div className="rounded-xl border border-blue-400/30 bg-blue-500/10 p-3">
        <p className="flex items-center gap-1.5 text-[11px] font-black text-blue-200"><ArrowRight size={14}/>지금 할 일</p>
        <p className="mt-2 text-xs font-bold leading-5 text-white">{proposal.next_action}</p>
      </div>
    </div>
    {proposal.warnings.length > 0 && <div className="mx-4 mb-4 flex gap-2 rounded-xl border border-amber-400/20 bg-amber-400/10 px-3 py-2.5 text-[11px] leading-5 text-amber-100"><AlertTriangle size={14} className="mt-0.5 shrink-0 text-amber-300"/><span>{proposal.warnings.join(' · ')}</span></div>}
  </section>;
};

export const WorkCardRenderer: React.FC<{ card: WorkCardDescriptor | null; context: WorkCardRenderContext }> = ({ card, context }) => {
  const proposal = card?.source === 'AI_PROPOSAL' ? card.payload as unknown as AiWorkCardProposal : null;
  let activeCard: React.ReactNode = null;
  switch (card?.card_type) {
    case 'QUESTION_PLAN':
      activeCard = <QuestionRecommendationCard caseId={context.caseId} requestedBy={context.requestedBy} initialQuestions={proposal?.questions} onQueued={context.onRefresh} onClose={context.onClose}/>;
      break;
    case 'VERIFICATION_REQUEST':
      activeCard = <VerificationRequestCard caseId={context.caseId} initialClaim={proposal?.suggested_claim ?? ''} initialTarget={proposal?.suggested_target ?? ''} onCreated={context.onRefresh} onClose={context.onClose}/>;
      break;
    case 'FACT_REVIEW':
      activeCard = <UnconfirmedFactsCard caseId={context.caseId} facts={context.facts} questions={context.questions} confirmedBy={context.requestedBy} onChanged={context.onRefresh} onOpenQuestions={() => context.onOpenCard('QUESTION_PLAN')} onClose={context.onClose}/>;
      break;
    case 'BANK_ACTION':
      activeCard = <BankActionCard caseId={context.caseId} requestedBy={context.requestedBy} initialActionType={proposal?.suggested_action_type ?? ''} initialNote={proposal?.suggested_action_note ?? ''} onCompleted={context.onRefresh} onClose={context.onClose}/>;
      break;
    case 'CUSTOMER_NOTICE':
      activeCard = <CustomerNoticeCard caseId={context.caseId} requestedBy={context.requestedBy} initialContent={proposal?.suggested_notice ?? ''} onCompleted={context.onRefresh} onClose={context.onClose}/>;
      break;
    case 'CASE_TRANSITION':
      activeCard = <CaseTransitionCard caseId={context.caseId} requestedBy={context.requestedBy} currentCase={context.currentCase} initialTarget={proposal?.suggested_transition} onCompleted={context.onRefresh} onClose={context.onClose}/>;
      break;
  }
  return <>{proposal && <ProposalOverview proposal={proposal}/>} {activeCard}</>;
};
