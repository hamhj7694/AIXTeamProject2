from __future__ import annotations

import unittest

from contracts.public_api.case_workflow import PublicRightPanelProjection
from general_api.app.domains.cases.right_panel_projection import build_right_panel_projection


class RightPanelProjectionTest(unittest.TestCase):
    def test_sources_are_attributed_and_transfer_request_is_not_a_transaction(self):
        case = {
            "case_id": "VP-25",
            "victim_transfer_status": "UNKNOWN",
            "diagnosis": {
                "context": {
                    "summary": "수사기관 사칭 및 송금 유도 정황이 있는 사건입니다.",
                    "feature_narratives": [
                        {"code": "INCIDENT_CLAIM", "sentence": "계좌가 범죄에 연루됐다고 주장함", "status": "CLAIMED",
                         "speaker_role": "SUSPECTED_PARTY", "source_turns": [3], "atom_ids": ["claim-1"]},
                        {"code": "ACTION_TRANSFER_REQUEST", "sentence": "300만원 송금을 요구함", "status": "REQUESTED",
                         "speaker_role": "SUSPECTED_PARTY", "source_turns": [5], "atom_ids": ["demand-1"]},
                    ],
                },
                "semantic_mentions": [
                    {"mention_id": "entity-1", "mention_type": "INSTITUTION", "normalized_value": "서울중앙지검",
                     "speaker_role": "SUSPECTED_PARTY", "sequence_index": 3},
                ],
            },
        }
        context = {
            "situation_summary": "수사기관 사칭 및 송금 유도 정황이 있는 사건입니다.",
            "money_events": [
                {"event_id": "amount-1", "atom_id": "a-1", "amount_krw": 3_000_000,
                 "amount_role": "REQUESTED_AMOUNT", "action_state": "REQUESTED",
                 "speaker_role": "SUSPECTED_PARTY", "predicate": "안전계좌 송금 요구"},
                {"event_id": "amount-2", "atom_id": "a-2", "amount_krw": 3_000_000,
                 "amount_role": "TRANSFER_OUT", "action_state": "COMPLETED", "claim_status": "REPORTED",
                 "speaker_role": "CUSTOMER", "predicate": "송금했다고 답변"},
                {"event_id": "amount-3", "atom_id": "a-3", "amount_krw": 3_000_000,
                 "amount_role": "REQUESTED_AMOUNT", "action_state": "REQUESTED",
                 "speaker_role": "SUSPECTED_PARTY", "predicate": "환급을 위한 다른 계좌 이체 요구"},
            ],
        }
        result = build_right_panel_projection(
            case=case, case_context=context,
            questions=[{"question_id": "q-transfer", "target_field": "transfer_status", "status": "ANSWERED", "answer_text": "송금했어요"}],
            verifications=[
                {"verification_task_id": "v-1", "target": "기관 소속", "status": "COMPLETED", "result_summary": "회신 내용을 기록함"},
                {"verification_task_id": "v-2", "target": "사건번호", "status": "COMPLETED", "result_summary": "공식 조회 결과 불일치", "evidence_url": "https://www.police.go.kr/check"},
            ],
        )

        money = [item for item in result["exposure"] if "300만원" in item["title"]]
        self.assertEqual(len(money), 1)
        self.assertEqual(money[0]["title"], "300만원 송금 요구")
        self.assertEqual(money[0]["source_badge"], "상대방 요구")
        self.assertEqual(money[0]["presentation_group"], "money")
        exposure_groups = {item["title"]: item["presentation_group"] for item in result["exposure"]}
        self.assertEqual(exposure_groups["실제 송금"], "money")
        self.assertEqual(exposure_groups["실제 개인정보 제공"], "personal_information")
        self.assertEqual(exposure_groups["실제 인증정보 제공"], "authentication_information")
        self.assertEqual(exposure_groups["원격제어 앱 설치"], "device_access")
        self.assertFalse(any("금액 관련 언급" in item["title"] for item in result["exposure"]))
        self.assertTrue(any(item["title"] == "실제 송금" and item["source_badge"] == "고객 진술" for item in result["exposure"]))
        self.assertEqual(result["contact_information"][0]["title"], "서울중앙지검")
        self.assertEqual(result["contact_information"][0]["source_badge"], "상대방 주장")
        verification_badges = {item["title"]: item["source_badge"] for item in result["verification"]}
        self.assertEqual(verification_badges["기관 소속 확인"], "직원 기록")
        self.assertEqual(verification_badges["사건번호 확인"], "공식 확인")
        self.assertEqual(result["summary_badges"][-1], {
            "key": "institution", "label": "기관 확인 필요", "tone": "attention",
        })

    def test_vp25_categories_entities_and_test_verification_are_human_readable(self):
        case = {"diagnosis": {"context": {"feature_narratives": [
            {"code": "ROLE_PROSECUTION", "sentence": "보이스피싱 의심 인물이 수사관 역할로 제시됨.",
             "status": "CLAIMED", "speaker_role": "SUSPECTED_PARTY", "source_turns": [6],
             "entity_names": ["김인수", "용의자", "INVESTIGATOR"], "atom_ids": ["role-1"]},
            {"code": "CLAIM_ACCOUNT_VERIFICATION", "sentence": "보이스피싱 의심 인물이 고객 계좌가 범죄에 연루됐다고 주장함.",
             "status": "CLAIMED", "speaker_role": "SUSPECTED_PARTY", "source_turns": [7],
             "entity_names": ["김인수"], "atom_ids": ["claim-1"]},
            {"code": "REQUEST_PERSONAL_INFO", "sentence": "보이스피싱 의심 인물이 고객에게 개인 정보 제공을 요구함.",
             "status": "REQUESTED", "speaker_role": "SUSPECTED_PARTY", "source_turns": [8],
             "entity_names": ["김민수", "BANK_EMPLOYEE"], "atom_ids": ["request-1"]},
            {"code": "TACTIC_FEAR", "sentence": "보이스피싱 의심 인물이 처벌 불안을 조성함.",
             "status": "CLAIMED", "speaker_role": "SUSPECTED_PARTY", "source_turns": [9],
             "entity_names": [], "atom_ids": ["pressure-1"]},
        ]}, "semantic_mentions": [
            {"mention_id": "name-1", "mention_type": "PERSON_NAME", "normalized_value": "김인수",
             "speaker_role": "SUSPECTED_PARTY", "sequence_index": 1, "source_turn_id": 6},
            {"mention_id": "role-1", "mention_type": "ROLE", "normalized_value": "용의자",
             "speaker_role": "SUSPECTED_PARTY", "sequence_index": 2, "source_turn_id": 6},
            {"mention_id": "code-1", "mention_type": "INSTITUTION", "normalized_value": "BANK",
             "speaker_role": "SUSPECTED_PARTY", "sequence_index": 3, "source_turn_id": 6},
            {"mention_id": "name-2", "mention_type": "PERSON_NAME", "normalized_value": "김민수",
             "speaker_role": "SUSPECTED_PARTY", "sequence_index": 4, "source_turn_id": 8},
            {"mention_id": "role-2", "mention_type": "ROLE", "normalized_value": "BANK_EMPLOYEE",
             "speaker_role": "SUSPECTED_PARTY", "sequence_index": 5, "source_turn_id": 8},
            {"mention_id": "court-1", "mention_type": "INSTITUTION", "normalized_value": "서울중앙지검",
             "speaker_role": "SUSPECTED_PARTY", "sequence_index": 6, "source_turn_id": 8},
        ]}}
        result = build_right_panel_projection(
            case=case, case_context={},
            verifications=[
                {"verification_task_id": "test-1", "target": "테스트 담당자", "claim": "테스트 내용", "status": "PENDING"},
                {"verification_task_id": "real-1", "target": "서울중앙지검 소속", "claim": "소속 확인", "status": "PENDING"},
            ],
        )

        groups = {group["key"]: group["items"] for group in result["fraud_signals"]}
        self.assertTrue(any("범죄에 연루됐다고 주장함" in item["title"] for item in groups["claim"]))
        self.assertEqual(groups["demand"][0]["title"], "개인정보·민감정보 제공 요구")
        self.assertTrue(groups["pressure"])
        contacts = {item["title"]: item for item in result["contact_information"]}
        self.assertEqual(contacts["김인수"]["detail"], "용의자로 지목")
        self.assertEqual(contacts["김민수"]["detail"], "은행 직원으로 언급")
        self.assertNotIn("BANK", contacts)
        self.assertNotIn("INVESTIGATOR", contacts)
        self.assertNotIn("테스트 담당자", {item["title"] for item in result["verification"]})
        self.assertEqual([item["title"] for item in result["verification"]], ["서울중앙지검 소속 확인"])

    def test_checklist_recommendations_are_work_not_activity(self):
        action = {"action_id": "check-1", "action_type": "AI_CHECKLIST:P0:transfer_status",
                  "status": "REQUESTED", "note": "실제 송금 진행 여부 확인 필요",
                  "created_at": "2026-09-28T08:00:00Z"}
        result = build_right_panel_projection(case={}, case_context={}, actions=[action])
        self.assertEqual([item["title"] for item in result["incomplete_work"]], ["실제 송금 여부 확인"])
        self.assertEqual(result["activity"], [])

        completed = {**action, "status": "COMPLETED", "updated_at": "2026-09-28T08:15:00Z"}
        result = build_right_panel_projection(case={}, case_context={}, actions=[completed])
        self.assertEqual([item["title"] for item in result["completed_work"]], ["실제 송금 여부 확인"])
        self.assertEqual([item["title"] for item in result["activity"]], ["업무 완료: 실제 송금 여부 확인"])

    def test_absent_answers_are_unknown_not_no_harm(self):
        result = build_right_panel_projection(case={"diagnosis": {}}, case_context={})
        self.assertEqual(len(result["exposure"]), 4)
        self.assertTrue(all(item["source_badge"] == "미확인" for item in result["exposure"]))
        self.assertTrue(all(not item["detail"] for item in result["exposure"]))
        self.assertEqual(result["summary_badges"], [
            {"key": "transfer", "label": "송금 미확인", "tone": "unknown"},
            {"key": "information", "label": "정보 노출 미확인", "tone": "unknown"},
        ])

    def test_actual_transfer_signal_is_not_grouped_as_a_demand(self):
        result = build_right_panel_projection(case={"diagnosis": {"context": {"feature_narratives": [
            {"code": "TRANSFER_OUT", "sentence": "고객이 송금했다고 진술함", "status": "REPORTED",
             "speaker_role": "CUSTOMER", "atom_ids": ["transfer-1"]},
            {"code": "ACTION_TRANSFER_REQUEST", "sentence": "상대방이 송금을 요구함", "status": "REQUESTED",
             "speaker_role": "SUSPECTED_PARTY", "atom_ids": ["request-1"]},
        ]}}}, case_context={})
        groups = {group["key"]: group["items"] for group in result["fraud_signals"]}
        self.assertEqual([item["title"] for item in groups["money"]], ["실제 송금"])
        self.assertEqual([item["title"] for item in groups["demand"]], ["금전 이동 요구"])

    def test_ai_brief_title_is_used_without_clipping_and_full_narrative_is_preserved(self):
        brief_title = "고객 계정에서 승인되지 않은 결제가 발생했다고 주장하며 외부 이체를 안내"
        sentence = "보이스피싱 의심 인물이 고객 계정에서 승인되지 않은 결제가 발생했다고 주장함. 실제 결제 발생 여부는 확인되지 않았으며, 외부 계좌 이체를 안내한 정황이 있음."
        result = build_right_panel_projection(case={"diagnosis": {"context": {"feature_narratives": [{
            "code": "CLAIM_UNAUTHORIZED_PAYMENT", "brief_title": brief_title,
            "sentence": sentence, "status": "CLAIMED", "speaker_role": "SUSPECTED_PARTY",
            "actor_role": "SUSPECTED_PARTY", "target_role": "CUSTOMER",
            "reported_by_role": "SUSPECTED_PARTY", "atom_ids": ["claim-1"],
        }]}}}, case_context={})

        row = next(item for group in result["fraud_signals"] for item in group["items"])
        self.assertEqual(row["title"], brief_title)
        self.assertNotIn("…", row["title"])
        self.assertEqual(row["detail"], sentence)

    def test_processing_history_contains_persisted_events_not_open_recommendations(self):
        result = build_right_panel_projection(
            case={}, case_context={},
            questions=[
                {"question_id": "q-1", "target_field": "transfer_status", "question_text": "실제 송금했나요?",
                 "asked_at": "2026-09-28T08:00:00Z"},
                {"question_id": "q-2", "target_field": "remote_control_app", "question_text": "앱을 설치했나요?",
                 "asked_at": "2026-09-28T08:05:00Z", "answered_at": "2026-09-28T08:10:00Z",
                 "answer_text": "설치하지 않았어요"},
            ],
            actions=[
                {"action_id": "pending-1", "action_type": "CALLBACK", "title": "Recommendation: call the customer",
                 "status": "COMPLETED", "created_at": "2026-09-28T08:11:00Z", "updated_at": "2026-09-28T08:13:00Z"},
                {"action_id": "enum-1", "action_type": "STAFF_TASK", "title": "BANK_EMPLOYEE",
                 "status": "COMPLETED", "created_at": "2026-09-28T08:12:00Z", "updated_at": "2026-09-28T08:15:00Z"},
            ],
            verifications=[
                {"verification_task_id": "v-code", "target": "COURT", "claim": "BANK_EMPLOYEE",
                 "status": "PENDING", "created_at": "2026-09-28T08:20:00Z"},
            ],
        )
        titles = [item["title"] for item in result["activity"]]
        self.assertTrue(any("송금 여부 질문 발송" in title for title in titles))
        self.assertIn("고객 답변 수신", titles)
        self.assertNotIn("Recommendation: call the customer", titles)
        self.assertNotIn("BANK_EMPLOYEE", " ".join(titles))
        self.assertNotIn(" 업무 등록", titles)

    def test_official_institution_badge_requires_completed_official_evidence(self):
        case = {"diagnosis": {"semantic_mentions": [
            {"mention_id": "m-1", "mention_type": "INSTITUTION", "normalized_value": "서울중앙지검"},
        ]}}
        completed = {"verification_task_id": "v-1", "target": "COURT", "claim": "서울중앙지검 소속", "status": "COMPLETED",
                     "result_summary": "공식 회신 확인", "evidence_url": "https://www.spo.go.kr/example"}
        result = build_right_panel_projection(case=case, case_context={}, verifications=[completed])
        self.assertIn({"key": "institution", "label": "기관 공식 여부 확인됨", "tone": "verified"}, result["summary_badges"])
        self.assertEqual(result["verification"][0]["title"], "서울중앙지검 소속 확인")

    def test_exposure_requests_and_unknown_states_use_semantic_groups_once(self):
        case = {"diagnosis": {"context": {"feature_narratives": [
            {"code": "EXTERNAL_TRANSFER_REQUEST", "sentence": "외부 계좌로 송금을 요구함", "status": "REQUESTED",
             "speaker_role": "SUSPECTED_PARTY", "atom_ids": ["money-1"]},
            {"code": "OTP_REQUEST", "sentence": "인증번호 제공을 요구함", "status": "REQUESTED",
             "speaker_role": "SUSPECTED_PARTY", "atom_ids": ["auth-1"]},
            {"code": "REMOTE_CONTROL_INSTALL_REQUEST", "sentence": "원격제어 앱 설치를 요구함", "status": "REQUESTED",
             "speaker_role": "SUSPECTED_PARTY", "atom_ids": ["device-1"]},
        ]}}}
        result = build_right_panel_projection(case=case, case_context={})
        by_group = {}
        for row in result["exposure"]:
            by_group.setdefault(row["presentation_group"], []).append(row)
        self.assertEqual(by_group["money"][0]["title"], "외부 계좌 송금 요구")
        self.assertEqual(by_group["money"][0]["source_badge"], "상대방 요구")
        self.assertEqual([row["title"] for row in by_group["authentication_information"]], ["인증정보 제공 요구", "실제 인증정보 제공"])
        self.assertEqual(by_group["authentication_information"][0]["source_badge"], "상대방 요구")
        self.assertEqual(by_group["authentication_information"][1]["source_badge"], "미확인")
        self.assertEqual([row["title"] for row in by_group["device_access"]], ["원격제어 앱 설치 요구", "원격제어 앱 설치"])
        self.assertFalse(any(row["presentation_group"] == "other" for row in result["exposure"]))

    def test_reported_transfer_replaces_synthetic_unknown_exposure_row(self):
        result = build_right_panel_projection(case={"diagnosis": {"context": {"feature_narratives": [
            {"code": "TRANSFER_OUT", "sentence": "고객이 300만원을 송금했다고 진술함", "status": "REPORTED",
             "speaker_role": "CUSTOMER", "atom_ids": ["transfer-out-1"]},
        ]}}}, case_context={})
        transfer_rows = [
            row for row in [*result["exposure"], *(item for category in result["fraud_signals"] for item in category["items"])]
            if row["presentation_group"] == "money" and "송금" in row["title"]
        ]
        self.assertEqual(len(transfer_rows), 1)
        self.assertEqual(transfer_rows[0]["title"], "실제 송금")
        self.assertEqual(transfer_rows[0]["source_badge"], "고객 진술")

    def test_six_exposure_rows_are_grouped_and_contract_rejects_missing_metadata(self):
        case = {"diagnosis": {"context": {"feature_narratives": [
            {"code": "EXTERNAL_TRANSFER_REQUEST", "sentence": "외부 계좌로 송금을 요구함", "status": "REQUESTED",
             "speaker_role": "SUSPECTED_PARTY", "atom_ids": ["money-1"]},
            {"code": "OTP_REQUEST", "sentence": "인증번호 제공을 요구함", "status": "REQUESTED",
             "speaker_role": "SUSPECTED_PARTY", "atom_ids": ["auth-1"]},
        ]}}}
        projection = build_right_panel_projection(case=case, case_context={})
        expected = {"money": 2, "personal_information": 1, "authentication_information": 2, "device_access": 1}
        counts = {key: sum(item["presentation_group"] == key for item in projection["exposure"])
                  for key in expected}
        self.assertEqual(counts, expected)
        self.assertEqual(len(projection["exposure"]), 6)
        self.assertEqual(sum(counts.values()), len(projection["exposure"]))
        self.assertEqual(sum(item["presentation_group"] == "other" for item in projection["exposure"]), 0)
        self.assertEqual([item["source_badge"] for item in projection["exposure"] if item["title"].endswith("요구")],
                         ["상대방 요구", "상대방 요구"])
        PublicRightPanelProjection.model_validate(projection)

        projection["exposure"][0]["presentation_group"] = None
        with self.assertRaises(ValueError):
            PublicRightPanelProjection.model_validate(projection)

    def test_duplicate_transfer_requests_collapse_and_deadline_stays_a_fraud_signal(self):
        case = {"diagnosis": {"context": {"feature_narratives": [
            {"code": "EXTERNAL_TRANSFER_REQUEST", "sentence": "300만원을 외부 계좌로 송금하라고 요구함", "status": "REQUESTED",
             "speaker_role": "SUSPECTED_PARTY", "atom_ids": ["request-narrative-1"]},
            {"code": "ACTION_TRANSFER_REQUEST", "sentence": "300만원 송금을 요구함", "status": "REQUESTED",
             "speaker_role": "SUSPECTED_PARTY", "atom_ids": ["request-narrative-2"]},
            {"code": "DEADLINE_TODAY", "sentence": "오늘 반드시 처리해야 한다고 압박함", "status": "CLAIMED",
             "speaker_role": "SUSPECTED_PARTY", "atom_ids": ["deadline-1"]},
        ]}}}
        case_context = {"proposed_facts": [
            {"fact_id": "request-fact-1", "field": "requested_amount_krw", "value": "300만원 송금 요구",
             "status": "PROPOSED", "source_kind": "AI_ANALYSIS", "evidence_refs": ["request-fact-evidence-1"]},
            {"fact_id": "request-fact-2", "field": "requested_amount_krw", "value": "300만원을 송금하라고 요구",
             "status": "PROPOSED", "source_kind": "AI_ANALYSIS", "evidence_refs": ["request-fact-evidence-2"]},
        ]}
        projection = build_right_panel_projection(case=case, case_context=case_context)
        money_rows = [row for row in projection["exposure"] if row["presentation_group"] == "money"]
        requests = [row for row in money_rows if row["semantic_key"].startswith(("demand:", "chat-request:"))]
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["title"], "송금 요구")
        self.assertIn("300만원", requests[0]["detail"])
        self.assertEqual(set(requests[0]["evidence_refs"]), {
            "request-narrative-1", "request-narrative-2", "request-fact-evidence-1", "request-fact-evidence-2",
        })
        self.assertEqual(len(money_rows), 2)  # one consolidated demand plus the distinct transfer-status item

        groups = {category["key"]: category["items"] for category in projection["fraud_signals"]}
        self.assertEqual(len(groups["pressure"]), 1)
        self.assertIn("DEADLINE_TODAY", groups["pressure"][0]["semantic_key"])
        self.assertEqual(groups["pressure"][0]["title"], "당일 처리 압박")
        self.assertEqual(groups["pressure"][0]["detail"], "오늘 반드시 처리해야 한다고 압박함")
        self.assertEqual(groups["money"], [])
        PublicRightPanelProjection.model_validate(projection)

    def test_staff_attested_fact_projects_without_becoming_a_bank_record(self):
        result = build_right_panel_projection(case={}, case_context={
            "confirmed_facts": [],
            "proposed_facts": [
                {"fact_id": "staff-transfer-status", "field": "transfer_status", "value": "송금했음",
                 "status": "PROPOSED", "source_kind": "STAFF_OBSERVATION", "staff_attested": True,
                 "evidence_refs": ["msg-staff"]},
                {"fact_id": "staff-transfer-amount", "field": "transfer.actual.amount", "value": "500만원 송금",
                 "status": "PROPOSED", "source_kind": "STAFF_OBSERVATION", "staff_attested": True,
                 "evidence_refs": ["msg-staff"]},
                {"fact_id": "staff-request", "field": "requested_amount_krw", "value": "700만원 요구",
                 "status": "PROPOSED", "source_kind": "STAFF_OBSERVATION", "staff_attested": False,
                 "evidence_refs": ["msg-demand"]},
            ],
        })
        transfer = [row for row in result["exposure"] if row["title"] == "실제 송금 여부"]
        request = [row for row in result["exposure"] if row["title"] == "700만원 송금 요구"]
        self.assertEqual(len(transfer), 1)
        self.assertEqual(transfer[0]["source_badge"], "담당자 확인 보고")
        self.assertIsNone(transfer[0]["status"])  # staff attestation is provenance, not a completed task
        self.assertIn("500만원 송금", transfer[0]["detail"])
        self.assertEqual(transfer[0]["evidence_refs"], ["msg-staff"])
        self.assertEqual(len(request), 1)
        self.assertNotEqual(transfer[0]["title"], request[0]["title"])
        self.assertNotIn("BANK_RECORD", str(transfer))

    def test_staff_attested_exposure_and_device_facts_keep_source_not_work_status(self):
        fields = (
            ("exposure.personal_information", "개인정보 제공됨", "personal_information"),
            ("exposure.authentication_information", "인증정보 제공됨", "authentication_information"),
            ("device.remote_control_app", "원격제어 앱 설치됨", "device_access"),
        )
        projection = build_right_panel_projection(case={}, case_context={
            "confirmed_facts": [],
            "proposed_facts": [
                {"fact_id": f"staff-{group}", "field": field, "value": value,
                 "status": "PROPOSED", "source_kind": "STAFF_OBSERVATION", "staff_attested": True,
                 "evidence_refs": [f"msg-{group}"]}
                for group, (field, value, _) in enumerate(fields)
            ],
        })
        outcomes = {row["presentation_group"]: row for row in projection["exposure"]
                    if row["source_badge"] == "담당자 확인 보고"}
        self.assertEqual(set(outcomes), {group for _, _, group in fields})
        for group, row in outcomes.items():
            with self.subTest(group=group):
                self.assertIsNone(row["status"])
                self.assertTrue(row["evidence_refs"])

    def test_checklist_work_has_verification_group_and_response_tasks_stay_separate(self):
        actions = [{"action_id": f"check-{field}", "action_type": f"AI_CHECKLIST:P0:{field}", "status": "REQUESTED"}
                   for field in ("transfer_status", "personal_information_exposure", "authentication_information_exposure",
                                 "transfer_purpose", "claimed_organization", "incident_claim")]
        tasks = [{"task_id": "protect-1", "task_type": "PROTECTIVE_ACTION", "title": "계정 보호 조치"},
                 {"task_id": "review-1", "task_type": "TRANSACTION_REVIEW", "title": "거래 기록 조회"}]
        result = build_right_panel_projection(case={}, case_context={}, actions=actions, tasks=tasks)
        work = {row["title"]: row["progress_group"] for row in result["incomplete_work"]}
        self.assertEqual(sum(group == "verification" for group in work.values()), 7)
        self.assertEqual(work["계정 보호 조치"], "response")
        self.assertEqual(work["거래 기록 조회"], "verification")

    def test_identity_entity_and_same_evidence_interpretation_have_one_default_row(self):
        case = {"diagnosis": {"context": {"feature_narratives": [
            {"code": "ROLE_CARD_CENTER", "sentence": "상대방이 카드사 보안센터 소속이라고 주장함", "status": "CLAIMED",
             "speaker_role": "SUSPECTED_PARTY", "entity_names": ["카드사 보안센터"], "source_turns": [1], "atom_ids": ["identity-1"]},
            {"code": "INCIDENT_CLAIM", "sentence": "미승인 결제가 발생했다고 주장함", "status": "CLAIMED",
             "speaker_role": "SUSPECTED_PARTY", "atom_ids": ["claim-1"]},
            {"code": "CLAIM_INTERPRETATION", "sentence": "해당 주장으로 권위와 피해 불안을 높인 정황", "status": "CLAIMED",
             "speaker_role": "SUSPECTED_PARTY", "atom_ids": ["claim-1"]},
        ]}, "semantic_mentions": [{"mention_id": "org-1", "mention_type": "INSTITUTION",
                                    "normalized_value": "카드사 보안센터", "speaker_role": "SUSPECTED_PARTY", "sequence_index": 1}]}}
        result = build_right_panel_projection(case=case, case_context={})
        groups = {group["key"]: group["items"] for group in result["fraud_signals"]}
        self.assertEqual([row["title"] for row in groups["identity"]], ["카드사 보안센터 소속 사칭"])
        self.assertEqual(groups["identity"][0]["source_badge"], "상대방 주장")
        self.assertEqual([row["title"] for row in groups["claim"]], ["미승인 결제가 발생했다고 주장함"])
        self.assertEqual(result["contact_information"], [])


if __name__ == "__main__":
    unittest.main()
