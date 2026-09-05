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
}
PATTERN = re.compile(r'(?<![A-Za-z0-9_])(' + '|'.join(re.escape(key) for key in sorted(LABELS, key=len, reverse=True)) + r')(?![A-Za-z0-9_])', re.I)

def user_text(text: str) -> str:
    parts = re.split(r'(https?://[^\s<>]+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})', text)
    return ''.join(part if index % 2 else PATTERN.sub(lambda m: LABELS[m.group().lower()], part) for index, part in enumerate(parts))
