import fs from 'node:fs/promises';
import path from 'node:path';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const projectRoot = path.resolve(process.cwd(), '..', '..', '..');
const root = path.join(projectRoot, 'MVP_v3');
const outputDir = path.join(root, 'outputs', 'db-function-catalog');
const catalogPath = path.join(root, 'database', 'DB_CATALOG.md');

const clean = (value) => String(value ?? '')
  .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
  .replace(/`/g, '')
  .replace(/\s+/g, ' ')
  .trim();

const splitRow = (line) => line.trim().replace(/^\||\|$/g, '').split('|').map(clean);
const isSeparator = (line) => /^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?$/.test(line.trim());

function parseOverview(markdown) {
  const start = markdown.indexOf('## 엔티티별 전체 테이블');
  const end = markdown.indexOf('## 금액 저장 위치 구분');
  const block = markdown.slice(start, end > start ? end : undefined);
  return block.split(/\r?\n/).filter((line) => line.trim().startsWith('|'))
    .filter((line) => !line.includes('---') && !line.includes('엔티티'))
    .map(splitRow)
    .filter((row) => row.length >= 6 && /^[a-z_]+$/.test(row[1]));
}

function parseTableSections(markdown) {
  const sections = [];
  const re = /###\s+([a-z0-9_]+)\s*\n([\s\S]*?)(?=\n###\s+|\n##\s+|$)/g;
  let match;
  while ((match = re.exec(markdown))) {
    const tableName = match[1];
    const body = match[2];
    const engineLine = body.split(/\r?\n/).find((line) => line.includes('Engine:')) ?? '';
    const description = clean(body.split(/\r?\n/).find((line) => line.trim() && !line.includes('Engine:') && !line.startsWith('|')) ?? '');
    const lines = body.split(/\r?\n/);
    const headerIndex = lines.findIndex((line) => line.includes('| 컬럼 |') || line.includes('| 而щ읆 |'));
    const columns = [];
    if (headerIndex >= 0) {
      for (const line of lines.slice(headerIndex + 1)) {
        if (!line.trim() || !line.trim().startsWith('|') || isSeparator(line)) break;
        const row = splitRow(line);
        if (row.length >= 6 && row[0] && !row[0].startsWith('---')) columns.push(row);
      }
    }
    const countMatch = engineLine.match(/쨌\s*(\d+)\s*개/);
    sections.push({ tableName, description, engine: engineLine, rowCount: countMatch ? Number(countMatch[1]) : null, columns });
  }
  return sections;
}

const featureRows = [
  ['Case 생성', '원문 입력', '사용자가 통화·사건 원문을 입력해 분석 요청을 준비합니다.', 'HomeDashboardPage.tsx', '/api/cases/analyze', 'analysis pipeline / case repository', 'case_inputs', 'cases', '저장', 'case_inputs.input_text (초기 입력 저장)', '아니오', '구현 완료', 'frontend/src/pages/HomeDashboardPage.tsx; backend/general_api/app/main.py', '데모에서만 원문을 보관하며 일반 Case 조회에는 노출하지 않음'],
  ['Case 생성', '구조화 분석 생성', '원문을 Analysis Envelope와 사건 정황·semantic 데이터로 분해합니다.', 'HomeDashboardPage.tsx', '/api/cases/analyze; AI analysis endpoint', 'analysis service; projection writer', 'cases.diagnosis_json', 'analysis_segments; context_features; case_semantic_atoms; case_semantic_relations; case_context_signals', '저장·투영', 'cases.diagnosis_json', '분석 결과 metadata만', '부분 구현', 'CURRENT_STATUS.md; DB_USAGE_AUDIT.md; backend/general_api/app/main.py', '실제 외부 live AI corpus·비용 검증은 미완료'],
  ['Case 생성', '분석 결과 표시', '분석된 정황·주장·요구·위험 정보를 초기 결과 화면에 보여줍니다.', 'HomeDashboardPage.tsx; analysis presentation components', '/api/cases/{case_id}; /api/cases/{case_id}/bundle', 'case retrieval; bundle service', 'cases', 'case_reports; case_report_sections', '조회', 'cases.diagnosis_json', '아니오', '구현 완료', 'CURRENT_STATUS.md; frontend/src/analysisPresentation.ts', '원문은 transient 표시 범위로 제한'],
  ['은행 화면 채팅', '메시지 저장', '은행 직원·고객·AI의 대화를 Case 타임라인에 저장합니다.', 'CaseRoomPage.tsx; SharedConversation.tsx', '/api/cases/{case_id}/messages', 'message repository', 'messages', 'case_events', '저장', 'messages', '채널별 visibility 적용', '구현 완료', 'backend/general_api/app/main.py; frontend/src/api/cases.ts', '첨부파일은 호환 필드만 유지'],
  ['은행 화면 채팅', 'AI 응답', '은행 직원이 사건 맥락을 바탕으로 AI 응답을 요청합니다.', 'CaseRoomPage.tsx; ConversationComposer.tsx', '/api/cases/{case_id}/ai/invocations', 'AI invocation service', 'messages', 'case_context_facts_v2; case_events', '조회·저장', 'case_context_facts_v2 + messages', '고객 공유 여부 분리', '부분 구현', 'CURRENT_STATUS.md; backend/general_api/app/main.py', '실제 live AI 호출은 운영 검증 전'],
  ['은행 화면 채팅', '대화 기반 정황 추출', '새 메시지에서 분석 정황·질문 후보·근거를 추출합니다.', 'CaseRoomPage.tsx; contextWorkspace.ts', '/api/cases/{case_id}/context-extractions/{message_id}; /api/cases/{case_id}/context-v2/facts', 'context extraction; Context V2 repository', 'message_context_extractions; case_context_facts_v2', 'case_gaps; case_events', '저장·갱신', 'case_context_facts_v2', '원문 대신 구조화 evidence reference 사용', '구현 완료', 'backend/general_api/app/main.py; context_workspace.py', '상태 필드는 호환 보존이며 화면은 정황 중심'],
  ['은행 화면 우측 패널', '사건 요약·분석 정황', '최신 사건 요약과 구조화 정황을 한 패널에서 확인합니다.', 'ContextPanelFoundation.tsx; ContextWorkspace.tsx', '/api/cases/{case_id}/context-v2/workspace; /api/cases/{case_id}/context-v2/panel', 'context workspace; projection repository', 'case_context_facts_v2', 'case_context_projections; cases.diagnosis_json', '조회', 'case_context_facts_v2 + projection', '캐시 stale 시 마지막 성공 payload 사용', '부분 구현', 'AUTHORITATIVE_SOURCE_MATRIX.md; frontend/src/context-v3', '최종 패널 계약은 계속 조정 중'],
  ['은행 화면 우측 패널', '추가 확인 사항', '확인이 필요한 질문·gap·verification 작업을 표시합니다.', 'ContextWorkspace.tsx; ContextPanelFoundation.tsx', '/api/cases/{case_id}/context-v2/gaps; /api/cases/{case_id}/verifications; /api/cases/{case_id}/customer-questions', 'gap; verification; question services', 'case_gaps; verification_tasks; customer_questions', 'case_events', '저장·조회', 'case_gaps / verification_tasks', '직원 확인 업무로 표시', '구현 완료', 'backend/general_api/app/main.py; CURRENT_STATUS.md', '실제 기관 확인 연동은 미구현'],
  ['은행 화면 우측 패널', '업무·Task·Decision', '대응 가이드와 직원 업무·결정을 관리합니다.', 'ContextWorkspace.tsx; ContextPanelFoundation.tsx', '/api/cases/{case_id}/context-v2/tasks; /api/cases/{case_id}/context-v2/decisions; /api/cases/{case_id}/actions', 'task/action/decision repositories', 'case_tasks; actions; case_decisions', 'case_ai_suggestions; case_events', '저장·갱신', '각 resource 테이블', '실제 금융기관 실행 증빙과 분리', '부분 구현', 'AUTHORITATIVE_SOURCE_MATRIX.md; backend/general_api/app/main.py', 'resource별 상세 history API는 예정'],
  ['은행 화면 우측 패널', '송금 기록 조회', '실제 은행 연동이 아닌 Case 내부 데모 거래 목록을 표시합니다.', 'CaseRoomPage.tsx; AdditionalLookupCard.tsx', '/api/cases/{case_id}/transactions', 'transaction repository', 'case_transactions', 'cases.actual_loss_amount_krw; case_context_facts_v2', '조회·직원 입력', 'case_transactions (데모 목록)', '요구 금액·진술을 거래로 자동 승격하지 않음', '구현 완료', 'DB_USAGE_AUDIT.md; AUTHORITATIVE_SOURCE_MATRIX.md', '실제 은행 원장 연동 아님'],
  ['고객 화면 채팅', '고객 메시지', '고객과 은행 담당자·AI가 안전 안내를 주고받습니다.', 'CustomerCaseRoomPage.tsx; CustomerConversation.tsx', '/api/cases/{case_id}/messages?view=customer', 'message repository; customer bundle', 'messages', 'case_events; case_context_facts_v2', '저장·조회', 'messages + customer-visible projection', 'CUSTOMER visibility 적용', '구현 완료', 'frontend/src/customer; backend/general_api/app/main.py', '고객에게 내부 정황·근거를 직접 노출하지 않음'],
  ['고객 화면 채팅', '고객 질문·답변', '은행이 확인 질문을 보내고 고객 답변을 저장합니다.', 'CustomerQuestionCard.tsx; CustomerCaseRoomPage.tsx', '/api/cases/{case_id}/customer-questions; .../answer', 'question repository', 'customer_questions', 'messages; case_context_facts_v2', '저장·갱신', 'customer_questions', '답변은 확인 후보로 활용', '구현 완료', 'backend/general_api/app/main.py; frontend/src/api/cases.ts', '자동 확정 대신 직원 확인 흐름과 연결'],
  ['고객 화면 채팅', '고객 진행 상태', '안전·신고·피해구제 진행 단계를 고객에게 표시합니다.', 'CustomerProgressPanel.tsx; RecoveryCards.tsx', '/api/cases/{case_id}/customer-progress/{step}', 'customer progress service', 'case_context_items', 'customer_questions; case_events', '저장·조회', 'case_context_items / progress projection', '실제 접수·신고 완료를 자동 의미하지 않음', '구현 완료', 'CURRENT_STATUS.md; backend/general_api/app/main.py', '외부 기관 접수 API 미연동'],
  ['담당자 관리·Case 배정', '은행 담당자 디렉터리', '은행 담당자의 역할·상태·배정 가능 여부를 관리합니다.', 'BankStaffDialog.tsx; participant components', '/api/bank/staff', 'bank staff repository', 'bank_staff_directory', 'case_members', '저장·조회', 'bank_staff_directory', 'Case와 독립적인 직원 원장', '구현 완료', 'backend/general_api/app/main.py; DB_CATALOG.md', '상태 변경에 따른 배정 가능 UI 규칙 포함'],
  ['담당자 관리·Case 배정', 'Case 참여자·배정', 'Case에 담당자를 배정하고 참여자 수·권한을 관리합니다.', 'CaseRoomPage.tsx; ParticipantDialog.tsx', '/api/cases/{case_id}/members; /assignee; /presence', 'case member/presence repository', 'case_members; case_presence', 'bank_staff_directory; case_events', '저장·갱신', 'case_members', 'role과 assignment_role 책임 분리', '구현 완료', 'DB_USAGE_AUDIT.md; backend/general_api/app/main.py', '독립 RBAC는 미구현'],
  ['보고서·사건 이력', 'LIVE/FINAL 보고서', '초기 분석과 최종 보고서를 버전별로 보관합니다.', 'CaseRoomPage.tsx; report views', '/api/cases/{case_id}/reports/live; /reports/finalize; /reports/final', 'report repository', 'case_reports; case_report_sections', 'cases.diagnosis_json', '저장·조회', 'case_reports', '원본 분석과 별도 report snapshot', '구현 완료', 'AUTHORITATIVE_SOURCE_MATRIX.md; backend/general_api/app/main.py', '전체 resource history API는 예정'],
  ['보고서·사건 이력', 'Case 이벤트', '메시지·업무·상태 변경 이벤트를 타임라인으로 조회합니다.', 'SharedConversation.tsx; HistoryDrawer.tsx', '/api/cases/{case_id}/events', 'event repository', 'case_events', 'messages; actions; case_context_v2_history', '저장·조회', 'case_events', '전체 resource before/after history는 별도 예정', '부분 구현', 'CURRENT_STATUS.md; backend/general_api/app/main.py', 'cursor 기반 전체 이력 API 미구현'],
  ['알림·개인 기록', '알림함', '분석 결과·Case 생성 결과를 브라우저 알림으로 보여줍니다.', 'App.tsx; NotificationCenter.tsx', '프론트 localStorage 기반', 'frontend notification store', '없음 (브라우저 localStorage)', 'cases API 조회', '조회·로컬 저장', '브라우저 localStorage', '서버 DB 영속 알림 아님', '구현 완료', 'frontend/src/App.tsx; NotificationCenter.tsx', '다중 기기 동기화 없음'],
  ['알림·개인 기록', '북마크·개인 메모', '직원이 대화와 메모를 개인적으로 저장합니다.', 'CaseRoomPage.tsx; bank/bookmarks.ts; PersonalNoteDialog.tsx', '/api/cases/{case_id}/personal-notes', 'personal note repository; browser bookmark store', 'personal_notes', 'messages', '저장·로컬 저장', 'personal_notes (메모); localStorage (북마크)', '북마크는 브라우저 단위', '부분 구현', 'frontend/src/bank/bookmarks.ts; backend/general_api/app/main.py', '북마크 서버 저장·동기화 없음'],
  ['호환·향후 기능', '음성 세션', '음성 통화 세션 metadata를 호환 경로로 관리합니다.', '현재 핵심 화면 직접 사용 없음', '/api/cases/{case_id}/voice-sessions', 'voice session repository', 'voice_sessions', 'cases', '호환 유지', 'voice_sessions', '원문 transcript 저장 아님', '호환 유지', 'DB_USAGE_AUDIT.md; CURRENT_STATUS.md', '실제 음성 corpus·live 연동 보류'],
  ['호환·향후 기능', '첨부파일', '첨부파일 API와 테이블은 데모 범위에서 비활성화된 호환 경로입니다.', '현재 첨부 UI 제외', '/api/.../attachments → 410', '없음/호환 route', '없음; messages.attachments_json 호환 필드', '없음', '호환 유지', '없음', '첨부 저장·signed URL 미지원', '보류', 'DB_USAGE_AUDIT.md; backend/general_api/app/main.py', '실제 파일 저장 기능은 별도 설계 필요'],
  ['운영·향후 기능', '실시간 동기화', '여러 화면·사용자 사이의 변경을 실시간으로 전달합니다.', '현재 polling 중심', 'SSE/WebSocket 미구현', '없음', 'case_events (향후 기반)', '없음', '예정', 'case_events', '현재 polling 중심', '미구현·예정', 'CURRENT_STATUS.md', 'SSE/WebSocket 설계 필요'],
  ['운영·향후 기능', '실제 은행 거래 연동', '은행 원장/FDS와 연결해 실거래를 검증합니다.', '미구현', '외부 은행 API 없음', '없음', '없음', 'case_transactions (데모 대체)', '예정', '외부 시스템 필요', '현재는 데모 입력·표시만 제공', '미구현·예정', 'DB_USAGE_AUDIT.md; CURRENT_STATUS.md', '외부 API 계약·보안·감사 필요'],
];

const authorityRows = [
  ['최초 AI 분석', 'cases.diagnosis_json', 'analysis_segments; context_features; case_semantic_atoms; case_semantic_relations; case_context_signals', 'case_context_projections.last_success_payload', '분석 생성 시 projection 생성; 원본 변경 시 재생성', '원본 분석을 직원 Fact로 자동 덮어쓰지 않음', 'Case 생성·초기 분석'],
  ['Case 정황·Fact', 'case_context_facts_v2', 'Context workspace; support projection', '없음', '직원 입력·AI 추출·질문 답변으로 갱신', '확정/승격을 금융 거래 사실로 자동 의미하지 않음', '은행 패널·채팅 AI'],
  ['추가 확인·미확실 항목', 'case_gaps; verification_tasks', 'Context workspace; 고객 공유 진행', '필요 시 projection', '질문·답변·직원 확인 결과로 상태 갱신', '기관 확인 전에는 실제 은행 결과로 단정하지 않음', '질문·검증·고객 안내'],
  ['업무·조치·결정', 'actions; case_tasks; case_decisions', 'Context Panel·타임라인', '없음', '직원 작업·완료·결정 기록', 'AI 제안과 직원 실행을 분리', '대응 업무·감사'],
  ['LIVE/FINAL 보고서', 'case_reports + case_report_sections', 'Case bundle', '없음', '보고서 생성·finalize 시 버전 추가', '원본 Fact 원장을 대체하지 않음', '보고서·내보내기'],
  ['Context 표시 문구', 'case_context_items', '직원 Context Panel', 'case_context_projections', '표시용 편집·revision 반영', '표시 override와 원본 Fact 분리', '우측 패널'],
  ['송금 기록 목록', 'case_transactions', '송금 기록 조회 카드', '없음', '직원 데모 입력·수정', '실제 은행 원장 아님; 요구 금액 자동 승격 금지', '송금 기록 조회'],
  ['Case 요약 손실 금액', 'cases.actual_loss_amount_krw', 'Case 목록·요약', '없음', '직원·Case 단위 요약값 갱신', 'case_transactions 자동 합산 금지', 'Case 요약'],
];

const cautionRows = [
  ['실제 은행/FDS API', '보류', '실제 은행 거래·FDS·수사기관 API는 연결되지 않음', 'case_transactions는 Case 내부 데모 표시 목록', 'DB_USAGE_AUDIT.md; CURRENT_STATUS.md'],
  ['송금 금액 책임', '주의', '요구 금액·고객 진술·직원 확인 거래를 분리', 'actual_loss_amount_krw 자동 합산·자동 승격 금지', 'DB_USAGE_AUDIT.md; AUTHORITATIVE_SOURCE_MATRIX.md'],
  ['Fact 상태 모델', '주의', '상태 컬럼은 호환성 때문에 남아 있지만 화면은 분석 정황 중심', '직원 확인 없이 금융 사실로 단정하지 않음', '현재 frontend ContextWorkspace/backend context_workspace.py'],
  ['레거시 경로', '호환 유지', 'voice_sessions, attachments_json, legacy facts route 등이 호환 목적으로 남아 있음', '신규 일반 실행 경로와 구분 필요', 'DB_USAGE_AUDIT.md; API_CONTRACT_AUDIT.md'],
  ['첨부파일', '보류', '첨부 route는 410이며 object storage·signed URL 미구현', '데모 범위에서 기능 제외', 'DB_USAGE_AUDIT.md; main.py'],
  ['실시간 동기화', '예정', '현재 polling 중심', 'SSE/WebSocket과 fallback 정책 필요', 'CURRENT_STATUS.md'],
  ['전체 resource history', '예정', '현재 recent events 중심이며 before/after·cursor API 부족', 'resource별 이력 계약 필요', 'CURRENT_STATUS.md'],
  ['권한·RBAC', '부분', 'assignment_role과 권한 role이 분리되어 있으나 독립 RBAC는 미완료', '실제 운영 인증·RBAC 전제 필요', 'DB_USAGE_AUDIT.md; CURRENT_STATUS.md'],
  ['원문·개인정보', '주의', '초기 입력은 case_inputs에 저장되지만 일반 Case read/list/bundle에는 노출하지 않음', '엑셀에는 literal 미수록', 'DB_USAGE_AUDIT.md'],
];

function statusFill(status) {
  return ({ '구현 완료': '#E8F5E9', '부분 구현': '#FFF4CC', '호환 유지': '#E8EEF7', '보류': '#FCE8E6', '미구현·예정': '#FDE9D9' })[status] ?? '#FFFFFF';
}

function writeTable(sheet, title, subtitle, headers, rows, widths, tableName, tabColor) {
  sheet.showGridLines = false;
  sheet.tabColor = tabColor;
  const endCol = String.fromCharCode(64 + headers.length);
  sheet.mergeCells(`A1:${endCol}1`);
  sheet.getRange('A1').values = [[title]];
  sheet.getRange('A1').format = { font: { name: 'Arial', size: 16, bold: true, color: '#172B4D' } };
  sheet.mergeCells(`A2:${endCol}2`);
  sheet.getRange('A2').values = [[subtitle]];
  sheet.getRange('A2').format = { font: { name: 'Arial', size: 10, color: '#667085', italic: true }, wrapText: true };
  sheet.getRange(`A4:${endCol}4`).values = [headers];
  sheet.getRange(`A4:${endCol}4`).format = { fill: '#1F4E78', font: { name: 'Arial', size: 10, bold: true, color: '#FFFFFF' }, horizontalAlignment: 'center', verticalAlignment: 'center', wrapText: true };
  if (rows.length) {
    sheet.getRange(`A5:${endCol}${rows.length + 4}`).values = rows;
    sheet.getRange(`A5:${endCol}${rows.length + 4}`).format = { font: { name: 'Arial', size: 10, color: '#1F2937' }, verticalAlignment: 'center', wrapText: true };
    sheet.getRange(`A4:${endCol}${rows.length + 4}`).format.borders = { preset: 'inside', style: 'thin', color: '#D9E2F3' };
    sheet.tables.add(`A4:${endCol}${rows.length + 4}`, true, tableName);
  }
  widths.forEach((width, index) => sheet.getRangeByIndexes(0, index, Math.max(rows.length + 4, 4), 1).format.columnWidth = width);
  sheet.getRange(`A1:${endCol}${Math.max(rows.length + 4, 4)}`).format.verticalAlignment = 'center';
  sheet.getRange(`A4:${endCol}4`).format.rowHeight = 34;
  sheet.freezePanes.freezeRows(4);
  const statusIndex = headers.indexOf('구현 상태');
  if (statusIndex >= 0 && rows.length) {
    rows.forEach((row, i) => {
      const status = row[statusIndex];
      if (status) sheet.getCell(i + 4, statusIndex).format.fill = statusFill(status);
    });
  }
}

const markdown = await fs.readFile(catalogPath, 'utf8');
const overview = parseOverview(markdown);
const sections = parseTableSections(markdown);
// The catalog is markdown-generated and may vary in localized header text. Use
// pipe structure as a safe fallback so every catalog column is still captured.
for (const section of sections) {
  const sectionStart = markdown.indexOf(`### ${section.tableName}`);
  const nextSection = markdown.indexOf('\n### ', sectionStart + 5);
  const body = markdown.slice(sectionStart, nextSection > sectionStart ? nextSection : undefined);
  const lines = body.split(/\r?\n/);
  const headerIndex = lines.findIndex((line) => line.trim().startsWith('|') && !isSeparator(line));
  if (section.columns.length === 0 && headerIndex >= 0) {
    section.columns = lines.slice(headerIndex + 2).map(splitRow).filter((row) => row.length >= 6 && row[0] && !row[0].startsWith('---'));
  }
  const rowCountMatch = body.match(/(\d+)행/);
  if (rowCountMatch) section.rowCount = Number(rowCountMatch[1]);
}
const overviewMap = new Map(overview.map((row) => [row[1], row]));
const tableRows = sections.map((section) => {
  const row = overviewMap.get(section.tableName) ?? [];
  return [row[0] ?? '미분류', section.tableName, section.description || row[2] || '', section.rowCount ?? row[3] ?? '', row[4] ?? '', row[5] ?? '', '카탈로그·코드 대조 필요', section.tableName === 'cases' || section.tableName === 'case_context_facts_v2' ? '권위 원본' : 'projection/지원', '문서 기준선', 'DB_CATALOG.md'];
});
const columnRows = sections.flatMap((section) => section.columns.map((row) => [section.tableName, row[0], row[1], row[2], row[3], row[4], row[5], row[0].includes('text') || row[0].includes('json') ? '구조화·텍스트 데이터' : '식별자·상태·메타데이터', row[0].includes('text') ? '원문/설명 가능성 확인' : 'literal 원문 아님', 'DB_CATALOG.md']));

