import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Archive, Check, ChevronDown, ChevronUp, MoreHorizontal, PanelRightClose, PanelRightOpen, Pencil, Plus, RotateCcw, Trash2 } from 'lucide-react';
import { casesApi } from '../api/cases';
import type {
  CaseBundle, CaseSupportSnapshot, RightPanelItem, RightPanelProjection, RightPanelStoredItem,
  RightPanelStorageSection, StoredCase,
} from '../api/types';
import { completeContextTask, loadContextTasks, updateContextTask, editContextTask, cancelContextTask } from './api';
import type { ContextTaskV2 } from './api';

const FRAUD_GROUPS = [
  { key: 'identity', label: '사칭·접촉', categoryKeys: ['identity'], includesContacts: true },
  { key: 'claim', label: '사건·상황 주장', categoryKeys: ['claim'], includesContacts: false },
  { key: 'demand', label: '요구·행동', categoryKeys: ['demand'], includesContacts: false },
  { key: 'pressure', label: '압박·연락 통제', categoryKeys: ['pressure'], includesContacts: false },
] as const;
const EXPOSURE_SIGNAL_GROUPS = [
  { key: 'money', label: '금전', categoryKeys: ['money'] },
  { key: 'personal_information', label: '개인정보', categoryKeys: [] },
  { key: 'authentication_information', label: '인증정보', categoryKeys: [] },
  { key: 'device_access', label: '기기·접근', categoryKeys: [] },
  { key: 'other', label: '기타 피해·노출', categoryKeys: ['exposure'] },
] as const;
type RightPanelAddChoice = {
  id: string;
  label: string;
  section: RightPanelItem['section'];
  signalKey?: string;
  groupKey?: string;
};
export const RIGHT_PANEL_ADD_CHOICES: Record<'exposure' | 'progress' | 'fraud', RightPanelAddChoice[]> = {
  exposure: [
    { id: 'exposure-item', label: '피해·노출 항목 추가', section: 'EXPOSURE', groupKey: 'other' },
    ...EXPOSURE_SIGNAL_GROUPS.filter((group) => group.categoryKeys.length === 0).map((group) => ({
      id: `exposure-item:${group.key}`, label: `${group.label} 항목 추가`, section: 'EXPOSURE' as const,
      groupKey: group.key,
    })),
    ...EXPOSURE_SIGNAL_GROUPS.filter((group) => group.key !== 'other').flatMap((group) => group.categoryKeys.map((signalKey) => ({
      id: `exposure-signal:${signalKey}`, label: `${group.label} 정황 추가`, section: 'SIGNAL' as const,
      signalKey, groupKey: group.key,
    }))),
  ],
  progress: [
    { id: 'work', label: '대응 업무 추가', section: 'WORK' },
    { id: 'verification', label: '확인 대상 추가', section: 'VERIFICATION' },
  ],
  fraud: [
    ...FRAUD_GROUPS.flatMap((group) => [
      ...(group.includesContacts ? [{ id: 'contact', label: '인물·기관 추가', section: 'CONTACT' as const, groupKey: group.key }] : []),
      ...group.categoryKeys.map((signalKey) => ({
        id: `fraud-signal:${signalKey}`, label: `${group.label} 정황 추가`, section: 'SIGNAL' as const,
        signalKey, groupKey: group.key,
      })),
    ]),
  ],
};
export const RIGHT_PANEL_TOP_LEVEL_LABELS = [
	'현재 사건 요약', '1. 피해·노출', '2. 확인·조치 진행', '3. 주요 사기 정황', '4. 처리 기록',
] as const;

type ExposureGroupKey = NonNullable<RightPanelItem['presentation_group']>;
const EXPOSURE_GROUP_KEYS = new Set<ExposureGroupKey>([
  'money', 'personal_information', 'authentication_information', 'device_access', 'other',
]);
const exposureGroupForRow = (row: RightPanelItem): ExposureGroupKey | null => {
  if (row.presentation_group && EXPOSURE_GROUP_KEYS.has(row.presentation_group)) return row.presentation_group;
  const groupRef = row.evidence_refs.find((value) => value.startsWith('presentation-group:'))?.slice('presentation-group:'.length);
  if (groupRef && EXPOSURE_GROUP_KEYS.has(groupRef as ExposureGroupKey)) return groupRef as ExposureGroupKey;
  const categoryRef = row.evidence_refs.find((value) => value.startsWith('category:'))?.slice('category:'.length);
  if (categoryRef === 'money') return 'money';
  if (categoryRef === 'exposure') return 'other';
  return null;
};
export const groupExposureRows = (rows: RightPanelItem[]) => ({
  groups: Object.fromEntries([...EXPOSURE_GROUP_KEYS].map((key) => [
    key, rows.filter((row) => exposureGroupForRow(row) === key),
  ])) as Record<ExposureGroupKey, RightPanelItem[]>,
  unclassified: rows.filter((row) => exposureGroupForRow(row) === null),
});

export const rightPanelPresentation = (projection: RightPanelProjection | null | undefined) => {
  const categories = new Map((projection?.fraud_signals ?? []).map((category) => [category.key, category]));
  return {
    summary: projection?.current_case_summary?.trim() || '현재 확인된 사건 요약이 없습니다.',
    summaryBadges: projection?.summary_badges ?? [],
    fraudGroups: FRAUD_GROUPS.map((group) => ({
      ...group,
      items: group.categoryKeys.flatMap((key) => categories.get(key)?.items ?? []),
    })),
    exposureSignalGroups: EXPOSURE_SIGNAL_GROUPS.map((group) => ({
      ...group,
      items: ['money', 'exposure'].flatMap((key) => categories.get(key)?.items ?? [])
        .filter((item) => item.presentation_group === group.key),
    })),
  };
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
  headerActions?: React.ReactNode;
};

