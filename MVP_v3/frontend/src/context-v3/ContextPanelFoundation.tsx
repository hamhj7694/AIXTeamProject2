import React, { useEffect, useMemo, useState } from 'react';
import { Archive, Check, ChevronDown, ChevronUp, ClipboardCheck, PanelRightClose, PanelRightOpen, Pencil, Plus, RotateCcw, Sparkles } from 'lucide-react';
import type { CaseBundle, CaseSupportSnapshot, StoredCase } from '../api/types';

type BriefCategoryKey = 'identity' | 'claim' | 'demand' | 'pressure' | 'money' | 'exposure';
type GuideStage = 'recommended' | 'inProgress' | 'completed';
type GuideType = '고객 소통' | '금융 보호' | '기록·증빙';
type BriefEntry = { id: string; text: string };
type ArchivedBriefEntry = BriefEntry & { categoryKey: BriefCategoryKey };
type BriefCategory = { key: BriefCategoryKey; label: string; entries: BriefEntry[] };
type GuideEntry = { id: string; title: string; description: string; type: GuideType; stage: GuideStage; actor?: string; timestamp?: string; actionLabel?: string; onAction?: () => void };
type SummaryItem = { label: string; value: string };

type Props = {
  open: boolean;
  onToggle: () => void;
  caseItem: StoredCase;
  bundle: CaseBundle;
  support: CaseSupportSnapshot | null;
  onOpenQuestions: () => void;
  onOpenTransactionLookup: () => void;
};

const CATEGORY_LABELS: Record<BriefCategoryKey, string> = { identity: '신분·관계', claim: '상황·사건 주장', demand: '요구 행동', pressure: '압박·연락 통제', money: '금전 관련 정황', exposure: '고객 피해·노출' };
const uniqueText = (items: Array<string | null | undefined>) => [...new Set(items.map((item) => item?.trim()).filter((item): item is string => Boolean(item)))];
const shortTime = (value?: string | null) => value ? new Date(value).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }) : '';
const formatPanelUpdatedAt = (value?: string | null) => {
  if (!value) return '업데이트 : 시간 확인 필요';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return '업데이트 : 시간 확인 필요';
  const formatted = new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: true, timeZone: 'Asia/Seoul',
  }).format(parsed);
  return `업데이트 : ${formatted}`;
};
const includesAny = (value: string, words: string[]) => words.some((word) => value.includes(word));

const compactSummaryText = (value: string) => value
  .replace(/^사건\s*[:：]\s*/, '')
  .replace(/\s+/g, ' ')
  .replace(/\s*[|/]\s*/g, ' · ')
  .replace(/[.!?。]+$/, '')
  .trim();

const buildSummaryHeadline = (caseItem: StoredCase, support: CaseSupportSnapshot | null) => {
  const context = support?.case_context;
  const diagnosis = caseItem.diagnosis.context;
  const claim = compactSummaryText(uniqueText(context?.offender_claims ?? diagnosis?.claims ?? [])[0] ?? '');
  const demand = compactSummaryText(uniqueText(context?.offender_demands ?? diagnosis?.demands ?? [])[0] ?? '');
  if (claim && demand) return `${claim}하며 ${demand}.`;
  if (claim) return `${claim}.`;
  if (demand) return `${demand}.`;
  const source = context?.situation_summary || support?.case_brief?.summary || caseItem.initial_brief || '현재 사건 정보를 준비 중입니다.';
  return `${compactSummaryText(source).split(/[.!?。]/)[0].trim()}.`;
};

const buildSummaryItems = (caseItem: StoredCase, support: CaseSupportSnapshot | null): SummaryItem[] => {
  const context = support?.case_context;
  const diagnosis = caseItem.diagnosis.context;
  const items: SummaryItem[] = [];
  const claims = uniqueText(context?.offender_claims ?? diagnosis?.claims ?? []);
  const demands = uniqueText(context?.offender_demands ?? diagnosis?.demands ?? []);
  const tactics = uniqueText(context?.manipulation_tactics ?? diagnosis?.manipulation_tactics ?? []);
  const exposure = uniqueText(context?.customer_exposure ?? []);
  if (claims[0]) items.push({ label: '상대방 주장', value: claims[0] });
  if (demands[0]) items.push({ label: '요구 행동', value: demands[0] });
  if (tactics[0]) items.push({ label: '압박·통제', value: tactics[0] });
  if (exposure[0]) items.push({ label: '피해·노출', value: exposure[0] });
  else items.push({
    label: '송금 상태',
    value: caseItem.victim_transfer_status === 'YES'
      ? '고객이 실제 송금했다고 진술한 기록 있음.'
      : caseItem.victim_transfer_status === 'NO'
        ? '고객이 송금하지 않았다고 진술한 기록 있음.'
        : '실제 송금 여부 확인 필요.',
  });
  return items.filter((item, index) => items.findIndex((candidate) => candidate.value === item.value) === index).slice(0, 4);
};

