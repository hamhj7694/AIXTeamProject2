import React from 'react';
import type { ContextPanelSectionV3 } from './types';

const shortLabels: Record<string, string> = { SUMMARY: '요약', EXPOSURE: '피해', IMPERSONATION_CONTACT: '사칭', FRAUD_CIRCUMSTANCES: '정황', FACT_VERIFICATION: '확인', STAFF_ACTIONS: '조치', CUSTOMER_SHARE: '공유' };
const count = (section: ContextPanelSectionV3) => section.items.length + Object.values(section.groups).reduce((sum, items) => sum + items.length, 0);

export const ContextQuickNav: React.FC<{
  sections: ContextPanelSectionV3[];
  activeSection: ContextPanelSectionV3['section_id'] | null;
  onNavigate: (sectionId: ContextPanelSectionV3['section_id']) => void;
}> = ({ sections, activeSection, onNavigate }) => <nav className="context-quick-nav" aria-label="사건 맥락 빠른 이동">
  {sections.map((section) => <button type="button" key={section.section_id} className={activeSection === section.section_id ? 'is-active' : ''} aria-current={activeSection === section.section_id ? 'location' : undefined} onClick={() => onNavigate(section.section_id)}><span>{shortLabels[section.section_id]}</span>{section.section_id !== 'CUSTOMER_SHARE' && <b>{count(section)}</b>}</button>)}
</nav>;