type PanelRow = RightPanelItem & { display_status?: 'TODO' | 'COMPLETED'; staff_authored?: boolean };
type RowAction = { label: string; icon: React.ReactNode; onClick: () => void; danger?: boolean };
const PANEL_SECTIONS: Record<RightPanelItem['section'], RightPanelStorageSection> = {
  EXPOSURE: 'RP_EXPOSURE', CONTACT: 'RP_CONTACT', SIGNAL: 'RP_SIGNAL',
  VERIFICATION: 'RP_VERIFICATION', WORK: 'RP_WORK', ACTIVITY: 'RP_ACTIVITY',
};
const sectionName: Record<RightPanelItem['section'], string> = {
  EXPOSURE: '피해·노출', CONTACT: '주요 사기 정황', SIGNAL: '주요 사기 정황',
  VERIFICATION: '확인·조치 진행', WORK: '확인·조치 진행', ACTIVITY: '처리 기록',
};
const statusText = (status: string | null | undefined) => ({
  TODO: '미완료', IN_PROGRESS: '미완료', BLOCKED: '미완료', COMPLETED: '완료',
  PENDING: '확인 대기', ON_HOLD: '확인 보류', FAILED: '재확인 필요',
  '확인 대기': '확인 대기', '확인 진행 중': '확인 진행 중', '확인 필요': '확인 필요',
  '재확인 필요': '재확인 필요', '확인 보류': '확인 보류',
} as Record<string, string>)[status ?? ''] ?? '';
const formatTime = (value: string | null | undefined) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Seoul' }).format(date);
};
const newSemanticKey = () => `staff:${globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`}`;
const taskIdFrom = (row: PanelRow) => row.evidence_refs.find((value) => value.startsWith('task:'))?.slice(5) ?? null;
const actionIdFrom = (row: PanelRow) => row.evidence_refs.find((value) => value.startsWith('action:'))?.slice(7) ?? null;
const storedKey = (section: RightPanelItem['section'], key: string) => `${PANEL_SECTIONS[section]}|${key}`;

const RowActions: React.FC<{ actions: RowAction[] }> = ({ actions }) => {
  const [open, setOpen] = useState(false);
  const [menuPosition, setMenuPosition] = useState<{ top: number; left: number } | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return undefined;
    const pointer = (event: PointerEvent) => {
      if (!(event.target instanceof Node) || (!wrapperRef.current?.contains(event.target) && !menuRef.current?.contains(event.target))) setOpen(false);
    };
    const keydown = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpen(false); };
    document.addEventListener('pointerdown', pointer);
    document.addEventListener('keydown', keydown);
    return () => { document.removeEventListener('pointerdown', pointer); document.removeEventListener('keydown', keydown); };
  }, [open]);
  useLayoutEffect(() => {
    if (!open) { setMenuPosition(null); return undefined; }
    const positionMenu = () => {
      const trigger = triggerRef.current;
      const menu = menuRef.current;
      if (!trigger || !menu) return;
      const triggerRect = trigger.getBoundingClientRect();
      const menuRect = menu.getBoundingClientRect();
      const left = Math.max(8, Math.min(window.innerWidth - menuRect.width - 8, triggerRect.right - menuRect.width));
      let top = triggerRect.top - menuRect.height - 5;
      if (top < 8) top = Math.min(window.innerHeight - menuRect.height - 8, triggerRect.bottom + 5);
      setMenuPosition({ top: Math.max(8, top), left });
    };
    positionMenu();
    window.addEventListener('resize', positionMenu);
    document.addEventListener('scroll', positionMenu, true);
    return () => { window.removeEventListener('resize', positionMenu); document.removeEventListener('scroll', positionMenu, true); };
  }, [open, actions.length]);
  return <div ref={wrapperRef} className={`right-panel-row-actions${open ? ' is-open' : ''}`}>
    <button ref={triggerRef} type="button" className="right-panel-row-menu-trigger" aria-label="추가 작업 열기" aria-expanded={open} title="추가 작업" onClick={() => setOpen((current) => !current)}><MoreHorizontal size={15}/></button>
    {open && createPortal(<div ref={menuRef} className="right-panel-row-action-menu is-portalled" role="menu" style={menuPosition ?? undefined}>{actions.map((action) => <button key={action.label} type="button" role="menuitem" className={`right-panel-row-action${action.danger ? ' is-danger' : ''}`} onClick={() => { setOpen(false); action.onClick(); }}>{action.icon}<span>{action.label}</span></button>)}</div>, document.body)}
  </div>;
};

export const ContextPanelFoundation: React.FC<Props> = ({ open, onToggle, caseItem, support, headerActions }) => {
  const [storedItems, setStoredItems] = useState<RightPanelStoredItem[]>([]);
  const [tasks, setTasks] = useState<ContextTaskV2[]>([]);
  const [loadError, setLoadError] = useState('');
  const [saving, setSaving] = useState(false);
  const [summaryOverride, setSummaryOverride] = useState<CaseSupportSnapshot | null>(null);
  const [openBlocks, setOpenBlocks] = useState<Record<string, boolean>>({});
  const [expandedSignalIds, setExpandedSignalIds] = useState<Set<string>>(() => new Set());
  const [editing, setEditing] = useState<{ id: string; text: string } | null>(null);
  const [addingSection, setAddingSection] = useState<RightPanelItem['section'] | null>(null);
  const [addingSignalKey, setAddingSignalKey] = useState<string | null>(null);
  const [addingGroupKey, setAddingGroupKey] = useState<string | null>(null);
  const [addChooser, setAddChooser] = useState<{ scope: keyof typeof RIGHT_PANEL_ADD_CHOICES; groupKey?: string; choices: RightPanelAddChoice[] } | null>(null);
  const [draft, setDraft] = useState('');
  const activeSupport = summaryOverride ?? support;
  const projection = activeSupport?.right_panel ?? null;
  const presentation = rightPanelPresentation(projection);

  const reloadStored = async (signal?: AbortSignal) => {
    const rows = await casesApi.rightPanelItems(caseItem.case_id, signal);
    setStoredItems(rows);
    return rows;
  };
  useEffect(() => {
    const controller = new AbortController();
    setStoredItems([]); setTasks([]); setLoadError(''); setSummaryOverride(null); setExpandedSignalIds(new Set());
    void Promise.all([reloadStored(controller.signal), loadContextTasks(caseItem.case_id, controller.signal)])
      .then(([rows, loadedTasks]) => { if (!controller.signal.aborted) { setStoredItems(rows); setTasks(loadedTasks); } })
      .catch((reason) => { if (!controller.signal.aborted) setLoadError(reason instanceof Error ? reason.message : '우측 패널의 저장 정보를 불러오지 못했습니다.'); });
    return () => controller.abort();
  // Reload only when the active Case changes. Snapshot updates are supplied by the parent.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseItem.case_id]);
  useEffect(() => { setSummaryOverride(null); }, [support?.source_revision, support?.projection_revision]);
  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([reloadStored(controller.signal), loadContextTasks(caseItem.case_id, controller.signal)])
      .then(([, next]) => { if (!controller.signal.aborted) setTasks(next); })
      .catch(() => { if (!controller.signal.aborted) setLoadError('최신 업무를 불러오지 못했습니다. 다시 확인해 주세요.'); });
    return () => controller.abort();
  }, [caseItem.case_id, support?.source_revision]);
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const focus = (event: Event) => {
      const action = (event as CustomEvent).detail;
      if (action?.target_type !== 'TASK') return;
      if (!open) onToggle();
      setOpenBlocks((current) => ({ ...current, progress: true, 'progress:todo': true, 'progress:completed': true }));
      timer = setTimeout(() => {
        const node = document.querySelector<HTMLElement>(`[data-task-id="${CSS.escape(action.target_id)}"]`);
        node?.scrollIntoView({ block: 'nearest' }); node?.focus();
      }, 0);
    };
    window.addEventListener('csr:focus-resource', focus);
    return () => { window.removeEventListener('csr:focus-resource', focus); clearTimeout(timer); };
  }, [open, onToggle]);

  const storedMap = useMemo(() => new Map(storedItems.map((item) => [`${item.section}|${item.semantic_key}`, item])), [storedItems]);
  const tasksById = useMemo(() => new Map(tasks.map((task) => [task.task_id, task])), [tasks]);
  const mergeRows = (section: RightPanelItem['section'], sourceRows: RightPanelItem[], categoryKey?: string): { active: PanelRow[]; archived: PanelRow[] } => {
    const panelSection = PANEL_SECTIONS[section];
    const matchedKeys = new Set<string>();
    const activeRows: PanelRow[] = [];
    const archivedRows: PanelRow[] = [];
    for (const source of sourceRows) {
      const key = `${panelSection}|${source.semantic_key}`;
      const stored = storedMap.get(key);
      if (stored) matchedKeys.add(key);
      if (stored?.permanently_hidden) continue;
      const row: PanelRow = {
        ...source,
        title: stored?.staff_text ?? source.title,
        display_status: stored?.display_status ?? undefined,
        staff_authored: stored?.staff_authored ?? false,
      };
      if (stored?.deleted_by) archivedRows.push(row);
      else activeRows.push(row);
    }
    for (const stored of storedItems) {
      const key = `${stored.section}|${stored.semantic_key}`;
      if (stored.section !== panelSection || matchedKeys.has(key) || stored.permanently_hidden || !stored.staff_authored) continue;
      if (section === 'SIGNAL' && stored.evidence_refs.find((value) => value.startsWith('category:'))?.slice(9) !== categoryKey) continue;
      const row: PanelRow = {
        item_id: stored.item_id, section, semantic_key: stored.semantic_key,
        title: stored.staff_text ?? stored.ai_text ?? '', detail: '', source_badge: '직원 기록',
        origin: 'STAFF_ADDED', status: stored.display_status ?? (section === 'WORK' ? 'TODO' : null),
        occurred_at: null, evidence_refs: stored.evidence_refs, actor_id: stored.updated_by,
        version: stored.item_version, display_status: stored.display_status ?? undefined, staff_authored: true,
      };
      if (!row.title.trim()) continue;
      if (stored.deleted_by) archivedRows.push(row); else activeRows.push(row);
    }
    return { active: activeRows, archived: archivedRows };
  };

  const rawExposure = projection?.exposure ?? [];
  const rawContacts = projection?.contact_information ?? [];
  const rawSignals = projection?.fraud_signals ?? [];
  const rawVerification = projection?.verification ?? [];
  const rawWork = [...(projection?.incomplete_work ?? []), ...(projection?.completed_work ?? [])];
  const rawActivity = projection?.activity ?? [];
  const exposure = mergeRows('EXPOSURE', rawExposure);
  const contacts = mergeRows('CONTACT', rawContacts);
  const verifications = mergeRows('VERIFICATION', rawVerification);
  const work = mergeRows('WORK', rawWork);
  const activity = mergeRows('ACTIVITY', rawActivity);
  const signalCategories = rawSignals.map((category) => ({ ...category, ...mergeRows('SIGNAL', category.items, category.key) }));
  const signalCategoriesByKey = new Map(signalCategories.map((category) => [category.key, category]));
  const fraudGroups = presentation.fraudGroups.map((group) => ({
    ...group,
    active: group.categoryKeys.flatMap((key) => signalCategoriesByKey.get(key)?.active ?? []),
    categories: group.categoryKeys.map((key) => signalCategoriesByKey.get(key)).filter((item): item is NonNullable<typeof item> => Boolean(item)),
  }));
  // Fraud signal categories are displayed in the fraud section. Only the
  // dedicated exposure projection belongs in the exposure/status subsection.
  const exposureSourceRows = exposure.active;
  const groupedExposureRows = groupExposureRows(exposureSourceRows);
  const exposureGroups = EXPOSURE_SIGNAL_GROUPS.map((group) => ({
    ...group,
    active: groupedExposureRows.groups[group.key],
  }));
  const unclassifiedExposureRows = groupedExposureRows.unclassified;
  const archivedSignals = signalCategories.flatMap((category) => category.archived.map((row) => ({ ...row, categoryLabel: category.label })));
  const archivedAll: Array<PanelRow & { categoryLabel: string }> = [
    ...exposure.archived.map((row) => ({ ...row, categoryLabel: sectionName.EXPOSURE })),
    ...contacts.archived.map((row) => ({ ...row, categoryLabel: sectionName.CONTACT })),
    ...archivedSignals,
    ...verifications.archived.map((row) => ({ ...row, categoryLabel: sectionName.VERIFICATION })),
    ...work.archived.map((row) => ({ ...row, categoryLabel: sectionName.WORK })),
    ...activity.archived.map((row) => ({ ...row, categoryLabel: sectionName.ACTIVITY })),
  ];
  const workRows = work.active.map((row) => {
    const taskId = taskIdFrom(row);
    const actionId = actionIdFrom(row);
    const task = taskId ? tasksById.get(taskId) : undefined;
    const state = taskId ? task?.status ?? row.status ?? 'TODO'
      : actionId ? row.status ?? 'TODO'
        : row.display_status ?? row.status ?? 'TODO';
    return { ...row, status: state };
  });
  const incompleteWork = workRows.filter((row) => row.status !== 'COMPLETED');
  const completedWork = workRows.filter((row) => row.status === 'COMPLETED');
  const incompleteChecks = incompleteWork.filter((row) => row.progress_group === 'verification');
  const incompleteActions = incompleteWork.filter((row) => row.progress_group !== 'verification');
  const completedChecks = completedWork.filter((row) => row.progress_group === 'verification');
  const completedActions = completedWork.filter((row) => row.progress_group !== 'verification');
  const incompleteVerifications = verifications.active.filter((row) => row.status !== '완료');
  const completedVerifications = verifications.active.filter((row) => row.status === '완료');
  const openProgressCount = incompleteWork.length + incompleteVerifications.length;
  const completedProgressCount = completedWork.length + completedVerifications.length;
  const summary = presentation.summary;

  const refreshAfterTask = async () => {
    const [loadedTasks, latestSupport] = await Promise.all([
      loadContextTasks(caseItem.case_id), casesApi.support(caseItem.case_id),
    ]);
    setTasks(loadedTasks); setSummaryOverride(latestSupport);
  };
  const mutateRow = async (row: PanelRow, operation: 'EDIT' | 'ARCHIVE' | 'RESTORE' | 'PERMANENT_HIDE' | 'SET_STATUS', text?: string, displayStatus?: 'TODO' | 'COMPLETED') => {
    const existing = storedMap.get(storedKey(row.section, row.semantic_key));
    const mutation = await casesApi.mutateRightPanelItem(caseItem.case_id, PANEL_SECTIONS[row.section], row.semantic_key, {
      expected_version: existing?.item_version ?? 0,
      operation,
      ...(text ? { text } : {}),
      ...(existing?.ai_text || row.title ? { source_text: existing?.ai_text ?? row.title } : {}),
      evidence_refs: row.evidence_refs,
      ...(displayStatus ? { display_status: displayStatus } : {}),
    });
    setStoredItems((current) => [...current.filter((item) => !(item.section === mutation.section && item.semantic_key === mutation.semantic_key)), mutation]);
  };
  const safeMutation = async (operation: () => Promise<void>) => {
    setSaving(true); setLoadError('');
    try { await operation(); }
    catch (reason) {
      setLoadError(reason instanceof Error ? reason.message : '저장하지 못했습니다. 최신 정보를 확인해 주세요.');
      try { await reloadStored(); } catch { /* keep the original conflict/error message */ }
    } finally { setSaving(false); }
  };
  const saveEdit = (row: PanelRow) => {
    if (!editing?.text.trim()) return;
    const task = tasksById.get(taskIdFrom(row) ?? '');
    if (task) {
      void safeMutation(async () => { await editContextTask(caseItem.case_id, task.task_id, task.version, editing.text.trim(), task.description); setEditing(null); await refreshAfterTask(); });
      return;
    }
    void safeMutation(async () => { await mutateRow(row, 'EDIT', editing.text.trim()); setEditing(null); });
  };
  const archiveRow = (row: PanelRow) => void safeMutation(async () => {
    const task = tasksById.get(taskIdFrom(row) ?? '');
    if (task) { await cancelContextTask(caseItem.case_id, task.task_id, task.version, '직원이 업무 목록에서 제외함'); await refreshAfterTask(); }
    else await mutateRow(row, 'ARCHIVE');
  });
  const addRow = (section: RightPanelItem['section'], categoryKey?: string, groupKey?: string) => {
    const title = draft.trim();
    if (!title) return;
    const semanticKey = newSemanticKey();
    void safeMutation(async () => {
      const item = await casesApi.mutateRightPanelItem(caseItem.case_id, PANEL_SECTIONS[section], semanticKey, {
        expected_version: 0, operation: 'ADD', text: title,
        evidence_refs: categoryKey ? [`category:${categoryKey}`]
          : section === 'EXPOSURE' && groupKey ? [`presentation-group:${groupKey}`] : [],
      });
      setStoredItems((current) => [...current, item]); setDraft(''); setAddingSection(null); setAddingSignalKey(null); setAddingGroupKey(null);
    });
  };
  const toggleTask = async (row: PanelRow) => {
    const taskId = taskIdFrom(row);
    if (taskId) {
      let task = tasksById.get(taskId);
      if (!task) { await refreshAfterTask(); return; }
      if (task.status === 'COMPLETED') await updateContextTask(caseItem.case_id, task.task_id, task.version, 'TODO');
      else {
        if (task.status !== 'TODO') task = await updateContextTask(caseItem.case_id, task.task_id, task.version, 'TODO') as ContextTaskV2;
        await completeContextTask(caseItem.case_id, task.task_id, task.version, `우측 패널에서 완료 처리: ${row.title}`);
      }
      await refreshAfterTask();
    } else {
      const actionId = actionIdFrom(row);
      if (actionId) {
        await casesApi.updateAction(caseItem.case_id, actionId, {
          status: row.status === 'COMPLETED' ? 'REQUESTED' : 'COMPLETED',
        });
        await refreshAfterTask();
        return;
      }
      const status = row.status === 'COMPLETED' ? 'TODO' : 'COMPLETED';
      await mutateRow(row, 'SET_STATUS', undefined, status);
    }
  };

  const renderAddForm = (section: RightPanelItem['section'], categoryKey?: string, groupKey?: string) => addingSection === section && (section !== 'SIGNAL' || addingSignalKey === categoryKey) && (section !== 'EXPOSURE' || addingGroupKey === groupKey) ? <form className="right-panel-inline-form rp-add-form" onSubmit={(event) => { event.preventDefault(); addRow(section, categoryKey, groupKey); }}>
    <textarea autoFocus value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={section === 'WORK' ? '업무 내용을 입력하세요.' : '항목 내용을 입력하세요.'}/>
    <div><button type="button" onClick={() => { setAddingSection(null); setAddingGroupKey(null); setDraft(''); }}>취소</button><button type="submit" disabled={saving || !draft.trim()}><Check size={13}/>추가</button></div>
  </form> : null;
  const renderRows = (rows: PanelRow[], emptyLabel = '등록된 항목 없음') => <div className="right-panel-category-list rp-row-list">
    {rows.length ? rows.map((row) => {
      const section = row.section;
      const editorId = `${section}:${row.semantic_key}`;
      const checked = section === 'WORK' && row.status === 'COMPLETED';
      const badge = section === 'VERIFICATION'
        ? row.source_badge === '공식 확인' ? '공식 확인'
          : row.status === '완료' ? '직원 기록'
            : row.status ?? '확인 필요'
        : section === 'WORK' ? statusText(row.status) : row.source_badge;
      const actions: RowAction[] = [
        ...(section === 'WORK' ? [{ label: checked ? '미완료로 변경' : '완료', icon: checked ? <RotateCcw size={13}/> : <Check size={13}/>, onClick: () => void safeMutation(() => toggleTask(row)) }] : []),
        { label: '수정', icon: <Pencil size={13}/>, onClick: () => setEditing({ id: editorId, text: row.title }) },
        { label: '보관', icon: <Archive size={13}/>, onClick: () => archiveRow(row) },
      ];
      const hasSignalDetail = section === 'SIGNAL' && Boolean(row.detail?.trim());
      const isSignalExpanded = hasSignalDetail && expandedSignalIds.has(editorId);
      return <div data-task-id={taskIdFrom(row) ?? undefined} tabIndex={-1} className={`right-panel-brief-item rp-item-row${checked ? ' is-completed' : ''}${section === 'WORK' ? ' is-work-item' : ''}${hasSignalDetail ? ' is-signal-with-detail' : ''}${isSignalExpanded ? ' is-signal-expanded' : ''}`} key={editorId}>
        {editing?.id === editorId ? <form className="right-panel-inline-form rp-edit-form" onSubmit={(event) => { event.preventDefault(); saveEdit(row); }}>
          <textarea autoFocus value={editing.text} onChange={(event) => setEditing((current) => current ? { ...current, text: event.target.value } : current)}/>
          <div><button type="button" onClick={() => setEditing(null)}>취소</button><button type="submit" disabled={saving || !editing.text.trim()}><Check size={13}/>저장</button></div>
        </form> : <>
          <span className={`rp-item-indicator${section === 'WORK' ? ' is-hidden' : ''}`} aria-hidden="true" />
          {section === 'WORK' && <input className="rp-work-checkbox" aria-label={`${row.title} 완료`} type="checkbox" checked={checked} disabled={saving} onChange={() => void safeMutation(() => toggleTask(row))}/ >}
          <div className="rp-item-copy">
            {hasSignalDetail ? <button type="button" className="rp-signal-toggle" aria-expanded={isSignalExpanded} aria-controls={`${editorId}-detail`}
              onClick={() => setExpandedSignalIds((current) => {
                const next = new Set(current);
                if (next.has(editorId)) next.delete(editorId); else next.add(editorId);
                return next;
              })}>
              <span className="rp-item-heading"><span className="rp-signal-title">{row.title}</span>{badge && <span className={`rp-badge${badge === '미확인' || badge.includes('대기') || badge.includes('필요') ? ' is-unknown' : badge === '공식 확인' ? ' is-official' : ' is-source'}`}>{badge}</span>}{isSignalExpanded ? <ChevronUp className="rp-signal-toggle-indicator" size={14} aria-hidden="true"/> : <ChevronDown className="rp-signal-toggle-indicator" size={14} aria-hidden="true"/>}</span>
              <small id={`${editorId}-detail`} className="rp-signal-detail" hidden={!isSignalExpanded}>{row.detail}</small>
            </button> : <>
              <div className="rp-item-heading"><p>{row.title}</p>{badge && <span className={`rp-badge${badge === '미확인' || badge.includes('대기') || badge.includes('필요') ? ' is-unknown' : badge === '공식 확인' ? ' is-official' : ' is-source'}`}>{badge}</span>}</div>
              {row.detail && <small>{row.detail}</small>}
            </>}
            {section !== 'WORK' && formatTime(row.occurred_at) && <div className="rp-item-meta"><time dateTime={row.occurred_at ?? undefined}>{formatTime(row.occurred_at)}</time></div>}
          </div>
          <RowActions actions={actions}/>
        </>}
      </div>;
    }) : <p className="right-panel-empty rp-empty">{emptyLabel}</p>}
  </div>;
  const selectAddChoice = (scope: keyof typeof RIGHT_PANEL_ADD_CHOICES, choice: RightPanelAddChoice) => {
    setAddingSection(choice.section);
    setAddingSignalKey(choice.signalKey ?? null);
    setAddingGroupKey(choice.groupKey ?? null);
    setAddChooser(null);
    setOpenBlocks((current) => ({
      ...current,
      [scope]: true,
      ...(scope === 'progress' ? { 'progress:todo': true } : {}),
      ...(choice.groupKey ? { [`${scope === 'exposure' ? 'exposure-group' : 'fraud'}:${choice.groupKey}`]: true } : {}),
    }));
  };
  const requestAdd = (scope: keyof typeof RIGHT_PANEL_ADD_CHOICES, groupKey?: string) => {
    const choices = RIGHT_PANEL_ADD_CHOICES[scope].filter((choice) => !groupKey || choice.groupKey === groupKey);
    if (choices.length === 1) selectAddChoice(scope, choices[0]);
    else if (choices.length > 1) setAddChooser((current) => current?.scope === scope && current.groupKey === groupKey ? null : { scope, groupKey, choices });
  };
  const renderAddChooser = (scope: keyof typeof RIGHT_PANEL_ADD_CHOICES, groupKey?: string) => addChooser?.scope === scope && addChooser.groupKey === groupKey ? <div className="rp-add-choice-list" role="group" aria-label="추가할 항목 종류 선택">
    {addChooser.choices.map((choice) => <button key={choice.id} type="button" onClick={() => selectAddChoice(scope, choice)}>{choice.label}</button>)}
  </div> : null;
  const renderBlockHeader = (id: string, title: string, count: React.ReactNode, defaultOpen = true, addScope?: keyof typeof RIGHT_PANEL_ADD_CHOICES) => {
    const expanded = openBlocks[id] ?? defaultOpen;
    return <header className="right-panel-block-header rp-section-header">
      <button type="button" className="rp-section-heading" aria-expanded={expanded} onClick={() => setOpenBlocks((current) => ({ ...current, [id]: !(current[id] ?? defaultOpen) }))}><strong>{title}</strong><small>{count}건</small></button>
      {addScope && <button type="button" className="right-panel-icon-button" aria-label={`${title} 항목 추가`} title="항목 추가" aria-haspopup="true" aria-expanded={addChooser?.scope === addScope} onClick={() => { setOpenBlocks((current) => ({ ...current, [id]: true })); requestAdd(addScope); }}><Plus size={15}/></button>}
      <button type="button" className="rp-collapse-toggle" aria-label={expanded ? `${title} 접기` : `${title} 펼치기`} title={expanded ? '접기' : '펼치기'} aria-expanded={expanded} onClick={() => setOpenBlocks((current) => ({ ...current, [id]: !(current[id] ?? defaultOpen) }))}>{expanded ? <ChevronUp size={16}/> : <ChevronDown size={16}/>}</button>
    </header>;
  };
  const blockIsOpen = (id: string, defaultOpen = true) => openBlocks[id] ?? defaultOpen;
  const fraudRowCount = contacts.active.length + fraudGroups.reduce((count, group) => count + group.active.length, 0);
  const exposureRowCount = exposureGroups.reduce((count, group) => count + group.active.length, 0) + unclassifiedExposureRows.length;
  const workflowRowCount = openProgressCount + completedProgressCount;
  const renderProgressGroup = (id: string, title: string, rows: PanelRow[], addSection?: RightPanelItem['section'], canAdd = id.endsWith('-todo')) => {
    const actionSection = addSection ?? (id === 'progress-work-todo' ? 'WORK' : undefined);
    const expanded = openBlocks[id] ?? true;
    return rows.length > 0 || canAdd ? <div className="rp-presentation-group" key={id}>
    <header className="rp-presentation-group-header"><button type="button" className="rp-presentation-group-title" aria-expanded={expanded} onClick={() => setOpenBlocks((current) => ({ ...current, [id]: !(current[id] ?? true) }))}><strong>{title}</strong><small>{rows.length}건</small></button>
      <button type="button" className="rp-collapse-toggle" aria-label={expanded ? `${title} 접기` : `${title} 펼치기`} title={expanded ? '접기' : '펼치기'} aria-expanded={expanded} onClick={() => setOpenBlocks((current) => ({ ...current, [id]: !(current[id] ?? true) }))}>{expanded ? <ChevronUp size={15}/> : <ChevronDown size={15}/>}</button>
      {canAdd && actionSection && <button type="button" className="right-panel-icon-button rp-middle-add-trigger" aria-label={`${title} 추가`} title={`${title} 추가`} onClick={() => {
        const choice = RIGHT_PANEL_ADD_CHOICES.progress.find((item) => item.section === actionSection);
        if (choice) selectAddChoice('progress', choice);
      }}><Plus size={14}/></button>}
    </header>
    {expanded && <>{canAdd && actionSection && renderAddForm(actionSection)}{rows.length > 0 && renderRows(rows)}</>}
  </div> : null;
  };

  return <aside className={`context-panel context-panel-v3 context-panel-foundation ${open ? 'is-open' : ''}`} aria-label="우측 사건 패널">
    {headerActions && <div className="context-panel-room-actions">{headerActions}</div>}
    <div className="context-header context-v3-sticky-header"><div><h2>사건 현황</h2><small>{caseItem.updated_at ? `업데이트 · ${formatTime(caseItem.updated_at)}` : '업데이트 시간 확인 필요'}</small></div>
      <button type="button" className="context-open context-header-toggle" onClick={onToggle} aria-label={open ? '사건 패널 닫기' : '사건 패널 열기'} title={open ? '사건 패널 닫기' : '사건 패널 열기'}>{open ? <PanelRightClose size={17}/> : <PanelRightOpen size={17}/>}</button>
    </div>
    <div className="right-panel-scroll rp-current-snapshot-panel">
      <section className="right-panel-one-line right-panel-current-snapshot"><span>{RIGHT_PANEL_TOP_LEVEL_LABELS[0]}</span><p className="right-panel-summary-headline">{summary}</p>
        {presentation.summaryBadges.length > 0 && <div className="rp-summary-badges">{presentation.summaryBadges.map((badge) => <span key={badge.key} className={`rp-summary-badge is-${badge.tone}`}>{badge.label}</span>)}</div>}
      </section>

      <section className="right-panel-block rp-data-block">
        {renderBlockHeader('exposure', RIGHT_PANEL_TOP_LEVEL_LABELS[1], exposureRowCount)}
        {blockIsOpen('exposure') && <>
          <div className="rp-presentation-groups">
            {exposureGroups.map((group) => {
              const id = `exposure-group:${group.key}`;
              const expanded = openBlocks[id] ?? group.active.length > 0;
              return <section className="rp-presentation-group" key={group.key}>
                <header className="rp-presentation-group-header"><button type="button" className="rp-presentation-group-title" aria-expanded={expanded} onClick={() => setOpenBlocks((current) => ({ ...current, [id]: !(current[id] ?? group.active.length > 0) }))}><strong>{group.label}</strong><small>{group.active.length}건</small></button>
                  <button type="button" className="right-panel-icon-button rp-middle-add-trigger" aria-label={`${group.label} 항목 추가`} title={`${group.label} 항목 추가`} onClick={() => requestAdd('exposure', group.key)}><Plus size={14}/></button>
                  <button type="button" className="rp-collapse-toggle" aria-label={expanded ? `${group.label} 접기` : `${group.label} 펼치기`} title={expanded ? '접기' : '펼치기'} aria-expanded={expanded} onClick={() => setOpenBlocks((current) => ({ ...current, [id]: !(current[id] ?? group.active.length > 0) }))}>{expanded ? <ChevronUp size={15}/> : <ChevronDown size={15}/>}</button>
                </header>
                {renderAddChooser('exposure', group.key)}
                {expanded && <>{renderAddForm('EXPOSURE', undefined, group.key)}{group.categoryKeys.map((categoryKey) => <React.Fragment key={categoryKey}>{renderAddForm('SIGNAL', categoryKey)}</React.Fragment>)}{group.active.length > 0 && renderRows(group.active)}</>}
              </section>;
            })}
          </div>
          {unclassifiedExposureRows.length > 0 && <section className="rp-unclassified-exposure" aria-live="polite">
            <div><strong>분류 확인 필요 · {unclassifiedExposureRows.length}건</strong><p>항목은 보존했습니다. API/프론트 버전을 확인하고 새로고침해 주세요.</p></div>
            {renderRows(unclassifiedExposureRows)}
          </section>}
        </>}
      </section>
      <section className="right-panel-block rp-data-block">
        {renderBlockHeader('progress', RIGHT_PANEL_TOP_LEVEL_LABELS[2], workflowRowCount)}
        {blockIsOpen('progress') && <>
          <section className="right-panel-guide-lane is-incomplete"><button type="button" className="right-panel-lane-header" aria-expanded={openBlocks['progress:todo'] ?? true} onClick={() => setOpenBlocks((current) => ({ ...current, 'progress:todo': !(current['progress:todo'] ?? true) }))}><span>진행 중</span><b>{openProgressCount}건</b>{openBlocks['progress:todo'] === false ? <ChevronDown size={16}/> : <ChevronUp size={16}/>}</button>
            {(openBlocks['progress:todo'] ?? true) && <div className="rp-progress-content">{renderProgressGroup('progress-verify-todo', '확인 업무', [...incompleteVerifications, ...incompleteChecks], 'VERIFICATION')}{renderProgressGroup('progress-work-todo', '대응 조치', incompleteActions, 'WORK')}</div>}
          </section>
          <section className="right-panel-guide-lane is-completed"><button type="button" className="right-panel-lane-header" aria-expanded={openBlocks['progress:done'] ?? false} onClick={() => setOpenBlocks((current) => ({ ...current, 'progress:done': !(current['progress:done'] ?? false) }))}><span>완료</span><b>{completedProgressCount}건</b>{openBlocks['progress:done'] ? <ChevronUp size={16}/> : <ChevronDown size={16}/>}</button>
            {openBlocks['progress:done'] && <div className="rp-progress-content">{renderProgressGroup('progress-verify-done', '확인 완료', [...completedVerifications, ...completedChecks], undefined, false)}{renderProgressGroup('progress-work-done', '조치 완료', completedActions, undefined, false)}</div>}
          </section>
          {openProgressCount + completedProgressCount === 0 && <p className="right-panel-empty rp-empty">확인·조치 기록이 없습니다.</p>}
        </>}
      </section>
      <section className="right-panel-block rp-data-block">
        {renderBlockHeader('fraud', RIGHT_PANEL_TOP_LEVEL_LABELS[3], fraudRowCount)}
        {blockIsOpen('fraud') && <div className="rp-presentation-groups">
          {fraudGroups.map((group) => {
            const rows = [...(group.includesContacts ? contacts.active : []), ...group.active];
            const id = `fraud:${group.key}`;
            const expanded = openBlocks[id] ?? rows.length > 0;
            return <section className="rp-presentation-group" key={group.key}>
              <header className="rp-presentation-group-header"><button type="button" className="rp-presentation-group-title" aria-expanded={expanded} onClick={() => setOpenBlocks((current) => ({ ...current, [id]: !(current[id] ?? rows.length > 0) }))}><strong>{group.label}</strong><small>{rows.length}건</small></button>
                <button type="button" className="right-panel-icon-button rp-middle-add-trigger" aria-label={`${group.label} 항목 추가`} title={`${group.label} 항목 추가`} onClick={() => requestAdd('fraud', group.key)}><Plus size={14}/></button>
                <button type="button" className="rp-collapse-toggle" aria-label={expanded ? `${group.label} 접기` : `${group.label} 펼치기`} title={expanded ? '접기' : '펼치기'} aria-expanded={expanded} onClick={() => setOpenBlocks((current) => ({ ...current, [id]: !(current[id] ?? rows.length > 0) }))}>{expanded ? <ChevronUp size={15}/> : <ChevronDown size={15}/>}</button>
              </header>
              {renderAddChooser('fraud', group.key)}
              {expanded && <>{group.includesContacts && renderAddForm('CONTACT')}{group.categories.map((category) => <React.Fragment key={category.key}>{renderAddForm('SIGNAL', category.key)}</React.Fragment>)}{renderRows(rows, `${group.label} 없음`)}</>}
            </section>;
          })}
        </div>}
      </section>
      <section className="right-panel-block rp-data-block">
        {renderBlockHeader('activity', RIGHT_PANEL_TOP_LEVEL_LABELS[4], activity.active.length, false)}
        {blockIsOpen('activity', false) && renderRows(activity.active, '처리 기록 없음')}
      </section>

      {archivedAll.length > 0 && <details className="right-panel-archive rp-archive-all"><summary><Archive size={14}/>제외·보관된 항목 {archivedAll.length}건</summary>
        {archivedAll.map((row) => {
          const stored = storedMap.get(storedKey(row.section, row.semantic_key));
          if (!stored) return null;
          return <div className="right-panel-archive-row rp-archived-item" key={`${row.section}:${row.semantic_key}`}>
            <div><small>{row.categoryLabel}</small><span>{row.title}</span></div>
            <div className="right-panel-archive-actions"><button type="button" aria-label="항목 복구" title="복구" disabled={saving} onClick={() => void safeMutation(() => mutateRow(row, 'RESTORE'))}><RotateCcw size={13}/></button>
              <button type="button" className="right-panel-permanent-delete" disabled={saving} onClick={() => {
                if (!window.confirm('완전 삭제하면 복구가 불가능 합니다. 삭제하시겠습니까?')) return;
                void safeMutation(() => mutateRow(row, 'PERMANENT_HIDE'));
              }}><Trash2 size={13}/><span>완전 삭제</span></button></div>
          </div>;
        })}
      </details>}
      {loadError && <p className="rp-error" role="alert">{loadError}</p>}
      {saving && <span className="rp-saving" role="status">저장 중…</span>}
    </div>
  </aside>;
};
