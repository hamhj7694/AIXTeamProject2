import type { ReactNode } from 'react';
import { formatDateTimeKST } from '../../presentation';

export const cardStyles = {
  card: { border: '1px solid #d8e5f5', borderRadius: 12, padding: 12, background: '#fff', boxShadow: '0 3px 10px rgba(16,24,40,.05)', color: '#172033' } as const,
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 8 } as const,
  title: { fontSize: 13, fontWeight: 850, color: '#175cd3' } as const,
  updated: { color: '#667085', fontSize: 10, whiteSpace: 'nowrap' } as const,
  description: { margin: '0 0 8px', color: '#344054', fontSize: 11, lineHeight: 1.45 } as const,
  badge: { borderRadius: 6, padding: '3px 6px', fontSize: 10, fontWeight: 800 } as const,
};

export function CardHeader({ title, updatedAt, icon = '●' }: { title: string; updatedAt: string; icon?: ReactNode }) {
  return <div style={cardStyles.header}><div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><span aria-hidden style={{ color: '#12b76a' }}>{icon}</span><strong style={cardStyles.title}>{title}</strong></div><span style={cardStyles.updated}>실시간 반영&nbsp; {formatDateTimeKST(updatedAt)}</span></div>;
}

export function Badge({ children, tone = 'blue' }: { children: ReactNode; tone?: 'blue' | 'red' | 'green' | 'amber' | 'purple' }) {
  const colors = { blue: ['#eff4ff', '#175cd3'], red: ['#fef3f2', '#b42318'], green: ['#ecfdf3', '#067647'], amber: ['#fffaeb', '#b54708'], purple: ['#f4f3ff', '#6941c6'] }[tone];
  return <span style={{ ...cardStyles.badge, background: colors[0], color: colors[1] }}>{children}</span>;
}
