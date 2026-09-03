import { FileText, Landmark, Phone, ShieldAlert, type LucideIcon } from 'lucide-react';

export interface RecoveryStepDefinition {
  id: 'CONTACT' | 'EVIDENCE' | 'REPORT' | 'RELIEF';
  icon: LucideIcon;
  title: string;
  summary: string;
  purpose: string;
  actions: string[];
  caution: string;
  contact: string;
}

export const recoverySteps: RecoveryStepDefinition[] = [
  {
    id: 'CONTACT', icon: Phone, title: '즉시 연락', summary: '거래 은행에 연락해 지급정지 가능 여부를 문의하세요.',
    purpose: '피해금이 다른 계좌로 이동하기 전에 거래 은행의 공식 사고 신고 채널로 지급정지를 요청합니다.',
    actions: ['거래 은행 공식 앱 또는 대표번호를 확인합니다.', '송금 시각·금액·받는 계좌를 준비합니다.', '보이스피싱 피해 사실과 지급정지 요청을 명확히 전달합니다.', '접수번호와 담당 부서를 기록합니다.'],
    caution: '상대방이 알려준 전화번호나 링크는 사용하지 마세요.', contact: '거래 은행 공식 대표번호·앱 사고신고 메뉴',
  },
  {
    id: 'EVIDENCE', icon: FileText, title: '증빙 확보', summary: '거래 내역·문자·대화·첨부 자료를 원본으로 보관하세요.',
    purpose: '신고와 피해구제 신청에 사용할 수 있도록 시간 순서와 원본성을 유지해 자료를 확보합니다.',
    actions: ['계좌이체 내역과 영수증을 저장합니다.', '문자·메신저·통화기록 화면을 캡처 및 녹음 후 저장합니다.', '상대 계좌번호·전화번호·URL을 기록합니다.', '파일을 수정하지 말고 원본과 사본을 함께 보관합니다.'],
    caution: '대화방을 나가거나 메시지를 삭제하기 전에 증빙부터 확보하세요.', contact: '현재 Case의 파일 첨부 기능을 이용해 담당자와 공유 가능',
  },
  {
    id: 'REPORT', icon: ShieldAlert, title: '신고 접수', summary: '긴급 피해는 경찰청 112, 금융 상담은 금융감독원 1332에 문의하세요.',
    purpose: '수사기관과 금융기관에 피해 사실을 공식 접수해 후속 조치의 근거를 남깁니다.',
    actions: ['긴급한 추가 피해 위험이 있으면 112에 신고합니다.', '금융 피해 상담과 절차 안내는 1332에 문의합니다.', '사건 경위와 송금 정보를 시간 순서대로 설명합니다.', '신고·상담 접수번호를 Case에 기록합니다.'],
    caution: '기관 담당자는 안전계좌 이체나 원격제어 앱 설치를 요구하지 않습니다.', contact: '경찰청 112 · 금융감독원 1332',
  },
  {
    id: 'RELIEF', icon: Landmark, title: '구제 신청', summary: '은행의 피해구제 절차와 필요 서류를 안내받으세요.',
    purpose: '지급정지 이후 피해금 환급 가능 여부와 신청 절차를 거래 은행에서 확인합니다.',
    actions: ['은행에 피해구제 신청 가능 여부를 확인합니다.', '신분증·이체확인증·신고 증빙 등 필요 서류를 확인합니다.', '신청서 제출 방법과 보완 기한을 기록합니다.', '처리 상태와 추가 요청 자료를 Case에서 계속 확인합니다.'],
    caution: '피해금 반환을 명목으로 추가 입금이나 수수료를 요구하면 응하지 마세요.', contact: '거래 은행 피해구제 담당 부서',
  },
];
