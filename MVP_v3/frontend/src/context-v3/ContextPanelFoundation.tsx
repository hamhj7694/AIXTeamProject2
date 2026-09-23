import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Archive, Check, ChevronDown, ChevronUp, ClipboardCheck, Loader2, MoreHorizontal, PanelRightClose, PanelRightOpen, Pencil, Plus, RotateCcw, Sparkles, UserRound } from 'lucide-react';
import { casesApi, CURRENT_BANK_USER } from '../api/cases';
import type { CaseBundle, CaseSupportSnapshot, StoredCase } from '../api/types';

type BriefCategoryKey = 'identity' | 'claim' | 'demand' | 'pressure' | 'money' | 'exposure';
type GuideStage = 'recommended' | 'inProgress' | 'completed';
type GuideActionKey = 'CUSTOMER_QUESTION' | 'TRANSACTION_LOOKUP' | 'OFFICIAL_VERIFICATION' | 'RESPONSE_ACTION' | 'NONE';
type GuideType = '고객 소통' | '금융 보호' | '기록·증빙';
type BriefEntry = { id: string; text: string };
type ArchivedBriefEntry = BriefEntry & { categoryKey: BriefCategoryKey };
type BriefCategory = { key: BriefCategoryKey; label: string; entries: BriefEntry[] };
type GuideStep = { id: string; title: string; description?: string; completed?: boolean; archived?: boolean; actor?: string; timestamp?: string; actionKey?: GuideActionKey; actionLabel?: string; onAction?: () => void };
type GuideEntry = { id: string; title: string; description: string; contextSummary?: string; type: GuideType; stage: GuideStage; actor?: string; timestamp?: string; actionKey?: GuideActionKey; actionLabel?: string; onAction?: () => void; steps?: GuideStep[] };
type SummaryItem = { label: string; value: string };
type AssigneeOption = { name: string; role?: string; displayRole?: string | null; positionTitle?: string | null };
type RowAction = { label: string; title: string; icon: React.ReactNode; onClick: () => void; danger?: boolean };
type NewGuideDraft = { parentId: string; parentTitle: string; stepTitle: string; stepDescription: string };

const RightPanelRowActions: React.FC<{ actions: RowAction[] }> = ({ actions }) => {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return undefined;
    const closeOnOutsidePointer = (event: PointerEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('pointerdown', closeOnOutsidePointer);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsidePointer);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [open]);

  return <div ref={menuRef} className={`right-panel-row-actions${open ? ' is-open' : ''}`}>
    <button type="button" className="right-panel-row-menu-trigger" aria-label="추가 작업 열기" aria-expanded={open} title="추가 작업" onClick={() => setOpen((current) => !current)}><MoreHorizontal size={15}/></button>
    {open && <div className="right-panel-row-action-menu" role="menu">{actions.map((action) => <button key={action.label} type="button" className={`right-panel-row-action${action.danger ? ' is-danger' : ''}`} role="menuitem" title={action.title} onClick={() => { setOpen(false); action.onClick(); }}>{action.icon}<span>{action.label}</span></button>)}</div>}
  </div>;
};

type Props = {
  open: boolean;
  onToggle: () => void;
  caseItem: StoredCase;
  bundle: CaseBundle;
  support: CaseSupportSnapshot | null;
  onOpenQuestions: () => void;
  onOpenTransactionLookup: () => void;
  onOpenVerification: () => void;
  onOpenAction: () => void;
  assigneeOptions?: AssigneeOption[];
};

