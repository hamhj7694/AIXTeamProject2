import { Message, RiskSignal, SituationInfo } from '../../types';
import { generateId, getCurrentTimestamp } from '../../utils/helpers';
import { delay } from '../../utils/helpers';
import { useConsultationStore } from './store/consultationStore';

/**
 * 상담 흐름 관리
 * 사용자 선택에 따라 다음 AI 메시지를 결정하는 로직
 */

type UserSelection = string;

/**
 * 상담 흐름 맵 - 각 단계에서 사용자 선택에 따른 다음 메시지
 */
const CONSULTATION_FLOW_MAP: Record<string, Record<string, any>> = {
  // 초기 상황 확인
  situation_check: {
    call_received: {
      message: '전화를 받으신 거군요. 누가 전화를 거셨어요?',
      choices: [
        { id: 'bank', label: '은행 직원이라고 했어요', value: 'bank_claimed' },
        { id: 'prosecutor', label: '검찰, 경찰이라고 했어요', value: 'prosecutor_claimed' },
        { id: 'company', label: '회사나 기관이라고 했어요', value: 'company_claimed' },
        { id: 'personal', label: '가족이나 친구라고 했어요', value: 'personal_claimed' },
        { id: 'unsure', label: '누구인지 잘 모르겠어요', value: 'unknown_caller' },
      ],
      nextStep: 'caller_identity',
      situationToAdd: {
        description: '전화를 받음',
        category: 'contact_type',
      },
    },
    message_received: {
      message: '문자를 받으신 거군요. 누가 보낸 문자였어요?',
      choices: [
        { id: 'bank', label: '은행이라고 표시됐어요', value: 'bank_claimed' },
        { id: 'delivery', label: '배송사라고 표시됐어요', value: 'delivery_claimed' },
        { id: 'unknown', label: '출처가 불명확해요', value: 'unknown_source' },
      ],
      nextStep: 'message_identity',
      situationToAdd: {
        description: '문자를 받음',
        category: 'contact_type',
      },
    },
    money_requested: {
      message: '누가 송금을 요구하셨어요?',
      choices: [
        { id: 'call', label: '전화로 요구받았어요', value: 'phone_request' },
        { id: 'message', label: '문자로 요구받았어요', value: 'message_request' },
        { id: 'meeting', label: '직접 만나서 요구받았어요', value: 'face_to_face_request' },
      ],
      nextStep: 'money_request_method',
      situationToAdd: {
        description: '송금을 요구받음',
        category: 'request_type',
      },
    },
    info_requested: {
      message: '개인정보를 요구받으셨군요. 어떤 정보를 요청했나요?',
      choices: [
        { id: 'phone', label: '휴대폰 번호를 달라고 했어요', value: 'phone_requested' },
        { id: 'id', label: '주민등록번호를 달라고 했어요', value: 'id_requested' },
        { id: 'banking', label: '계좌정보/비밀번호를 달라고 했어요', value: 'banking_info_requested' },
        { id: 'other', label: '다른 정보를 요청했어요', value: 'other_info_requested' },
      ],
      nextStep: 'info_request_type',
      situationToAdd: {
        description: '개인정보를 요구받음',
        category: 'request_type',
      },
      riskSignalToAdd: {
        signal: '개인정보 요구',
        severity: 'high',
      },
    },
    app_installed: {
      message: '앱을 설치하셨군요. 어떤 앱이라고 했나요?',
      choices: [
        { id: 'bank', label: '은행 앱이라고 했어요', value: 'bank_app' },
        { id: 'gov', label: '공식기관 앱이라고 했어요', value: 'government_app' },
        { id: 'security', label: '보안/바이러스 앱이라고 했어요', value: 'security_app' },
        { id: 'other', label: '다른 앱이라고 했어요', value: 'other_app' },
        { id: 'unclear', label: '뭐라고 했는지 명확하지 않아요', value: 'unclear_app' },
      ],
      nextStep: 'app_type_check',
      situationToAdd: {
        description: '앱을 설치함',
        category: 'action_taken',
      },
      riskSignalToAdd: {
        signal: '의심 앱 설치',
        severity: 'high',
      },
    },
  },

  // 앱 설치 유형 확인
  app_type_check: {
    bank_app: {
      message: '은행 앱이라고 하셨군요. 은행앱을 이용하면서 아래와 같은 행동을 하셨나요?',
      choices: [
        { id: 'login', label: '로그인 정보를 입력했어요', value: 'login_info_entered' },
        { id: 'account', label: '계좌번호/카드번호를 입력했어요', value: 'account_info_entered' },
        { id: 'auth', label: '인증번호를 입력했어요', value: 'auth_code_entered' },
        { id: 'nothing', label: '아무것도 입력하지 않았어요', value: 'nothing_entered' },
      ],
      nextStep: 'app_action_status',
      situationToAdd: {
        description: '은행 앱을 설치함',
        category: 'app_type',
      },
      riskSignalToAdd: {
        signal: '은행 앱 위장 악성 앱',
        severity: 'high',
      },
    },
    government_app: {
      message: '공식기관 앱을 이용하셨군요. 앱을 이용하는 과정에서 어떤 정보를 입력하셨나요?',
      choices: [
        { id: 'personal', label: '개인정보(주민등록번호 등)를 입력했어요', value: 'personal_info_entered' },
        { id: 'banking', label: '계좌정보를 입력했어요', value: 'banking_info_entered' },
        { id: 'nothing', label: '아무것도 입력하지 않았어요', value: 'nothing_entered' },
      ],
      nextStep: 'app_action_status',
      situationToAdd: {
        description: '공식기관 앱을 설치함',
        category: 'app_type',
      },
      riskSignalToAdd: {
        signal: '공식기관 앱 위장 악성 앱',
        severity: 'high',
      },
    },
    security_app: {
      message: '보안 앱이라고 하셨군요. 앱을 설치한 후 어떤 일이 있었나요?',
      choices: [
        { id: 'scanned', label: '휴대폰을 스캔하고 보안 문제가 있다고 했어요', value: 'fake_scan_alert' },
        { id: 'money', label: '요금을 내야 한다고 했어요', value: 'money_charged' },
        { id: 'permission', label: '권한 허용을 계속 요구했어요', value: 'permission_requested' },
        { id: 'nothing', label: '특별한 일은 없었어요', value: 'nothing_happened' },
      ],
      nextStep: 'security_app_action',
      situationToAdd: {
        description: '보안/바이러스 앱을 설치함',
        category: 'app_type',
      },
      riskSignalToAdd: {
        signal: '사기성 보안 앱 설치',
        severity: 'high',
      },
    },
    other_app: {
      message: '앱 설치 후 어떤 요청을 받으셨나요?',
      choices: [
        { id: 'info_request', label: '개인정보 입력을 요청받았어요', value: 'info_input_requested' },
        { id: 'money_request', label: '돈을 내라고 했어요', value: 'money_request_app' },
        { id: 'permission', label: '휴대폰 권한을 요청했어요', value: 'permission_request_app' },
        { id: 'nothing', label: '아무것도 요구하지 않았어요', value: 'nothing_app' },
      ],
      nextStep: 'app_consequence',
      situationToAdd: {
        description: '알 수 없는 앱을 설치함',
        category: 'app_type',
      },
      riskSignalToAdd: {
        signal: '정체불명의 앱 설치',
        severity: 'high',
      },
    },
    unclear_app: {
      message: '앱이 명확하지 않으시군요. 혹시 그 이후로 이상한 일이 있었나요?',
      choices: [
        { id: 'phone_issue', label: '휴대폰이 이상해졌어요', value: 'phone_malfunction' },
        { id: 'money', label: '계좌에서 돈이 빠져나갔어요', value: 'money_missing' },
        { id: 'contact', label: '계속 연락이 와요', value: 'continued_contact_from_app' },
        { id: 'nothing', label: '특별한 일은 없었어요', value: 'nothing_after_app' },
      ],
      nextStep: 'unclear_app_consequence',
      situationToAdd: {
        description: '불명확한 앱을 설치함',
        category: 'app_type',
      },
      riskSignalToAdd: {
        signal: '정체불명 앱 설치',
        severity: 'high',
      },
    },
  },

  // 앱 설치 후 정보 입력 상태
  app_action_status: {
    login_info_entered: {
      message: '로그인 정보를 입력하셨군요. 지금은 그 앱에 접근할 수 없도록 삭제하셔야 합니다.',
      nextStep: 'app_damage_check',
      riskSignalToAdd: {
        signal: '로그인 정보 탈취 위험',
        severity: 'high',
      },
      shouldShowIntervention: true,
      interventionType: 'already_damaged',
    },
    account_info_entered: {
      message: '계좌 정보를 입력하셨군요. 지금은 즉시 은행에 연락해야 할 수도 있습니다.',
      nextStep: 'app_damage_check',
      riskSignalToAdd: {
        signal: '금융 정보 탈취',
        severity: 'high',
      },
      shouldShowIntervention: true,
      interventionType: 'already_damaged',
    },
    auth_code_entered: {
      message: '인증번호를 입력하셨군요. 혹시 그 이후로 계좌에서 이상한 일이 있었나요?',
      choices: [
        { id: 'money_out', label: '계좌에서 돈이 빠져나갔어요', value: 'unauthorized_transaction' },
        { id: 'nothing', label: '특별한 일은 없었어요', value: 'nothing_yet_auth' },
      ],
      nextStep: 'auth_code_consequence',
      riskSignalToAdd: {
        signal: '인증 정보 탈취',
        severity: 'high',
      },
    },
    nothing_entered: {
      message: '그렇다면 다행이에요. 지금이라도 그 앱을 삭제하시고, 앱스토어에서 이상한 설치 기록이 없는지 확인해주세요.',
      nextStep: 'app_safety_check',
      riskSignalToAdd: {
        signal: '악성 앱 노출 (정보 입력 안 함)',
        severity: 'medium',
      },
    },
  },

  // 보안 앱 관련 조치
  security_app_action: {
    fake_scan_alert: {
      message: '사기성 보안 앱의 전형적인 수법입니다. 지금은 그 앱을 즉시 삭제하셔야 합니다.',
      nextStep: 'app_safety_check',
      riskSignalToAdd: {
        signal: '사기성 스캔 경고',
        severity: 'high',
      },
    },
    money_charged: {
      message: '돈을 내도록 요구하는 것은 100% 사기입니다. 그 앱을 즉시 삭제하세요.',
      nextStep: 'app_safety_check',
      riskSignalToAdd: {
        signal: '불법 요금 청구',
        severity: 'high',
      },
      shouldShowIntervention: true,
      interventionType: 'already_damaged',
    },
    permission_requested: {
      message: '권한을 계속 요구하는 것도 의심스러운 신호입니다. 지금 그 앱을 삭제해주세요.',
      nextStep: 'app_safety_check',
      riskSignalToAdd: {
        signal: '과도한 권한 요구',
        severity: 'high',
      },
    },
    nothing_happened: {
      message: '그렇다면 다행이에요. 하지만 정체불명의 앱은 언제 어떤 피해를 줄지 모르니, 지금 삭제하는 것이 안전해요.',
      nextStep: 'app_safety_check',
      riskSignalToAdd: {
        signal: '불명 보안 앱 설치',
        severity: 'medium',
      },
    },
  },

  // 앱 설치로 인한 피해 확인
  app_damage_check: {
    '': {
      message: '현재 상황을 확인했습니다. 지금부터 안전한 대응 방법을 알려드릴게요.',
      nextStep: 'app_response_guide',
    },
  },

  // 인증번호 입력 후 결과
  auth_code_consequence: {
    unauthorized_transaction: {
      message: '이미 피해가 발생하셨군요. 지금은 은행에 즉시 연락해서 거래 정지를 요청하셔야 합니다.',
      nextStep: 'immediate_action',
      riskSignalToAdd: {
        signal: '무단 거래 발생',
        severity: 'high',
      },
      shouldShowIntervention: true,
      interventionType: 'already_damaged',
    },
    nothing_yet_auth: {
      message: '지금은 아무 일이 없지만, 앞으로도 감시해야 해요. 계속 지켜봐주세요.',
      nextStep: 'app_response_guide',
    },
  },

  // 앱 설치 후 미상의 피해
  app_consequence: {
    info_input_requested: {
      message: '개인정보 입력을 요구하는 것은 사기의 확실한 신호입니다. 그 앱을 즉시 삭제하세요.',
      nextStep: 'app_safety_check',
      riskSignalToAdd: {
        signal: '개인정보 수집 시도',
        severity: 'high',
      },
    },
    money_request_app: {
      message: '앱에서 돈을 요구하는 것은 100% 사기입니다. 절대 돈을 내지 마시고 앱을 삭제하세요.',
      nextStep: 'app_safety_check',
      riskSignalToAdd: {
        signal: '앱 내 불법 요금 청구',
        severity: 'high',
      },
      shouldShowIntervention: true,
      interventionType: 'already_damaged',
    },
    permission_request_app: {
      message: '휴대폰 권한을 요구하는 것도 악의적인 신호입니다. 지금 그 앱을 삭제해주세요.',
      nextStep: 'app_safety_check',
      riskSignalToAdd: {
        signal: '악성 권한 요구',
        severity: 'high',
      },
    },
    nothing_app: {
      message: '특별한 요구가 없다면 다행이지만, 정체불명의 앱이므로 삭제하는 것이 안전합니다.',
      nextStep: 'app_safety_check',
      riskSignalToAdd: {
        signal: '미확인 앱 설치',
        severity: 'medium',
      },
    },
  },

  // 불명확한 앱 설치 후 결과
  unclear_app_consequence: {
    phone_malfunction: {
      message: '휴대폰이 이상해진 것은 악성 앱 설치의 신호일 수 있습니다. 안전 모드로 진입해 앱을 삭제해주세요.',
      nextStep: 'immediate_action',
      riskSignalToAdd: {
        signal: '휴대폰 성능 저하 (악성 앱)',
        severity: 'high',
      },
    },
    money_missing: {
      message: '계좌에서 돈이 빠져나간 것은 이미 피해가 발생했다는 뜻입니다. 즉시 은행에 연락하세요.',
      nextStep: 'immediate_action',
      riskSignalToAdd: {
        signal: '무단 송금 발생',
        severity: 'high',
      },
      shouldShowIntervention: true,
      interventionType: 'already_damaged',
    },
    continued_contact_from_app: {
      message: '계속 연락이 온다면 사기꾼이 당신의 정보를 가지고 있을 가능성이 높습니다.',
      nextStep: 'immediate_action',
      riskSignalToAdd: {
        signal: '반복 접근 시도',
        severity: 'high',
      },
    },
    nothing_after_app: {
      message: '다행이에요. 하지만 지금이라도 그 앱을 삭제하고 휴대폰을 점검해주세요.',
      nextStep: 'app_safety_check',
      riskSignalToAdd: {
        signal: '미확인 앱 설치 (현재 피해 없음)',
        severity: 'medium',
      },
    },
  },

  // 앱 안전 점검
  app_safety_check: {
    '': {
      message: '앱 삭제 후 다음을 확인해주세요:\n\n1. 앱 스토어에서 결제/설치 기록 확인\n2. 휴대폰 설정에서 권한 확인\n3. 계좌 거래 내역 확인\n4. 의심 거래가 있으면 은행에 신고',
      nextStep: 'final_guidance',
    },
  },

  // 긴급 조치
  immediate_action: {
    '': {
      message: '지금 해야 할 일:\n\n1. 즉시 은행에 연락 (24시간 고객센터)\n2. 앱 삭제\n3. 휴대폰 점검\n4. 경찰 신고 (112)\n5. 금융감시원 신고 (1332)',
      nextStep: 'final_guidance',
    },
  },

  // 앱 설치 후 대응 가이드
  app_response_guide: {
    '': {
      message: '앞으로 이런 상황이 생기지 않도록:\n\n• 의심되는 앱은 절대 설치 금지\n• 공식 앱은 공식 스토어(앱스토어, 플레이스토어)에서만 설치\n• 모르는 사람의 지시대로 앱 설치 금지\n• 개인정보 입력 요구 시 즉시 거절',
      nextStep: 'final_guidance',
    },
  },

  // 최종 안내
  final_guidance: {
    '': {
      message: '상담을 완료했습니다.\n\n더 궁금한 점이 있으면 "안전 안내" 탭에서 자세한 정보를 확인할 수 있습니다.\n\n• 경찰청: 112\n• 금융감시원: 1332\n• 정보통신신문고: 1336',
      nextStep: 'completed',
    },
  },

  // 발신자 신원 확인
  caller_identity: {
    bank_claimed: {
      message: '은행 직원이라고 하셨군요. 어떤 안내를 받으셨나요?',
      choices: [
        { id: 'fraud', label: '계좌가 범죄에 이용됐다고 했어요', value: 'account_fraud_claim' },
        { id: 'loan', label: '금리 인하, 대출을 제안했어요', value: 'loan_offer' },
        { id: 'security', label: '계좌 보안 점검이라고 했어요', value: 'security_check_claim' },
        { id: 'other', label: '다른 이유라고 했어요', value: 'other_reason' },
      ],
      nextStep: 'bank_reason',
      situationToAdd: {
        description: '은행 직원을 사칭한 연락을 받음',
        category: 'caller_type',
      },
      riskSignalToAdd: {
        signal: '금융기관을 사칭',
        severity: 'high',
      },
    },
    prosecutor_claimed: {
      message: '검찰이나 경찰이라고 하셨군요. 전화로 어떤 안내를 받으셨을까요?',
      choices: [
        { id: 'crime', label: '범죄 혐의가 있다고 했어요', value: 'crime_accusation' },
        { id: 'investigation', label: '수사 협조라고 했어요', value: 'investigation_request' },
        { id: 'account', label: '계좌 이용이 문제라고 했어요', value: 'account_problem' },
      ],
      nextStep: 'prosecutor_reason',
      situationToAdd: {
        description: '검찰·경찰을 사칭한 연락을 받음',
        category: 'caller_type',
      },
      riskSignalToAdd: {
        signal: '관공서를 사칭',
        severity: 'high',
      },
    },
    unknown_caller: {
      message: '출처를 알 수 없는 전화이군요. 어떤일로 전화를 하셨을까요?',
      choices: [
        { id: 'money', label: '돈을 요청했어요', value: 'money_request_unknown' },
        { id: 'info', label: '개인정보를 요청했어요', value: 'info_request_unknown' },
        { id: 'unclear', label: '무슨 말인지 명확하지 않았어요', value: 'unclear_purpose' },
      ],
      nextStep: 'unknown_caller_reason',
      situationToAdd: {
        description: '출처 불명의 전화를 받음',
        category: 'caller_type',
      },
      riskSignalToAdd: {
        signal: '출처 불명의 전화',
        severity: 'medium',
      },
    },
  },

  // 은행 사칭 이유
  bank_reason: {
    account_fraud_claim: {
      message: '계좌가 범죄에 이용됐다고 하셨군요. 그러면 어떤 안내를 요청 받으셨나요?',
      choices: [
        { id: 'transfer', label: '다른 계좌로 송금하라고 했어요', value: 'transfer_demanded' },
        { id: 'verify', label: '비밀번호나 인증번호를 알려달라고 했어요', value: 'verify_demanded' },
        { id: 'app', label: '앱을 설치하라고 했어요', value: 'app_demanded' },
        { id: 'account_freeze', label: '계좌를 동결한다고 했어요', value: 'account_freeze_threat' },
      ],
      nextStep: 'bank_action',
      situationToAdd: {
        description: '계좌가 범죄에 이용되었다는 설명을 받음',
        category: 'reason_detail',
      },
      riskSignalToAdd: {
        signal: '계좌 문제를 이유로 금전을 요구',
        severity: 'high',
      },
    },
    loan_offer: {
      message: '금리 인하나 대출을 제안받으셨군요. 금리 인하나 대출 승인을 위해 어떤 조건을 제안 받으셨을까요?',
      choices: [
        { id: 'low_rate', label: '시장 금리보다 훨씬 낮은 금리라고 했어요', value: 'suspiciously_low_rate' },
        { id: 'fee', label: '선금이나 수수료를 내라고 했어요', value: 'upfront_payment_demanded' },
        { id: 'info', label: '개인정보를 입력하라고 했어요', value: 'personal_info_requested' },
      ],
      nextStep: 'loan_detail',
      situationToAdd: {
        description: '금리 인하 또는 대출 제안을 받음',
        category: 'reason_detail',
      },
      riskSignalToAdd: {
        signal: '과도하게 우호적인 금융 제안',
        severity: 'medium',
      },
    },
  },

  // 은행 사칭 - 요구 행동
  bank_action: {
    transfer_demanded: {
      message: '송금을 요구했군요. 언제까지 송금하라고 하셨나요?',
      choices: [
        { id: 'urgent', label: '지금 바로, 오늘 중에 해야 한다고 했어요', value: 'urgent_demand' },
        { id: 'soon', label: '빨리, 내일까지라고 했어요', value: 'soon_demand' },
        { id: 'normal', label: '시간 제한이 없었어요', value: 'no_time_limit' },
        { id: 'threat', label: '안 하면 큰일 난다고 협박했어요', value: 'threat' },
      ],
      nextStep: 'transfer_timeline',
      situationToAdd: {
        description: '다른 계좌로 송금을 요구받음',
        category: 'action_detail',
      },
      riskSignalToAdd: {
        signal: '긴급한 송금을 요구',
        severity: 'high',
      },
    },
    verify_demanded: {
      message: '비밀번호나 인증번호를 요청받으셨군요. 요청사항을 실제 행동으로 옮기셨나요?',
      choices: [
        { id: 'yes', label: '네, 알려줬어요', value: 'info_disclosed' },
        { id: 'no', label: '아니요, 거절했어요', value: 'info_not_disclosed' },
        { id: 'partial', label: '일부만 알려줬어요', value: 'partial_disclosure' },
      ],
      nextStep: 'info_disclosure_status',
      situationToAdd: {
        description: '비밀번호/인증번호를 요구받음',
        category: 'action_detail',
      },
      riskSignalToAdd: {
        signal: '금융 인증 정보 요구',
        severity: 'high',
      },
    },
  },

  // 송금 타이밍
  transfer_timeline: {
    urgent_demand: {
      message: '지금 바로 송금하라는 긴급 요구군요. 현재 송금할 준비가 되어 있으신가요?',
      choices: [
        { id: 'ready', label: '네, 송금할 준비를 했어요', value: 'transfer_ready' },
        { id: 'thinking', label: '아직 생각 중이에요', value: 'considering_transfer' },
        { id: 'hesitant', label: '뭔가 이상한 것 같아요', value: 'suspicious' },
        { id: 'refused', label: '거절했어요', value: 'transfer_refused' },
      ],
      nextStep: 'transfer_readiness',
      riskSignalToAdd: {
        signal: '긴급함을 강조하며 빠른 처리 강요',
        severity: 'high',
      },
    },
    threat: {
      message: '갑작스럽게 협박을 받으셔서 많이 놀라고 무셨우셨겠어요',
      choices: [
        { id: 'yes', label: '네, 매우 무서웠어요', value: 'very_scared' },
        { id: 'some', label: '좀 불안하지만 뭔가 이상해요', value: 'uncertain' },
        { id: 'no', label: '거짓인 것 같아요', value: 'disbelieving' },
      ],
      nextStep: 'fear_level',
      riskSignalToAdd: {
        signal: '협박과 위협',
        severity: 'high',
      },
    },
  },

  // 송금 준비도
  transfer_readiness: {
    transfer_ready: {
      message: '지금은 잠시 멈추고 다시 한 번 확인해보는 게 가장 안전해요.\n\n이런 상황에서는 서둘러 결론을 내리기보다,\n공식 기관 번호로 직접 확인하고 가족이나 주변 사람과 함께 상의해보는 게 좋아요.',
      nextStep: 'briefing',
    },
    considering_transfer: {
      message: '신중하게 생각해주셔서 다행이에요.\n\n지금까지 말씀해주신 상황을 다시 한번 정리해볼게요.',
      nextStep: 'briefing',
    },
    suspicious: {
      message: '맞습니다! 당신의 의심이 정당합니다.\n\n지금까지 확인한 상황이 보이스피싱의 특징과 매우 유사합니다.',
      nextStep: 'briefing',
    },
    transfer_refused: {
      message: '현명한 판단입니다! \n\n하지만 상대방이 계속 압박할 수 있으니\n이후 어떤 행동을 하셨는지 알려주세요.',
      nextStep: 'after_refusal',
    },
  },

  // 문자 신원 확인
  message_identity: {
    bank_claimed: {
      message: '은행이라고 표시됐군요. 문자에는 어떤 내용이 있었나요?',
      choices: [
        { id: 'link', label: '앱 다운로드 링크가 있었어요', value: 'link_included' },
        { id: 'confirm', label: '본인 확인을 요청했어요', value: 'confirmation_requested' },
        { id: 'action', label: '특정 행동을 하라고 했어요', value: 'action_demanded' },
      ],
      nextStep: 'message_content',
      situationToAdd: { description: '은행을 사칭한 문자를 받음', category: 'message_type' },
      riskSignalToAdd: { signal: '금융기관 사칭 문자', severity: 'high' },
    },
    delivery_claimed: {
      message: '배송사라고 표시됐군요. 어떤 내용의 문자였나요?',
      choices: [
        { id: 'link', label: '배송 조회 링크가 있었어요', value: 'delivery_link' },
        { id: 'payment', label: '배송료 결제를 요청했어요', value: 'delivery_payment' },
        { id: 'unclear', label: '무슨 말인지 명확하지 않았어요', value: 'unclear_message' },
      ],
      nextStep: 'message_content',
      situationToAdd: { description: '배송사를 사칭한 문자를 받음', category: 'message_type' },
      riskSignalToAdd: { signal: '배송사 사칭 문자', severity: 'medium' },
    },
  },

  // 문자 내용
  message_content: {
    link_included: {
      message: '링크를 클릭하셨나요?',
      choices: [
        { id: 'yes', label: '네, 클릭했어요', value: 'link_clicked' },
        { id: 'no', label: '아니요, 클릭하지 않았어요', value: 'link_not_clicked' },
        { id: 'hesitant', label: '뭔가 의심스러워서 안 했어요', value: 'suspicious_of_link' },
      ],
      nextStep: 'link_click_status',
      riskSignalToAdd: { signal: '악성 링크 포함 문자', severity: 'high' },
    },
  },

  // 링크 클릭 여부
  link_click_status: {
    link_clicked: {
      message: '링크를 클릭하셨군요. 그 이후로 어떤 일이 있었나요?',
      choices: [
        { id: 'app', label: '앱 설치를 요구받았어요', value: 'app_install_demanded_after_click' },
        { id: 'info', label: '개인정보 입력을 요구받았어요', value: 'personal_info_demanded_after_click' },
        { id: 'money', label: '돈을 요구받았어요', value: 'money_demanded_after_click' },
        { id: 'nothing', label: '특별한 일은 없었어요', value: 'nothing_happened' },
      ],
      nextStep: 'link_consequence',
      riskSignalToAdd: { signal: '악성 링크 클릭', severity: 'high' },
    },
    link_not_clicked: {
      message: '현명한 판단이에요. 그럼 링크를 클릭하지 않은 이유가 있었나요?',
      choices: [
        { id: 'suspicious', label: '뭔가 이상해 보였어요', value: 'looked_suspicious' },
        { id: 'habit', label: '평소에 조심해요', value: 'cautious_by_nature' },
        { id: 'timing', label: '시간이 없었어요', value: 'no_time' },
      ],
      nextStep: 'result',
    },
  },

  // 송금 방법
  money_request_method: {
    phone_request: {
      message: '전화로 송금을 요구받으셨군요. 어디로 송금하라고 하셨을까요?',
      choices: [
        { id: 'other_account', label: '다른 사람 계좌로 보내라고 했어요', value: 'third_party_account' },
        { id: 'app', label: '특정 앱으로 송금하라고 했어요', value: 'app_transfer' },
        { id: 'unclear', label: '정확하지 않았어요', value: 'unclear_method' },
      ],
      nextStep: 'transfer_destination',
    },
  },

  // 전송 목표
  transfer_destination: {
    third_party_account: {
      message: '다른 사람 계좌로 보내라고 했군요. 어떤 사람의 계좌라고 했나요?',
      choices: [
        { id: 'bank', label: '은행 또는 정부 기관이라고 했어요', value: 'official_account' },
        { id: 'personal', label: '개인이라고 했어요', value: 'personal_account' },
        { id: 'unclear', label: '명확히 안 했어요', value: 'unclear_recipient' },
      ],
      nextStep: 'recipient_info',
      riskSignalToAdd: { signal: '제3자 계좌로의 송금 요구', severity: 'high' },
    },
  },

  // 수신자 정보
  recipient_info: {
    official_account: {
      message: '공식 기관이라고 했군요. 그렇다면 공식 기관에 대해서 설명을 들으셨을까요?',
      choices: [
        { id: 'bank', label: '은행이라고 했어요', value: 'bank_official' },
        { id: 'government', label: '경찰, 검찰 등 관공서라고 했어요', value: 'government_official' },
        { id: 'other', label: '다른 기관이라고 했어요', value: 'other_official' },
      ],
      nextStep: 'briefing',
      riskSignalToAdd: { signal: '공식 기관 사칭하며 송금 요구', severity: 'high' },
    },
  },

  // 검찰/경찰 이유
  prosecutor_reason: {
    crime_accusation: {
      message: '범죄 혐의가 있다고 했군요. 어떤 사건에 연루되었다고 했을까요?',
      choices: [
        { id: 'money_laundry', label: '자금 세탁에 이용됐다고 했어요', value: 'money_laundering' },
        { id: 'fraud', label: '사기에 이용됐다고 했어요', value: 'fraud_accusation' },
        { id: 'other_crime', label: '다른 범죄라고 했어요', value: 'other_crime_accusation' },
      ],
      nextStep: 'briefing',
      riskSignalToAdd: { signal: '관공서 사칭하며 범죄 혐의 제기', severity: 'high' },
    },
  },

  // 출처 불명 전화 이유
  unknown_caller_reason: {
    money_request_unknown: {
      message: '돈을 요청했군요. 얼마를 요구하셨나요?',
      choices: [
        { id: 'small', label: '작은 금액이었어요', value: 'small_amount' },
        { id: 'large', label: '큰 금액이었어요', value: 'large_amount' },
        { id: 'depends', label: '조건에 따라 달라진다고 했어요', value: 'conditional_amount' },
      ],
      nextStep: 'result',
    },
  },

  // 대출 세부
  loan_detail: {
    suspiciously_low_rate: {
      message: '시장 금리보다 훨씬 낮다니, 정말 좋은 조건이네요. 그런데 실제로 신청하셨나요?',
      choices: [
        { id: 'yes', label: '네, 신청했어요', value: 'loan_applied' },
        { id: 'no', label: '아니요, 거절했어요', value: 'loan_refused' },
        { id: 'hesitant', label: '뭔가 이상해서 안 했어요', value: 'suspicious_of_loan' },
      ],
      nextStep: 'result',
      riskSignalToAdd: { signal: '과도하게 낮은 금리 제시', severity: 'high' },
    },
    upfront_payment_demanded: {
      message: '선금이나 수수료를 내라고 했군요. 실제로 내셨을까요?',
      choices: [
        { id: 'yes', label: '네, 냈어요', value: 'payment_made' },
        { id: 'no', label: '아니요, 거절했어요', value: 'payment_refused' },
        { id: 'hesitant', label: '뭔가 이상해서 안 했어요', value: 'suspicious_of_payment' },
      ],
      nextStep: 'result',
      riskSignalToAdd: { signal: '선금이나 수수료 요구', severity: 'high' },
    },
  },

  // 정보 공개 상태
  info_disclosure_status: {
    info_disclosed: {
      message: '개인정보를 알려주셨군요. 그 이후로 어떤 일이 있었나요?',
      choices: [
        { id: 'unauthorized_transfer', label: '계좌에서 돈이 빠져나갔어요', value: 'unauthorized_transfer_occurred' },
        { id: 'additional_contact', label: '상대방이 계속 연락했어요', value: 'continued_contact' },
        { id: 'nothing_yet', label: '아직 특별한 일은 없었어요', value: 'nothing_yet' },
      ],
      nextStep: 'result',
    },
  },

  // 두려움 수준
  fear_level: {
    very_scared: {
      message: '정말 무서우신 상황이네요. 괜찮아요. 지금부터 함께 대응방법을 알려드릴게요.',
      nextStep: 'result',
      riskSignalToAdd: { signal: '협박으로 인한 심리 압박', severity: 'high' },
    },
    uncertain: {
      message: '맞습니다. 당신의 의심이 정당해요. 이런 상황은 거의 모두 사기입니다.',
      nextStep: 'result',
      riskSignalToAdd: { signal: '협박과 의심 신호', severity: 'high' },
    },
  },

  // 행동 개입 후
  action_intervention: {
    '': {
      message: '지금처럼 신중하게 대응해주신다면 충분히 안전하게 막을 수 있어요.\n\n우선은 연락을 끊고, 공식 기관에 직접 확인해보는 것이 가장 중요해요.',
      nextStep: 'result',
    },
  },

  // 거절 후
  after_refusal: {
    '': {
      message: '정말 잘 하셨어요. 상대방이 계속 압박하더라도, 즉시 응하지 않고 잠시 멈춰서 확인하는 게 가장 안전합니다.',
      nextStep: 'briefing',
    },
  },

  // 상황 정리
  briefing: {
    '': {
      message: '지금까지 말씀해주신 상황을 정리해볼게요.\n위의 "위험 신호" 섹션을 확인해주세요.',
      nextStep: 'risk_assessment',
    },
  },

  // 위험도 평가
  risk_assessment: {
    '': {
      message: '상황을 분석한 결과를 바탕으로 다음을 권고드립니다.',
      nextStep: 'action_plan',
    },
  },

  // 조치 계획
  action_plan: {
    '': {
      message: '지금 해야 할 일:',
      choices: [
        { id: 'understood', label: '알겠습니다', value: 'action_confirmed' },
      ],
      nextStep: 'result',
    },
  },

  // 결과
  result: {
    action_confirmed: {
      message: '상담을 완료했습니다.\n\n더 도움이 필요하면 "안전 안내" 탭을 참고해주세요.\n\n긴급 신고 번호:\n- 경찰청: 112\n- 금융감시원: 1332',
      nextStep: 'completed',
    },
  },
};

