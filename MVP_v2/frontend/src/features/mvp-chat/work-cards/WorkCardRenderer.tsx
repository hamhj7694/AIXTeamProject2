import React from 'react';
import { QuestionRecommendationCard } from '../cards/QuestionRecommendationCard';
import { UnconfirmedFactsCard } from '../cards/UnconfirmedFactsCard';
import { VerificationRequestCard } from '../cards/VerificationRequestCard';
import { BankActionCard } from './BankActionCard';
import { BankQuestionAnswerFeed } from './BankQuestionAnswerFeed';
import { CaseTransitionCard } from './CaseTransitionCard';
import { CustomerNoticeCard } from './CustomerNoticeCard';
import type { WorkCardDescriptor, WorkCardRenderContext } from './types';

export const WorkCardRenderer: React.FC<{ card: WorkCardDescriptor | null; context: WorkCardRenderContext }> = ({ card, context }) => {
  let activeCard: React.ReactNode = null;
  switch (card?.card_type) {
    case 'QUESTION_PLAN':
      activeCard = <QuestionRecommendationCard caseId={context.caseId} requestedBy={context.requestedBy} onQueued={context.onRefresh} onClose={context.onClose}/>;
      break;
    case 'VERIFICATION_REQUEST':
      activeCard = <VerificationRequestCard caseId={context.caseId} onCreated={context.onRefresh} onClose={context.onClose}/>;
      break;
    case 'FACT_REVIEW':
      activeCard = <UnconfirmedFactsCard caseId={context.caseId} facts={context.facts} confirmedBy={context.requestedBy} onChanged={context.onRefresh} onOpenQuestions={() => context.onOpenCard('QUESTION_PLAN')} onClose={context.onClose}/>;
      break;
    case 'BANK_ACTION':
      activeCard = <BankActionCard caseId={context.caseId} requestedBy={context.requestedBy} onCompleted={context.onRefresh} onClose={context.onClose}/>;
      break;
    case 'CUSTOMER_NOTICE':
      activeCard = <CustomerNoticeCard caseId={context.caseId} requestedBy={context.requestedBy} onCompleted={context.onRefresh} onClose={context.onClose}/>;
      break;
    case 'CASE_TRANSITION':
      activeCard = <CaseTransitionCard caseId={context.caseId} requestedBy={context.requestedBy} currentCase={context.currentCase} onCompleted={context.onRefresh} onClose={context.onClose}/>;
      break;
  }
  return <><BankQuestionAnswerFeed caseId={context.caseId}/>{activeCard}</>;
};
