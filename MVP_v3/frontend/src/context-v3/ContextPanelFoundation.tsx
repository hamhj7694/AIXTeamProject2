import React from 'react';
import { PanelRightClose, PanelRightOpen } from 'lucide-react';

/**
 * Frontend-first foundation panel.
 *
 * The existing ContextPanelV3 remains available as a legacy implementation,
 * but the new frontend is intentionally empty until the new View Model and
 * API contract are approved. This component owns layout only and performs no
 * Fact interpretation or backend mutation.
 */
export const ContextPanelFoundation: React.FC<{
  open: boolean;
  onToggle: () => void;
}> = ({ open, onToggle }) => (
  <aside className={`context-panel context-panel-v3 context-panel-foundation ${open ? 'is-open' : ''}`} aria-label="새 사건 맥락 패널">
    <div className="context-header context-v3-sticky-header">
      <div>
        <p className="eyebrow">사건 정보</p>
        <h2>사건 현황</h2>
      </div>
      <button type="button" className="context-open context-header-toggle" onClick={onToggle} aria-label={open ? '사건 맥락 닫기' : '사건 맥락 열기'} title={open ? '사건 맥락 닫기' : '사건 맥락 열기'}>
        {open ? <PanelRightClose size={17}/> : <PanelRightOpen size={17}/>} 
      </button>
    </div>
    <div className="context-foundation-blank" aria-label="새 우측 패널 설계 영역" />
  </aside>
);