/**
 * 사용자 선택에 따른 다음 AI 메시지 생성
 */
export const getNextMessage = (
  currentStep: string,
  userSelection: string,
  flowMap: Record<string, any> = CONSULTATION_FLOW_MAP
): { message: Message; nextStep: string; riskSignal?: RiskSignal; situationInfo?: SituationInfo; shouldShowIntervention?: boolean; interventionType?: string } | null => {
  const stepFlow = flowMap[currentStep];
  if (!stepFlow || !stepFlow[userSelection]) {
    return null;
  }

  const flow = stepFlow[userSelection];

  const message: Message = {
    id: generateId(),
    role: 'assistant',
    type: flow.choices ? 'question' : 'text',
    content: flow.message,
    choices: flow.choices,
    createdAt: getCurrentTimestamp(),
  };

  return {
    message,
    nextStep: flow.nextStep || currentStep,
    riskSignal: flow.riskSignalToAdd,
    situationInfo: flow.situationToAdd,
    shouldShowIntervention: flow.shouldShowIntervention,
    interventionType: flow.interventionType,
  };
};

/**
 * 상담 흐름 처리
 */
export const handleConsultationFlow = async (
  userSelection: string,
  currentStep: string,
  store: any
) => {
  store.setLoading(true);
  await delay(500);

  const result = getNextMessage(currentStep, userSelection);
  if (!result) {
    store.setLoading(false);
    return;
  }

  const { message, nextStep, riskSignal, situationInfo, shouldShowIntervention, interventionType } = result;

  // 사용자 선택 메시지 추가
  store.addUserMessage(
    result.message.choices?.find((c) => c.value === userSelection)?.label || userSelection
  );

  await delay(300);

  // AI 응답 메시지 추가
  store.addMessage(message);

  // 위험 신호 추가
  if (riskSignal) {
    store.addRiskSignal(riskSignal);
  }

  // 상황 정보 추가
  if (situationInfo) {
    store.addSituationInfo(situationInfo);
  }

  // 현재 단계 업데이트
  store.updateCurrentStep(nextStep);

  // 행동 개입 표시
  if (shouldShowIntervention && interventionType) {
    store.showIntervention(interventionType);
  }

  store.setLoading(false);
};
