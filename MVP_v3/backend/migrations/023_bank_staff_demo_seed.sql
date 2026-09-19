-- 기본 화면 확인을 위한 은행 담당자 목데이터.
-- 동일한 staff_id를 사용해 마이그레이션을 여러 번 실행해도 중복 생성하지 않는다.
INSERT IGNORE INTO bank_staff_directory (
    staff_id,
    display_name,
    assignment_role,
    role_label,
    position_title,
    status_text,
    status_color_key,
    assignment_eligible,
    linked_user_id
) VALUES
    (
        'staff-demo-hong-gildong',
        '홍길동',
        'MONITORING',
        'FDS 모니터링 담당자',
        '대리',
        '근무 중',
        'GREEN',
        TRUE,
        NULL
    ),
    (
        'staff-demo-kim-cheolsu',
        '김철수',
        'CONSULTATION',
        '상담자',
        '주임',
        '근무 중',
        'GREEN',
        TRUE,
        NULL
    );
