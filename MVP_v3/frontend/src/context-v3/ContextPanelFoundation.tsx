import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Archive, Check, ChevronDown, ChevronUp, MoreHorizontal, PanelRightClose, PanelRightOpen, Pencil, Plus, RotateCcw, Trash2 } from 'lucide-react';
import { casesApi } from '../api/cases';
import type {
  CaseBundle, CaseSupportSnapshot, RightPanelItem, RightPanelProjection, RightPanelStoredItem,
  RightPanelStorageSection, StoredCase,
} from '../api/types';
import { completeContextTask, loadContextTasks, updateContextTask } from './api';
import type { ContextTaskV2 } from './api';

export const rightPanelPresentation = (projection: RightPanelProjection | null | undefined) => ({
  summary: projection?.current_case_summary?.trim() || '현재 확인된 사건 요약이 없습니다.',
  fraudSignals: projection?.fraud_signals ?? [],
});

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
  EXPOSURE: '피해·노출', CONTACT: '사칭·접촉 정보', SIGNAL: '주요 보이스피싱 정황',
  VERIFICATION: '확인·검증 현황', WORK: '업무 진행 현황', ACTIVITY: '처리 기록',
};
const statusText = (status: string | null | undefined) => ({
  TODO: '미완료', IN_PROGRESS: '미완료', BLOCKED: '미완료', COMPLETED: '완료',
  PENDING: '대기', ON_HOLD: '보류', FAILED: '확인 필요',
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
  const menuRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return undefined;
    const pointer = (event: PointerEvent) => { if (!(event.target instanceof Node) || !menuRef.current?.contains(event.target)) setOpen(false); };
    const keydown = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpen(false); };
    document.addEventListener('pointerdown', pointer);
    document.addEventListener('keydown', keydown);
    return () => { document.removeEventListener('pointerdown', pointer); document.removeEventListener('keydown', keydown); };
  }, [open]);
  return <div ref={menuRef} className={`right-panel-row-actions${open ? ' is-open' : ''}`}>
    <button type="button" className="right-panel-row-menu-trigger" aria-label="추가 작업 열기" aria-expanded={open} title="추가 작업" onClick={() => setOpen((current) => !current)}><MoreHorizontal size={15}/></button>
    {open && <div className="right-panel-row-action-menu" role="menu">{actions.map((action) => <button key={action.label} type="button" role="menuitem" className={`right-panel-row-action${action.danger ? ' is-danger' : ''}`} onClick={() => { setOpen(false); action.onClick(); }}>{action.icon}<span>{action.label}</span></button>)}</div>}
  </div>;
};