const CATEGORY_LABELS: Record<BriefCategoryKey, string> = { identity: '신분·관계', claim: '상황·사건 주장', demand: '요구 행동', pressure: '압박·연락 통제', money: '금전 관련 정황', exposure: '고객 피해·노출' };
const uniqueText = (items: Array<string | null | undefined>) => [...new Set(items.map((item) => item?.trim()).filter((item): item is string => Boolean(item)))];
const orderByConversationTurn = (items: string[], narratives: Array<{ sentence: string; source_turns: number[] }> = []) => items.map((text, index) => {
  const narrative = narratives.find((item) => item.sentence === text || item.sentence.includes(text) || text.includes(item.sentence));
  return { text, index, turn: narrative?.source_turns?.[0] ?? Number.MAX_SAFE_INTEGER };
}).sort((left, right) => left.turn - right.turn || left.index - right.index).map((item) => item.text);
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
  const latestSummary = context?.situation_summary || support?.case_brief?.summary;
  if (latestSummary) return `${compactSummaryText(latestSummary).split(/[.!?。]/)[0].trim()}.`;
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
  const narratives = diagnosis?.feature_narratives ?? [];
  const claims = orderByConversationTurn(uniqueText(context?.offender_claims ?? diagnosis?.claims ?? []), narratives);
  const demands = orderByConversationTurn(uniqueText(context?.offender_demands ?? diagnosis?.demands ?? []), narratives);
  const tactics = orderByConversationTurn(uniqueText(context?.manipulation_tactics ?? diagnosis?.manipulation_tactics ?? []), narratives);
  const exposure = orderByConversationTurn(uniqueText(context?.customer_exposure ?? []), narratives);
  const situation = orderByConversationTurn(uniqueText([...(context?.key_signals ?? []), ...(diagnosis?.customer_statements ?? [])]), narratives);
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
const actionLabelFor = (actionKey: GuideActionKey) => ({ CUSTOMER_QUESTION: '질문 열기', TRANSACTION_LOOKUP: '송금 기록 조회', OFFICIAL_VERIFICATION: '기관 확인 열기', RESPONSE_ACTION: '대응 조치 열기', NONE: '' }[actionKey]);
const guideActionFor = (value: string): GuideActionKey => {
  if (includesAny(value, ['송금', '이체', '거래', '금액'])) return 'TRANSACTION_LOOKUP';
  if (includesAny(value, ['기관', '소속', '공식', '신고'])) return 'OFFICIAL_VERIFICATION';
  if (includesAny(value, ['고객', '확인 질문', '진술'])) return 'CUSTOMER_QUESTION';
  if (includesAny(value, ['조치', '구제', '지급정지', '보호', '기록'])) return 'RESPONSE_ACTION';
  return 'NONE';
};
const buildGuides = (caseItem: StoredCase, bundle: CaseBundle, support: CaseSupportSnapshot | null, onQuestions: Props['onOpenQuestions'], onTransactionLookup: Props['onOpenTransactionLookup'], onVerification: Props['onOpenVerification'], onAction: Props['onOpenAction']): GuideEntry[] => {
  const context = support?.case_context;
  const transferQuestion = questionFor(bundle, ['TRANSFER', '송금', '이체']);
  const exposureQuestion = questionFor(bundle, ['AUTH', 'PERSONAL', '인증', '개인정보']);
  const claims = uniqueText(context?.offender_claims ?? []);
  const demands = uniqueText(context?.offender_demands ?? []);
  const exposure = uniqueText(context?.customer_exposure ?? []);
  const transferSignals = uniqueText([
    ...demands.filter((item) => includesAny(item, ['송금', '이체', '계좌', '환급', '금액'])),
    caseItem.victim_transfer_status === 'YES' ? '고객이 실제 송금했다고 진술한 기록 있음' : null,
    caseItem.victim_transfer_status === 'NO' ? '고객이 송금하지 않았다고 진술한 기록 있음' : null,
  ]);
  const contextLine = (signal: string | undefined, suffix: string, fallback: string) => signal ? `${compactSummaryText(signal)}. ${suffix}` : fallback;
  const transferContext = contextLine(transferSignals[0], '실제 송금 여부·시점·경로 확인 필요.', '실제 송금 여부·시점·경로 확인 필요.');
  const exposureContext = contextLine(exposure[0] ?? demands.find((item) => includesAny(item, ['인증', '비밀번호', 'OTP', '개인정보'])), '고객이 제공한 인증정보 범위 확인 필요.', '인증번호·비밀번호 제공 여부 확인 필요.');
  const officialContext = contextLine(claims.find((item) => includesAny(item, ['기관', '검찰', '경찰', '은행', '사칭'])), '기관명·소속·연락처를 공식 채널에서 대조 필요.', '상대방이 주장한 기관과 공식 연락처 확인 필요.');
  const responseContext = contextLine(demands.find((item) => includesAny(item, ['송금', '이체', '안전계좌', '지급정지', '신고'])), '추가 송금 방지와 필요한 보호 조치 확인 필요.', '현재 정황에 맞는 보호·신고·후속 조치 확인 필요.');
  const moneyNeeded = caseItem.victim_transfer_status === 'UNKNOWN' || demands.some((item) => includesAny(item, ['송금', '이체', '계좌', '환급']));
  const guides: GuideEntry[] = [];
  if (moneyNeeded) guides.push({ id: 'guide-transfer-lookup', title: '실제 송금 여부 확인', description: '송금 관련 기록 확인 필요.', contextSummary: transferContext, type: '금융 보호', stage: transferQuestion ? questionStage(transferQuestion.status) : 'recommended', actor: transferQuestion?.requested_by ?? undefined, timestamp: transferQuestion?.answered_at ?? transferQuestion?.asked_at ?? undefined, actionKey: 'TRANSACTION_LOOKUP', actionLabel: actionLabelFor('TRANSACTION_LOOKUP'), onAction: onTransactionLookup });
  guides.push({ id: 'guide-exposure', title: '인증정보 노출 여부 확인', description: '인증번호·비밀번호 제공 여부 확인 필요.', contextSummary: exposureContext, type: '고객 소통', stage: exposureQuestion ? questionStage(exposureQuestion.status) : 'recommended', actor: exposureQuestion?.requested_by ?? undefined, timestamp: exposureQuestion?.answered_at ?? exposureQuestion?.asked_at ?? undefined, actionKey: 'CUSTOMER_QUESTION', actionLabel: actionLabelFor('CUSTOMER_QUESTION'), onAction: onQuestions });
  const needsOfficialVerification = (context?.offender_claims ?? []).some((item) => includesAny(item, ['기관', '검찰', '경찰', '은행', '사칭']));
  if (needsOfficialVerification) guides.push({ id: 'guide-official-verification', title: '기관·소속 공식 여부 확인', description: '상대방이 주장한 기관과 연락처를 공식 채널에서 확인해야 합니다.', contextSummary: officialContext, type: '금융 보호', stage: 'recommended', actionKey: 'OFFICIAL_VERIFICATION', actionLabel: actionLabelFor('OFFICIAL_VERIFICATION'), onAction: onVerification });
  const needsResponseAction = (context?.offender_demands ?? []).some((item) => includesAny(item, ['송금', '이체', '안전계좌', '지급정지', '신고']));
  if (needsResponseAction) guides.push({ id: 'guide-response-action', title: '필요한 대응 조치 검토', description: '현재 정황에 맞는 보호·신고·후속 조치를 검토해야 합니다.', contextSummary: responseContext, type: '금융 보호', stage: 'recommended', actionKey: 'RESPONSE_ACTION', actionLabel: actionLabelFor('RESPONSE_ACTION'), onAction });
  const defaultSteps: Record<string, GuideStep[]> = {
    'guide-transfer-lookup': [
      { id: 'guide-transfer-lookup-statement', title: '고객 송금 진술 확인', description: '고객이 설명한 송금 시점과 경로를 확인합니다.', actionKey: 'CUSTOMER_QUESTION', actionLabel: actionLabelFor('CUSTOMER_QUESTION'), onAction: onQuestions },
      { id: 'guide-transfer-lookup-record', title: '거래 기록 조회', description: '확인 가능한 거래·이체 기록을 조회합니다.', actionKey: 'TRANSACTION_LOOKUP', actionLabel: actionLabelFor('TRANSACTION_LOOKUP'), onAction: onTransactionLookup },
      { id: 'guide-transfer-lookup-result', title: '실제 송금 여부 기록', description: '조회 결과와 추가 확인이 필요한 내용을 기록합니다.' },
    ],
    'guide-exposure': [
      { id: 'guide-exposure-customer', title: '고객 인증정보 제공 여부 확인', description: '고객에게 제공한 정보의 범위를 확인합니다.', actionKey: 'CUSTOMER_QUESTION', actionLabel: actionLabelFor('CUSTOMER_QUESTION'), onAction: onQuestions },
      { id: 'guide-exposure-scope', title: '노출 정보 범위 기록', description: '노출 가능성이 있는 정보와 후속 보호 조치를 기록합니다.' },
    ],
    'guide-official-verification': [
      { id: 'guide-official-verification-target', title: '주장 기관·부서 확인', description: '고객이 전달받은 기관명과 부서를 정리합니다.' },
      { id: 'guide-official-verification-channel', title: '공식 채널로 사실 확인', description: '등록된 공식 연락처와 확인 결과를 대조합니다.', actionKey: 'OFFICIAL_VERIFICATION', actionLabel: actionLabelFor('OFFICIAL_VERIFICATION'), onAction: onVerification },
      { id: 'guide-official-verification-record', title: '확인 결과 기록', description: '기관 회신과 내부 판단에 필요한 근거를 남깁니다.' },
    ],
    'guide-response-action': [
      { id: 'guide-response-action-relief', title: '피해 구제 절차 검토', description: '현재 상황에서 안내·접수 가능한 절차를 확인합니다.', actionKey: 'RESPONSE_ACTION', actionLabel: actionLabelFor('RESPONSE_ACTION'), onAction },
      { id: 'guide-response-action-stop', title: '지급정지·이체 취소 가능 여부 검토', description: '송금 상태와 내부 기준에 따라 가능한 조치를 검토합니다.', actionKey: 'TRANSACTION_LOOKUP', actionLabel: actionLabelFor('TRANSACTION_LOOKUP'), onAction: onTransactionLookup },
      { id: 'guide-response-action-report', title: '신고·내부 보고 기록', description: '필요한 신고와 내부 공유 결과를 기록합니다.' },
    ],
  };
  return guides.map((guide) => ({ ...guide, steps: guide.steps ?? defaultSteps[guide.id] }));
};

