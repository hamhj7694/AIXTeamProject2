import { ChevronDown, ChevronUp, X } from 'lucide-react';
import type { ReactNode } from 'react';
import type { BankCardKind } from './BankCardMenu';

const cardTitles: Record<BankCardKind, string> = {
  transaction: '은행 거래 확인',
  fds: 'FDS 분석 결과',
  additionalLookup: '추가 조회 결과',
};

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
      return <section id={`bank-card-${kind}`} key={kind} style={{ border: highlightedCard === kind ? '1px solid #84adff' : '1px solid #d8e5f5', borderRadius: 12, background: highlightedCard === kind ? '#eff4ff' : '#fff', transition: 'background 180ms ease, border-color 180ms ease' }}>
        <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, padding: '8px 10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}><strong style={{ color: '#175cd3', fontSize: 12 }}>{cardTitles[kind]}</strong>{updatedCards[kind] && <span style={{ borderRadius: 999, padding: '2px 6px', color: '#175cd3', background: '#dbe8ff', fontSize: 10, fontWeight: 800 }}>업데이트됨</span>}</div>
          <div style={{ display: 'flex', gap: 4 }}>
            <button type="button" onClick={() => { onToggleCollapsed(kind); onViewed(kind); }} aria-label={collapsed ? `${cardTitles[kind]} 펼치기` : `${cardTitles[kind]} 접기`} title={collapsed ? '펼치기' : '접기'} style={{ border: 0, background: 'transparent', cursor: 'pointer', padding: 3 }}>
              {collapsed ? <ChevronDown size={15}/> : <ChevronUp size={15}/>} 
            </button>
            <button type="button" onClick={() => onClose(kind)} aria-label={`${cardTitles[kind]} 닫기`} title="닫기" style={{ border: 0, background: 'transparent', cursor: 'pointer', padding: 3 }}>
              <X size={15}/>
            </button>
          </div>
        </header>
        {!collapsed && <div>{cardContent[kind]}</div>}
      </section>;
    })}
  </div>;
}
