import type { ReactNode } from 'react';
import type { BankCardKind } from './BankCardMenu';
import { BankCardChromeProvider } from './CardPrimitives';

type BankCardStackProps = {
  cards: BankCardKind[];
  cardContent: Record<BankCardKind, ReactNode>;
  collapsedCards: Partial<Record<BankCardKind, boolean>>;
  updatedCards: Partial<Record<BankCardKind, boolean>>;
  highlightedCard?: BankCardKind | null;
  onToggleCollapsed: (kind: BankCardKind) => void;
  onClose: (kind: BankCardKind) => void;
  onViewed: (kind: BankCardKind) => void;
};

export function BankCardStack({ cards, cardContent, collapsedCards, updatedCards, highlightedCard, onToggleCollapsed, onClose, onViewed }: BankCardStackProps) {
  return <div style={{ display: 'grid', gap: 10 }}>
    {cards.map((kind) => {
      const collapsed = Boolean(collapsedCards[kind]);
      return <BankCardChromeProvider key={kind} value={{ collapsed, updated: Boolean(updatedCards[kind]), onToggleCollapsed: () => onToggleCollapsed(kind), onClose: () => onClose(kind), onViewed: () => onViewed(kind) }}>
        <section id={`bank-card-${kind}`} style={{ outline: highlightedCard === kind ? '1px solid #84adff' : 'none', borderRadius: 12, background: highlightedCard === kind ? '#eff4ff' : 'transparent', transition: 'background 180ms ease, outline-color 180ms ease' }}>
          {cardContent[kind]}
        </section>
      </BankCardChromeProvider>;
    })}
  </div>;
}
