"""Customer-safe workflow state, shared by the UI and customer AI."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ProgressStep = Literal['SAFETY', 'EVIDENCE', 'PAYMENT_HOLD', 'REPORT', 'RELIEF']
ProgressStatus = Literal['UNKNOWN', 'IN_PROGRESS', 'SUBMITTED', 'COMPLETED', 'NOT_APPLICABLE']

LABELS = {
    'SAFETY': '추가 송금·접촉 중단', 'EVIDENCE': '증빙 자료 확보',
    'PAYMENT_HOLD': '은행 지급정지', 'REPORT': '기관 신고 접수', 'RELIEF': '피해구제 신청 접수',
}
STATUS_LABELS = {
    'UNKNOWN': '확인되지 않음', 'IN_PROGRESS': '담당자 확인·처리 중',
    'SUBMITTED': '제출 확인 · 접수 결과 대기', 'COMPLETED': '담당자 완료 확인',
    'NOT_APPLICABLE': '해당 없음',
}

class CustomerProgressItem(BaseModel):
    model_config = ConfigDict(extra='forbid')
    step: ProgressStep
    label: str
    status: ProgressStatus = 'UNKNOWN'
    status_label: str = '확인되지 않음'
    summary: str = '담당자의 처리 결과가 아직 등록되지 않았습니다.'
    next_action: str = ''
    reference: str = ''
    confirmed_at: datetime | None = None
    updated_at: str | None = None
    updated_by: str | None = None
    revision: int = 0
    confirmation_requested: bool = False

class UpdateCustomerProgress(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    expected_revision: int = Field(ge=0)
    status: ProgressStatus
    summary: str = Field(min_length=1, max_length=1000)
    next_action: str = Field(default='', max_length=500)
    reference: str = Field(default='', max_length=300)
    confirmed_at: datetime | None = None
    updated_by: str = Field(min_length=1, max_length=128)

    @model_validator(mode='after')
    def require_evidence(self):
        if self.status in {'SUBMITTED', 'COMPLETED'} and (not self.reference or not self.confirmed_at):
            raise ValueError('제출·완료 확인에는 확인 시각과 근거 또는 접수번호가 필요합니다.')
        return self
