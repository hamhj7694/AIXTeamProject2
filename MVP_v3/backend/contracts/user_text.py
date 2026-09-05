"""Normalize known machine labels in generated prose, never in structured keys."""
import re

LABELS = {
    'personal_info_shared': '개인정보 제공 여부', 'personal_information_exposure': '개인정보 제공 여부',
    'personal_info': '개인정보 제공 여부', 'authentication_information_exposure': '인증정보 제공 여부',
    'authentication_info': '인증정보 제공 여부', 'auth_info_shared': '인증정보 제공 여부', 'auth_info': '인증정보 제공 여부',
    'transfer_status': '실제 송금 여부', 'victim_transfer_status': '실제 송금 여부',
    'transfer_purpose': '송금 요구 이유', 'claimed_organization': '사칭 기관',
    'incident_claim': '상대방 주장', 'remote_control_app': '원격제어 앱 설치 여부',
    'requested_account': '요구받은 계좌', 'caller_phone': '상대방 전화번호',
    'impersonation': '기관·신분 사칭', 'action_request': '특정 행동 요구', 'action request': '특정 행동 요구',
    'money_movement': '금전 이동 요구', 'money movement': '금전 이동 요구',
    'psy_strategy': '심리적 압박', 'psy strategy': '심리적 압박',
    'actual_loss_amount_krw': '실제 피해 금액', 'sensitive_info': '개인정보 요구',
    'contact_restriction': '주변 연락 제한', 'prosecution': '검찰 사칭',
    'urgency': '긴급성 강조', 'isolation': '주변과의 연락 차단', 'fear': '불안·공포 조성',
    'casefact': '사건 확인 정보', 'proposed': '확인 전', 'confirmed': '담당자 확인', 'unresolved': '확인 필요',
    'payment_hold_review': '지급정지 검토', 'human_takeover': '담당자 직접 대응', 'staff_judgment': '담당자 판단',
    'evidence_preservation': '증빙 보관', 'account_report_guidance': '계좌 신고 안내',
    'not_provided': '제공하지 않음', 'not_transferred': '송금하지 않음', 'unknown': '확인되지 않음',
    'social engineering': '심리적 기만', 'social-engineering': '심리적 기만', 'social_engineering': '심리적 기만',
}
PATTERN = re.compile(r'(?<![A-Za-z0-9_])(' + '|'.join(re.escape(key) for key in sorted(LABELS, key=len, reverse=True)) + r')(?![A-Za-z0-9_])', re.I)

def user_text(text: str) -> str:
    parts = re.split(r'(https?://[^\s<>]+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|[^\s]+\.(?:pdf|docx?|xlsx?|png|jpe?g|txt|csv))', text, flags=re.I)
    return ''.join(part if index % 2 else PATTERN.sub(lambda m: LABELS[m.group().lower()], part) for index, part in enumerate(parts))