const buildBriefCategories = (caseItem: StoredCase, support: CaseSupportSnapshot | null): BriefCategory[] => {
  const context = support?.case_context;
  const diagnosis = caseItem.diagnosis.context;
  const claims = uniqueText(context?.offender_claims ?? diagnosis?.claims ?? []);
  const demands = uniqueText(context?.offender_demands ?? diagnosis?.demands ?? []);
  const tactics = uniqueText(context?.manipulation_tactics ?? diagnosis?.manipulation_tactics ?? []);
  const exposure = uniqueText(context?.customer_exposure ?? []);
  const situation = uniqueText([...(context?.key_signals ?? []), ...(diagnosis?.customer_statements ?? [])]);
  const money: string[] = [];
  if (caseItem.victim_transfer_status === 'YES') money.push('고객이 실제 송금했다고 진술한 기록 있음.');
  else if (caseItem.victim_transfer_status === 'NO') money.push('고객이 송금하지 않았다고 진술한 기록 있음.');
  else money.push('실제 송금 여부 확인 필요.');
  if (demands.some((item) => includesAny(item, ['송금', '이체', '계좌', '환급', '금액']))) money.unshift('송금·이체 요구 정황 있음.');
  return [
    { key: 'identity', label: CATEGORY_LABELS.identity, entries: claims.map((text, index) => ({ id: `identity-${index}`, text })) },
    { key: 'claim', label: CATEGORY_LABELS.claim, entries: situation.map((text, index) => ({ id: `claim-${index}`, text })) },
    { key: 'demand', label: CATEGORY_LABELS.demand, entries: demands.map((text, index) => ({ id: `demand-${index}`, text })) },
    { key: 'pressure', label: CATEGORY_LABELS.pressure, entries: tactics.map((text, index) => ({ id: `pressure-${index}`, text })) },
    { key: 'money', label: CATEGORY_LABELS.money, entries: money.map((text, index) => ({ id: `money-${index}`, text })) },
    { key: 'exposure', label: CATEGORY_LABELS.exposure, entries: exposure.map((text, index) => ({ id: `exposure-${index}`, text })) },
  ];
};

const categoryOpenState = (categories: BriefCategory[]): Record<BriefCategoryKey, boolean> => Object.fromEntries(categories.map((category) => [category.key, category.entries.length > 0])) as Record<BriefCategoryKey, boolean>;

const questionFor = (bundle: CaseBundle, targets: string[]) => bundle.questions.find((question) => targets.some((target) => question.target_field.toUpperCase().includes(target)));
const questionStage = (status?: string): GuideStage => status === 'ANSWERED' ? 'completed' : status === 'ASKED' ? 'inProgress' : 'recommended';
const buildGuides = (caseItem: StoredCase, bundle: CaseBundle, support: CaseSupportSnapshot | null, onQuestions: Props['onOpenQuestions'], onTransactionLookup: Props['onOpenTransactionLookup']): GuideEntry[] => {
  const context = support?.case_context;
  const transferQuestion = questionFor(bundle, ['TRANSFER', '송금', '이체']);
  const exposureQuestion = questionFor(bundle, ['AUTH', 'PERSONAL', '인증', '개인정보']);
  const moneyNeeded = caseItem.victim_transfer_status === 'UNKNOWN' || (context?.offender_demands ?? []).some((item) => includesAny(item, ['송금', '이체', '계좌', '환급']));
  const guides: GuideEntry[] = [];
  if (moneyNeeded) guides.push({ id: 'guide-transfer-lookup', title: '실제 송금 여부 확인', description: '송금 관련 기록 확인 필요.', type: '금융 보호', stage: transferQuestion ? questionStage(transferQuestion.status) : 'recommended', actor: transferQuestion?.requested_by ?? undefined, timestamp: transferQuestion?.answered_at ?? transferQuestion?.asked_at ?? undefined, actionLabel: '송금 기록 조회', onAction: onTransactionLookup });
  guides.push({ id: 'guide-exposure', title: '인증정보 노출 여부 확인', description: '인증번호·비밀번호 제공 여부 확인 필요.', type: '고객 소통', stage: exposureQuestion ? questionStage(exposureQuestion.status) : 'recommended', actor: exposureQuestion?.requested_by ?? undefined, timestamp: exposureQuestion?.answered_at ?? exposureQuestion?.asked_at ?? undefined, actionLabel: '질문 열기', onAction: onQuestions });
  return guides;
};