const workbook = Workbook.create();
const summary = workbook.worksheets.add('요약');
summary.showGridLines = false; summary.tabColor = '#17365D';
summary.mergeCells('A1:F1'); summary.getRange('A1').values = [['CSR DB·기능 연결 카탈로그']]; summary.getRange('A1').format = { font: { name: 'Arial', size: 18, bold: true, color: '#172B4D' } };
summary.mergeCells('A2:F2'); summary.getRange('A2').values = [['DB 구조, 화면 기능, API, Source of Truth와 구현 상태를 한 번에 확인하는 개발자용 기준표']]; summary.getRange('A2').format = { font: { name: 'Arial', size: 10, color: '#667085', italic: true } };
summary.getRange('A4:B10').values = [['기준 정보', '값'], ['카탈로그 기준일', '2026-09-22'], ['테이블 수', null], ['컬럼 수', null], ['기능 연결 행 수', null], ['구현 완료 기능 수', null], ['보류·예정 기능 수', null]];
summary.getRange('A4:B4').format = { fill: '#1F4E78', font: { name: 'Arial', size: 10, bold: true, color: '#FFFFFF' } };
summary.getRange('A5:A10').format = { fill: '#EAF0F6', font: { name: 'Arial', size: 10, bold: true, color: '#1F2937' } };
summary.getRange('B5:B10').format = { font: { name: 'Arial', size: 10, color: '#1F2937' } };
summary.getRange('A4:B10').format.borders = { preset: 'all', style: 'thin', color: '#D9E2F3' };
summary.getRange('D4:F10').values = [['핵심 원칙', '현재 기준', '개발자 메모'], ['분석 원본', 'cases.diagnosis_json', '초기 AI 분석 snapshot'], ['현재 정황', 'case_context_facts_v2', '채팅·직원 입력 기반 Context V2'], ['거래 표시', 'case_transactions', '실제 은행 원장 아님'], ['요약 손실액', 'cases.actual_loss_amount_krw', '자동 합산 금지'], ['원문 경계', 'case_inputs.input_text', '일반 Case API에 노출하지 않음'], ['구현 상태', '문서·코드 근거 병기', '추측으로 상태를 채우지 않음']];
summary.getRange('D4:F4').format = { fill: '#1F4E78', font: { name: 'Arial', size: 10, bold: true, color: '#FFFFFF' } };
summary.getRange('D5:D10').format = { fill: '#EAF0F6', font: { name: 'Arial', size: 10, bold: true } };
summary.getRange('D4:F10').format.borders = { preset: 'all', style: 'thin', color: '#D9E2F3' };
summary.getRange('A1:F10').format.wrapText = true; summary.getRange('A:A').format.columnWidth = 24; summary.getRange('B:B').format.columnWidth = 18; summary.getRange('C:C').format.columnWidth = 3; summary.getRange('D:D').format.columnWidth = 16; summary.getRange('E:E').format.columnWidth = 30; summary.getRange('F:F').format.columnWidth = 28;

