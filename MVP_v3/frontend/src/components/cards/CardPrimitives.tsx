import { createContext, useContext, type ReactNode } from 'react';
import { ChevronDown, ChevronUp, X } from 'lucide-react';
import { formatDateTimeKST } from '../../presentation';

export const cardStyles = {
  card: { border: '1px solid #d8e5f5', borderRadius: 12, padding: 12, background: '#fff', boxShadow: '0 3px 10px rgba(16,24,40,.05)', color: '#172033' } as const,
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 8 } as const,
  title: { fontSize: 13, fontWeight: 850, color: '#175cd3' } as const,
  updated: { color: '#667085', fontSize: 10, whiteSpace: 'nowrap' } as const,
  description: { margin: '0 0 8px', color: '#344054', fontSize: 11, lineHeight: 1.45 } as const,
  badge: { borderRadius: 6, padding: '3px 6px', fontSize: 10, fontWeight: 800 } as const,
};

export interface BankCardChromeState {
  collapsed: boolean;
  updated: boolean;
  onToggleCollapsed: () => void;
  onClose: () => void;
  onViewed: () => void;
}

const BankCardChromeContext = createContext<BankCardChromeState | null>(null);

export function BankCardChromeProvider({ value, children }: { value: BankCardChromeState; children: ReactNode }) {
  return <BankCardChromeContext.Provider value={value}>{children}</BankCardChromeContext.Provider>;
}

export function useBankCardChrome() {
  return useContext(BankCardChromeContext);
}

export function CardHeader({ title, updatedAt, icon = '●', leading }: { title: string; updatedAt: string; icon?: ReactNode; leading?: ReactNode }) {
  const chrome = useBankCardChrome();
  return <div style={cardStyles.header}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
      {leading}
      <span aria-hidden style={{ color: '#12b76a' }}>{icon}</span>
      <strong style={cardStyles.title}>{title}</strong>
      {chrome?.updated && <span style={{ borderRadius: 999, padding: '2px 6px', color: '#175cd3', background: '#dbe8ff', fontSize: 10, fontWeight: 800, whiteSpace: 'nowrap' }}>업데이트됨</span>}
    </div>
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 4, flexShrink: 0 }}>
      <span style={cardStyles.updated}>반영 시간&nbsp; {formatDateTimeKST(updatedAt)}</span>
      {chrome && <>
        <button type="button" onClick={() => { chrome.onToggleCollapsed(); chrome.onViewed(); }} aria-label={chrome.collapsed ? `${title} 펼치기` : `${title} 접기`} title={chrome.collapsed ? '펼치기' : '접기'} style={{ border: 0, background: 'transparent', cursor: 'pointer', padding: 3, display: 'inline-flex', alignItems: 'center' }}>
          {chrome.collapsed ? <ChevronDown size={15} /> : <ChevronUp size={15} />}
        </button>
        <button type="button" onClick={chrome.onClose} aria-label={`${title} 닫기`} title="닫기" style={{ border: 0, background: 'transparent', cursor: 'pointer', padding: 3, display: 'inline-flex', alignItems: 'center' }}>
          <X size={15} />
        </button>
      </>}
    </div>
  </div>;
}

export function Badge({ children, tone = 'blue' }: { children: ReactNode; tone?: 'blue' | 'red' | 'green' | 'amber' | 'purple' }) {
  const colors = { blue: ['#eff4ff', '#175cd3'], red: ['#fef3f2', '#b42318'], green: ['#ecfdf3', '#067647'], amber: ['#fffaeb', '#b54708'], purple: ['#f4f3ff', '#6941c6'] }[tone];
  return <span style={{ ...cardStyles.badge, background: colors[0], color: colors[1] }}>{children}</span>;
}