const stageLabel: Record<GuideStage, string> = { recommended: '추천 방향 (수행 전)', inProgress: '수행 중인 작업', completed: '수행 완료한 작업' };
const stageIcon: Record<GuideStage, React.ReactNode> = { recommended: <Sparkles size={14}/>, inProgress: <ClipboardCheck size={14}/>, completed: <Check size={14}/> };

export const ContextPanelFoundation: React.FC<Props> = ({ open, onToggle, caseItem, bundle, support, onOpenQuestions, onOpenTransactionLookup }) => {
  const initialBrief = useMemo(() => buildBriefCategories(caseItem, support), [caseItem.case_id, caseItem.updated_at, support?.source_revision, support?.projection_revision]);
  const [brief, setBrief] = useState(initialBrief);
  const [archivedBrief, setArchivedBrief] = useState<ArchivedBriefEntry[]>([]);
  const [briefOpen, setBriefOpen] = useState(true);
  const [openCategories, setOpenCategories] = useState<Record<BriefCategoryKey, boolean>>(() => categoryOpenState(initialBrief));
  const [addCategory, setAddCategory] = useState<BriefCategoryKey | null>(null);
  const [newBriefText, setNewBriefText] = useState('');
  const [editingBriefId, setEditingBriefId] = useState<string | null>(null);
  const [editingBriefText, setEditingBriefText] = useState('');
  const [archivedGuides, setArchivedGuides] = useState<string[]>([]);
  const [deletedGuideIds, setDeletedGuideIds] = useState<string[]>([]);
  const [customGuides, setCustomGuides] = useState<GuideEntry[]>([]);
  const [guideOverrides, setGuideOverrides] = useState<Record<string, Partial<GuideEntry>>>({});
  const [editingGuideId, setEditingGuideId] = useState<string | null>(null);
  const [editingGuide, setEditingGuide] = useState({ title: '', description: '' });
  const [showGuideForm, setShowGuideForm] = useState(false);
  const [newGuide, setNewGuide] = useState({ title: '', description: '', type: '기록·증빙' as GuideType });
  const [guideOpen, setGuideOpen] = useState<Record<GuideStage, boolean>>({ recommended: true, inProgress: true, completed: false });
  const [guideSectionOpen, setGuideSectionOpen] = useState(true);
  const [summaryExpanded, setSummaryExpanded] = useState(false);

  useEffect(() => {
    setBrief(initialBrief);
    setOpenCategories(categoryOpenState(initialBrief));
    setArchivedBrief([]);
    setArchivedGuides([]);
    setCustomGuides([]);
    setGuideOverrides({});
  }, [initialBrief]);
  useEffect(() => {
    setDeletedGuideIds([]);
  }, [caseItem.case_id]);
  const baseGuides = useMemo(() => buildGuides(caseItem, bundle, support, onOpenQuestions, onOpenTransactionLookup), [caseItem.case_id, caseItem.updated_at, bundle.questions, support?.source_revision]);
  const guides = useMemo(() => [...baseGuides, ...customGuides].filter((item) => !deletedGuideIds.includes(item.id)).map((item) => ({ ...item, ...guideOverrides[item.id] })), [baseGuides, customGuides, deletedGuideIds, guideOverrides]);
  const activeGuides = guides.filter((item) => !archivedGuides.includes(item.id));
  const archivedGuideItems = guides.filter((item) => archivedGuides.includes(item.id));
  const summary = useMemo(() => buildSummaryHeadline(caseItem, support), [caseItem.case_id, caseItem.initial_brief, caseItem.updated_at, support?.source_revision, support?.projection_revision]);
  const summaryItems = useMemo(() => buildSummaryItems(caseItem, support), [caseItem.case_id, caseItem.updated_at, caseItem.victim_transfer_status, support?.source_revision, support?.projection_revision]);
  const summaryCanExpand = summary.length > 90 || summaryItems.length > 0;
  useEffect(() => setSummaryExpanded(false), [summary]);
  const updateBriefItem = (categoryKey: BriefCategoryKey, itemId: string, text: string) => setBrief((current) => current.map((category) => category.key === categoryKey ? { ...category, entries: category.entries.map((entry) => entry.id === itemId ? { ...entry, text } : entry) } : category));
  const archiveBriefItem = (categoryKey: BriefCategoryKey, entry: BriefEntry) => { setBrief((current) => current.map((category) => category.key === categoryKey ? { ...category, entries: category.entries.filter((item) => item.id !== entry.id) } : category)); setArchivedBrief((current) => [...current, { ...entry, categoryKey }]); };
  const addBriefItem = () => { const text = newBriefText.trim(); if (!addCategory || !text) return; const entry = { id: `staff-${Date.now()}`, text }; setBrief((current) => current.map((category) => category.key === addCategory ? { ...category, entries: [...category.entries, entry] } : category)); setNewBriefText(''); setAddCategory(null); };
  const addGuideItem = () => { const title = newGuide.title.trim(); const description = newGuide.description.trim(); if (!title || !description) return; const id = `staff-guide-${Date.now()}`; setCustomGuides((current) => [...current, { id, title, description, type: newGuide.type, stage: 'recommended' }]); setArchivedGuides((current) => current.filter((item) => item !== id)); setNewGuide({ title: '', description: '', type: '기록·증빙' }); setShowGuideForm(false); };
  const permanentlyDeleteGuide = (item: GuideEntry) => { if (!window.confirm('완전 삭제하면 복구가 불가능 합니다. 삭제하시겠습니까?')) return; setDeletedGuideIds((current) => [...current, item.id]); setArchivedGuides((current) => current.filter((id) => id !== item.id)); setCustomGuides((current) => current.filter((guide) => guide.id !== item.id)); };
  const permanentlyDeleteBrief = (entry: ArchivedBriefEntry) => { if (!window.confirm('완전 삭제하면 복구가 불가능 합니다. 삭제하시겠습니까?')) return; setArchivedBrief((current) => current.filter((item) => item.id !== entry.id)); };
  const groupedGuides = (stage: GuideStage) => activeGuides.filter((item) => item.stage === stage);
  const renderGuide = (item: GuideEntry) => editingGuideId === item.id ? <form className="right-panel-inline-form" key={item.id} onSubmit={(event) => { event.preventDefault(); setGuideOverrides((current) => ({ ...current, [item.id]: { title: editingGuide.title.trim(), description: editingGuide.description.trim() } })); setEditingGuideId(null); }}><input value={editingGuide.title} onChange={(event) => setEditingGuide((current) => ({ ...current, title: event.target.value }))}/><textarea value={editingGuide.description} onChange={(event) => setEditingGuide((current) => ({ ...current, description: event.target.value }))}/><div><button type="button" onClick={() => setEditingGuideId(null)}>취소</button><button type="submit" disabled={!editingGuide.title.trim() || !editingGuide.description.trim()}><Check size={13}/>저장</button></div></form> : <article className={`right-panel-guide-row is-${item.stage}`} key={item.id}><div className="right-panel-guide-copy"><div className="right-panel-guide-title"><strong>{item.title}</strong><span>{item.type}</span></div><p>{item.description}</p>{item.actor && item.stage !== 'recommended' && <small>{item.actor} · {shortTime(item.timestamp)}</small>}</div><div className="right-panel-row-actions">{item.actionLabel && item.onAction && <button type="button" className="right-panel-link-action" onClick={item.onAction}>{item.actionLabel}</button>}<span className="right-panel-edit-actions"><button type="button" className="right-panel-icon-button" aria-label={`${item.title} 수정`} title="수정" onClick={() => { setEditingGuideId(item.id); setEditingGuide({ title: item.title, description: item.description }); }}><Pencil size={13}/></button><button type="button" className="right-panel-icon-button" aria-label={`${item.title} 보관`} title="보관" onClick={() => setArchivedGuides((current) => [...current, item.id])}><Archive size={13}/></button></span></div></article>;
  const renderBriefCategory = (category: BriefCategory) => <section className={`right-panel-brief-category ${category.entries.length === 0 ? 'is-empty' : ''}`} key={category.key}><header><button type="button" className="right-panel-category-toggle" disabled={category.entries.length === 0} aria-expanded={category.entries.length > 0 && openCategories[category.key]} onClick={() => setOpenCategories((current) => ({ ...current, [category.key]: !current[category.key] }))}><span>{category.label}</span><small>{category.entries.length}건</small>{category.entries.length > 0 && (openCategories[category.key] ? <ChevronUp size={15}/> : <ChevronDown size={15}/>)}</button><button type="button" className="right-panel-icon-button" aria-label={`${category.label} 정황 추가`} title="정황 추가" onClick={() => { setAddCategory(category.key); setOpenCategories((current) => ({ ...current, [category.key]: true })); }}><Plus size={14}/></button></header>{openCategories[category.key] && <div className="right-panel-brief-items">{category.entries.map((entry) => editingBriefId === entry.id ? <form className="right-panel-inline-form" key={entry.id} onSubmit={(event) => { event.preventDefault(); updateBriefItem(category.key, entry.id, editingBriefText.trim()); setEditingBriefId(null); }}><textarea value={editingBriefText} onChange={(event) => setEditingBriefText(event.target.value)}/><div><button type="button" onClick={() => setEditingBriefId(null)}>취소</button><button type="submit" disabled={!editingBriefText.trim()}><Check size={13}/>저장</button></div></form> : <div className="right-panel-brief-item" key={entry.id}><p>{entry.text}</p><span className="right-panel-row-actions right-panel-edit-actions"><button type="button" className="right-panel-icon-button" aria-label={`${category.label} 정황 수정`} title="수정" onClick={() => { setEditingBriefId(entry.id); setEditingBriefText(entry.text); }}><Pencil size={12}/></button><button type="button" className="right-panel-icon-button" aria-label={`${category.label} 정황 보관`} title="보관" onClick={() => archiveBriefItem(category.key, entry)}><Archive size={12}/></button></span></div>)}{addCategory === category.key && <form className="right-panel-inline-form" onSubmit={(event) => { event.preventDefault(); addBriefItem(); }}><textarea autoFocus value={newBriefText} onChange={(event) => setNewBriefText(event.target.value)} placeholder="정황 문장을 입력하세요."/><div><button type="button" onClick={() => { setAddCategory(null); setNewBriefText(''); }}>취소</button><button type="submit" disabled={!newBriefText.trim()}><Plus size={13}/>추가</button></div></form>}</div>}</section>;
 return <aside className={`context-panel context-panel-v3 context-panel-foundation ${open ? 'is-open' : ''}`} aria-label="우측 사건 패널"><div className="context-header context-v3-sticky-header"><div><h2>사건 현황</h2><small>{formatPanelUpdatedAt(caseItem.updated_at)}</small></div><button type="button" className="context-open context-header-toggle" onClick={onToggle} aria-label={open ? '사건 패널 닫기' : '사건 패널 열기'} title={open ? '사건 패널 닫기' : '사건 패널 열기'}>{open ? <PanelRightClose size={17}/> : <PanelRightOpen size={17}/>}</button></div><div className="right-panel-scroll"><section className={`right-panel-one-line ${summaryExpanded ? 'is-expanded' : ''}`}><span>현재 사건 요약</span><p className="right-panel-summary-headline">{summary}</p>{summaryExpanded && <ul className="right-panel-summary-list">{summaryItems.map((item) => <li key={`${item.label}:${item.value}`}><strong>{item.label}</strong><span>{item.value}</span></li>)}</ul>}{summaryCanExpand && <button type="button" className="right-panel-summary-toggle" onClick={() => setSummaryExpanded((current) => !current)}>{summaryExpanded ? '간단히 보기' : '세부 정황 보기'}{summaryExpanded ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}</button>}</section><section className="right-panel-block"><header className="right-panel-block-header"><button type="button" onClick={() => setGuideSectionOpen((current) => !current)}><strong>1. 은행 직원 대응 가이드</strong>{guideSectionOpen ? <ChevronUp size={15}/> : <ChevronDown size={15}/>}</button><button type="button" className="right-panel-icon-button" aria-label="대응 가이드 추가" title="대응 가이드 추가" onClick={() => setShowGuideForm((current) => !current)}><Plus size={14}/></button></header>{guideSectionOpen && <>{showGuideForm && <form className="right-panel-guide-form" onSubmit={(event) => { event.preventDefault(); addGuideItem(); }}><input autoFocus value={newGuide.title} onChange={(event) => setNewGuide((current) => ({ ...current, title: event.target.value }))} placeholder="대응 항목"/><textarea value={newGuide.description} onChange={(event) => setNewGuide((current) => ({ ...current, description: event.target.value }))} placeholder="직원이 해야 할 일을 짧게 입력하세요."/><select value={newGuide.type} onChange={(event) => setNewGuide((current) => ({ ...current, type: event.target.value as GuideType }))}><option>고객 소통</option><option>금융 보호</option><option>기록·증빙</option></select><div><button type="button" onClick={() => setShowGuideForm(false)}>취소</button><button type="submit" disabled={!newGuide.title.trim() || !newGuide.description.trim()}><Plus size={13}/>추가</button></div></form>}<div className="right-panel-guide-lanes">{(['recommended', 'inProgress', 'completed'] as GuideStage[]).map((stage) => <section className={`right-panel-guide-lane is-${stage}`} key={stage}><button type="button" className="right-panel-lane-header" aria-expanded={guideOpen[stage]} onClick={() => setGuideOpen((current) => ({ ...current, [stage]: !current[stage] }))}><span>{stageIcon[stage]}{stageLabel[stage]}</span><b>{groupedGuides(stage).length}건</b>{guideOpen[stage] ? <ChevronUp size={13}/> : <ChevronDown size={15}/>}</button>{guideOpen[stage] && <div className="right-panel-guide-list">{groupedGuides(stage).length ? groupedGuides(stage).map(renderGuide) : <p className="right-panel-empty">등록된 작업 없음.</p>}</div>}</section>)}{archivedGuideItems.length > 0 && <details className="right-panel-archive"><summary><Archive size={13}/>제외·보관된 작업 {archivedGuideItems.length}건</summary>{archivedGuideItems.map((item) => <div className="right-panel-archive-row" key={item.id}><span>{item.title}</span><div className="right-panel-archive-actions"><button type="button" className="right-panel-icon-button" aria-label={`${item.title} 복구`} title="복구" onClick={() => setArchivedGuides((current) => current.filter((id) => id !== item.id))}><RotateCcw size={12}/></button><button type="button" className="right-panel-permanent-delete" onClick={() => permanentlyDeleteGuide(item)}>완전 삭제</button></div></div>)}</details>}</div></>}</section><section className="right-panel-block"><header className="right-panel-block-header"><button type="button" onClick={() => setBriefOpen((current) => !current)}><strong>2. 현재 사건 브리핑</strong>{briefOpen ? <ChevronUp size={15}/> : <ChevronDown size={15}/>}</button><span className="right-panel-ai-note"><Sparkles size={13}/>AI·담당자 정리</span></header>{briefOpen && <div className="right-panel-brief"><section className="right-panel-brief-section"><header><h3>주요 보이스피싱 정황</h3><button type="button" className="right-panel-icon-button" aria-label="주요 정황 추가" title="정황 추가" onClick={() => { setAddCategory('claim'); setOpenCategories((current) => ({ ...current, claim: true })); }}><Plus size={14}/></button></header><div className="right-panel-category-list">{brief.map(renderBriefCategory)}</div></section>{archivedBrief.length > 0 && <details className="right-panel-archive"><summary><Archive size={13}/>제외·보관된 정황 {archivedBrief.length}건</summary>{archivedBrief.map((entry) => <div className="right-panel-archive-row" key={entry.id}><span>{entry.text}</span><div className="right-panel-archive-actions"><button type="button" className="right-panel-icon-button" aria-label="정황 복구" title="복구" onClick={() => { setArchivedBrief((current) => current.filter((item) => item.id !== entry.id)); setBrief((current) => current.map((category) => category.key === entry.categoryKey ? { ...category, entries: [...category.entries, { id: entry.id, text: entry.text }] } : category)); }}><RotateCcw size={12}/></button><button type="button" className="right-panel-permanent-delete" onClick={() => permanentlyDeleteBrief(entry)}>완전 삭제</button></div></div>)}</details>}</div>}</section></div></aside>;
};