const functionSheet = workbook.worksheets.add('기능-DB 연결');
writeTable(functionSheet, '기능-DB 연결', '화면·세부 기능별로 실제 연결된 프론트엔드, API, 서비스, DB, 원본과 구현 상태를 확인합니다.', ['기능 영역', '세부 기능', '기능 설명', '프론트엔드 파일', '백엔드 API', '백엔드 서비스/repository', '주요 DB', '보조 DB', '저장·조회·갱신', 'Source of Truth', 'projection/cache', '구현 상태', '확인 근거', '보류·주의사항'], featureRows, [18, 22, 42, 32, 40, 30, 28, 34, 15, 28, 22, 15, 38, 34], 'FeatureDbMap', '#2F75B5');
const statusSheet = workbook.worksheets.add('구현 상태');
const statusRows = featureRows.map((row) => [row[0], row[1], row[11], row[2], row[12], row[13], row[4], row[6]]);
writeTable(statusSheet, '구현 상태', '기능 연결표에서 확인한 현재 구현 범위와 미완료·보류 범위를 요약합니다.', ['기능 영역', '세부 기능', '상태', '현재 동작 범위', '근거', '다음 확인·작업', '주요 API', '주요 DB'], statusRows, [20, 24, 16, 48, 42, 42, 42, 30], 'ImplementationStatus', '#5B9BD5');
const tableSheet = workbook.worksheets.add('테이블 카탈로그');
writeTable(tableSheet, '테이블 카탈로그', 'DB_CATALOG.md의 테이블 단위 설명과 기능·원본 역할을 정리합니다.', ['도메인', '테이블명', '사람이 보는 설명', '현재 행 수', '기본 키', '외래 키 요약', '주요 기능', '권위 원본 여부', '구현 상태', '근거'], tableRows, [18, 30, 52, 14, 28, 34, 34, 18, 16, 28], 'TableCatalog', '#70AD47');
const columnSheet = workbook.worksheets.add('컬럼 사전');
writeTable(columnSheet, '컬럼 사전', '각 테이블의 컬럼 정의와 사람이 이해하기 위한 데이터 성격·주의사항입니다.', ['테이블명', '컬럼명', '데이터 타입', 'NULL 허용', '기본값', '키·인덱스', '컬럼 설명', '저장 데이터 성격', '원문·개인정보 경계', '근거'], columnRows, [30, 30, 24, 14, 24, 32, 48, 28, 28, 24], 'ColumnDictionary', '#70AD47');
const authoritySheet = workbook.worksheets.add('권위 원본 매트릭스');
writeTable(authoritySheet, '권위 원본 매트릭스', '같은 데이터가 여러 테이블에 보일 때 원본·projection·cache 책임을 구분합니다.', ['데이터 영역', '원본 테이블·컬럼', '조회·projection 모델', '캐시', '갱신 규칙', '자동 합산·승격 금지 여부', '관련 기능'], authorityRows, [24, 34, 42, 32, 42, 42, 30], 'AuthoritativeMatrix', '#8064A2');
const cautionSheet = workbook.worksheets.add('보류·주의사항');
writeTable(cautionSheet, '보류·주의사항', '현재 데모 범위의 한계, 호환 경로와 향후 개발 전제조건입니다.', ['항목', '분류', '현재 상태', '개발자 주의사항', '근거'], cautionRows, [24, 16, 54, 54, 36], 'Cautions', '#C0504D');

