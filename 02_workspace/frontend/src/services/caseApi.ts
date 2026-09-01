import { CaseRecord, MOCK_CASES } from '../data/mock/caseData';

export interface AnalyzeResponse { case: CaseRecord; initialBrief: string; }
// 실제 API 연결 시 이 파일의 구현만 fetch 기반으로 교체합니다.
export const caseApi = {
  list: async (): Promise<CaseRecord[]> => Promise.resolve(MOCK_CASES),
  analyze: async (input: string): Promise<AnalyzeResponse> => Promise.resolve({ case: MOCK_CASES[0], initialBrief: input ? '기관 사칭과 긴급 송금 요구가 함께 확인되어 추가 검증이 필요합니다.' : '' }),
};
