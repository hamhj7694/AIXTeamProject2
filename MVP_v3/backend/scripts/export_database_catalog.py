"""Generate an entity-grouped Markdown database catalog from read-only metadata."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from scripts.inspect_database import inspect
from scripts.schema_tools import MVP_ROOT

# Descriptions are contracts, never values read from customer/staff rows.
ENTITIES = {
    '사건·분석': {
        'cases':'사건 원장·요약·상태·구조화 분석 JSON',
        'case_inputs':'데모 입력 원문과 입력 유형을 보관하는 Case 입력 원장; 최초 분석 결과 화면에서만 일시 확인하고 일반 Case read/list/bundle·지원 AI에는 반환하지 않음',
        'analysis_segments':'원문이 아닌 정황 라벨·구간 위험도',
        'context_features':'정규화된 수치 피처',
        'case_semantic_atoms':'역할·행동·금액·시간을 보존하는 의미 단위',
        'case_semantic_relations':'의미 단위 간 순서·인과 등의 관계',
        'case_context_signals':'구조화 신호 투영',
    },
    '직원·참여자': {
        'bank_staff_directory':'등록 은행 직원과 배정 가능 직무',
        'case_members':'Case별 참여자·시스템 권한·배정 역할·제거 상태',
        'case_presence':'사용자 접속·만료 시각; 담당자 배정과 별개',
    },
    '대화·고객 질문': {
        'messages':'고객/은행/AI 대화와 시스템 이벤트; 통화 입력 원문과 별개; attachments_json은 현재 빈 호환 필드',
        'customer_questions':'고객 질문·선택지·답변·질문 버전',
        'message_context_extractions':'메시지→사실 후보 추출 작업·재시도 상태',
    },
    '금액·거래': {'case_transactions':'외부 은행 원장이 아닌 Case 내부 확인 거래 기록; Context V2 실제 금액 사실을 직원 확인 후 승격'},
    '사실·확인': {
        'case_facts':'기존 사실 모델; 하위 호환 유지',
    'case_context_facts_v2':'AI·대화·직원 확인에서 나온 사실 후보·확정·기각·대체 상태와 근거; 거래 승격 전의 기준 원장',
        'case_gaps':'미확인 사항과 해소 근거',
        'verification_tasks':'별도 확인 업무·결과·공개 여부',
        'case_context_observations':'표준 분류에 매핑되지 않은 구조화 관찰',
    },
    '조치·업무·결정': {
        'actions':'기존 조치 저널·고객 진행 상태 등; 실제 외부 실행 증거와 구분',
        'case_ai_suggestions':'AI 업무 제안·검토·채택 상태',
        'case_tasks':'담당자 업무·진행·완료·차단 상태',
        'case_decisions':'직원 판단·결정 기록',
    },
    '화면·캐시': {
        'case_context_items':'직원 표시 편집본과 버전; 원본 사실과 별개',
        'case_context_projections':'맥락 생성 lease·revision·마지막 성공 결과 캐시; 원본 사실·직원 이력과 별개',
        'personal_notes':'작성자 개인 메모',
    },
    '보고서·이력': {
        'case_reports':'LIVE/FINAL 보고서 원장; live_report는 초기 분석 snapshot이며 우측 Context Panel의 공개 계약과 분리',
        'case_report_sections':'보고서 섹션 JSON·버전',
        'case_events':'Case 업무 이벤트 타임라인',
        'case_context_item_history':'직원 표시 편집 변경 이력',
        'case_context_v2_history':'사실·업무 등 V2 자원 변경 이력',
    },
    '첨부파일': {
        'case_attachments':'첨부파일 metadata·저장 위치·공개 범위; 바이너리는 DB 외부',
        'message_attachments':'메시지와 첨부파일의 연결',
    },
    '음성·호환': {
        'voice_sessions':'음성 세션 상태·참여자 metadata; 원문 segment 저장 없음; API·bundle 호환용',
    },
    '스키마 운영': {'schema_migrations':'적용 또는 검증된 기준선의 전체 migration 파일명'},
}

COLUMN_NOTES = {
    'case_id':'사건 연결 키', 'created_at':'생성 시각', 'updated_at':'최종 갱신 시각',
    'deleted_at':'논리 삭제 시각', 'version':'낙관적 잠금/수정 버전',
    'context_revision':'의미 데이터 변경 revision', 'status':'자원별 처리 상태',
    'source':'데이터 출처', 'source_kind':'추출·진술·직원 관찰·공식 기록 등의 출처',
    'visibility':'공개 범위', 'client_request_id':'재요청 중복 방지 키',
    'value_json':'타입별 구조화 값; 금액 후보는 amount_krw와 상태·근거를 함께 해석',
    'evidence_refs_json':'근거 종류·ID 목록; 일부는 논리 참조이며 DB FK가 아님',
    'diagnosis_json':'원문 제거된 분석 결과와 정황 metadata',
    'payload_json':'해당 자원의 구조화 payload', 'state_json':'표시 편집본 상태',
    'actual_loss_amount_krw':'단일 요약 피해금액(KRW); 개별 송금 목록/자동 합계 아님',
    'victim_transfer_status':'Case 수준의 송금 여부; 개별 거래 완료 상태와 구분',
    'amount':'개별 거래 금액; KRW 정수(BIGINT), 합계 정책은 별도',
    'transaction_type':'송금/반환 등 거래 유형; TRANSFER_OUT·RETURN_IN·CANCELLED만 허용',
    'transaction_at':'거래 시각; 원문 발화 시각과 구분',
    'input_text':'데모 입력 원문; 최초 분석 결과 화면에서만 일시 확인하며 일반 Case read/list/bundle·지원 AI 입력에는 포함하지 않음', 'segment_text':'분석 구간의 원문 제거 라벨',
    'confirmed_by':'확인 담당자', 'confirmed_at':'확인 시각',
    'supersedes_fact_id':'대체 관계; 삭제 대신 이력 유지', 'semantic_key':'사실/화면 항목 분류 키',
    'atom_id':'Case 내부 의미 단위 식별자; 실제 거래 식별자와 동일하지 않음',
    'assignment_role':'업무 배정 역할; 시스템 권한 role과 별개',
    'role':'참여자의 시스템 권한 역할', 'migration_name':'숫자 접두사가 아닌 전체 파일명이 식별자',
    'applied_at':'적용/검증 기준선 등록 시각; 과거 실제 실행 시각으로 소급하지 않음',
    'last_error':'마지막 처리 오류; 민감 원문을 넣지 않음',
    'attachments_json':'구버전 채팅 계약 호환 필드; 현재는 빈 값만 유지하고 첨부 데이터 저장 금지',
}


def cell(value) -> str:
    if value is None:
        return '—'
    return str(value).replace('|', '\\|').replace('\r', '').replace('\n', '<br>')


def catalog(report: dict) -> str:
    tables = report['schema']['tables']
    described = {name for group in ENTITIES.values() for name in group}
    unknown = set(tables)-described
    groups = {**ENTITIES, **({'미분류 — 계약 등록 필요': {t:'신규 테이블; 엔티티 설명 필요' for t in sorted(unknown)}} if unknown else {})}
    columns = sum(len(t['columns']) for t in tables.values())
    checks = report['integrity']
    lines = ['# 전체 DB 구조·현재 상태 표', '',
             f"기준 DB: `{report['database']}` · 조회 시각(UTC): `{report['inspected_at_utc']}`", '',
             '> 실제 information_schema와 COUNT(*)로 생성한 시점별 스냅샷이다. 개인정보·대화·계좌 값은 포함하지 않는다. 0건은 테이블 누락이 아니라 비어 있는 상태다.', '',
             '| 검사 | 결과 |', '|---|---|',
             f'| 테이블 / 컬럼 | {len(tables)}개 / {columns}개 |',
             f"| 트리거 / 선언된 FK | {len(report['schema']['triggers'])}개 / {checks['foreign_keys_checked']}개 |",
             f"| FK 위반 / Case 연결 누락 | {len(checks['foreign_key_violations'])}종 / {len(checks['case_orphans'])}종 |",
             f"| 현재 migration 중 미기록 | {len(report['pending'])}개 |",
             f"| 현재 파일 없는 과거 적용 기록 | {', '.join(report['historical_records']) or '없음'} |", '',
             '과거 `021_bank_staff_assignment_fields.sql` 기록은 삭제/재작성하지 않는다. 현재 직원 구조는 020·024와 대조한다. `case_number_sequences`는 allocator 변경이 되돌려진 현재 코드에서 사용하지 않으므로 없는 것이 정상이다.',
             '첨부파일 기능은 데모 범위에서 제외되어 `case_attachments`·`message_attachments` 테이블이 존재하지 않는 것이 정상이다. `messages.attachments_json`은 구버전 계약 호환을 위해 현재 빈 값만 유지하며, 핫픽스 안정화 후 마지막 계약 변경에서 제거 여부를 재검토한다.', '',
             '## 읽는 방법', '',
             '- [엔티티별 마이그레이션](../backend/migrations/README.md) · [사용처·정리 감사](DB_USAGE_AUDIT.md) · [API 계약 대조](API_CONTRACT_AUDIT.md) · [운영/백업/재생성](README.md) · [확인된 데이터·금액 후속 문제](../docs/CURRENT_STATUS.md)',
             '- 업무 정황 Fact, 은행 확인 거래, 직원 편집본, 캐시는 서로 다른 책임이다. 같은 내용이 여러 테이블에 보인다고 즉시 삭제하지 않는다.',
             '- 거래 0건을 피해금액 0원으로 해석하지 않는다. NULL은 미등록/미확인이다. PROPOSED는 확인 전 후보다.', '',
             '## 엔티티별 전체 테이블', '', '| 엔티티 | 테이블 | 역할 | 행 수 | 기본 키 | 물리 FK 대상 |', '|---|---|---|---:|---|---|']
    for group, members in groups.items():
        for name, meaning in members.items():
            if name not in tables:
                continue
            meta = tables[name]
            pk = ', '.join(i['COLUMN_NAME'] for i in meta['indexes'].get('PRIMARY', []))
            parents = sorted({r['REFERENCED_TABLE_NAME'] for fk in meta['foreign_keys'].values() for r in fk})
            lines.append(f"| {group} | [`{name}`](#table-{name}) | {meaning} | {report['counts'][name]} | {pk or '없음'} | {', '.join(parents) or '—'} |")
    lines += ['', '## 금액 저장 위치 구분', '', '| 위치 | 의미 | 합산 시 주의 |', '|---|---|---|',
              '| `cases.actual_loss_amount_krw` | 사건별 단일 요약 피해금액 | 다중 송금 목록이 아님. 현재 자동 동기화 없음 |',
              '| `case_transactions.amount` | 직원 확인 후 등록된 Case 내부 개별 거래 | 외부 금융기관 연동값이 아님. 요구·약속·PROPOSED 사실은 자동 승격하지 않음 |',
              '| `case_context_facts_v2.value_json.amount_krw` | 요구/진술/확인 정보 | PROPOSED를 확정 거래 합계에 포함하지 않음 |',
              '| `case_semantic_atoms.payload_json.amount_value_krw` | 분석 정황의 금액 언급 | 반복 언급·예정·요구를 별도 거래로 간주하지 않음 |',
              '| `cases.diagnosis_json` / projection JSON | 분석·화면·AI 입력용 복제/캐시 | 원장과 중복 합산하지 않음 |', '', '## 테이블별 전체 컬럼·인덱스·제약조건', '']
    for group, members in groups.items():
        for name, meaning in members.items():
            if name not in tables:
                continue
            meta = tables[name]
            lines += [f'<a id="table-{name}"></a>', '', f'### {name}', '', f'{group} — {meaning}', '',
                      f"Engine: `{meta['engine']}` · Collation: `{meta['collation']}` · {report['counts'][name]}행", '',
                      '| 컬럼 | 타입 | NULL 허용 | 기본값 | 키/특성 | 의미 |', '|---|---|---|---|---|---|']
            for column, props in meta['columns'].items():
                keys = [key for key, parts in meta['indexes'].items() if any(p['COLUMN_NAME']==column for p in parts)]
                lines.append('| '+' | '.join(cell(v) for v in [f'`{column}`', props['COLUMN_TYPE'], props['IS_NULLABLE'], props['COLUMN_DEFAULT'], ', '.join(keys)+(' / '+props['EXTRA'] if props['EXTRA'] else ''), COLUMN_NOTES.get(column, '—')])+' |')
            lines += ['', '| 인덱스 | UNIQUE | 순서·컬럼 |', '|---|---|---|']
            for index, parts in meta['indexes'].items():
                lines.append(f"| `{index}` | {'예' if not parts[0]['NON_UNIQUE'] else '아니오'} | {', '.join(cell(p['COLUMN_NAME']) for p in parts)} |")
            lines += ['', '| FK / CHECK | 정의 |', '|---|---|']
            for key, parts in meta['foreign_keys'].items():
                definition = ', '.join(f"{p['COLUMN_NAME']} → {p['REFERENCED_TABLE_NAME']}.{p['REFERENCED_COLUMN_NAME']}" for p in parts)
                lines.append(f"| `{key}` | {definition}; DELETE {parts[0]['DELETE_RULE']}; UPDATE {parts[0]['UPDATE_RULE']} |")
            for key, definition in meta['checks'].items():
                lines.append(f"| `{key}` | `{cell(definition['clause'])}` ({definition['enforced']}) |")
            if not meta['foreign_keys'] and not meta['checks']:
                lines.append('| — | 없음 |')
            lines.append('')
    lines += ['## 트리거 목록', '', '| 이름 | 테이블 | 시점 | 작업 |', '|---|---|---|---|']
    for name, props in sorted(report['schema']['triggers'].items()):
        lines.append(f"| `{name}` | `{props['EVENT_OBJECT_TABLE']}` | {props['ACTION_TIMING']} | {props['EVENT_MANIPULATION']} |")
    return '\n'.join(lines)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database')
    parser.add_argument('--output', type=Path, default=MVP_ROOT / 'database/DB_CATALOG.md')
    args = parser.parse_args()
    load_dotenv(MVP_ROOT / '.env')
    report = inspect(args.database or os.getenv('MYSQL_DATABASE', 'csr'))
    args.output.write_text(catalog(report), encoding='utf-8', newline='\n')
    print(f'Wrote metadata-only catalog: {args.output}')


if __name__ == '__main__':
    main()
