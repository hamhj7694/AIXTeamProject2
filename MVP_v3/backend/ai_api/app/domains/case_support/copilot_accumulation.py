"""Bounded arithmetic over supplied text; never creates or updates Case Facts."""

from dataclasses import dataclass
from decimal import Decimal
import re
from typing import Iterable


def asks_total(prompt: str) -> bool:
    return bool(re.search(r"총|전체|합계|합산|누적|얼마", prompt) and re.search(r"송금|보냈|보낸|피해|사기당|금액|얼마", prompt))


def money_values(text: str) -> tuple[int, ...]:
    # 단위 없는 전화번호·날짜·횟수는 금액으로 해석하지 않는다.
    values = []
    for match in re.finditer(r"(?<![\d.,])([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(만\s*원|원)", text):
        amount = Decimal(match[1].replace(",", "")) * (10_000 if "만" in match[2] else 1)
        if amount == amount.to_integral_value():
            values.append(int(amount))
    return tuple(values)


@dataclass(frozen=True)
class TransferMention:
    subject: str
    won: int
    basis: str


@dataclass(frozen=True)
class AccumulationReview:
    items: tuple[TransferMention, ...]
    total_won: int | None
    needs_review: bool

    def context_note(self) -> str:
        rows = [f"{item.subject}: {item.won:,}원 ({item.basis})" for item in self.items]
        if self.total_won is not None:
            rows.append(f"전달된 식별 가능 내역의 산술 합계: {self.total_won:,}원. 실제 전체 피해의 확정값은 아님.")
        else:
            rows.append("중복·정정·누락 여부 또는 항목 구분이 불명확해 자동 합계를 제공하지 않음.")
        rows.append("원문과 상태를 함께 설명하고, 이 보조 계산을 별도 송금 내역으로 다시 더하지 마세요.")
        return "\n".join(rows)


def review_transfers(records: Iterable[str]) -> AccumulationReview:
    grouped: dict[str, TransferMention] = {}
    needs_review = False
    excluded_subjects: set[str] = set()
    for record in dict.fromkeys(records):
        # 현재 문자열 계약에서 구분 가능한 좁은 형태만 산술 보조에 사용한다.
        subjects = re.findall(r"([가-힣A-Za-z]+)\s*사칭", record)
        subject = subjects[0] + " 사칭" if len(subjects) == 1 else None
        if re.search(r"REJECTED|SUPERSEDED", record, re.I):
            if subject:
                excluded_subjects.add(subject)
            continue
        if re.search(r"(?:AI|Copilot|상담 AI)\s*:", record, re.I):
            continue
        amounts = money_values(record)
        if not amounts:
            # 파싱 불가 금액이나 금액 없는 정정을 무시하면 일부 합계를 전체로 오인한다.
            if re.search(r"송금|이체|보냈|보낸|보내", record) and (
                "원" in record or (subject and re.search(r"정정|아니|취소|않|안\s*보", record))
            ):
                needs_review = True
            continue
        if not re.search(r"보냈|보낸|보냄|송금|이체|TRANSFERRED", record, re.I):
            continue
        if (len(amounts) != 1 or subject is None or re.search(
            r"정정|아니라|다시|추가|취소|환급|환불|요구|요청|예정|안\s*보|못\s*보|않|않음|미확인|NOT_TRANSFERRED|\?|억|천\s*만|[0-9]\s*만\s*[0-9]|-\s*\d",
            record, re.I,
        )):
            needs_review = True
            continue
        if not re.search(r"보냈|보낸|보냄|송금(?:함|했|한)|이체(?:함|했|한)|\bTRANSFERRED\b", record, re.I):
            needs_review = True
            continue
        basis = "담당자 확인" if re.search(r"\(CONFIRMED\)|\(담당자 확인\)", record) else "고객 진술·확인 필요"
        item = TransferMention(subject, amounts[0], basis)
        previous = grouped.get(subject)
        if previous and previous.won != item.won:
            needs_review = True
        elif previous and previous.basis != basis:
            # 같은 대상을 다른 출처에서 반복하면 이중 계산하거나 확정 수준을 올리지 않는다.
            grouped[subject] = TransferMention(subject, item.won, "고객 진술·확인 필요")
        else:
            grouped[subject] = item
    if excluded_subjects & grouped.keys():
        needs_review = True
    items = tuple(grouped.values())
    total = sum(item.won for item in items) if items and not needs_review else None
    return AccumulationReview(items, total, needs_review)