export const ContextPanelFoundation: React.FC<Props> = ({ open, onToggle, caseItem, support, headerActions }) => {
  const [storedItems, setStoredItems] = useState<RightPanelStoredItem[]>([]);
  const [tasks, setTasks] = useState<ContextTaskV2[]>([]);
  const [loadError, setLoadError] = useState('');
  const [saving, setSaving] = useState(false);
  const [summaryOverride, setSummaryOverride] = useState<CaseSupportSnapshot | null>(null);
  const [openBlocks, setOpenBlocks] = useState<Record<string, boolean>>({});
  const [editing, setEditing] = useState<{ id: string; text: string } | null>(null);
  const [addingSection, setAddingSection] = useState<RightPanelItem['section'] | null>(null);
  const [addingSignalKey, setAddingSignalKey] = useState<string | null>(null);
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
    setStoredItems([]); setTasks([]); setLoadError(''); setSummaryOverride(null);
    void Promise.all([reloadStored(controller.signal), loadContextTasks(caseItem.case_id, controller.signal)])
      .then(([rows, loadedTasks]) => { if (!controller.signal.aborted) { setStoredItems(rows); setTasks(loadedTasks); } })
      .catch((reason) => { if (!controller.signal.aborted) setLoadError(reason instanceof Error ? reason.message : '우측 패널의 저장 정보를 불러오지 못했습니다.'); });
    return () => controller.abort();
  // Reload only when the active Case changes. Snapshot updates are supplied by the parent.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseItem.case_id]);
  useEffect(() => { setSummaryOverride(null); }, [support?.source_revision, support?.projection_revision]);

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
  const rawSignals = presentation.fraudSignals;
  const rawVerification = projection?.verification ?? [];
  const rawWork = [...(projection?.incomplete_work ?? []), ...(projection?.completed_work ?? [])];
  const rawActivity = projection?.activity ?? [];
  const exposure = mergeRows('EXPOSURE', rawExposure);
  const contacts = mergeRows('CONTACT', rawContacts);
  const verifications = mergeRows('VERIFICATION', rawVerification);
  const work = mergeRows('WORK', rawWork);
  const activity = mergeRows('ACTIVITY', rawActivity);
  const signalCategories = rawSignals.map((category) => ({ ...category, ...mergeRows('SIGNAL', category.items, category.key) }));
  const activeSignalRows = signalCategories.flatMap((category) => category.active);
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
    void safeMutation(async () => { await mutateRow(row, 'EDIT', editing.text.trim()); setEditing(null); });
  };
  const archiveRow = (row: PanelRow) => void safeMutation(() => mutateRow(row, 'ARCHIVE'));
  const addRow = (section: RightPanelItem['section'], categoryKey?: string) => {
    const title = draft.trim();
    if (!title) return;
    const semanticKey = newSemanticKey();
    void safeMutation(async () => {
      const item = await casesApi.mutateRightPanelItem(caseItem.case_id, PANEL_SECTIONS[section], semanticKey, {
        expected_version: 0, operation: 'ADD', text: title,
        evidence_refs: categoryKey ? [`category:${categoryKey}`] : [],
      });
      setStoredItems((current) => [...current, item]); setDraft(''); setAddingSection(null); setAddingSignalKey(null);
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

  const renderAddForm = (section: RightPanelItem['section'], categoryKey?: string) => addingSection === section && (section !== 'SIGNAL' || addingSignalKey === categoryKey) ? <form className="right-panel-inline-form rp-add-form" onSubmit={(event) => { event.preventDefault(); addRow(section, categoryKey); }}>
    <textarea autoFocus value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={section === 'WORK' ? '업무 내용을 입력하세요.' : '항목 내용을 입력하세요.'}/>
    <div><button type="button" onClick={() => { setAddingSection(null); setDraft(''); }}>취소</button><button type="submit" disabled={saving || !draft.trim()}><Plus size={13}/>추가</button></div>
  </form> : null;
  const renderRows = (section: RightPanelItem['section'], rows: PanelRow[]) => <div className="right-panel-category-list rp-row-list">
    {rows.length ? rows.map((row) => {
      const editorId = `${section}:${row.semantic_key}`;
      const checked = section === 'WORK' && row.status === 'COMPLETED';
      const actions: RowAction[] = [
        ...(section === 'WORK' ? [{ label: checked ? '미완료로 변경' : '완료', icon: checked ? <RotateCcw size={13}/> : <Check size={13}/>, onClick: () => void safeMutation(() => toggleTask(row)) }] : []),
        { label: '수정', icon: <Pencil size={13}/>, onClick: () => setEditing({ id: editorId, text: row.title }) },
        { label: '보관', icon: <Archive size={13}/>, onClick: () => archiveRow(row) },
      ];
      return <div className={`right-panel-brief-item rp-item-row${checked ? ' is-completed' : ''}`} key={editorId}>
        {editing?.id === editorId ? <form className="right-panel-inline-form rp-edit-form" onSubmit={(event) => { event.preventDefault(); saveEdit(row); }}>
          <textarea autoFocus value={editing.text} onChange={(event) => setEditing((current) => current ? { ...current, text: event.target.value } : current)}/>
          <div><button type="button" onClick={() => setEditing(null)}>취소</button><button type="submit" disabled={saving || !editing.text.trim()}><Check size={13}/>저장</button></div>
        </form> : <>
          <span className={`rp-item-indicator${section === 'WORK' ? ' is-hidden' : ''}`} aria-hidden="true" />
          {section === 'WORK' && <input className="rp-work-checkbox" aria-label={`${row.title} 완료`} type="checkbox" checked={checked} disabled={saving} onChange={() => void safeMutation(() => toggleTask(row))}/ >}
          <div className="rp-item-copy"><p>{row.title}</p>{row.detail && <small>{row.detail}</small>}
            <div className="rp-item-meta">{row.source_badge && <span className={`rp-badge is-${row.source_badge === '미확인' ? 'unknown' : row.source_badge === '공식 확인' ? 'official' : 'source'}`}>{row.source_badge}</span>}
              {section === 'VERIFICATION' && row.status && <span>{statusText(row.status)}</span>}
              {section === 'WORK' && <span>{statusText(row.status)}</span>}
              {row.actor_id && <span>담당자</span>}
              {formatTime(row.occurred_at) && <time dateTime={row.occurred_at ?? undefined}>{formatTime(row.occurred_at)}</time>}
            </div>
          </div>
          <RowActions actions={actions}/>
        </>}
      </div>;
    }) : <p className="right-panel-empty rp-empty">등록된 항목 없음</p>}
  </div>;
  const renderBlockHeader = (id: string, title: string, count: number, defaultOpen = true, addSection?: RightPanelItem['section']) => {
    const expanded = openBlocks[id] ?? defaultOpen;
    return <header className="right-panel-block-header rp-section-header">
      <button type="button" aria-expanded={expanded} onClick={() => setOpenBlocks((current) => ({ ...current, [id]: !(current[id] ?? defaultOpen) }))}>
        <strong>{title}</strong><small>{count}건</small>{expanded ? <ChevronUp size={16}/> : <ChevronDown size={16}/>}
      </button>
      {addSection && <button type="button" className="right-panel-icon-button" aria-label={`${title} 항목 추가`} title="항목 추가" onClick={() => { setAddingSection(addSection); setOpenBlocks((current) => ({ ...current, [id]: true })); }}><Plus size={15}/></button>}
    </header>;
  };
  const blockIsOpen = (id: string, defaultOpen = true) => openBlocks[id] ?? defaultOpen;

  return <aside className={`context-panel context-panel-v3 context-panel-foundation ${open ? 'is-open' : ''}`} aria-label="우측 사건 패널">
    {headerActions && <div className="context-panel-room-actions">{headerActions}</div>}
    <div className="context-header context-v3-sticky-header"><div><h2>사건 현황</h2><small>{caseItem.updated_at ? `업데이트 · ${formatTime(caseItem.updated_at)}` : '업데이트 시간 확인 필요'}</small></div>
      <button type="button" className="context-open context-header-toggle" onClick={onToggle} aria-label={open ? '사건 패널 닫기' : '사건 패널 열기'} title={open ? '사건 패널 닫기' : '사건 패널 열기'}>{open ? <PanelRightClose size={17}/> : <PanelRightOpen size={17}/>}</button>
    </div>
    <div className="right-panel-scroll rp-current-snapshot-panel">
      <section className="right-panel-one-line right-panel-current-snapshot"><span>현재 사건 요약</span><p className="right-panel-summary-headline">{summary}</p></section>

      <section className="right-panel-block rp-data-block">
        {renderBlockHeader('exposure', '1. 피해·노출', exposure.active.length, true, 'EXPOSURE')}
        {blockIsOpen('exposure') && <>{renderAddForm('EXPOSURE')}{renderRows('EXPOSURE', exposure.active)}</>}
      </section>
      <section className="right-panel-block rp-data-block">
        {renderBlockHeader('contacts', '2. 사칭·접촉 정보', contacts.active.length, true, 'CONTACT')}
        {blockIsOpen('contacts') && <>{renderAddForm('CONTACT')}{renderRows('CONTACT', contacts.active)}</>}
      </section>
      <section className="right-panel-block rp-data-block">
        {renderBlockHeader('signals', '3. 주요 보이스피싱 정황', activeSignalRows.length, true)}
        {blockIsOpen('signals') && <div className="right-panel-brief-section rp-signal-groups">{signalCategories.map((category) => {
          const id = `signal:${category.key}`;
          const expanded = openBlocks[id] ?? category.active.length > 0;
          return <section className={`right-panel-brief-category${category.active.length === 0 ? ' is-empty' : ''}`} key={category.key}>
            <header><button type="button" className="right-panel-category-toggle" aria-expanded={expanded} onClick={() => setOpenBlocks((current) => ({ ...current, [id]: !(current[id] ?? category.active.length > 0) }))}>
              {expanded ? <ChevronUp size={17}/> : <ChevronDown size={17}/>}<span>{category.label}</span><small>{category.active.length}건</small>
            </button><button type="button" className="right-panel-icon-button" aria-label={`${category.label} 정황 추가`} title="정황 추가" onClick={() => { setAddingSection('SIGNAL'); setAddingSignalKey(category.key); setOpenBlocks((current) => ({ ...current, signals: true, [id]: true })); }}><Plus size={14}/></button></header>
            {expanded && <>{renderAddForm('SIGNAL', category.key)}{renderRows('SIGNAL', category.active)}</>}
          </section>;
        })}</div>}
      </section>
      <section className="right-panel-block rp-data-block">
        {renderBlockHeader('verification', '4. 확인·검증 현황', verifications.active.length, true, 'VERIFICATION')}
        {blockIsOpen('verification') && <>{renderAddForm('VERIFICATION')}{renderRows('VERIFICATION', verifications.active)}</>}
      </section>
      <section className="right-panel-block rp-data-block">
        {renderBlockHeader('work', '5. 업무 진행 현황', workRows.length, true, 'WORK')}
        {blockIsOpen('work') && <>
          {renderAddForm('WORK')}
          <section className="right-panel-guide-lane is-incomplete"><button type="button" className="right-panel-lane-header" aria-expanded={openBlocks['work:todo'] ?? true} onClick={() => setOpenBlocks((current) => ({ ...current, 'work:todo': !(current['work:todo'] ?? true) }))}><span>미완료</span><b>{incompleteWork.length}건</b>{openBlocks['work:todo'] === false ? <ChevronDown size={16}/> : <ChevronUp size={16}/>}</button>{(openBlocks['work:todo'] ?? true) && renderRows('WORK', incompleteWork)}</section>
          <section className="right-panel-guide-lane is-completed"><button type="button" className="right-panel-lane-header" aria-expanded={openBlocks['work:done'] ?? false} onClick={() => setOpenBlocks((current) => ({ ...current, 'work:done': !(current['work:done'] ?? false) }))}><span>완료</span><b>{completedWork.length}건</b>{openBlocks['work:done'] && <ChevronUp size={16}/>}</button>{openBlocks['work:done'] && renderRows('WORK', completedWork)}</section>
        </>}
      </section>
      <section className="right-panel-block rp-data-block">
        {renderBlockHeader('activity', '6. 처리 기록', activity.active.length, false)}
        {blockIsOpen('activity', false) && renderRows('ACTIVITY', activity.active)}
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
