import React from 'react';
import { CustomerQuestionCard } from '../cards/CustomerQuestionCard';
import { CustomerAnswerReceiptCard } from './CustomerAnswerReceiptCard';
import { CustomerVerificationResultCard } from './CustomerVerificationResultCard';
import { RecoveryStepDetailCard } from './RecoveryStepDetailCard';
import type { CustomerCardDescriptor } from './types';

interface Props {
  cards: CustomerCardDescriptor[];
  submitting: boolean;
  onAnswer: (answer: string) => Promise<void>;
  onRecoveryRequest: (kind: 'AI_ADVICE' | 'HUMAN_HANDOFF', step: string) => Promise<void> | void;
}

export const CustomerCardRenderer: React.FC<Props> = ({ cards, submitting, onAnswer, onRecoveryRequest }) => <>
  {cards.map((card) => {
    if (card.card_type === 'QUESTION') return <CustomerQuestionCard key={card.card_id} question={card.payload.question} submitting={submitting} onSubmit={onAnswer}/>;
    if (card.card_type === 'ANSWER_RECEIPT') return <CustomerAnswerReceiptCard key={card.card_id} question={card.payload.question} answer={card.payload.answer}/>;
    if (card.card_type === 'VERIFICATION_RESULT') return <CustomerVerificationResultCard key={card.card_id} result={card.payload.result}/>;
    return <RecoveryStepDetailCard key={card.card_id} stepId={card.payload.stepId} onRequest={onRecoveryRequest}/>;
  })}
</>;