const stageLabel: Record<GuideStage, string> = { recommended: '수행 추천', inProgress: '수행 중인 작업', completed: '수행 완료한 작업' };
const stageIcon: Record<GuideStage, React.ReactNode> = { recommended: <Sparkles size={14}/>, inProgress: <ClipboardCheck size={14}/>, completed: <Check size={14}/> };

export const ContextPanelFoundation: React.FC<Props> = ({ open, onToggle, caseItem, bundle, support, onOpenQuestions, onOpenTransactionLookup, onOpenVerification, onOpenAction, assigneeOptions = [] }) => {
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
  const [newGuideSteps, setNewGuideSteps] = useState<GuideStep[]>([]);
  const [expandedGuideIds, setExpandedGuideIds] = useState<Record<string, boolean>>({});
  const [editingGuideId, setEditingGuideId] = useState<string | null>(null);
  const [editingGuide, setEditingGuide] = useState({ title: '', description: '' });
  const [editingGuideStep, setEditingGuideStep] = useState<{ guideId: string; stepId: string; title: string; description: string } | null>(null);
  const [showGuideForm, setShowGuideForm] = useState(false);
  const [newGuide, setNewGuide] = useState<NewGuideDraft>({ parentId: '', parentTitle: '', stepTitle: '', stepDescription: '' });
  const [guideAiBusy, setGuideAiBusy] = useState(false);
  const [guideAiMessage, setGuideAiMessage] = useState('');
  const [guideOpen, setGuideOpen] = useState<Record<GuideStage, boolean>>({ recommended: true, inProgress: false, completed: false });
  const [guideSectionOpen, setGuideSectionOpen] = useState(true);
  const [summaryExpanded, setSummaryExpanded] = useState(false);
  const previousInProgressCount = useRef<number | null>(null);
  const [assigningGuideId, setAssigningGuideId] = useState<string | null>(null);
  const [assigningStepKey, setAssigningStepKey] = useState<string | null>(null);
  const [selectedAssignee, setSelectedAssignee] = useState('');

  useEffect(() => {
    setBrief(initialBrief);
    setOpenCategories(categoryOpenState(initialBrief));
    setArchivedBrief([]);
    setArchivedGuides([]);
    setCustomGuides([]);
    setGuideOverrides({});
    setNewGuideSteps([]);
    setExpandedGuideIds({});
    setEditingGuideStep(null);
    setAssigningGuideId(null);
    setAssigningStepKey(null);
    setSelectedAssignee('');
  }, [initialBrief]);
  useEffect(() => {
    setDeletedGuideIds([]);
  }, [caseItem.case_id]);
  const baseGuides = useMemo(() => buildGuides(caseItem, bundle, support, onOpenQuestions, onOpenTransactionLookup, onOpenVerification, onOpenAction).filter((item) => item.id !== 'guide-response-action'), [caseItem.case_id, caseItem.updated_at, bundle.questions, support?.source_revision, onOpenQuestions, onOpenTransactionLookup, onOpenVerification, onOpenAction]);
  const guides = useMemo(() => [...baseGuides, ...customGuides].filter((item) => !deletedGuideIds.includes(item.id)).map((item) => ({ ...item, ...guideOverrides[item.id] })), [baseGuides, customGuides, deletedGuideIds, guideOverrides]);
  const activeGuides = guides.filter((item) => !archivedGuides.includes(item.id));
  const availableAssignees = useMemo(() => {
    const options: AssigneeOption[] = [{ name: CURRENT_BANK_USER.display_name, role: '현재 사용자' }, ...assigneeOptions, ...activeGuides.flatMap((item) => [
      { name: item.actor ?? '' },
      ...(item.steps ?? []).map((step) => ({ name: step.actor ?? '' })),
    ])];
    return options.filter((item, index) => item.name.trim() && options.findIndex((candidate) => candidate.name === item.name) === index);
  }, [activeGuides, assigneeOptions]);
  const inProgressCount = activeGuides.filter((item) => item.stage === 'inProgress').length;
  useEffect(() => {
    const previousCount = previousInProgressCount.current;
    if (previousCount === 0 && inProgressCount > 0) {
      setGuideOpen((current) => ({ ...current, inProgress: true }));
    }
    previousInProgressCount.current = inProgressCount;
  }, [inProgressCount]);
  useEffect(() => {
    previousInProgressCount.current = inProgressCount;
    setGuideOpen((current) => ({ ...current, inProgress: false }));
  }, [caseItem.case_id]);
  const archivedGuideItems = guides.filter((item) => archivedGuides.includes(item.id));
  const summary = useMemo(() => buildSummaryHeadline(caseItem, support), [caseItem.case_id, caseItem.initial_brief, caseItem.updated_at, support?.source_revision, support?.projection_revision]);
  const summaryItems = useMemo(() => {
    const latestByCategory = brief.flatMap((category) => {
      const latest = category.entries[category.entries.length - 1];
      return latest ? [{ label: category.label, value: latest.text }] : [];
    });
    return latestByCategory.length > 0
      ? latestByCategory
      : buildSummaryItems(caseItem, support);
  }, [brief, caseItem.case_id, caseItem.updated_at, caseItem.victim_transfer_status, support?.source_revision, support?.projection_revision]);
  const summaryCanExpand = summary.length > 90 || summaryItems.length > 0;
  useEffect(() => setSummaryExpanded(false), [summary]);
  const updateBriefItem = (categoryKey: BriefCategoryKey, itemId: string, text: string) => setBrief((current) => current.map((category) => category.key === categoryKey ? { ...category, entries: category.entries.map((entry) => entry.id === itemId ? { ...entry, text } : entry) } : category));
  const archiveBriefItem = (categoryKey: BriefCategoryKey, entry: BriefEntry) => { setBrief((current) => current.map((category) => category.key === categoryKey ? { ...category, entries: category.entries.filter((item) => item.id !== entry.id) } : category)); setArchivedBrief((current) => [...current, { ...entry, categoryKey }]); };
  const addBriefItem = () => { const text = newBriefText.trim(); if (!addCategory || !text) return; const entry = { id: `staff-${Date.now()}`, text }; setBrief((current) => current.map((category) => category.key === addCategory ? { ...category, entries: [...category.entries, entry] } : category)); setNewBriefText(''); setAddCategory(null); };
  const addGuideItem = () => {
    const parentId = newGuide.parentId.trim();
    const parentTitle = newGuide.parentTitle.trim();
    const stepTitle = newGuide.stepTitle.trim();
    const stepDescription = newGuide.stepDescription.trim();
    if (!parentId || (parentId === '__new__' && !parentTitle) || !stepTitle || !stepDescription) return;
    const steps = [{ id: `staff-guide-step-${Date.now()}`, title: stepTitle, description: stepDescription }, ...newGuideSteps];
    if (parentId === '__new__') {
      const id = `staff-guide-${Date.now()}`;
      setCustomGuides((current) => [...current, { id, title: parentTitle, description: '', type: '기록·증빙', stage: 'recommended', steps }]);
      setArchivedGuides((current) => current.filter((item) => item !== id));
      setExpandedGuideIds((current) => ({ ...current, [id]: true }));
    } else {
      const parent = guides.find((item) => item.id === parentId);
      if (!parent) return;
      setGuideOverrides((current) => ({ ...current, [parentId]: { ...current[parentId], steps: [...(parent.steps ?? []), ...steps] } }));
      setExpandedGuideIds((current) => ({ ...current, [parentId]: true }));
    }
    setNewGuide({ parentId: '', parentTitle: '', stepTitle: '', stepDescription: '' });
    setNewGuideSteps([]);
    setGuideAiMessage('');
    setShowGuideForm(false);
  };
  const recommendGuide = async () => {
    if (guideAiBusy) return;
    setGuideAiBusy(true); setGuideAiMessage('');
    try {
      const card = await casesApi.generateWorkCard(caseItem.case_id, 'BANK_ACTION');
      const suggestion = card.suggested_actions?.[0];
      const title = suggestion?.title?.trim() || card.suggested_action_type?.trim() || card.title?.trim() || '';
      const description = suggestion?.note?.trim() || card.suggested_action_note?.trim() || card.next_action?.trim() || card.summary?.trim() || '';
      const steps = (suggestion?.steps ?? []).slice(0, 8).map((step, index) => {
        const title = step.title.trim();
        const description = step.note?.trim() || undefined;
        const actionKey = guideActionFor(`${title} ${description ?? ''}`);
        const actionProps = actionKey === 'CUSTOMER_QUESTION'
          ? { actionKey, actionLabel: actionLabelFor(actionKey), onAction: onOpenQuestions }
          : actionKey === 'TRANSACTION_LOOKUP'
            ? { actionKey, actionLabel: actionLabelFor(actionKey), onAction: onOpenTransactionLookup }
            : actionKey === 'OFFICIAL_VERIFICATION'
              ? { actionKey, actionLabel: actionLabelFor(actionKey), onAction: onOpenVerification }
              : actionKey === 'RESPONSE_ACTION'
                ? { actionKey, actionLabel: actionLabelFor(actionKey), onAction: onOpenAction }
                : {};
        return { id: `ai-guide-step-${Date.now()}-${index}`, title, description, ...actionProps };
      }).filter((step) => step.title);
      if (!title || !description) {
        setGuideAiMessage('현재 사건에서 추천할 대응 가이드 초안을 만들지 못했습니다. 직접 입력해 주세요.');
        return;
      }
      const firstStep = steps[0] ?? { title, description };
      setNewGuide({ parentId: '__new__', parentTitle: title, stepTitle: firstStep.title, stepDescription: firstStep.description ?? description });
      setNewGuideSteps(steps.slice(1));
      setGuideAiMessage(steps.length > 0 ? `AI 추천 내용을 입력했습니다. 하위 단계 ${steps.length}개가 함께 추가됩니다. 검토 후 추가해 주세요.` : 'AI 추천 내용을 입력했습니다. 검토 후 추가해 주세요.');
    } catch (reason) {
      setGuideAiMessage(reason instanceof Error ? reason.message : 'AI 추천을 불러오지 못했습니다. 직접 입력해 주세요.');
    } finally {
      setGuideAiBusy(false);
    }
  };
  const permanentlyDeleteGuide = (item: GuideEntry) => { if (!window.confirm('완전 삭제하면 복구가 불가능 합니다. 삭제하시겠습니까?')) return; setDeletedGuideIds((current) => [...current, item.id]); setArchivedGuides((current) => current.filter((id) => id !== item.id)); setCustomGuides((current) => current.filter((guide) => guide.id !== item.id)); };
  const permanentlyDeleteBrief = (entry: ArchivedBriefEntry) => { if (!window.confirm('완전 삭제하면 복구가 불가능 합니다. 삭제하시겠습니까?')) return; setArchivedBrief((current) => current.filter((item) => item.id !== entry.id)); };
  const groupedGuides = (stage: GuideStage) => activeGuides.filter((item) => item.stage === stage);
  const visibleGuideSteps = (item: GuideEntry) => (item.steps ?? []).filter((step) => !step.archived);
  const groupedGuideStepCount = (stage: GuideStage) => groupedGuides(stage).reduce((total, item) => total + visibleGuideSteps(item).length, 0);
  const selectGuideParent = (value: string) => {
    const existing = activeGuides.find((item) => item.title === value);
    if (existing) {
      setNewGuide((current) => ({ ...current, parentId: existing.id, parentTitle: '' }));
      return;
    }
    setNewGuide((current) => ({ ...current, parentId: '__new__', parentTitle: value === '직접 입력' ? '' : value }));
  };
  const updateGuideStep = (item: GuideEntry, stepId: string, updater: (step: GuideStep) => GuideStep) => {
    setGuideOverrides((current) => ({
      ...current,
      [item.id]: {
        ...current[item.id],
        steps: (item.steps ?? []).map((step) => step.id === stepId ? updater(step) : step),
      },
    }));
  };
  const toggleGuideStep = (item: GuideEntry, stepId: string) => updateGuideStep(item, stepId, (step) => ({
    ...step,
    completed: !step.completed,
    timestamp: !step.completed ? new Date().toISOString() : undefined,
  }));
  const stepKey = (item: GuideEntry, step: GuideStep) => `${item.id}:${step.id}`;
  const renderHierarchicalGuide = (item: GuideEntry) => {
    const steps = visibleGuideSteps(item);
    const archivedSteps = (item.steps ?? []).filter((step) => step.archived);
    const completedSteps = steps.filter((step) => step.completed).length;
    const expanded = Boolean(expandedGuideIds[item.id]);
    const expandable = steps.length > 0 || archivedSteps.length > 0;
    const toggleParent = () => {
      if (!expandable) return;
      setExpandedGuideIds((current) => ({ ...current, [item.id]: !current[item.id] }));
    };
    const handleRowClick = (event: React.MouseEvent<HTMLElement>) => {
      if ((event.target as HTMLElement).closest('button, input, select, textarea, a')) return;
      toggleParent();
    };
    return editingGuideId === item.id ? <form className="right-panel-inline-form" key={item.id} onSubmit={(event) => {
      event.preventDefault();
      setGuideOverrides((current) => ({ ...current, [item.id]: { ...current[item.id], title: editingGuide.title.trim(), description: editingGuide.description.trim() } }));
      setEditingGuideId(null);
    }}><input value={editingGuide.title} onChange={(event) => setEditingGuide((current) => ({ ...current, title: event.target.value }))}/><textarea value={editingGuide.description} onChange={(event) => setEditingGuide((current) => ({ ...current, description: event.target.value }))}/><div><button type="button" onClick={() => setEditingGuideId(null)}>취소</button><button type="submit" disabled={!editingGuide.title.trim() || !editingGuide.description.trim()}><Check size={13}/>저장</button></div></form> : <article className={`right-panel-guide-row is-${item.stage}${expandable ? ' is-expandable' : ''}`} key={item.id} onClick={expandable ? handleRowClick : undefined} onKeyDown={expandable ? (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); toggleParent(); } } : undefined} tabIndex={expandable ? 0 : undefined} role={expandable ? 'button' : undefined} aria-expanded={expandable ? expanded : undefined}>
      <div className="right-panel-guide-copy">
        <div className="right-panel-guide-title">
          {(steps.length > 0 || archivedSteps.length > 0) && <span className="right-panel-guide-parent-toggle" aria-hidden="true">{expanded ? <ChevronUp size={20}/> : <ChevronDown size={20}/>}</span>}
          <strong>{item.title}</strong>
          {(steps.length > 0 || archivedSteps.length > 0) && <span className="right-panel-guide-progress">{completedSteps}/{steps.length}</span>}
        </div>
        {(steps.length > 0 || archivedSteps.length > 0) && expanded && <div className="right-panel-guide-expanded" onClick={(event) => event.stopPropagation()}>
          {item.contextSummary && <p className="right-panel-guide-context">{item.contextSummary}</p>}
          {item.description && <p>{item.description}</p>}
          {item.actor && <small>{item.actor} · {shortTime(item.timestamp)}</small>}
          <div className="right-panel-guide-steps">
            {steps.map((step) => {
              const isEditing = editingGuideStep?.guideId === item.id && editingGuideStep.stepId === step.id;
              const isAssigning = assigningStepKey === stepKey(item, step);
              if (isEditing) {
                return <form className="right-panel-guide-step right-panel-guide-step-edit" key={step.id} onSubmit={(event) => { event.preventDefault(); saveGuideStep(); }}>
                  <input aria-label="하위 작업 제목" value={editingGuideStep.title} onChange={(event) => setEditingGuideStep((current) => current ? { ...current, title: event.target.value } : current)} />
                  <textarea aria-label="하위 작업 설명" value={editingGuideStep.description} onChange={(event) => setEditingGuideStep((current) => current ? { ...current, description: event.target.value } : current)} />
                  <div className="right-panel-guide-step-edit-actions"><button type="button" onClick={() => setEditingGuideStep(null)}>취소</button><button type="submit" disabled={!editingGuideStep.title.trim()}><Check size={13}/>저장</button></div>
                </form>;
              }
              return <div className={`right-panel-guide-step${step.completed ? ' is-completed' : ''}`} key={step.id}>
                <label><input type="checkbox" checked={Boolean(step.completed)} onChange={() => toggleGuideStep(item, step.id)}/><span>{step.title}</span></label>
                {step.actionLabel && step.onAction && <button type="button" className="right-panel-guide-step-action" onClick={step.onAction}>{step.actionLabel}</button>}
                <RightPanelRowActions actions={guideStepRowActions(item, step)}/>
                {step.description && <small>{step.description}</small>}
                {step.actor && <small className="right-panel-guide-step-assignee">담당: {step.actor} · {shortTime(step.timestamp)}</small>}
                {isAssigning && <div className="right-panel-guide-step-assignment"><select aria-label={`${step.title} 담당자 선택`} value={selectedAssignee} onChange={(event) => setSelectedAssignee(event.target.value)}><option value="">담당자 선택</option>{availableAssignees.map((assignee) => <option key={assignee.name} value={assignee.name}>{assigneeLabel(assignee)}</option>)}</select><button type="button" disabled={!selectedAssignee.trim()} onClick={() => assignGuideStep(item, step)}><UserRound size={12}/>배정</button></div>}
              </div>;
            })}
            {archivedSteps.length > 0 && <details className="right-panel-guide-archived-steps"><summary>제외·보관된 하위 작업 {archivedSteps.length}건</summary>{archivedSteps.map((step) => <div className="right-panel-guide-archived-step" key={step.id}><span>{step.title}</span><button type="button" onClick={() => restoreGuideStep(item, step)}><RotateCcw size={12}/>되돌리기</button></div>)}</details>}
          </div>
        </div>}
      </div>
      <RightPanelRowActions actions={guideRowActions(item)}/>
      {assigningGuideId === item.id && <div className="right-panel-guide-assignment"><select aria-label={`${item.title} 담당자 선택`} value={selectedAssignee} onChange={(event) => setSelectedAssignee(event.target.value)}><option value="">담당자 선택</option>{availableAssignees.map((assignee) => <option key={assignee.name} value={assignee.name}>{assigneeLabel(assignee)}</option>)}</select><button type="button" disabled={!selectedAssignee.trim()} onClick={() => assignGuide(item)}><UserRound size={12}/>배정</button></div>}
    </article>;
  };
  const openAssignment = (item: GuideEntry) => { const current = availableAssignees.find((assignee) => assignee.name === item.actor || assigneeLabel(assignee) === item.actor); setAssigningGuideId((value) => value === item.id ? null : item.id); setSelectedAssignee(current?.name ?? item.actor ?? availableAssignees[0]?.name ?? ''); };
  const assignGuide = (item: GuideEntry) => {
    const assignee = selectedAssignee.trim();
    if (!assignee) return;
    const selected = availableAssignees.find((option) => option.name === assignee);
    setGuideOverrides((current) => ({ ...current, [item.id]: { ...current[item.id], stage: 'inProgress', actor: selected ? assigneeLabel(selected) : assignee, timestamp: new Date().toISOString() } }));
    setAssigningGuideId(null);
    setSelectedAssignee('');
  };
  const moveGuideBackToRecommended = (item: GuideEntry) => {
    setGuideOverrides((current) => ({ ...current, [item.id]: { ...current[item.id], stage: 'recommended', actor: undefined, timestamp: undefined } }));
    setAssigningGuideId(null);
  };
  const completeGuide = (item: GuideEntry) => {
    setGuideOverrides((current) => ({ ...current, [item.id]: { ...current[item.id], stage: 'completed', timestamp: new Date().toISOString() } }));
    setAssigningGuideId(null);
  };
  const assigneeLabel = (assignee: AssigneeOption) => {
    const details = [assignee.displayRole, assignee.positionTitle].filter((value): value is string => Boolean(value?.trim()));
    const assignmentRole = assignee.role ? ` · ${assignee.role}` : '';
    return `${assignee.name}${assignmentRole}${details.length ? ` (${details.join(' · ')})` : ''}`;
  };
  const openStepAssignment = (item: GuideEntry, step: GuideStep) => {
    const current = availableAssignees.find((assignee) => assignee.name === step.actor || assigneeLabel(assignee) === step.actor);
    const key = stepKey(item, step);
    setAssigningStepKey((value) => value === key ? null : key);
    setAssigningGuideId(null);
    setSelectedAssignee(current?.name ?? step.actor ?? availableAssignees[0]?.name ?? '');
  };
  const assignGuideStep = (item: GuideEntry, step: GuideStep) => {
    const assignee = selectedAssignee.trim();
    if (!assignee) return;
    const selected = availableAssignees.find((option) => option.name === assignee);
    updateGuideStep(item, step.id, (currentStep) => ({
      ...currentStep,
      actor: selected ? assigneeLabel(selected) : assignee,
      timestamp: new Date().toISOString(),
    }));
    setAssigningStepKey(null);
    setSelectedAssignee('');
  };
  const beginEditGuideStep = (item: GuideEntry, step: GuideStep) => {
    setEditingGuideStep({ guideId: item.id, stepId: step.id, title: step.title, description: step.description ?? '' });
    setAssigningStepKey(null);
  };
  const saveGuideStep = () => {
    if (!editingGuideStep) return;
    const title = editingGuideStep.title.trim();
    const description = editingGuideStep.description.trim();
    if (!title) return;
    const item = guides.find((guide) => guide.id === editingGuideStep.guideId);
    if (item) updateGuideStep(item, editingGuideStep.stepId, (step) => ({ ...step, title, description }));
    setEditingGuideStep(null);
  };
  const archiveGuideStep = (item: GuideEntry, step: GuideStep) => {
    updateGuideStep(item, step.id, (currentStep) => ({ ...currentStep, archived: true }));
    setAssigningStepKey(null);
    setEditingGuideStep((current) => current?.guideId === item.id && current.stepId === step.id ? null : current);
  };
  const restoreGuideStep = (item: GuideEntry, step: GuideStep) => updateGuideStep(item, step.id, (currentStep) => ({ ...currentStep, archived: false }));
  const moveGuideStepBack = (item: GuideEntry, step: GuideStep) => {
    updateGuideStep(item, step.id, (currentStep) => ({ ...currentStep, completed: false, actor: undefined, timestamp: undefined }));
  };
  const guideRowActions = (item: GuideEntry): RowAction[] => [
    ...(item.stage === 'recommended' ? [{ label: '담당자 배정', title: '담당자 배정', icon: <UserRound size={13}/>, onClick: () => openAssignment(item) }] : []),
    ...(item.stage !== 'recommended' ? [{ label: '수행 전으로 되돌리기', title: '수행 전으로 되돌리기', icon: <RotateCcw size={13}/>, onClick: () => moveGuideBackToRecommended(item) }] : []),
    ...(item.stage === 'inProgress' ? [{ label: '수행 완료', title: '수행 완료', icon: <Check size={13}/>, onClick: () => completeGuide(item) }] : []),
    ...(item.stage === 'completed' ? [{ label: '담당자 재배정', title: '담당자 재배정', icon: <UserRound size={13}/>, onClick: () => openAssignment(item) }] : []),
    { label: '수정', title: '수정', icon: <Pencil size={13}/>, onClick: () => { setEditingGuideId(item.id); setEditingGuide({ title: item.title, description: item.description }); } },
    { label: '보관', title: '보관', icon: <Archive size={13}/>, onClick: () => setArchivedGuides((current) => [...current, item.id]) },
  ];
  const guideStepRowActions = (item: GuideEntry, step: GuideStep): RowAction[] => [
    { label: '담당자 배정', title: '이 하위 작업의 담당자 배정', icon: <UserRound size={13}/>, onClick: () => openStepAssignment(item, step) },
    ...(step.completed || step.actor ? [{ label: '수행 전으로 되돌리기', title: '이 하위 작업만 수행 전으로 되돌리기', icon: <RotateCcw size={13}/>, onClick: () => moveGuideStepBack(item, step) }] : []),
    { label: '수정', title: '이 하위 작업 수정', icon: <Pencil size={13}/>, onClick: () => beginEditGuideStep(item, step) },
    { label: '보관', title: '이 하위 작업 보관', icon: <Archive size={13}/>, onClick: () => archiveGuideStep(item, step) },
  ];
  const renderGuide = (item: GuideEntry) => editingGuideId === item.id ? <form className="right-panel-inline-form" key={item.id} onSubmit={(event) => { event.preventDefault(); setGuideOverrides((current) => ({ ...current, [item.id]: { ...current[item.id], title: editingGuide.title.trim(), description: editingGuide.description.trim() } })); setEditingGuideId(null); }}><input value={editingGuide.title} onChange={(event) => setEditingGuide((current) => ({ ...current, title: event.target.value }))}/><textarea value={editingGuide.description} onChange={(event) => setEditingGuide((current) => ({ ...current, description: event.target.value }))}/><div><button type="button" onClick={() => setEditingGuideId(null)}>취소</button><button type="submit" disabled={!editingGuide.title.trim() || !editingGuide.description.trim()}><Check size={13}/>저장</button></div></form> : <article className={`right-panel-guide-row is-${item.stage}`} key={item.id}><div className="right-panel-guide-copy"><div className="right-panel-guide-title">{item.actionLabel && item.onAction ? <button type="button" className="right-panel-guide-title-action" onClick={item.onAction} title={item.actionLabel}>{item.title}</button> : <strong>{item.title}</strong>}</div><p>{item.description}</p>{item.actor && item.stage !== 'recommended' && <small>{item.actor} · {shortTime(item.timestamp)}</small>}</div><RightPanelRowActions actions={guideRowActions(item)}/>{assigningGuideId === item.id && <div className="right-panel-guide-assignment"><select aria-label={`${item.title} 담당자 선택`} value={selectedAssignee} onChange={(event) => setSelectedAssignee(event.target.value)}><option value="">담당자 선택</option>{availableAssignees.map((assignee) => <option key={assignee.name} value={assignee.name}>{assigneeLabel(assignee)}</option>)}</select><button type="button" disabled={!selectedAssignee.trim()} onClick={() => assignGuide(item)}><UserRound size={12}/>배정</button></div>}</article>;
  const renderBriefCategory = (category: BriefCategory) => <section className={`right-panel-brief-category ${category.entries.length === 0 ? 'is-empty' : ''}`} key={category.key}><header><button type="button" className="right-panel-category-toggle" disabled={category.entries.length === 0} aria-expanded={category.entries.length > 0 && openCategories[category.key]} onClick={() => setOpenCategories((current) => ({ ...current, [category.key]: !current[category.key] }))}>{category.entries.length > 0 && (openCategories[category.key] ? <ChevronUp size={15}/> : <ChevronDown size={15}/>)}<span>{category.label}</span><small>{category.entries.length}건</small></button><button type="button" className="right-panel-icon-button" aria-label={`${category.label} 정황 추가`} title="정황 추가" onClick={() => { setAddCategory(category.key); setOpenCategories((current) => ({ ...current, [category.key]: true })); }}><Plus size={14}/></button></header>{openCategories[category.key] && <div className="right-panel-brief-items">{category.entries.map((entry) => editingBriefId === entry.id ? <form className="right-panel-inline-form" key={entry.id} onSubmit={(event) => { event.preventDefault(); updateBriefItem(category.key, entry.id, editingBriefText.trim()); setEditingBriefId(null); }}><textarea value={editingBriefText} onChange={(event) => setEditingBriefText(event.target.value)}/><div><button type="button" onClick={() => setEditingBriefId(null)}>취소</button><button type="submit" disabled={!editingBriefText.trim()}><Check size={13}/>저장</button></div></form> : <div className="right-panel-brief-item" key={entry.id}><p>{entry.text}</p><RightPanelRowActions actions={[{ label: '수정', title: '수정', icon: <Pencil size={12}/>, onClick: () => { setEditingBriefId(entry.id); setEditingBriefText(entry.text); } }, { label: '보관', title: '보관', icon: <Archive size={12}/>, onClick: () => archiveBriefItem(category.key, entry) }]}/></div>)}{addCategory === category.key && <form className="right-panel-inline-form right-panel-brief-add-form" onSubmit={(event) => { event.preventDefault(); addBriefItem(); }}><textarea autoFocus value={newBriefText} onChange={(event) => setNewBriefText(event.target.value)} placeholder="정황 문장을 입력하세요."/><div><button type="button" onClick={() => { setAddCategory(null); setNewBriefText(''); }}>취소</button><button type="submit" disabled={!newBriefText.trim()}><Plus size={13}/>추가</button></div></form>}</div>}</section>;
 return <aside className={`context-panel context-panel-v3 context-panel-foundation ${open ? 'is-open' : ''}`} aria-label="우측 사건 패널"><div className="context-header context-v3-sticky-header"><div><h2>사건 현황</h2><small>{formatPanelUpdatedAt(caseItem.updated_at)}</small></div><button type="button" className="context-open context-header-toggle" onClick={onToggle} aria-label={open ? '사건 패널 닫기' : '사건 패널 열기'} title={open ? '사건 패널 닫기' : '사건 패널 열기'}>{open ? <PanelRightClose size={17}/> : <PanelRightOpen size={17}/>}</button></div><div className="right-panel-scroll"><section className={`right-panel-one-line ${summaryExpanded ? 'is-expanded' : ''}`}><span>현재 사건 요약</span><p className="right-panel-summary-headline">{summary}</p>{summaryExpanded && <ul className="right-panel-summary-list">{summaryItems.map((item) => <li key={`${item.label}:${item.value}`}><strong>{item.label}</strong><span>{item.value}</span></li>)}</ul>}{summaryCanExpand && <button type="button" className="right-panel-summary-toggle" onClick={() => setSummaryExpanded((current) => !current)}>{summaryExpanded ? '간단히 보기' : '세부 정황 보기'}{summaryExpanded ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}</button>}</section><section className="right-panel-block"><header className="right-panel-block-header"><button type="button" onClick={() => setGuideSectionOpen((current) => !current)}><strong>1. 은행 직원 대응 가이드</strong>{guideSectionOpen ? <ChevronUp size={15}/> : <ChevronDown size={15}/>}</button><button type="button" className="right-panel-icon-button" aria-label="대응 가이드 추가" title="대응 가이드 추가" onClick={() => setShowGuideForm((current) => !current)}><Plus size={14}/></button></header>{guideSectionOpen && <>{showGuideForm && <form className="right-panel-guide-form" onSubmit={(event) => { event.preventDefault(); addGuideItem(); }}><div className="right-panel-guide-form-row"><input autoFocus list="right-panel-guide-parent-options" value={newGuide.parentId === '__new__' ? newGuide.parentTitle : activeGuides.find((item) => item.id === newGuide.parentId)?.title ?? ''} onChange={(event) => selectGuideParent(event.target.value)} placeholder="최상위 제목 선택 또는 직접 입력"/><datalist id="right-panel-guide-parent-options"><option value="직접 입력"/>{activeGuides.map((item) => <option value={item.title} key={item.id}/>)}</datalist><input value={newGuide.stepTitle} onChange={(event) => setNewGuide((current) => ({ ...current, stepTitle: event.target.value }))} placeholder="하위 대응 항목"/></div><textarea value={newGuide.stepDescription} onChange={(event) => setNewGuide((current) => ({ ...current, stepDescription: event.target.value }))} placeholder="하위 대응 항목에 대한 직원이 해야 할 업무 내용을 입력하세요."/><div><button type="button" onClick={() => setShowGuideForm(false)}>취소</button><button type="button" className="right-panel-guide-ai-button" onClick={() => void recommendGuide()} disabled={guideAiBusy}>{guideAiBusy ? <Loader2 className="spin" size={13}/> : <Sparkles size={13}/>} {guideAiBusy ? '추천 중' : 'AI 추천'}</button><button type="submit" disabled={!newGuide.parentId || (newGuide.parentId === '__new__' && !newGuide.parentTitle.trim()) || !newGuide.stepTitle.trim() || !newGuide.stepDescription.trim()}><Plus size={13}/>추가</button></div></form>}{showGuideForm && guideAiMessage && <p className="right-panel-guide-ai-message">{guideAiMessage}</p>}<div className="right-panel-guide-lanes">{(['recommended', 'inProgress', 'completed'] as GuideStage[]).map((stage) => <section className={`right-panel-guide-lane is-${stage}`} key={stage}><button type="button" className="right-panel-lane-header" aria-expanded={guideOpen[stage]} onClick={() => setGuideOpen((current) => ({ ...current, [stage]: !current[stage] }))}><span>{stageIcon[stage]}{stageLabel[stage]}</span><b>{groupedGuideStepCount(stage)}건</b>{guideOpen[stage] ? <ChevronUp size={15}/> : <ChevronDown size={15}/>}</button>{guideOpen[stage] && <div className="right-panel-guide-list">{groupedGuides(stage).length ? groupedGuides(stage).map(renderHierarchicalGuide) : <p className="right-panel-empty">등록된 작업 없음.</p>}</div>}</section>)}{archivedGuideItems.length > 0 && <details className="right-panel-archive"><summary><Archive size={13}/>제외·보관된 작업 {archivedGuideItems.length}건</summary>{archivedGuideItems.map((item) => <div className="right-panel-archive-row" key={item.id}><span>{item.title}</span><div className="right-panel-archive-actions"><button type="button" className="right-panel-icon-button" aria-label={`${item.title} 복구`} title="복구" onClick={() => setArchivedGuides((current) => current.filter((id) => id !== item.id))}><RotateCcw size={12}/></button><button type="button" className="right-panel-permanent-delete" onClick={() => permanentlyDeleteGuide(item)}>완전 삭제</button></div></div>)}</details>}</div></>}</section><section className="right-panel-block"><header className="right-panel-block-header"><button type="button" onClick={() => setBriefOpen((current) => !current)}><strong>2. 현재 사건 브리핑</strong>{briefOpen ? <ChevronUp size={15}/> : <ChevronDown size={15}/>}</button><span className="right-panel-ai-note"><Sparkles size={13}/>AI·담당자 정리</span></header>{briefOpen && <div className="right-panel-brief"><section className="right-panel-brief-section"><header><h3>주요 보이스피싱 정황</h3></header><p className="right-panel-brief-order-note">발화 흐름 및 확인된 시간 순서 기준으로 정리됨</p><div className="right-panel-category-list">{brief.map(renderBriefCategory)}</div></section>{archivedBrief.length > 0 && <details className="right-panel-archive"><summary><Archive size={13}/>제외·보관된 정황 {archivedBrief.length}건</summary>{archivedBrief.map((entry) => <div className="right-panel-archive-row" key={entry.id}><span>{entry.text}</span><div className="right-panel-archive-actions"><button type="button" className="right-panel-icon-button" aria-label="정황 복구" title="복구" onClick={() => { setArchivedBrief((current) => current.filter((item) => item.id !== entry.id)); setBrief((current) => current.map((category) => category.key === entry.categoryKey ? { ...category, entries: [...category.entries, { id: entry.id, text: entry.text }] } : category)); }}><RotateCcw size={12}/></button><button type="button" className="right-panel-permanent-delete" onClick={() => permanentlyDeleteBrief(entry)}>완전 삭제</button></div></div>)}</details>}</div>}</section></div></aside>;
};
