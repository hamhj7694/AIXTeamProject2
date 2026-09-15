const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {buildSync} = require('esbuild');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');

const source = (relative) => fs.readFileSync(path.resolve(__dirname, '..', relative), 'utf8');
const types = source('src/context-v3/types.ts');
const panel = source('src/context-v3/ContextPanelV3.tsx');
const sections = source('src/context-v3/sections.tsx');
const components = source('src/context-v3/components.tsx');
const quickNav = source('src/context-v3/ContextQuickNav.tsx');
const history = source('src/context-v3/HistoryDrawer.tsx');
const api = source('src/context-v3/api.ts');
const room = source('src/pages/CaseRoomPage.tsx');
const question = source('src/customer/CustomerQuestionCard.tsx');
const progressEditorSource = source('src/components/CustomerProgressEditor.tsx');
const styles = source('src/styles.css');

for (const section of ['SUMMARY', 'EXPOSURE', 'IMPERSONATION_CONTACT', 'FRAUD_CIRCUMSTANCES', 'FACT_VERIFICATION', 'STAFF_ACTIONS', 'CUSTOMER_SHARE']) {
  assert.match(types, new RegExp(`\\b${section}\\b`));
}
assert.match(room, /import \{ ContextPanelV3 \}/);
assert.match(room, /<ContextPanelV3/);
assert.doesNotMatch(room, /import \{ CaseContextPanel \}/);
assert.match(panel, /reviewContextFact/);
assert.match(panel, /reviewContextSuggestion/);
assert.match(panel, /createContextFact/);
assert.match(panel, /createContextTask/);
assert.match(panel, /completeContextTask/);
assert.match(sections, /현재 사건 요약/);
assert.match(sections, /피해·노출/);
assert.match(sections, /사칭·접촉 정보/);
assert.match(sections, /상대방 주장/);
assert.match(sections, /사실·확인 현황/);
assert.match(sections, /AI 제안 · 직원 검토 필요/);
assert.match(sections, /고객 공유 결과/);
assert.match(sections, /<SectionShell id="CUSTOMER_SHARE" title="고객 공유 결과" open=/);
assert.doesNotMatch(sections, /context-share-notice|context-share-lane|context-progress-editor|고객에게 공개된 안내·확정 결과|별도로 공개된 안내·확정 결과가 없습니다/);
assert.match(sections, /const caseMetadata = `위험도 \$\{risk\} · 진행 상태 \$\{status\}`/);
assert.match(sections, /item\.source_kind !== 'DETERMINISTIC_PROJECTION' \|\| item\.display_value !== caseMetadata/);
assert.doesNotMatch(sections, /includes\(['"]위험도|startsWith\(['"]위험도/);
assert.doesNotMatch(sections, /서버 allowlist|현재 고객에게 공유된 결과가 없습니다/);
assert.match(progressEditorSource, /고객 화면에 공개되며 고객 상담 AI의 참고 정보로도 사용됩니다/);
assert.match(components, /Evidence/);
assert.match(components, /context-fact-row/);
assert.match(components, /context-evidence-empty/);
assert.match(components, /context-evidence-toggle/);
assert.match(components, /open && summaryList/);
assert.match(components, /<Evidence item=\{item\} compact\/>/);
assert.match(components, /'완료·취소 업무'\} \{items\.length\}건/);
assert.match(components, /aria-expanded=\{open\}/);
assert.match(components, /업무 복구/);
assert.match(components, /kind === 'fact' \? '제외된 정보'/);
assert.match(components, /items\.length === 0 && kind === 'task'/);
assert.match(components, /제외된 정보가 없습니다/);
assert.match(components, /kind === 'fact' \? '정보 복구'/);
assert.equal((sections.match(/<HistoryHint kind="fact"/g) ?? []).length, 4);
assert.match(panel, /decision === 'RESTORE'/);
assert.match(api, /'CONFIRM' \| 'REJECT' \| 'RESTORE' \| 'UNCONFIRM' \| 'INVALIDATE'/);
assert.match(components, /정보 정정/);
assert.match(components, /확정 취소/);
assert.match(panel, /supersedes_fact_id: item\.item_id/);
assert.match(panel, /decision === 'INVALIDATE'/);
assert.match(sections, /onWorkflow\(item, 'RESTORE'\)/);
assert.match(panel, /action === 'RESTORE'/);
assert.match(panel, /updateContextTask\(props\.caseItem\.case_id, item\.item_id, item\.version, 'TODO'\)/);
assert.match(styles, /\.context-archive-list/);
assert.match(sections, /needs\.map\(\(item\) => <FactRow/);
assert.match(components, /VerificationCard[\s\S]*context-domain-card verification-card/);
assert.match(components, /SuggestionCard[\s\S]*context-domain-card suggestion-card/);
assert.match(components, /TaskCard[\s\S]*context-domain-card task-card/);
assert.match(styles, /\.context-fact-row \{[^}]*gap: 2px;[^}]*padding: 5px 1px 6px;[^}]*background: transparent/);
assert.match(styles, /\.context-fact-marker \{[^}]*height: 24px;[^}]*place-items: center/);
assert.match(styles, /\.context-fact-main > p \{[^}]*padding-top: 4px;[^}]*font-size: 10px;[^}]*line-height: 1\.4/);
assert.match(styles, /\.context-fact-meta \{[^}]*grid-template-columns: max-content max-content minmax\(0,1fr\)/);
assert.match(styles, /\.context-compact-evidence-panel \{[^}]*grid-column: 1 \/ -1/);
assert.match(styles, /\.context-fact-row \.context-more-trigger \{[^}]*width: 30px;[^}]*height: 30px/);
assert.match(styles, /\.context-more-trigger \{[^}]*display: inline-flex;[^}]*align-items: center;[^}]*justify-content: center;[^}]*padding: 0;[^}]*line-height: 0/);
assert.match(styles, /\.context-more-trigger svg \{[^}]*display: block;[^}]*width: 15px;[^}]*height: 15px/);
assert.match(styles, /\.context-section-toggle strong \{[^}]*font-size: 12px/);
assert.match(styles, /\.context-source-badge, \.context-status-badge \{[^}]*font-size: 8px/);
assert.match(styles, /\.context-evidence-toggle, \.context-evidence-empty \{[^}]*font-size: 9px/);
assert.doesNotMatch(components, /API 필요|Backend 계약|전용 API/);
assert.match(components, /AI 추출 · 확인 필요/);
assert.match(components, /VERIFICATION_RESULT: '기관 확인 결과'/);
assert.match(components, /BANK_TRANSACTION: '거래 기록'/);
assert.match(components, /counts\.set\(label, \(counts\.get\(label\) \?\? 0\) \+ 1\)/);
assert.doesNotMatch(components, />\{ref\.type\} · \{ref\.id\}/);
assert.doesNotMatch(components, /AI 신뢰도 \{Math\.round/);
assert.match(components, /TRANSFERRED: '이체함', NOT_TRANSFERRED: '이체하지 않음', UNKNOWN: '확인 필요'/);
assert.match(components, /staffDisplayValue\(item\)/);
assert.doesNotMatch(components, /title=\{sourceLabels\[source\]/);
assert.doesNotMatch(components, /title=\{statusLabels\[status\]/);
assert.doesNotMatch(history, /title=\{eventLabels|title=\{actorLabels/);
assert.match(panel, /저장 후 ‘확인 필요’ 상태로 등록/);
assert.doesNotMatch(panel, />CASE CONTEXT</);
assert.match(quickNav, /사건 맥락 빠른 이동/);
assert.match(quickNav, /onNavigate\(section\.section_id\)/);
assert.match(quickNav, /activeSection === section\.section_id \? 'is-active'/);
assert.match(quickNav, /aria-current=/);
assert.match(quickNav, /section\.section_id !== 'CUSTOMER_SHARE' && <b>\{count\(section\)\}<\/b>/);
assert.doesNotMatch(quickNav, /countOverrides/);
assert.doesNotMatch(quickNav, /href=|filter/);
assert.match(styles, /\.context-quick-nav button\.is-active/);
assert.match(styles, /\.context-quick-nav \{[^}]*min-height: 45px;[^}]*flex: 0 0 auto;/);
assert.match(styles, /\.context-scroll \{[^}]*flex: 1 1 auto;[^}]*overflow-y: auto;[^}]*scrollbar-gutter: stable;/);
assert.match(styles, /\.context-panel-v3 \.context-scroll \{ padding: 8px 4px 20px; \}/);
assert.match(styles, /\.context-summary-area > header \{ flex-wrap: wrap;/);
assert.match(styles, /\.context-section-toggle strong \{[^}]*min-width: min-content;[^}]*word-break: keep-all;/);
assert.match(styles, /\.context-summary-actions \{[^}]*flex: 0 0 auto;[^}]*white-space: nowrap;/);
assert.match(sections, /aria-label="표시 요약 편집" title="표시 요약 편집"/);
assert.match(styles, /@container context-panel \(max-width: 340px\)[\s\S]*\.context-summary-area > header \{ flex-wrap: nowrap; \}/);
assert.match(styles, /\.context-summary-actions > button > span \{ display: none; \}/);
assert.match(styles, /\.context-v3-summary-edit \{[^}]*margin: 12px 0 0;/);
assert.match(styles, /\.context-v3-summary-edit textarea \{[^}]*box-sizing: border-box;[^}]*min-height: 112px;[^}]*max-height: 260px;/);
assert.match(styles, /\.context-v3-summary-edit button:last-child \{[^}]*background: #2463eb;/);
assert.doesNotMatch(styles, /\.context-v3-summary-edit \{ margin: -5px/);
assert.match(styles, /scroll-margin-top: 10px/);
assert.doesNotMatch(history, /Audit History|전용 조회 API|Fact·Task/);
assert.match(api, /\/context-v2\/facts/);
assert.match(room, /<HistoryDrawer/);
assert.match(room, /<ParticipantManager/);
assert.match(room, /해결 및 종료/);
assert.doesNotMatch(panel, /onOpenParticipants|onFinalize|onReopen|onTrash/);
assert.match(question, /aria-pressed=\{active\}/);
assert.match(question, /question\.allow_multi_select/);
assert.match(question, /selected_option_ids/);
assert.match(question, /free_text/);

// Fact confirm must never infer a supersede target merely from semantic_key.
assert.doesNotMatch(panel, /\.find\(\(candidate\).*candidate\.semantic_key.*CONFIRMED/);
assert.match(panel, /reviewContextFact\([^;]+decision === 'UNCONFIRM' \? '직원이 확정 취소'/);
assert.match(panel, /supersedes_fact_id: item\.item_id/);

// Terminal and unknown states are explicitly read-only; Suggestions mutate only while proposed.
assert.match(components, /item\.status === 'REJECTED'/);
assert.match(components, /item\.status === 'SUPERSEDED'/);
assert.match(components, /item\.status === 'PROPOSED' && <footer>/);
assert.match(components, /const confirmed = item\.status === 'CONFIRMED'/);
assert.match(components, /상태 확인 필요/);
assert.match(components, /기타 출처/);

// Quick Nav and accordion headers share the panel-owned open state. Navigation
// opens only its target, scrolls after React commits it, and does not use timers.
assert.doesNotMatch(components, /<details[^>]*open=\{defaultOpen\}/);
assert.match(components, /className="context-section-toggle"[^>]+onClick=\{\(\) => onOpenChange\(!open\)/);
assert.match(components, /<\/button>\{action && <div className="context-section-action">/);
assert.doesNotMatch(components, /useState\(defaultOpen\)|forceOpen/);
assert.match(panel, /<Fragment key=\{props\.caseItem\.case_id\}>/);
assert.match(panel, /const \[openSections, setOpenSections\]/);
assert.match(panel, /if \(sectionId !== 'SUMMARY'\) setSectionOpen\(sectionId, true\)/);
assert.match(panel, /scrollIntoView\(\{ behavior: 'smooth', block: 'start' \}\)/);
assert.match(panel, /setActiveSection\(null\); setScrollRequest\(null\)/);
assert.doesNotMatch(panel, /customerShareCount|countOverrides/);
assert.match(panel, /visibleSummaryItems\(getSection\('SUMMARY'\), props\.caseItem\.risk, props\.caseItem\.status\)/);
assert.doesNotMatch(panel, /setTimeout/);
assert.match(panel, /setFactDraft\(null\)/);

// Inline create UX: one draft at a time, same-button toggle, section-first
// placement, successful reset, failed-request preservation, and Case isolation.
assert.match(panel, /const opening = factDraft\?\.section !== target/);
assert.match(panel, /setTaskDraft\(opening \? \{ title: '', description: '' \} : null\)/);
assert.match(panel, /setSectionOpen\(target, true\)/);
assert.match(panel, /setSectionOpen\('STAFF_ACTIONS', true\)/);
assert.match(panel, /setTaskDraft\(null\); setTaskFormError\(''\); setFactFormError\(''\)/);
assert.match(panel, /setFactDraft\(null\); setFactFormError\(''\); setTaskDraft\(null\); setTaskFormError\(''\)/);
assert.match(panel, /await createContextTask\([^;]+\); setTaskDraft\(null\); await load\(\)/);
assert.match(panel, /catch \(reason\) \{ setTaskFormError/);
assert.match(panel, /catch \(reason\) \{ setFactFormError/);
assert.doesNotMatch(panel, /추가할 담당자 업무 제목|업무 내용과 확인 기준을 입력하세요.'\)\?\.trim/);
assert.match(panel, /id="context-create-staff_actions"/);
assert.match(panel, /context-task-form/);
assert.match(sections, /\{props\.createForm\}<FactList/);
assert.match(sections, /controls="context-create-fraud_circumstances"\/>\}>\s*\{props\.createForm\}/);
assert.match(sections, /controls="context-create-staff_actions"\/>\}>\s*\{createForm\}/);
assert.match(sections, /aria-expanded=\{expanded\}/);

// Missing server sections are filled in expected order and surfaced to the user.
assert.match(panel, /const expectedSections/);
assert.match(panel, /normalizeSections/);
assert.doesNotMatch(panel, /sections\.find\([^\n]+\)!/);
assert.match(panel, /서버 응답에서 누락된 영역을 빈 상태로 표시합니다/);

// Verification/task guards and verified projector ID contract.
assert.match(components, /item\.status === 'ON_HOLD' \? '확인 재개·결과 기록'/);
assert.match(components, /item\.status === 'FAILED' \? '재시도' : ''/);
assert.match(components, /ON_HOLD: '확인 중단'/);
assert.match(sections, /item\.status === 'PENDING'/);
assert.match(sections, /item\.status === 'IN_PROGRESS'/);
assert.match(sections, /item\.status === 'COMPLETED'/);
assert.match(sections, /확인 실패·중단/);
assert.match(sections, /onCreateVerification/);
assert.doesNotMatch(sections, /API 필요|전용 API가 없어|Canonical Fact|Revision 연동/);
assert.match(room, /onCreateVerification=\{\(\) => setDialog\(\{ type: 'verification' \}\)\}/);
assert.match(components, /\['TODO', 'IN_PROGRESS', 'BLOCKED'\]\.includes/);
assert.match(panel, /item\.verification_task_id === id/);
assert.match(panel, /\['PENDING', 'ON_HOLD', 'FAILED'\]\.includes\(task\.status\)/);
assert.match(panel, /\{ \.\.\.task, status: 'IN_PROGRESS' \}/);

// User-facing history and popovers do not expose raw enums or incomplete menu semantics.
assert.match(history, /최근 사건 기록/);
assert.match(history, /기타 사건 기록/);
assert.match(history, /알 수 없는 수행자/);
assert.doesNotMatch(history, /replace\(\/_\/g/);
assert.doesNotMatch(components, /role="menu"|role="menuitem"/);
assert.match(components, /role="group"/);
assert.match(components, /aria-controls=\{popoverId\}/);
assert.match(history, /event\.key !== 'Tab'/);
assert.match(history, /previousFocus\?\.focus\(\)/);

// Participant/global case controls stay in the header, not the Context Panel.
assert.equal((room.match(/<ParticipantManager/g) ?? []).length, 1);
assert.doesNotMatch(panel, /ParticipantManager|finalizeCase|reopenCase|trashCase/);

// Render the production cards to verify state-dependent controls, rather than
// relying only on source strings for the highest-risk guards.
const built = buildSync({entryPoints:[path.resolve(__dirname, '../src/context-v3/components.tsx')], bundle:true, platform:'node', format:'cjs', packages:'external', write:false});
const moduleUnderTest = {exports:{}};
vm.runInNewContext(built.outputFiles[0].text, {module:moduleUnderTest, exports:moduleUnderTest.exports, require});
const {FactRow, SuggestionCard, VerificationCard, TaskCard} = moduleUnderTest.exports;
const item = (status) => ({item_id:'item-1', semantic_key:'test.key', label:'테스트 정보', display_value:'표시 값', value:{}, source_kind:'STAFF_CREATED', status, evidence_refs:[], visibility:'BANK_INTERNAL', masked:false, version:1});
const noop = () => {};
const renderFact = (status) => renderToStaticMarkup(React.createElement(FactRow, {item:item(status), busy:false, onConfirm:noop, onReject:noop}));
const proposedFact = renderFact('PROPOSED');
assert.match(proposedFact, /context-fact-row/);
assert.equal((proposedFact.match(/context-primary-action/g) ?? []).length, 1);
assert.match(proposedFact, /근거 없음/);
assert.doesNotMatch(proposedFact, /context-evidence-toggle/);
assert.match(proposedFact, /context-more-trigger/);
assert.doesNotMatch(proposedFact, /context-domain-card/);
const supportedFact = renderToStaticMarkup(React.createElement(FactRow, {item:{...item('PROPOSED'), evidence_refs:[{type:'MESSAGE', id:'message-1'}]}, busy:false, onConfirm:noop, onReject:noop}));
assert.match(supportedFact, /context-evidence-toggle/); assert.match(supportedFact, /근거 1건/); assert.match(supportedFact, /aria-expanded="false"/); assert.doesNotMatch(supportedFact, /context-compact-evidence-panel/);
const rejectedFact = renderFact('REJECTED');
assert.match(rejectedFact, /검토에서 제외된 정보/); assert.doesNotMatch(rejectedFact, /직원이 확인한 정보|context-primary-action|새 값으로 대체/);
const supersededFact = renderFact('SUPERSEDED');
assert.match(supersededFact, /새 정보로 대체된 기록/); assert.doesNotMatch(supersededFact, /직원이 확인한 정보|context-primary-action|새 값으로 대체/);
const confirmedFact = renderFact('CONFIRMED');
assert.match(confirmedFact, /context-fact-marker/); assert.match(confirmedFact, />확정</); assert.doesNotMatch(confirmedFact, /context-primary-action/);
const unknownFact = renderFact('FUTURE_STATE');
assert.match(unknownFact, /상태 확인 필요|읽기 전용 정보/); assert.doesNotMatch(unknownFact, /context-primary-action|새 값으로 대체/);
const acceptedSuggestion = renderToStaticMarkup(React.createElement(SuggestionCard, {item:item('ACCEPTED'), busy:false, onAccept:noop, onDismiss:noop}));
assert.doesNotMatch(acceptedSuggestion, /업무로 채택|제안 제외/);
const completedVerification = renderToStaticMarkup(React.createElement(VerificationCard, {item:item('COMPLETED'), busy:false, onOpen:noop}));
assert.doesNotMatch(completedVerification, /context-primary-action/);
for (const [status, label] of [['PENDING', '확인 시작'], ['IN_PROGRESS', '결과 기록'], ['ON_HOLD', '확인 재개·결과 기록'], ['FAILED', '재시도']]) {
  const verification = renderToStaticMarkup(React.createElement(VerificationCard, {item:item(status), busy:false, onOpen:noop}));
  assert.match(verification, /context-primary-action/); assert.match(verification, new RegExp(label));
}
for (const status of ['COMPLETED', 'CANCELLED']) {
  const task = renderToStaticMarkup(React.createElement(TaskCard, {item:item(status), busy:false, onStart:noop, onComplete:noop, onBlock:noop, onCancel:noop}));
  assert.doesNotMatch(task, /context-primary-action|업무 취소/);
}

// Customer Share is a single editing surface; removed publication lanes and their
// counts/empty states must not reappear around the existing progress editor.
const sectionsBuilt = buildSync({entryPoints:[path.resolve(__dirname, '../src/context-v3/sections.tsx')], bundle:true, platform:'node', format:'cjs', packages:'external', write:false});
const sectionsModule = {exports:{}};
vm.runInNewContext(sectionsBuilt.outputFiles[0].text, {module:sectionsModule, exports:sectionsModule.exports, require});
const {CustomerShareSection, SummarySection, visibleSummaryItems} = sectionsModule.exports;
const renderShare = () => renderToStaticMarkup(React.createElement(CustomerShareSection, {section:{section_id:'CUSTOMER_SHARE', title:'고객 공유', items:[], groups:{}}, progressEditor:React.createElement('div', {className:'public-progress-editor'}, 'd'), open:true, onOpenChange:noop}));
const share = renderShare();
assert.match(share, /context-section-customer_share-content/);
assert.match(share, /public-progress-editor/);
assert.match(share, />d</);
assert.doesNotMatch(share, /context-share-notice|context-share-lane|context-progress-editor|고객 공유 결과<\/strong><b>|별도로 공개된 안내·확정 결과가 없습니다|Customer Share 전용 Backend workflow/);

// Summary removes only the deterministic line that exactly matches the
// structured Case risk/status fields. Other summary content and controls remain.
const summary = {section_id:'SUMMARY', title:'현재 사건 요약', groups:{}, items:[
  {...item('CURRENT'), item_id:'summary-1', source_kind:'DETERMINISTIC_PROJECTION', display_value:'가족 사칭 송금 요구 사건입니다.'},
  {...item('CURRENT'), item_id:'summary-2', source_kind:'DETERMINISTIC_PROJECTION', display_value:'위험도 HIGH · 진행 상태 TRIAGE'},
  {...item('CURRENT'), item_id:'summary-3', source_kind:'DETERMINISTIC_PROJECTION', display_value:'확정 사실 3건 · 검토 대기 0건'},
]};
assert.deepEqual(Array.from(visibleSummaryItems(summary, 'HIGH', 'TRIAGE'), (entry) => entry.item_id), ['summary-1', 'summary-3']);
const renderedSummary = renderToStaticMarkup(React.createElement(SummarySection, {section:summary, caseRisk:'HIGH', caseStatus:'TRIAGE', projectionStatus:'CURRENT', editing:false, onEdit:noop, onReset:noop, editor:null}));
assert.match(renderedSummary, /가족 사칭 송금 요구 사건입니다/);
assert.match(renderedSummary, /확정 사실 3건 · 검토 대기 0건/);
assert.doesNotMatch(renderedSummary, /위험도 HIGH · 진행 상태 TRIAGE/);
assert.match(renderedSummary, /표시 요약 편집|자동 요약으로 복원/);
assert.match(renderedSummary, /사건 정보 기준 자동 요약/);
assert.doesNotMatch(renderedSummary, /Canonical Fact|Revision 연동|API 필요/);

console.log('Context V3: compact Fact rows, inline create UX, state guards, accordion ownership, enum UX, and seven-section fallback passed');