// Re-apply summary formulas after all referenced worksheets exist.
summary.getRange('B6').formulas = [[`=COUNTA('테이블 카탈로그'!B5:B${tableRows.length + 4})`]];
summary.getRange('B7').formulas = [[`=COUNTA('컬럼 사전'!B5:B${columnRows.length + 4})`]];
summary.getRange('B8').formulas = [[`=COUNTA('기능-DB 연결'!B5:B${featureRows.length + 4})`]];
summary.getRange('B9').formulas = [[`=COUNTIF('기능-DB 연결'!L5:L${featureRows.length + 4},"구현 완료")`]];
summary.getRange('B10').formulas = [[`=COUNTIF('기능-DB 연결'!L5:L${featureRows.length + 4},"보류")+COUNTIF('기능-DB 연결'!L5:L${featureRows.length + 4},"미구현·예정")`]];

workbook.recalculate();
const summaryPreview = await workbook.render({ sheetName: '요약', autoCrop: 'all', scale: 1, format: 'png' });
await fs.writeFile(path.join(outputDir, 'summary-preview.png'), new Uint8Array(await summaryPreview.arrayBuffer()));
const featurePreview = await workbook.render({ sheetName: '기능-DB 연결', range: 'A1:N18', scale: 1, format: 'png' });
await fs.writeFile(path.join(outputDir, 'feature-preview.png'), new Uint8Array(await featurePreview.arrayBuffer()));
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(path.join(outputDir, 'CSR_DB_Function_Catalog.xlsx'));
console.log(JSON.stringify({ output: path.join(outputDir, 'CSR_DB_Function_Catalog.xlsx'), tables: sections.length, columns: columnRows.length, features: featureRows.length }));
