const SMALL_NUMBER_VALUES: Record<string, number> = {
  일: 1, 이: 2, 삼: 3, 사: 4, 오: 5, 육: 6, 륙: 6, 칠: 7, 팔: 8, 구: 9,
};

/**
 * 직원 입력용 금액 표현을 KRW 정수로 바꾼다.
 * 원문 표현은 화면에 남기고, 이 결과만 백엔드의 amount_krw로 보낸다.
 */
export const parseKoreanWon = (input: string): number | null => {
  const normalized = input.trim().replace(/\s+/g, '').replace(/원$/, '').replace(/,/g, '');
  if (!normalized || !/^[0-9일이삼사오육륙칠팔구십백천만억]+$/.test(normalized)) return null;

  const parseBelowMan = (value: string): number | null => {
    if (!value) return 1;
    if (/^\d+$/.test(value)) return Number(value);
    let total = 0;
    let pending = '';
    for (const char of value) {
      if (/\d/.test(char)) { pending += char; continue; }
      if (SMALL_NUMBER_VALUES[char]) { pending += String(SMALL_NUMBER_VALUES[char]); continue; }
      const unit = { 십: 10, 백: 100, 천: 1000 }[char as '십' | '백' | '천'];
      if (!unit) return null;
      total += (pending ? Number(pending) : 1) * unit;
      pending = '';
    }
    if (pending) total += Number(pending);
    return Number.isFinite(total) ? total : null;
  };

  let rest = normalized;
  let total = 0;
  const hundredMillionIndex = rest.indexOf('억');
  if (hundredMillionIndex >= 0) {
    const billions = parseBelowMan(rest.slice(0, hundredMillionIndex));
    if (billions === null) return null;
    total += billions * 100_000_000;
    rest = rest.slice(hundredMillionIndex + 1);
  }
  const tenThousandIndex = rest.indexOf('만');
  if (tenThousandIndex >= 0) {
    const tenThousands = parseBelowMan(rest.slice(0, tenThousandIndex));
    if (tenThousands === null) return null;
    total += tenThousands * 10_000;
    rest = rest.slice(tenThousandIndex + 1);
  }
  if (rest) {
    const remainder = parseBelowMan(rest);
    if (remainder === null) return null;
    total += remainder;
  }
  return Number.isSafeInteger(total) && total >= 0 ? total : null;
};

export const formatWonInput = (value: number) => `${value.toLocaleString('ko-KR')}원`;
