import React, { FormEvent, useEffect, useRef, useState } from 'react';
import { AlertCircle, ArrowLeftRight, BrainCircuit, CheckCircle2, ChevronRight, FileSearch, Loader2, MessageSquareText, Play, ShieldAlert, ShieldCheck, Sparkles, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { casesApi } from '../api/cases';
import type { AnalyzeCaseResponse, StoredCase } from '../api/types';
import {
  analysisCodeLabel as structuredCodeLabel,
  analysisConcreteLabel,
  attributionWarning,
  observedTermLabel,
  replaceAnalysisTokens,
} from '../analysisPresentation';
import { caseState, caseStateTone } from '../presentation';
import { generateUuid } from '../uuid';
import { markInitialAssignmentPending } from '../assignmentPromptState';
import { startBackgroundAnalysis } from '../analysisQueue';

type AnalysisState = 'INPUT' | 'ANALYZING' | 'CREATED' | 'NO_CASE' | 'ERROR';
type SampleType = 'PHISHING' | 'FINANCE' | 'DAILY';
type AnalysisRequest = { requestId: string; submittedText: string };

const CALL_SAMPLES: Record<SampleType, string[]> = {
  PHISHING: [
    ['서울지검 수사관입니다. 고객님 명의 계좌가 범죄에 연루됐습니다.', '현재 자금 추적을 위해 계좌 검증이 필요합니다.', '오늘 안에 안내드리는 안전계좌로 자금을 이체하셔야 합니다.', '수사 중이므로 가족이나 은행 직원에게는 알리지 마세요.', '통화를 끊지 말고 지금 바로 이체 절차를 진행해 주세요.'].join('\n'),
    ['금융감독원 조사팀입니다. 고객님 계좌에서 불법 거래가 발견됐습니다.', '본인 확인을 위해 주민등록번호와 계좌번호를 말씀해 주세요.', '곧 문자로 보내는 링크에서 보안 앱을 설치하셔야 합니다.', '조사가 끝날 때까지 누구에게도 이 내용을 말하면 안 됩니다.', '지금 처리하지 않으면 계좌가 즉시 정지됩니다.'].join('\n'),
    ['카드사 보안센터인데 해외에서 고액 결제가 승인됐습니다.', '어떤 결제인지 확인하고 싶습니다.', '취소하려면 문자로 전송된 인증번호를 지금 불러 주세요.', '인증번호를 말하면 결제가 취소되나요?', '환불 전용 계좌로 보증금을 보내면 결제가 바로 취소됩니다.', '은행에 문의하면 처리가 지연되니 저희 안내만 따라 주세요.', '알겠습니다. 확인해 보겠습니다.'].join('\n'),
    ['엄마, 휴대폰이 고장 나서 임시 번호로 연락해.', '급하게 결제해야 하는데 내 인증서가 작동하지 않아.', '내가 보내는 계좌로 먼저 300만 원만 이체해 줘.', '지금 회의 중이라 전화는 받을 수 없으니 문자로만 답해 줘.', '오늘 안에 꼭 필요하니까 다른 사람에게 묻지 말고 보내 줘.'].join('\n'),
    ['저금리 대환대출 승인 담당자입니다.', '기존 대출을 먼저 상환해야 신규 대출금이 지급됩니다.', '상환금은 지금 알려드리는 개인 명의 계좌로 보내시면 됩니다.', '신용점수 보호를 위해 원격제어 앱을 설치해 주세요.', '오늘 입금하지 않으면 승인 건이 자동 취소됩니다.'].join('\n'),
  ],
  FINANCE: [
    ['안녕하세요, 정기예금 만기일을 확인하고 싶습니다.', '고객님 본인 확인 후 만기일과 예상 이자를 안내드리겠습니다.', '앱에서 본인 인증을 완료해 주시겠어요?', '인증이 확인되어 만기일은 다음 달 15일입니다.', '재예치 여부는 만기 전에 앱이나 영업점에서 선택하실 수 있습니다.'].join('\n'),
    ['체크카드를 분실해서 사용 정지를 요청하려고 합니다.', '즉시 카드 사용을 정지하고 최근 승인 내역을 확인하겠습니다.', '어제 편의점 결제 이후에는 제가 사용한 내역이 아닙니다.', '해당 거래는 이의 신청으로 접수하고 새 카드를 재발급하겠습니다.', '접수번호는 공식 앱 알림으로 확인하실 수 있습니다.'].join('\n'),
    ['주택담보대출 금리와 준비 서류를 상담받고 싶습니다.', '소득과 담보 조건에 따라 적용 금리가 달라질 수 있습니다.', '필요 서류 목록을 은행 공식 앱 상담함으로 보내드리겠습니다.', '서류 제출 전 예상 한도 조회도 가능합니다.', '검토 후 영업점 방문 일정을 예약해 드리겠습니다.'].join('\n'),
    ['해외 송금 수수료와 처리 시간을 알고 싶습니다.', '송금 국가와 통화, 금액을 확인하면 예상 비용을 안내할 수 있습니다.', '미국으로 2천 달러를 보내려고 합니다.', '영업일 기준 처리 시간과 중계 수수료를 안내드리겠습니다.', '최종 송금 전 앱 화면에서 수취인 정보를 다시 확인해 주세요.'].join('\n'),
    ['자동이체 날짜를 매월 10일에서 25일로 바꾸고 싶습니다.', '등록된 자동이체 항목을 확인한 뒤 변경할 수 있습니다.', '통신비 자동이체 한 건만 변경해 주세요.', '변경 내용은 다음 출금일부터 적용됩니다.', '처리 결과는 은행 앱 알림으로 보내드리겠습니다.'].join('\n'),
  ],
  DAILY: [
    ['오늘 저녁에 같이 식사할래?', '좋아, 퇴근하고 일곱 시쯤 가능해.', '지난번에 갔던 식당 앞에서 만날까?', '응, 내가 먼저 도착하면 자리 잡고 있을게.', '늦어지면 출발 전에 연락할게.'].join('\n'),
    ['주말에 등산 가기로 한 것 기억하지?', '응, 토요일 아침 날씨부터 확인해 보자.', '비가 안 오면 아홉 시에 입구에서 만나자.', '물하고 간단한 간식은 내가 준비할게.', '좋아, 금요일 저녁에 다시 연락하자.'].join('\n'),
    ['택배가 오늘 오후에 도착할 예정이래.', '집에 사람이 없으면 경비실에 맡겨 달라고 해 줘.', '알겠어, 배송 메모를 확인해 볼게.', '상자가 무거우니 저녁에 같이 옮기자.', '도착 알림이 오면 알려 줄게.'].join('\n'),
    ['회의 시간이 오후 두 시로 바뀌었습니다.', '회의실도 변경됐나요?', '네, 3층 소회의실에서 진행합니다.', '자료는 시작 전에 공유 폴더에 올려 주세요.', '확인했습니다. 참석자들에게도 전달하겠습니다.'].join('\n'),
    ['병원 예약을 다음 주로 변경하려고 해.', '어느 요일이 가장 편해?', '수요일 오후면 좋을 것 같아.', '예약실에 확인하고 가능한 시간을 알려 줄게.', '고마워, 확인되면 메시지 남겨 줘.'].join('\n'),
  ],
};

const valueList = (report: StoredCase['initial_report'], key: string) => {
  const content = report?.sections?.find((item) => item.section_key === key)?.content;
  return Array.isArray(content?.items) ? content.items.filter((item): item is string => typeof item === 'string') : [];
};

type StaffFeature = {
  id: string;
  category: string;
  title: string;
  description: string;
  status: string;
  tone: 'risk' | 'info';
  metadata: string[];
  details: string[];
};

type StructuredDetailItem = {
  key: string;
  title: string;
  summary: string;
  metadata: string[];
};

type StructuredDetailGroup = {
  key: string;
  title: string;
  items: StructuredDetailItem[];
};

const confidenceLabel = (value?: number | null) => value === null || value === undefined
  ? null
  : `신뢰도 ${Math.round(value * 100)}%`;

const simplifyAttributionSentence = (value: string, code?: string, entityNames: string[] = []) => {
  const text = value.replace(/\s+/g, ' ').trim();
  if (text.includes('발화자·행위자 귀속은 확인 필요')) {
    const normalizedCode = normalizeStaffFeatureCode(code || '');
    if (normalizedCode === 'CLAIM_DEVICE_BROKEN') {
      const hasChildRelationship = entityNames.some((item) => ['CHILD', 'FAMILY_MEMBER', '자녀', '아들', '딸'].includes(item));
      return hasChildRelationship
        ? '보이스피싱 의심 인물로 추정되는 사람이 자녀를 사칭하며 휴대전화가 고장 났다고 주장한 정황'
        : '보이스피싱 의심 인물로 추정되는 사람이 휴대전화가 고장 났다고 주장한 정황';
    }
    if (isSuspectedFeatureCode(normalizedCode)) {
      return `보이스피싱 의심 인물로 추정되는 발화자가 ${staffFeatureLabel(normalizedCode)}을(를) 말하거나 요구한 정황`;
    }
    return '정황은 확인되었으나 행위자 귀속이 명확하지 않습니다.';
  }
  return text;
};

const staffFeatureLabels: Record<string, string> = {
  ROLE_PROSECUTION: '수사기관을 사칭한 정황', ROLE_POLICE: '경찰을 사칭한 정황',
  ROLE_BANK: '금융기관을 사칭한 정황', ROLE_FAMILY: '가족·지인을 사칭한 정황',
  ROLE_SUPPORT: '지원기관을 사칭한 정황',
  CLAIMED_ORGANIZATION: '특정 기관을 사칭한 정황',
  CLAIM_CRIME_INVOLVEMENT: '계좌·명의가 범죄에 연루됐다는 주장',
  CLAIM_ACCOUNT_VERIFICATION: '계좌 확인이 필요하다는 주장', CLAIM_DEVICE_BROKEN: '휴대전화 이상을 이유로 한 주장',
  CLAIM_UNAUTHORIZED_PAYMENT: '승인되지 않은 결제가 발생했다는 주장', CLAIM_LOAN_APPROVAL: '대출 승인이 났다는 주장',
  REQUEST_TRANSFER: '송금·이체 요구', REQUEST_INSTALL_APP: '앱 설치 요구', REQUEST_AUTH_INFO: '인증정보 제공 요구',
  REQUEST_PERSONAL_INFO: '개인정보 제공 요구', REQUEST_KEEP_CALL: '통화 유지 요구', REQUEST_SECRECY: '외부 연락 제한 요구',
  REQUEST_OPEN_URL: '링크·앱 실행 요구',
  REQUEST_AMOUNT: '요구 금액', EXTRACTED_CONTEXT: '추출된 통화 정황',
  PURPOSE_SAFE_ACCOUNT: '안전계좌로 자금 이동을 유도한 정황', PURPOSE_LOAN_REPAYMENT: '대출 상환을 요구한 정황',
  PURPOSE_REPAIR: '기기·계정 수리를 이유로 한 요구', PURPOSE_REFUND: '환급을 이유로 한 요구',
  DEADLINE_TODAY: '오늘 안에 처리하도록 재촉한 정황', DEADLINE_IMMEDIATE: '즉시 처리하도록 재촉한 정황',
  TACTIC_FEAR: '처벌·피해에 대한 불안을 유발한 정황', TACTIC_URGENCY: '긴급 처리를 재촉한 정황',
  TACTIC_ISOLATION: '가족·은행 직원과의 상의를 막은 정황',
  CUSTOMER_TRANSFERRED: '고객이 송금·이체했다고 보고함', CUSTOMER_NOT_TRANSFERRED: '고객이 송금·이체하지 않았다고 보고함',
  CUSTOMER_PROVIDED_AUTH: '고객이 인증정보를 제공했다고 보고함', CUSTOMER_PROVIDED_PERSONAL_INFO: '고객이 개인정보를 제공했다고 보고함',
  CUSTOMER_INSTALLED_APP: '고객이 앱을 설치했다고 보고함',
  NORMAL_DEPOSIT_CONSULTATION: '정상적인 예금 상담 정황', NORMAL_CARD_CONSULTATION: '정상적인 카드 상담 정황',
  NORMAL_DAILY_CALL: '일상적인 통화 정황',
};

const normalizeStaffFeatureCode = (code: string) => {
  const normalized = code.toUpperCase();
  if (staffFeatureLabels[normalized]) return normalized;
  if (normalized.startsWith('CLAIMED_ROLE:')) return `ROLE_${normalized.split(':')[1]}`;
  if (normalized.startsWith('REQUEST:')) return `REQUEST_${normalized.split(':')[1]}`;
  if (['URGENCY', 'FEAR', 'ISOLATION'].includes(normalized)) return `TACTIC_${normalized}`;
  if (normalized === 'AUTH_INFO' || normalized === 'SENSITIVE_INFO') return 'REQUEST_AUTH_INFO';
  if (normalized === 'TRANSFER') return 'REQUEST_TRANSFER';
  if (normalized === 'CLAIMS_ORGANIZATION') return 'CLAIMED_ORGANIZATION';
  if (normalized === 'OPEN_URL') return 'REQUEST_OPEN_URL';
  if (normalized === 'INSTALL_APP') return 'REQUEST_INSTALL_APP';
  return normalized;
};

const isSuspectedFeatureCode = (code: string) => [
  'ROLE_', 'CLAIM_', 'CLAIMED_', 'REQUEST_', 'PURPOSE_', 'TACTIC_', 'DEADLINE_',
].some((prefix) => code.startsWith(prefix));

const normalizeStaffNarrativeSentence = (code: string, sentence: string, entityNames: string[]) => {
  const text = sentence.replace(/상대방/g, '보이스피싱 의심 인물').replace(/\s+/g, ' ').trim();
  if (!isSuspectedFeatureCode(code) || (!text.startsWith('고객이 ') && !text.includes('요청받'))) return text;
  const organizationValue = entityNames.find((item) => item && !['UNKNOWN', 'CUSTOMER', 'CALLER'].includes(item));
  const organization = analysisConcreteLabel(organizationValue, '금융기관');
  if (code === 'CLAIM_UNAUTHORIZED_PAYMENT') return `보이스피싱 의심 인물이 ${organization} 직원을 사칭해 승인되지 않은 결제가 발생했다고 주장한 것으로 추정됨.`;
  if (code === 'CLAIM_CRIME_INVOLVEMENT') return '보이스피싱 의심 인물이 고객 계좌·명의가 범죄에 연루됐다고 주장함.';
  if (code === 'CLAIM_ACCOUNT_VERIFICATION') return `보이스피싱 의심 인물이 ${organization} 명의로 고객 계좌 확인이 필요하다고 주장함.`;
  if (code === 'REQUEST_AUTH_INFO') return '보이스피싱 의심 인물이 고객에게 인증정보 제공을 요구함.';
  if (code === 'REQUEST_INSTALL_APP') return '보이스피싱 의심 인물이 고객에게 특정 앱 설치를 요구함.';
  if (['REQUEST_TRANSFER', 'PURPOSE_SAFE_ACCOUNT', 'PURPOSE_REFUND'].includes(code)) return '보이스피싱 의심 인물이 고객에게 자금 이체 또는 송금을 요구함.';
  if (code === 'REQUEST_KEEP_CALL') return '보이스피싱 의심 인물이 고객에게 통화를 계속 유지하라고 요구함.';
  if (code === 'REQUEST_SECRECY' || code === 'TACTIC_ISOLATION') return '보이스피싱 의심 인물이 고객에게 외부 연락이나 사실 공유를 제한함.';
  return text.startsWith('고객이 ') ? `보이스피싱 의심 인물이 ${text.slice(4)}` : text;
};

const normalizeStaffClaimLine = (value: string) => {
  const text = value.replace(/상대방/g, '보이스피싱 의심 인물').replace(/\s+/g, ' ').trim();
  if (!text.includes('고객이')) return text;
  if (text.includes('카드사') && (text.includes('불법 결제') || text.includes('승인되지 않은 결제'))) return '보이스피싱 의심 인물이 카드사 관계자를 사칭하며 승인되지 않은 결제가 발생했다고 주장함.';
  if (text.includes('인증번호') || text.includes('인증정보')) return '보이스피싱 의심 인물이 고객에게 인증정보 제공을 요구함.';
  if (text.includes('계좌') && text.includes('범죄')) return '보이스피싱 의심 인물이 고객 계좌·명의가 범죄에 연루됐다고 주장함.';
  if (text.includes('계좌') && text.includes('확인')) return '보이스피싱 의심 인물이 고객 계좌 확인이 필요하다고 주장함.';
  return text.replace('고객이 ', '보이스피싱 의심 인물이 ');
};

const normalizeStaffSummary = (value: string) => {
  const text = value.replace(/상대방/g, '보이스피싱 의심 인물').replace(/\s+/g, ' ').trim();
  const match = text.match(/^고객이 (.+?)라 자칭하는 자(?:에 의해|에게) (.+)$/);
  if (match) return `보이스피싱 의심 인물이 ${match[1]} 관계자를 사칭하며 ${match[2]}`;
  if (text.startsWith('고객은 ') && (text.includes('요구받') || text.includes('주장'))) return `보이스피싱 의심 인물이 고객에게 ${text.slice(4).replace('요구받았습니다', '요구함').replace('요구받았다', '요구함')}`;
  return text.includes('고객이') && text.includes('자칭') ? text.replace('고객이 ', '보이스피싱 의심 인물이 ') : text;
};

const normalizeStaffCustomerStatement = (value: string) => {
  const text = value.replace(/상대방/g, '보이스피싱 의심 인물').replace(/\s+/g, ' ').trim();
  if (text.includes('주장을 전달')) return '';
  if (/(송금|이체|설치|제공)했다고/.test(text) && !text.includes('은행 내부 채널')) {
    return `${text.replace(/[.。]\s*$/, '')}. 실제 거래·행동 완료 여부는 은행 내부 채널에서 별도 확인 필요`;
  }
  return text;
};

const compactSummaryLine = (value: string) => value.replace(/^보이스피싱 의심 인물이\s+/, '').trim();

const staffFeatureLabel = (code: string) => staffFeatureLabels[normalizeStaffFeatureCode(code)] ?? '추가로 확인된 통화 정황';

const staffFeatureCategory = (code: string) => {
  const normalized = normalizeStaffFeatureCode(code);
  if (normalized.startsWith('ROLE_') || normalized.startsWith('CLAIM_') || normalized.startsWith('CLAIMED_')) return '주장';
  if (normalized.startsWith('REQUEST_') || normalized.startsWith('PURPOSE_')) return '요구';
  if (normalized.startsWith('TACTIC_') || normalized.startsWith('DEADLINE_')) return '압박·통제';
  if (normalized.startsWith('CUSTOMER_')) return '고객 진술';
  if (normalized.startsWith('NORMAL_')) return '참고';
  return '분석 정황';
};

const featureCategoryLabel = (feature: StaffFeature) => feature.title.endsWith(feature.category) ? '' : feature.category;

const staffFeatureStatus = (code: string) => {
  const normalized = normalizeStaffFeatureCode(code);
  if (normalized.startsWith('CUSTOMER_')) return '고객 진술 · 확인 필요';
  if (normalized.startsWith('NORMAL_')) return '참고';
  if (normalized.startsWith('CLAIM_') || normalized.startsWith('CLAIMED_') || normalized.startsWith('ROLE_')) return '주장 · 확인 필요';
  if (normalized.startsWith('REQUEST_') || normalized.startsWith('PURPOSE_')) return '요구 · 확인 필요';
  if (normalized.startsWith('TACTIC_') || normalized.startsWith('DEADLINE_')) return '압박·통제 · 확인 필요';
  return '분석 정황 · 직원 확인 필요';
};

const formatWon = (amount: number) => `${new Intl.NumberFormat('ko-KR').format(amount)}원`;

const atomFeatureCode = (atom: NonNullable<StoredCase['diagnosis']['semantic_atoms']>[number]) => {
  const predicate = atom.predicate.toUpperCase();
  if (predicate === 'CLAIMS_ORGANIZATION') return 'CLAIMED_ORGANIZATION';
  if (predicate === 'CLAIMS_CRIME_INVOLVEMENT' || predicate === 'CLAIMS_ACCOUNT_INVOLVEMENT') return 'CLAIM_CRIME_INVOLVEMENT';
  if (predicate === 'TRANSFER_FUNDS' || predicate === 'WITHDRAW_CASH') return 'REQUEST_TRANSFER';
  if (predicate === 'DISCLOSE_OTP' || predicate === 'DISCLOSE_PASSWORD' || predicate === 'PROVIDE_CARD_INFO') return 'REQUEST_AUTH_INFO';
  if (predicate === 'INSTALL_APP') return 'REQUEST_INSTALL_APP';
  if (predicate === 'OPEN_URL') return 'REQUEST_OPEN_URL';
  if (predicate === 'MAINTAIN_CALL') return 'REQUEST_KEEP_CALL';
  if (predicate === 'KEEP_SECRET' || predicate === 'AVOID_REPORTING' || predicate === 'AVOID_EXTERNAL_CONTACT') return 'REQUEST_SECRECY';
  if (predicate === 'THREATEN_ARREST' || predicate === 'THREATEN_ASSET_FREEZE') return 'TACTIC_FEAR';
  if (predicate === 'JUSTIFY_ASSET_PROTECTION') return 'PURPOSE_SAFE_ACCOUNT';
  return null;
};

const observationStatus = (status: string, code: string) => {
  if (status === 'REPORTED') return '고객 진술 · 확인 필요';
  if (status === 'REQUESTED') return '요구 · 확인 필요';
  if (status === 'CLAIMED') return staffFeatureStatus(code);
  return staffFeatureStatus(code);
};

const featureStatusKind = (status: string) => {
  if (status.includes('역할 귀속') || status.includes('화자 미상') || status.includes('추가 확인')) return 'unknown';
  if (status.includes('고객 진술')) return 'customer';
  if (status.includes('요구')) return 'request';
  if (status.includes('주장')) return 'claim';
  return 'info';
};

const featureStatusLabel = (status: string) => status
  .replace(/\s*·\s*확인 필요/g, '')
  .replace(/^추가 확인 필요$/, '')
  .trim();

const staffFeatureFallback = (code: string, title: string) => {
  const normalized = normalizeStaffFeatureCode(code);
  if (normalized.startsWith('ROLE_') || normalized === 'CLAIMED_ORGANIZATION' || normalized.startsWith('CLAIM_')) {
    return `${title}과 관련된 정황이 확인되었으며 실제 신분·사실 여부는 확인 필요`;
  }
  if (normalized.startsWith('REQUEST_') || normalized.startsWith('PURPOSE_') || normalized.startsWith('DEADLINE_')) {
    return `보이스피싱 의심 인물이 ${title}와 관련된 행동을 요구하거나 유도함`;
  }
  if (normalized.startsWith('TACTIC_')) return `보이스피싱 의심 인물이 ${title} 방식으로 고객의 판단을 압박하거나 통제하려 한 정황이 확인됨`;
  if (normalized.startsWith('CUSTOMER_')) return `${title}. 실제 완료 여부는 은행 내부 채널에서 별도 확인 필요`;
  if (normalized.startsWith('NORMAL_')) return `${title}으로 분류된 통화 맥락입니다.`;
  return `${title}과 관련된 정황이 확인되었습니다.`;
};

const buildStaffFeatures = (diagnosis: StoredCase['diagnosis']): StaffFeature[] => {
  const features = diagnosis.case_context_features;
  const events = diagnosis.events || [];
  const result: StaffFeature[] = [];
  const seen = new Set<string>();
  const seenSemanticCodes = new Set<string>();
  const narratedCodes = new Set<string>();
  const narratedAtomIds = new Set<string>();
  const unique = (items: Array<string | null | undefined>) => [...new Set(items.map((item) => item?.trim()).filter((item): item is string => Boolean(item)))];
  const formatRemaining = (minutes?: number | null) => {
    if (minutes === null || minutes === undefined) return null;
    const hours = Math.floor(minutes / 60);
    const rest = minutes % 60;
    return `기한까지 약 ${hours ? `${hours}시간` : ''}${hours && rest ? ' ' : ''}${rest ? `${rest}분` : ''} 남음`;
  };
  const evidenceForCode = (code: string) => {
    const normalizedCode = normalizeStaffFeatureCode(code);
    const matching = events.filter((event) => {
      const eventCode = event.event_family === 'IMPERSONATION'
        ? (event.impersonation_group ? `ROLE_${event.impersonation_group}` : event.subtype ? `CLAIM_${event.subtype}` : 'CLAIMED_ORGANIZATION')
        : event.event_family === 'MONEY_MOVEMENT' || event.event_family === 'ACTION_REQUEST'
          ? `REQUEST_${event.subtype || event.event_family}`
          : event.event_family === 'PSY_STRATEGY'
            ? `TACTIC_${event.subtype || event.event_family}`
            : event.subtype || event.event_family;
      return normalizeStaffFeatureCode(eventCode) === normalizedCode;
    });
    return unique(matching.map((event) => event.evidence_text));
  };
  const add = (
    id: string, code: string, description?: string, status?: string, dedupeSemantic = true,
    metadata: string[] = [], details: string[] = [],
  ) => {
    const normalizedCode = normalizeStaffFeatureCode(code);
    if (!description && narratedCodes.has(normalizedCode)) return;
    if (seen.has(id) || (dedupeSemantic && seenSemanticCodes.has(normalizedCode))) return;
    seen.add(id);
    if (dedupeSemantic) seenSemanticCodes.add(normalizedCode);
    const title = staffFeatureLabel(normalizedCode);
    const evidence = evidenceForCode(normalizedCode);
    const renderedDescription = description || (evidence.length ? `분석 근거: ${evidence.join(' · ')}` : staffFeatureFallback(normalizedCode, title));
    result.push({
      id, category: staffFeatureCategory(normalizedCode), title,
      description: replaceAnalysisTokens(renderedDescription),
      status: status || staffFeatureStatus(normalizedCode),
      tone: normalizedCode.startsWith('NORMAL_') ? 'info' : 'risk',
      metadata: unique(metadata.filter((item) => !item.startsWith('근거 턴:'))), details: unique(details),
    });
  };
  const addCodes = (codes: string[] | undefined) => (codes || []).forEach((code) => add(code, code));

  (diagnosis.context?.feature_narratives || []).filter((narrative) => narrative.status !== 'DENIED').forEach((narrative, index) => {
    const normalizedCode = normalizeStaffFeatureCode(narrative.code);
    narratedCodes.add(normalizedCode);
    narrative.atom_ids.forEach((atomId) => narratedAtomIds.add(atomId));
    const reference = narrative.source_turns.length ? narrative.source_turns.join('-') : narrative.atom_ids.join('-');
    const actorRole = narrative.actor_role || 'UNKNOWN';
    const narrativeRoleWarning = attributionWarning(
      normalizedCode,
      actorRole,
      narrative.status === 'REPORTED' ? 'CUSTOMER_REPORTED' : narrative.status,
    );
    const sentence = replaceAnalysisTokens(actorRole === 'UNKNOWN' || narrativeRoleWarning
      ? simplifyAttributionSentence(narrative.sentence, normalizedCode, narrative.entity_names || [])
      : actorRole === 'SUSPECTED_PARTY' && !normalizedCode.startsWith('CUSTOMER_')
      ? normalizeStaffNarrativeSentence(normalizedCode, narrative.sentence, narrative.entity_names || [])
      : narrative.sentence.split('상대방').join('보이스피싱 의심 인물'));
    const metadata = unique([
      narrative.deadline_at ? `요구 기한: ${narrative.deadline_at}` : null,
      formatRemaining(narrative.relative_deadline_minutes),
      (narrative.occurrence_count || 1) > 1 ? `반복 ${narrative.occurrence_count}회` : null,
    ]);
    const details = [
      ...(narrative.entity_names || []).map((item) => `구체 명칭·신분: ${analysisConcreteLabel(item)}`),
      ...(narrative.detail_items || []).map((item) => `확인된 세부 내용: ${analysisConcreteLabel(item)}`),
    ];
    add(
      `narrative-${normalizedCode}-${reference || 'none'}-${index}`,
      normalizedCode,
      sentence,
      narrativeRoleWarning || (actorRole === 'UNKNOWN' ? '추가 확인 필요' : observationStatus(narrative.status, normalizedCode)),
      false,
      metadata,
      details,
    );
  });

  (features?.observations || []).filter((observation) => observation.status !== 'DENIED').forEach((observation, index) => {
    add(`observation-${observation.turn}-${observation.code}-${index}`, observation.code, undefined, observationStatus(observation.status, observation.code), true);
  });
  addCodes(features?.claimed_actor_types);
  addCodes(features?.claim_codes);
  addCodes(features?.requested_action_codes);
  addCodes(features?.manipulation_tactic_codes);
  addCodes(features?.exposure_risk_codes);

  const requestedAmounts = features?.requested_amount_values_krw?.length
    ? features.requested_amount_values_krw : features?.amount_values_krw || [];
  [...new Set(requestedAmounts.filter((amount): amount is number => typeof amount === 'number' && amount > 0))].forEach((amount, index) => {
    add(`amount-${amount}-${index}`, 'REQUEST_AMOUNT', `보이스피싱 의심 인물이 ${formatWon(amount)}의 송금·이체를 요구한 정황이 확인됨`, '금액 정보 · 직원 확인 필요', false, [], [`요구 금액: ${formatWon(amount)}`]);
  });

  (diagnosis.semantic_atoms || []).forEach((atom, index) => {
    const code = atomFeatureCode(atom);
    if (!code || narratedAtomIds.has(atom.atom_id)) return;
    const concreteEntities = unique([atom.claimed_organization_name, atom.claimed_branch_name, atom.claimed_person_name, atom.claimed_role_name, atom.claimed_role, atom.claimed_relationship, atom.vocative_target]);
    const termDetails = unique((atom.observed_terms || []).map(observedTermLabel));
    const actorRole = atom.actor_role || atom.actor;
    const roleWarning = attributionWarning(atom.predicate, actorRole, atom.claim_status);
    const attributionUnknown = !actorRole || actorRole === 'UNKNOWN';
    const metadata = unique([
      atom.deadline_at ? `요구 기한: ${atom.deadline_at}` : null,
      formatRemaining(atom.relative_deadline_minutes),
      (atom.occurrence_count || 1) > 1 ? `반복 ${atom.occurrence_count}회` : null,
    ]);
    const details = unique([
      ...concreteEntities.map((item) => `구체 명칭·신분·관계: ${analysisConcreteLabel(item)}`),
      ...termDetails.map((item) => `확인된 세부 내용: ${item}`),
      atom.amount_value_krw ? `금액: ${formatWon(atom.amount_value_krw)}` : null,
      atom.claimed_purpose ? `주장된 목적: ${structuredCodeLabel(atom.claimed_purpose)}` : null,
    ]);
    const description = roleWarning
      ? '정황은 확인되었으나 추가 확인이 필요합니다.'
      : attributionUnknown
        ? '정황은 확인되었으나 추가 확인이 필요합니다.'
        : concreteEntities.length && code.startsWith('ROLE_')
          ? `보이스피싱 의심 인물이 ‘${concreteEntities.map((item) => analysisConcreteLabel(item)).join(' · ')}’ 명칭·신분을 사용해 사칭한 정황이 확인됨`
          : staffFeatureFallback(code, staffFeatureLabel(code));
    add(`atom-${atom.atom_id || index}`, code, description, roleWarning || (attributionUnknown ? '추가 확인 필요' : undefined), false, metadata, details);
  });

  const eventFallbacks = (diagnosis.evidence || []).map((event) => event.text).filter(Boolean);
  if (result.length === 0) eventFallbacks.forEach((text, index) => add(`evidence-${index}-${text}`, 'EXTRACTED_CONTEXT', text, '분석 정황 · 직원 확인 필요', false));
  return result;
};

const buildStructuredDetailGroups = (diagnosis: StoredCase['diagnosis']): StructuredDetailGroup[] => {
  const compact = (values: Array<string | null | undefined>) => values.filter((value): value is string => Boolean(value));
  const atoms = diagnosis.semantic_atoms ?? [];
  const atomById = new Map(atoms.map((atom) => [atom.atom_id, atom]));
  const atomLabel = (atomId: string) => {
    const atom = atomById.get(atomId);
    return atom ? `${structuredCodeLabel(atom.predicate)} (${atom.source_turn_id}번 턴)` : '연결 정황 확인 필요';
  };
  const atomItems: StructuredDetailItem[] = atoms.map((atom, index) => {
    const concrete = compact([
      atom.claimed_organization_name, atom.claimed_organization, atom.claimed_branch_name, atom.claimed_person_name,
      atom.claimed_role_name, atom.claimed_role, atom.claimed_relationship, atom.vocative_target,
      atom.object, atom.destination,
      ...(atom.observed_terms ?? []).map(observedTermLabel),
    ]).map((value) => analysisConcreteLabel(value));
    const pressures = compact([
      atom.urgency && `긴급성 ${structuredCodeLabel(atom.urgency)}`,
      atom.authority_pressure && `권위 압박 ${structuredCodeLabel(atom.authority_pressure)}`,
      atom.fear_pressure && `공포 압박 ${structuredCodeLabel(atom.fear_pressure)}`,
      atom.secrecy_pressure && `비밀 유지 압박 ${structuredCodeLabel(atom.secrecy_pressure)}`,
      atom.isolation_pressure && `연락 차단 압박 ${structuredCodeLabel(atom.isolation_pressure)}`,
      atom.financial_pressure && `금전 압박 ${structuredCodeLabel(atom.financial_pressure)}`,
      atom.repetition_pressure && `반복 압박 ${structuredCodeLabel(atom.repetition_pressure)}`,
    ]);
    return {
      key: atom.atom_id || `atom-${index}`,
      title: structuredCodeLabel(atom.predicate),
      summary: concrete.length ? concrete.join(' · ') : `${structuredCodeLabel(atom.atom_class)} 의미 단위`,
      metadata: compact([
        `근거 턴: ${atom.source_turn_id}`,
        atom.speech_act ? `발화 기능: ${structuredCodeLabel(atom.speech_act)}` : null,
        atom.modality ? `양태: ${structuredCodeLabel(atom.modality)}` : null,
        atom.directive_strength ? `지시 강도: ${structuredCodeLabel(atom.directive_strength)}` : null,
        atom.obligation ? `의무 표현: ${structuredCodeLabel(atom.obligation)}` : null,
        atom.action_state ? `행동 상태: ${structuredCodeLabel(atom.action_state)}` : null,
        atom.claim_status ? `사실 상태: ${structuredCodeLabel(atom.claim_status)}` : null,
        atom.polarity ? `극성: ${structuredCodeLabel(atom.polarity)}` : null,
        atom.amount_value_krw ? `금액: ${formatWon(atom.amount_value_krw)}` : null,
        atom.amount_role ? `금액 역할: ${structuredCodeLabel(atom.amount_role)}` : null,
        atom.amount_direction ? `금액 방향: ${structuredCodeLabel(atom.amount_direction)}` : null,
        atom.amount_scope ? `금액 범위: ${structuredCodeLabel(atom.amount_scope)}` : null,
        atom.threat_type ? `위협 유형: ${structuredCodeLabel(atom.threat_type)}` : null,
        atom.communication_control ? `연락 통제: ${structuredCodeLabel(atom.communication_control)}` : null,
        atom.auth_secret_type ? `인증정보 유형: ${structuredCodeLabel(atom.auth_secret_type)}` : null,
        ...(atom.lexical_cues ?? []).map((cue) => `핵심 표현: ${structuredCodeLabel(cue)}`),
        ...(atom.speech_form_codes ?? []).map((code) => `발화 형식: ${structuredCodeLabel(code)}`),
        atom.deadline_at ? `기한: ${atom.deadline_at}` : null,
        atom.relative_deadline_minutes !== null && atom.relative_deadline_minutes !== undefined
          ? `기한까지 약 ${atom.relative_deadline_minutes}분` : null,
        (atom.occurrence_count || 1) > 1 ? `반복 ${atom.occurrence_count}회` : null,
        ...pressures,
      ]),
    };
  });
  const relationItems: StructuredDetailItem[] = (diagnosis.semantic_relations ?? []).map((relation) => ({
    key: relation.relation_id,
    title: structuredCodeLabel(relation.relation_type),
    summary: `${atomLabel(relation.source_atom_id)} → ${atomLabel(relation.target_atom_id)}`,
    metadata: compact([confidenceLabel(relation.confidence)]),
  }));
  const episodeItems: StructuredDetailItem[] = (diagnosis.conversation_episodes ?? []).map((episode) => ({
    key: episode.episode_id,
    title: structuredCodeLabel(episode.episode_type),
    summary: episode.atom_ids.map(atomLabel).join(' · '),
    metadata: [`${episode.start_turn}~${episode.end_turn}번 턴`, `연결 정황 ${episode.atom_ids.length}건`],
  }));
  const actionItems: StructuredDetailItem[] = (diagnosis.action_groups ?? []).map((group) => ({
    key: group.group_id,
    title: structuredCodeLabel(group.action_predicate),
    summary: group.atom_ids.map(atomLabel).join(' · '),
    metadata: compact([
      group.action_states.length ? `행동 상태: ${group.action_states.map((value) => structuredCodeLabel(value)).join(' · ')}` : null,
      group.target_codes.length ? `대상: ${group.target_codes.map((code) => analysisConcreteLabel(code)).join(' · ')}` : null,
    ]),
  }));
  const entityItems: StructuredDetailItem[] = (diagnosis.entity_registry ?? []).map((entity) => ({
    key: entity.entity_id,
    title: analysisConcreteLabel(entity.entity_code, '식별 대상 · 확인 필요'),
    summary: entity.mention_roles.length
      ? `문맥 역할: ${entity.mention_roles.map((value) => structuredCodeLabel(value)).join(' · ')}`
      : 'AI 분석에서 식별된 명칭·대상',
    metadata: [`등장 턴: ${entity.source_turn_ids.join(', ')}`, `연결 정황 ${entity.atom_ids.length}건`],
  }));
  const mentionItems: StructuredDetailItem[] = (diagnosis.semantic_mentions ?? []).map((mention) => ({
    key: mention.mention_id,
    title: analysisConcreteLabel(mention.normalized_value, '세부 명칭 확인 필요'),
    summary: `${structuredCodeLabel(mention.mention_type)} 문맥`,
    metadata: [
      `등장 순서 ${mention.sequence_index}`,
      mention.first_turn_id === mention.last_turn_id
        ? `${mention.first_turn_id}번 턴`
        : `${mention.first_turn_id}~${mention.last_turn_id}번 턴`,
      `${mention.occurrence_count}회`,
      `신뢰도 ${Math.round(mention.confidence * 100)}%`,
    ],
  }));
  const unmappedItems: StructuredDetailItem[] = (diagnosis.unmapped_observations ?? []).map((observation) => {
    const terms = compact(observation.observed_terms.map(observedTermLabel));
    return {
      key: observation.observation_id,
      title: '분류 검토가 필요한 추가 정황',
      summary: terms.length
        ? terms.join(' · ')
        : observation.candidate_categories.map((value) => structuredCodeLabel(value)).join(' · ') || '정규 분류에 아직 연결되지 않은 정보',
      metadata: compact([
        `유형: ${structuredCodeLabel(observation.observation_type)}`,
        `근거 턴: ${observation.source_turn_id}`,
        observation.speech_act ? `발화 기능: ${structuredCodeLabel(observation.speech_act)}` : null,
        observation.action_state ? `행동 상태: ${structuredCodeLabel(observation.action_state)}` : null,
        observation.amount_value_krw ? `금액: ${formatWon(observation.amount_value_krw)}` : null,
        confidenceLabel(observation.confidence),
        `상태: ${structuredCodeLabel(observation.status)}`,
      ]),
    };
  });
  return [
    { key: 'atoms', title: '의미 단위', items: atomItems },
    { key: 'relations', title: '정황 간 관계', items: relationItems },
    { key: 'episodes', title: '대화 흐름 구간', items: episodeItems },
    { key: 'actions', title: '행동 묶음', items: actionItems },
    { key: 'entities', title: '기관·인물·대상', items: entityItems },
    { key: 'mentions', title: '세부 명칭·표현', items: mentionItems },
    { key: 'unmapped', title: '분류 검토 필요 정보', items: unmappedItems },
  ].filter((group) => group.items.length > 0);
};

const StructuredEnvelopeDetails: React.FC<{ diagnosis: StoredCase['diagnosis'] }> = ({ diagnosis }) => {
  const groups = buildStructuredDetailGroups(diagnosis);
  const total = groups.reduce((sum, group) => sum + group.items.length, 0);
  if (!total) return null;
  return <details className="analysis-structured-details">
    <summary><span>세부 분석 정보</span><small>{total}건 · 펼쳐서 전체 확인</small></summary>
    <div className="analysis-structured-groups">
      {groups.map((group) => <section key={group.key} className="analysis-structured-group">
        <h4>{group.title}<span>{group.items.length}</span></h4>
        <ul>{group.items.map((item) => <li key={item.key}>
          <b>{item.title}</b>
          <p>{item.summary}</p>
          {item.metadata.length > 0 && <div>{item.metadata.map((entry, index) => <span key={`${item.key}-${index}`} data-warning={entry.includes('확인 필요') || undefined}>{entry}</span>)}</div>}
        </li>)}</ul>
      </section>)}
    </div>
  </details>;
};

const structuredSignalLabel = (code: string) => ({
  IMPERSONATION_TRANSFER_CONTROL_COMBINATION: '사칭·송금·연락 제한이 함께 나타난 정황',
}[code] ?? '여러 위험 정황이 함께 나타남');

const staffFacingCopy = (value: string) => replaceAnalysisTokens(value.split('상대방').join('보이스피싱 의심 인물'));

export const AnalysisResult: React.FC<{ result: AnalyzeCaseResponse; caseItem?: StoredCase; sourceText: string; onOpenCase: () => void; onRestart: () => void; showActions?: boolean }> = ({ result, caseItem, sourceText, onOpenCase, onRestart, showActions = true }) => {
  if (result.disposition === 'NO_CASE') return <section className="analysis-result no-case">
    <div className="analysis-result-heading"><span><CheckCircle2 size={21}/></span><div><p>분석 완료</p><h2>현재는 보이스피싱 Case 생성 기준에 해당하지 않습니다.</h2></div></div>
    <p className="analysis-brief">{staffFacingCopy(result.initial_brief || '')}</p>
    <p className="analysis-disclaimer">CSR에는 통화 원문이 전달되지 않으며, AI가 분석한 정보만 사용했습니다.</p>
    <div className="analysis-result-actions"><button type="button" onClick={onRestart}>다른 통화 분석하기</button></div>
  </section>;
  if (!caseItem) return <section className="analysis-result error"><AlertCircle size={20}/><div><h2>Case는 생성됐지만 분석 결과를 불러오지 못했습니다.</h2><p>사건 목록에서 새 Case를 열어 확인해 주세요.</p></div><button type="button" onClick={onOpenCase}>Case 열기</button></section>;
  const context = caseItem.diagnosis.context ?? {};
  const structuredSignals = caseItem.diagnosis.context_signals ?? [];
  const staffFeatures = buildStaffFeatures(caseItem.diagnosis);
  const claims = (context.claims ?? []).map(normalizeStaffClaimLine);
  const demands = (context.demands ?? []).map(normalizeStaffClaimLine);
  const customerStatements = (context.customer_statements ?? []).map(normalizeStaffCustomerStatement).filter(Boolean);
  const recommended = context.recommended_next_steps ?? [];
  const unresolved = valueList(caseItem.initial_report, 'unresolved_items');
  const nextChecks = valueList(caseItem.initial_report, 'next_checks');
  return <section className="analysis-result created">
    <div className="analysis-result-heading"><span className={caseStateTone(caseState(caseItem))}><ShieldAlert size={21}/></span><div><p>Shared Case 생성 완료 · {caseItem.case_id}</p><h2>{staffFacingCopy(context.incident_type || '통화 맥락 분석을 완료했습니다.')}</h2><small>{staffFacingCopy(normalizeStaffSummary(caseItem.initial_brief))}</small></div>{showActions && <div className="analysis-result-actions"><button type="button" onClick={onRestart}>새 통화 분석하기</button><button type="button" className="primary" onClick={onOpenCase}>생성된 Case 열기<ChevronRight size={16}/></button></div>}</div>
    <div className="analysis-result-grid">
      <section><header><BrainCircuit size={16}/><div><b>통화에서 확인된 주요 정황</b><span>AI가 확인한 주장·요구·압박 수법을 기관명·인물·관계·시간 정보와 함께 표시합니다.</span></div></header><div className="analysis-window-list">{structuredSignals.length > 0 && <div className="analysis-composite-summary"><b>종합 정황</b>{structuredSignals.map((signal) => <p key={signal.signal_id}>{structuredSignalLabel(signal.signal_code)}</p>)}</div>}{staffFeatures.length > 0 ? <ul className="analysis-feature-list">{staffFeatures.map((feature) => <li key={feature.id} className={`analysis-feature-item ${feature.tone}`}><div className="analysis-feature-heading"><b>{feature.title}</b>{featureCategoryLabel(feature) && <span>{featureCategoryLabel(feature)}</span>}</div><p>{feature.description}</p>{feature.metadata.length > 0 && <div className="analysis-feature-metadata">{feature.metadata.map((item) => <span key={item} data-warning={item.includes('확인 필요') || undefined}>{item}</span>)}</div>}{feature.details.length > 0 && <ul className="analysis-feature-details">{feature.details.map((item) => <li key={item}>{item}</li>)}</ul>}{featureStatusLabel(feature.status) && <small data-kind={featureStatusKind(feature.status)}>{featureStatusLabel(feature.status)}</small>}</li>)}</ul> : <p className="analysis-empty-signal">확인된 주요 정황이 없습니다. 분석 결과를 다시 확인해 주세요.</p>}<StructuredEnvelopeDetails diagnosis={caseItem.diagnosis}/></div></section>
      <section><header><Sparkles size={16}/><div><b>사건 초기 정리</b><span>검증된 분석 정보를 바탕으로 역할과 사실 상태를 구분해 정리했습니다.</span></div></header><div className="analysis-case-summary"><p>{staffFacingCopy(normalizeStaffSummary(context.summary || caseItem.initial_brief))}</p><div><b>보이스피싱 의심 인물의 주장</b><ul>{claims.length ? claims.map((claim) => <li key={claim}>{staffFacingCopy(compactSummaryLine(claim))}</li>) : <li>확인된 주장이 없습니다.</li>}</ul></div>{demands.length > 0 && <div><b>보이스피싱 의심 인물의 요구</b><ul>{demands.map((item) => <li key={item}>{staffFacingCopy(compactSummaryLine(item))}</li>)}</ul></div>}{customerStatements.length > 0 && <div><b>고객의 진술·행동</b><ul>{customerStatements.map((item) => <li key={item}>{staffFacingCopy(item)}</li>)}</ul></div>}<div><b>우선 권장 조치</b><ul>{recommended.length ? recommended.map((item) => <li key={item}>{staffFacingCopy(item)}</li>) : nextChecks.map((item) => <li key={item}>{staffFacingCopy(item)}</li>)}</ul></div>{unresolved.length > 0 && <div><b>아직 확인할 정보</b><ul>{unresolved.map((item) => <li key={item}>{staffFacingCopy(item)}</li>)}</ul></div>}</div></section>
    </div>
    {sourceText.trim() && <details className="analysis-original-transcript">
      <summary>데모 입력 원문 확인</summary>
      <pre>{sourceText.trim()}</pre>
      <p><b>데모 전용 표시</b> · 이 원문은 화면에서만 확인하며 Case API·저장 데이터에는 전달하거나 보관하지 않습니다.</p>
    </details>}
    <p className="analysis-disclaimer">CSR은 통화 원문을 보관하거나 표시하지 않습니다. AI가 추출한 분석 정보만 업무용 문장으로 정리했으며, 실제 금융 조치와 사실 확정은 담당자의 확인이 필요합니다.</p>
  </section>;
};

interface HomePageProps {
  embedded?: boolean;
  onCloseEmbedded?: () => void;
  onAnalysisBusyChange?: (busy: boolean) => void;
}

export const HomePage: React.FC<HomePageProps> = ({ embedded = false, onCloseEmbedded, onAnalysisBusyChange }) => {
  const navigate = useNavigate();
  const [open, setOpen] = useState(embedded);
  const [text, setText] = useState('');
  const [sourceText, setSourceText] = useState('');
  const [state, setState] = useState<AnalysisState>('INPUT');
  const [result, setResult] = useState<AnalyzeCaseResponse | null>(null);
  const [caseItem, setCaseItem] = useState<StoredCase | undefined>();
  const [error, setError] = useState('');
  const [lastSample, setLastSample] = useState<Partial<Record<SampleType, number>>>({});
  const analysisRequestRef = useRef<AnalysisRequest | null>(null);
  useEffect(() => {
    onAnalysisBusyChange?.(state === 'ANALYZING');
    return () => onAnalysisBusyChange?.(false);
  }, [onAnalysisBusyChange, state]);
  const applySample = (type: SampleType) => {
    const samples = CALL_SAMPLES[type];
    const previous = lastSample[type];
    let index = Math.floor(Math.random() * samples.length);
    if (samples.length > 1 && index === previous) index = (index + 1 + Math.floor(Math.random() * (samples.length - 1))) % samples.length;
    setLastSample((current) => ({ ...current, [type]: index }));
    analysisRequestRef.current = null;
    setText(samples[index]); setError(''); setState('INPUT');
  };
  const reset = () => { analysisRequestRef.current = null; setText(''); setSourceText(''); setResult(null); setCaseItem(undefined); setError(''); setState('INPUT'); setOpen(true); };
  const close = () => { if (embedded && onCloseEmbedded) onCloseEmbedded(); else setOpen(embedded); setError(''); };
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const submittedText = text.trim();
    if (!submittedText || state === 'ANALYZING') return;
    const previousRequest = analysisRequestRef.current;
    const analysisRequest = previousRequest?.submittedText === submittedText
      ? previousRequest
      : { requestId: generateUuid(), submittedText };
    // state가 반영되기 전 같은 handler가 다시 실행돼도 동일한 논리 요청 ID를 사용한다.
    analysisRequestRef.current = analysisRequest;
    setState('ANALYZING'); setError(''); setResult(null); setCaseItem(undefined);
    try {
      const response = await startBackgroundAnalysis(submittedText, analysisRequest.requestId);
      analysisRequestRef.current = null;
      // The source transcript is intentionally transient in this screen too.
      setSourceText(submittedText);
      setText('');
      setResult(response);
      if (response.disposition === 'CASE_CREATED' && response.case_id) {
        // Keep the one-time assignment prompt pending until the user saves or skips it.
        // This also covers opening the newly-created Case later from the case board.
        markInitialAssignmentPending(response.case_id);
        // Creation has succeeded. A failed follow-up read must not invite another analysis.
        setState('CREATED');
        try { setCaseItem(await casesApi.get(response.case_id)); }
        catch { setCaseItem(undefined); }
      }
      else if (response.disposition === 'NO_CASE') setState('NO_CASE');
      else { setState('ERROR'); setError(response.error?.message || '통화 내용을 분석하지 못했습니다.'); }
    } catch (reason) { setState('ERROR'); setError(reason instanceof Error ? reason.message : '통화 내용을 분석하지 못했습니다.'); }
  };
  const resultOpen = state === 'CREATED' && Boolean(caseItem);
  return <section className={embedded ? `home-analysis-embed${resultOpen ? ' analysis-result-open' : ''}` : `home-empty ${open ? 'analysis-open' : ''}`}>
    {!open ? <><div className="home-mark"><ShieldCheck size={26}/></div><p className="eyebrow">CSR | Case Share Room</p><h1>대응할 사건을 선택하세요.</h1><p>통화 맥락, 고객 대화, 기관 확인과 대응 업무를 하나의 Shared Case에서 이어서 확인할 수 있습니다.</p><div className="home-principles"><span><MessageSquareText size={17}/>대화와 업무 기록을 한 흐름으로</span><span><ArrowLeftRight size={17}/>고객 응답과 Case 맥락을 양방향으로</span></div><button className="start-analysis-button" type="button" onClick={() => setOpen(true)}><FileSearch size={17}/>새 통화 분석하기</button><a className="judge-guide-link" href="/judge/index.html">프로젝트 먼저 살펴보기 →</a></> : <div className={`home-analysis-panel${resultOpen ? ' has-analysis-result' : ''}`}>
      <header><div><p className="eyebrow">NEW SHARED CASE · DEMO ADAPTER</p><h1>새 통화 분석하기</h1><span>AI가 통화 내용을 분석한 뒤, 확인된 정보만 CSR Case로 정리합니다.</span></div><button type="button" onClick={close} aria-label="새 통화 분석 닫기"><X size={19}/></button></header>
      {state === 'INPUT' || state === 'ANALYZING' || state === 'ERROR' ? <form onSubmit={submit}><label htmlFor="call-transcript">온디바이스 분석 데모 입력</label><div className="analysis-sample-row"><span>샘플 입력</span><button type="button" disabled={state === 'ANALYZING'} onClick={() => applySample('PHISHING')}>보이스피싱 사례 샘플</button><button type="button" disabled={state === 'ANALYZING'} onClick={() => applySample('FINANCE')}>정상 금융 상담 샘플</button><button type="button" disabled={state === 'ANALYZING'} onClick={() => applySample('DAILY')}>일상 통화 샘플</button></div><textarea id="call-transcript" value={text} disabled={state === 'ANALYZING'} onChange={(event) => { const nextText = event.target.value; if (analysisRequestRef.current?.submittedText !== nextText.trim()) analysisRequestRef.current = null; setText(nextText); }} placeholder={'데모용 통화 원문을 화자 라벨 없이 붙여 넣으세요. AI가 대화 흐름과 표현을 바탕으로 발화자를 구분합니다.\n실제 운영에서는 AI가 분석한 정보만 CSR Case 생성에 사용합니다.'}/><div className="analysis-input-meta"><span>데모 입력 최대 50,000자</span></div><p className="analysis-privacy-note">이 입력은 외부 AI 분석 계층을 모사하기 위한 데모입니다. CSR Case에는 원문이 전달·저장되지 않고 AI가 추출한 역할·관계·명칭·시간·행동·신뢰도만 저장됩니다.</p>{state === 'ANALYZING' && <div className="analysis-progress" role="status" aria-live="polite"><span className="analysis-progress-icon"><Loader2 size={20} className="spin"/></span><div><strong>AI가 통화 내용을 분석하고 있습니다</strong><span>AI가 대화 흐름에서 화자·행위자·대상자를 구분한 뒤, CSR은 확인된 정보와 정황을 검토합니다.</span></div><div className="analysis-progress-track" aria-hidden="true"><span/></div></div>}{error && <p className="analysis-error"><AlertCircle size={15}/>{error}</p>}<footer><button type="button" onClick={close} disabled={state === 'ANALYZING'}>취소</button><button type="submit" className="primary" disabled={!text.trim() || state === 'ANALYZING'}>{state === 'ANALYZING' ? <><Loader2 size={16} className="spin"/>AI 분석·Case 생성 중</> : <><Play size={16}/>데모 분석하고 Case 만들기</>}</button></footer></form> : result && <AnalysisResult result={result} caseItem={caseItem} sourceText={sourceText} onOpenCase={() => result.case_id && navigate(`/cases/${encodeURIComponent(result.case_id)}`, { state: { initialAssignmentRecommendation: true } })} onRestart={reset}/>}</div>}
  </section>;
};
